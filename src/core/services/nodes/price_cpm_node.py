from typing import Literal

from langgraph.types import Command, interrupt
from langchain.schema import HumanMessage
from langchain.prompts import PromptTemplate

from .node import Node, State


class PriceCPMNode(Node):
    prompt_detect_behaviour_cpm = PromptTemplate(
        input_variables=['text'],
        template=(
            "Analyze the following message to determine the response regarding CPM collaboration. "
            "Based on the analysis, return one of the following options:\n"
            "- AGREEMENT: If the message indicates full agreement with CPM terms.\n"
            "- LOW_CAP: If the message indicates dissatisfaction with the cap (maximum payout).\n"
            "- LOW_CPM: If the message indicates dissatisfaction with the CPM rate itself.\n"
            "- NO_CPM: If the message indicates the influencer completely rejects the CPM system.\n"
            "Message: {text}\n\n"
            "Response:"
        )
    )

    prompt_offer_cpm_15 = PromptTemplate(
        input_variables=["client_price", "cap", "text", "new_cpm"],
        template=(
            "Compose a professional and compelling message to the influencer, offering an increased payment based on the system's cost-per-mile (CPM) model. "
            "Highlight that this new rate includes a 15% increase in CPM to align better with their value and ensure a mutually beneficial partnership. "
            "Also, mention the updated maximum payout (cap) that they could receive for the integration.\n\n"
            "Details:\n"
            "- Original CPM Price: {client_price}\n"
            "- Increased CPM Price (+15%): {new_cpm}\n"
            "- Updated Maximum Payout (Cap): {cap}\n"
            "- Previous user's message: {text}\n\n"
            "Response:"
        )
    )

    prompt_offer_cpm_cap = PromptTemplate(
        input_variables=["client_price", "text", "new_cap"],
        template=(
            "Compose a professional and persuasive message to the influencer, offering a payment based on the system's cost-per-mile (CPM) model. "
            "Emphasize that the maximum payout (cap) has been increased by 30% to reflect their value and ensure a stronger collaboration. "
            "Highlight how this adjustment demonstrates the commitment to achieving a mutually beneficial partnership.\n\n"
            "Details:\n"
            "- Suggested CPM Price: {client_price}\n"
            "- Updated Maximum Payout (Cap +30%): {new_cap}\n"
            "- Previous user's message: {text}\n\n"
            "Response:"
        )
    )

    prompt_offer_fix_price = PromptTemplate(
        input_variables=["fix_price", "text"],
        template=(
            "Compose a professional and persuasive message to the influencer, offering a collaboration based on a fixed-price model. "
            "Highlight the advantages of this payment structure and emphasize that it reflects their value and ensures a reliable and transparent partnership. "
            "Clearly specify the fixed price for the collaboration.\n\n"
            "Details:\n"
            "- Fixed Price: {fix_price}\n"
            "- Previous user's message: {text}\n\n"
            "Response:"
        )
    )

    async def __call__(self, state: State) -> Command[Literal['END', 'PRICE_CPM_CAP', 'PRICE_CPM_15', 'PRICE_FIX']]:
        response = interrupt({})
        state.update({'message': response.get('message', state['message'])})

        message = HumanMessage(
            content=self.prompt_detect_behaviour_cpm.format(
                text=state.get("message")
            )
        )

        match (await self.engine.llm.ainvoke(message.content)).content.strip():

            case 'AGREEMENT':

                self.engine.cpm = True
                return Command(update=state, goto='END')

            case 'NO_CPM':

                message = HumanMessage(
                    content=self.prompt_offer_fix_price.format(
                        fix_price=self._calc_cap(state),
                        text=state.get('message')
                    )
                )
                text = (await self.engine.llm.ainvoke(message.content)).content.strip()
                state.update({'message': text})

                return Command(update=state, goto='PRICE_FIX')

            case 'LOW_CAP':

                message = HumanMessage(
                    content=self.prompt_offer_cpm_cap.format(
                        client_price=int(state.get('client_cpm')),
                        new_cap=1.3 * int(self._calc_cap(state)),
                        text=state.get('message')
                    )
                )
                text = (await self.engine.llm.ainvoke(message.content)).content.strip()
                state.update({'message': text})

                return Command(update=state, goto='PRICE_CPM_CAP')

            case 'LOW_CPM':

                message = HumanMessage(
                    content=self.prompt_offer_cpm_15.format(
                        client_price=int(state.get('client_cpm')),
                        cap=1.15 * int(self._calc_cap(state)),
                        text=state.get('message'),
                        new_cpm=int(state.get('client_cpm')) * 1.15
                    )
                )
                text = (await self.engine.llm.ainvoke(message.content)).content.strip()
                state.update(
                    {
                        'message': text,
                        'client_cpm': str(int(state.get('client_cpm')) * 1.15),
                        'influencer_price': str(1.15 * int(self._calc_cap(state)))
                    }
                )

                return Command(update=state, goto='PRICE_CPM_15')
            
            