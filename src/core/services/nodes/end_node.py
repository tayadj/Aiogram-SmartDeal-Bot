from langchain.schema import HumanMessage
from langchain.prompts import PromptTemplate

from .node import Node, State


class EndNode(Node):
    prompt_send_confirmation = PromptTemplate(
        input_variables=["text", "status", "price", "cpm"],
        template=(
            "Compose a professional and concise summary message as a manager's response to the following user interaction. "
            "Ensure the response clearly communicates the outcome of the discussion, including the decision and price in a structured and professional tone.\n\n"
            "Details:\n"
            "- Previous user's message: {text}\n"
            "- User agreement status: {status}\n"
            "- Final Agreed Price: {price}\n"
            "- Used system CPM: {cpm}\n\n"
            "Response:"
        )
    )

    async def __call__(self, state: State):
        message = HumanMessage(
            content=self.prompt_send_confirmation.format(
                text=state.get('message'),
                price=state.get('influencer_price'),
                status=self.engine.success,
                cpm=self.engine.cpm
            )
        )

        confirmation = (await self.engine.llm.ainvoke(message.content)).content.strip()

        return {'message': confirmation}
