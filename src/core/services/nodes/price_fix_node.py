from typing import Literal

from langgraph.types import Command, interrupt
from langchain.schema import HumanMessage
from langchain.prompts import PromptTemplate

from .node import Node, State


class PriceFixNode(Node):
    prompt_detect_behaviour_fix_price = PromptTemplate(
        input_variables=["text"],
        template=(
            "Analyze the following message to determine the response regarding the fixed-price collaboration offer. "
            "Based on the analysis, return one of the following options:\n"
            "- AGREEMENT: If the message indicates full agreement with the fixed-price terms.\n"
            "- LOW_FIX_PRICE: If the message indicates dissatisfaction with the fixed price or a desire for further negotiation.\n"
            "Message: {text}\n\n"
            "Response:"
        )
    )

    prompt_offer_fix_price_20 = PromptTemplate(
        input_variables=["original_price", "text", "new_fix_price"],
        template=(
            "Compose a professional and persuasive message to the influencer, offering a new fixed-price payment model with a 20% increase. "
            "Emphasize that this updated rate reflects their exceptional value and showcases a commitment to building a successful partnership. "
            "Clearly outline the new fixed price for the collaboration.\n\n"
            "Details:\n"
            "- Original Fixed Price: {original_price}\n"
            "- New Fixed Price (+20%): {new_fix_price}\n"
            "- Previous user's message: {text}\n\n"
            "Response:"
        )
    )

    async def __call__(self, state: State) -> Command[Literal['END', 'PRICE_FIX_20']]:

        response = interrupt({})
        state.update({'message': response.get('message', state['message'])})

        message = HumanMessage(
            content=self.prompt_detect_behaviour_fix_price.format(
                text=state.get("message")
            )
        )

        match (await self.engine.llm.ainvoke(message.content)).content.strip():

            case 'AGREEMENT':

                return Command(update=state, goto='END')

            case 'LOW_FIX_PRICE':

                message = HumanMessage(
                    content=self.prompt_offer_fix_price_20.format(
                        original_price=int(state.get('client_cpm')) / 4000 * (
                                    int(state.get('min_views')) + 3 * int(state.get('max_views'))),
                        text=state.get('message'),
                        new_fix_price=1.2 * int(self._calc_cap(state))
                    )
                )
                text = (await self.engine.llm.ainvoke(message.content)).content.strip()
                state.update({'message': text, 'influencer_price': str(1.2 * int(self._calc_cap(state)))})

                return Command(update=state, goto='PRICE_FIX_20')
