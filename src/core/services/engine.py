import asyncio
from langgraph.graph import StateGraph, END
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
from langchain_openai import ChatOpenAI
from typing import TypedDict



class Engine:

    class State(TypedDict):

        message: str
        client_cpm: str
        influencer_price: str
        views: str

    def __init__(self, api_key: str):

        self.llm = ChatOpenAI(model="gpt-4", api_key=api_key)

        self.setup_engine()

    def setup_engine(self):

        workflow = StateGraph(self.State)

        workflow.set_entry_point("START")
        workflow.add_node("START", self._start_node)
        workflow.add_node("PRICE_CPM", self._price_cpm_node)
        workflow.add_node("PRICE_CPM_15", self._price_cpm_15_node)
        workflow.add_node("PRICE_CPM_CAP", self._price_cpm_cap_node)
        workflow.add_node("PRICE_FIX", self._price_fix_node)
        workflow.add_node("PRICE_FIX_20", self._price_fix_20_node)
        workflow.add_node("PRICE_FIX_30", self._price_fix_30_node)
        workflow.add_node("END", self._end_node)
        workflow.set_finish_point("END")

        workflow.add_edge("START", "END")

        self.app = workflow.compile()
 
    async def _start_node(self, state: State):

        prompt = PromptTemplate(
           input_variables = ["text"],
           template = "Find in this message price for advertisements and return integer, and if it's not there then return 0. Message: {text}\nPrice: "
        )

        message = HumanMessage(content=prompt.format(text = state.get("message")))
        influencer_price = (await self.llm.ainvoke(message.content)).content.strip()

        return {'influencer_price': influencer_price, 'message': 'example message'}

    async def _price_cpm_node(self, state: State):

        pass

    async def _price_cpm_15_node(self, state: State):

        pass

    async def _price_cpm_cap_node(self, state: State):

        pass

    async def _price_fix_node(self, state: State):

        pass

    async def _price_fix_20_node(self, state: State):

        pass

    async def _price_fix_30_node(self, state: State):

        pass

    async def _end_node(self, state: State):

        return {'message': 'example message'}

    async def query(self, state):

        state_data = await state.get_data()

        initial_state = {
            message: state_data.get('message'),
            client_cpm: state_data.get('client_cpm', 0),
            influencer_price: state_data.get('influencer_price', 0),
            views: state_data.get('views', 0)
        }

        return await self.app.ainvoke(initial_state)

        # return should contain 'message' field for straightforward answer via bot
        # e.g. : {'message': 'example of message', ...}
