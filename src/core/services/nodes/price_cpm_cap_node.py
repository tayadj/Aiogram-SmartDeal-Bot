from typing import Literal

from langgraph.types import Command, interrupt
from langchain.schema import HumanMessage
from langchain.prompts import PromptTemplate

from .node import Node, State


class PriceCPMCapNode(Node):
    prompt_detect_behaviour_cpm_cap = PromptTemplate(
        input_variables=['text'],
        template=(
            "Analyze the following message to determine the response regarding the new maximum payout (cap) offer in the CPM collaboration. "
            "Based on the analysis, return one of the following options:\n"
            "- AGREEMENT: If the message indicates full agreement with the new maximum payout (cap).\n"
            "- LOW_CAP: If the message indicates dissatisfaction with the new maximum payout (cap).\n"
            "Message: {text}\n\n"
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

    async def __call__(self, state: State) -> Command[Literal['END', 'PRICE_FIX']]:
        response = interrupt({})
        state.update({'message': response.get('message', state['message'])})

        message = HumanMessage(
            content=self.prompt_detect_behaviour_cpm_cap.format(
                text=state.get("message")
            )
        )

        match (await self.engine.llm.ainvoke(message.content)).content.strip():

            case 'AGREEMENT':

                self.engine.cpm = True
                return Command(update=state, goto='END')

            case 'LOW_CAP':

                message = HumanMessage(
                    content=self.prompt_offer_fix_price.format(
                        fix_price=int(self._calc_cap(state)),
                        text=state.get('message')
                    )
                )
                text = (await self.engine.llm.ainvoke(message.content)).content.strip()
                state.update({'message': text, 'influencer_price': self._calc_cap(state)})

                return Command(update=state, goto='PRICE_FIX')