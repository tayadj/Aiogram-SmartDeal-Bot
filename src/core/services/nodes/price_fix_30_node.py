from typing import Literal

from langgraph.types import Command, interrupt
from langchain.schema import HumanMessage
from langchain.prompts import PromptTemplate

from .node import Node, State


class PriceFix30Node(Node):
    prompt_detect_behaviour_fix_price_30 = PromptTemplate(
        input_variables=['text'],
        template=(
            "Analyze the following message to determine the response regarding the new fixed price offer with a 30% increase. "
            "Based on the analysis, return one of the following options:\n"
            "- AGREEMENT: If the message indicates full agreement with the new fixed price terms, including the 30% increase.\n"
            "- LOW_FIX_PRICE: If the message indicates dissatisfaction with the new fixed price, even after the increase.\n"
            "Message: {text}\n\n"
            "Response:"
        )
    )

    async def __call__(self, state: State) -> Command[Literal['END']]:

        response = interrupt({})
        state.update({'message': response.get('message', state['message'])})

        message = HumanMessage(
            content=self.prompt_detect_behaviour_fix_price_30.format(
                text=state.get("message")
            )
        )

        match (await self.engine.llm.ainvoke(message.content)).content.strip():

            case 'AGREEMENT':
                return Command(update=state, goto='END')

            case 'LOW_FIX_PRICE':
                self.engine.success = False
                return Command(update=state, goto='END')
