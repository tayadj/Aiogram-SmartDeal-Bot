from typing import Literal

from langgraph.types import Command, interrupt
from langchain.schema import HumanMessage
from langchain.prompts import PromptTemplate

from .node import Node, State


class PriceFix20Node(Node):
    prompt_detect_behaviour_fix_price_20 = PromptTemplate(
        input_variables=['text'],
        template=(
            "Analyze the following message to determine the response regarding the new fixed price offer with a 20% increase. "
            "Based on the analysis, return one of the following options:\n"
            "- AGREEMENT: If the message indicates full agreement with the new fixed price terms, including the 20% increase.\n"
            "- LOW_FIX_PRICE: If the message indicates dissatisfaction with the new fixed price, even after the increase.\n"
            "Message: {text}\n\n"
            "Response:"
        )
    )

    prompt_offer_fix_price_30 = PromptTemplate(
        input_variables=["original_price", "text", "new_fix_price"],
        template=(
            "Compose a professional and compelling message to the influencer, offering a new fixed-price payment model with a 30% increase. "
            "Highlight that this increased rate reflects their tremendous value and reinforces the commitment to a strong and mutually beneficial collaboration. "
            "Provide a clear breakdown of the new fixed price for the partnership.\n\n"
            "Details:\n"
            "- Original Fixed Price: {original_price}\n"
            "- New Fixed Price (+30%): {new_fix_price}\n"
            "- Previous user's message: {text}\n\n"
            "Response:"
        )
    )

    async def __call__(self, state: State) -> Command[Literal['END', 'PRICE_FIX_30']]:

        response = interrupt({})
        state.update({'message': response.get('message', state['message'])})

        message = HumanMessage(
            content=self.prompt_detect_behaviour_fix_price_20.format(
                text=state.get("message")
            )
        )

        match (await self.engine.llm.ainvoke(message.content)).content.strip():

            case 'AGREEMENT':

                return Command(update=state, goto='END')

            case 'LOW_FIX_PRICE':

                message = HumanMessage(
                    content=self.prompt_offer_fix_price_30.format(
                        original_price=int(self._calc_cap(state)),
                        text=state.get('message'),
                        new_fix_price=1.3 * int(self._calc_cap(state)),
                    )
                )
                text = (await self.engine.llm.ainvoke(message.content)).content.strip()
                state.update({'message': text, 'influencer_price': str(1.3 * int(self._calc_cap(state)))})

                return Command(update=state, goto='PRICE_FIX_30')
