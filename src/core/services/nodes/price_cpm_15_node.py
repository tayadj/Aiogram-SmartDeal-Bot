from typing import Literal

from langgraph.types import Command, interrupt
from langchain.schema import HumanMessage
from langchain.prompts import PromptTemplate

from .node import Node, State


class PriceCPM15Node(Node):
    prompt_detect_behaviour_cpm_15 = PromptTemplate(
        input_variables=['text'],
        template=(
            "Analyze the following message to determine the response regarding the new CPM collaboration offer. "
            "Based on the analysis, return one of the following options:\n"
            "- AGREEMENT: If the message indicates full agreement with the new CPM terms, including the increased rate.\n"
            "- LOW_CPM: If the message indicates dissatisfaction with the new CPM rate, even after the increase.\n"
            "Message: {text}\n\n"
            "Response:"
        )
    )

    async def __call__(self, state: State) -> Command[Literal['END', 'PRICE_FIX']]:
        response = interrupt({})
        state.update({'message': response.get('message', state['message'])})

        message = HumanMessage(
            content=self.prompt_detect_behaviour_cpm_15.format(
                text=state.get("message")
            )
        )

        match (await self.engine.llm.ainvoke(message.content)).content.strip():

            case 'AGREEMENT':

                self.engine.cpm = True
                return Command(update=state, goto='END')

            case 'LOW_CPM':

                return Command(update=state, goto='PRICE_FIX')
