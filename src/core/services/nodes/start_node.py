from typing import Literal

from langgraph.types import Command
from langchain.schema import HumanMessage
from langchain.prompts import PromptTemplate

from .node import Node, State


class StartNode(Node):
    prompt_find_price = PromptTemplate(
        input_variables=["text"],
        template=(
            "Analyze the following message and extract the price for advertisements. "
            "If the price is not explicitly mentioned in the message, return 0. "
            "Ensure the response is strictly an integer.\n\n"
            "Message: {text}\n\n"
            "Response:"
        )
    )

    prompt_no_price = PromptTemplate(
        input_variables=["text"],
        template=(
            "Analyze the following message and compose a professional and concise summary message as a manager's response to the following user interaction. "
            "Previous message didn't contain the price for collaboration, you should ask a user to explicitly mention the price for collaboration.\n\n"
            "Message: {text}\n\n"
            "Response:"
        )
    )

    prompt_offer_cpm = PromptTemplate(
        input_variables=["client_price", "cap", 'text'],
        template=(
            "Compose a professional and persuasive message to the influencer, offering a payment based on the system's cost-per-mile (CPM) model. "
            "Highlight that this pricing structure aligns better with the client's performance benchmarks. "
            "Make sure to include the maximum payout (cap) that the influencer could receive for the integration.\n\n"
            "Details:\n"
            "- Suggested CPM Price: {client_price}\n"
            "- Maximum Payout (Cap): {cap}\n"
            "- Previous user's message: {text}\n\n"
            "Response:"
        )
    )

    async def __call__(self, state: State) -> Command[Literal['END', 'NO_PRICE', 'PRICE_CPM']]:

        message = HumanMessage(
            content=self.prompt_find_price.format(
                text=state.get('message')
            )
        )
        influencer_price = (await self.engine.llm.ainvoke(message.content)).content.strip()
        state.update({'influencer_price': influencer_price})

        if influencer_price == '0':

            message = HumanMessage(
                content=self.prompt_no_price.format(
                    text=state.get('message')
                )
            )
            text = (await self.engine.llm.ainvoke(message.content)).content.strip()
            state.update({'message': text})

            return Command(update=state, goto='NO_PRICE')

        else:

            match self.condition_start_price(state):

                case True:

                    return Command(update=state, goto='END')

                case False:

                    message = HumanMessage(
                        content=self.prompt_offer_cpm.format(
                            client_price=int(state.get('client_cpm')),
                            cap=self._calc_cap(state),
                            text=state.get('message')
                        )
                    )
                    text = (await self.engine.llm.ainvoke(message.content)).content.strip()
                    state.update({'message': text, 'influencer_price': self._calc_cap(state)})

                    return Command(update=state, goto='PRICE_CPM')
