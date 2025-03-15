import asyncio
from langgraph.graph import StateGraph, END
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from typing import TypedDict



class Engine:
    first_query = False  # sos wtf
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

        workflow.add_edge("START", "PRICE_CPM")
        workflow.add_edge("PRICE_CPM", "END")

        self.app = workflow.compile(checkpointer=MemorySaver())
 
    async def _start_node(self, state: State):
        # without condition_edges!!! case if price indicated in message, but he higher than client_price

        prompt_find_price = PromptTemplate(
           input_variables = ["text"],
           template = "Find in this message price for advertisements and return integer, and if it's not there then return 0. Message: {text}\nPrice: "
        )

        message = HumanMessage(content=prompt_find_price.format(text = state.get("message")))
        influencer_price = (await self.llm.ainvoke(message.content)).content.strip()
        state.update({'influencer_price': influencer_price})

        prompt_offer_price = PromptTemplate(
            input_variables = ["client_price", "cap"],
            template = "Offer influencer purchase by system costs per mile, also add that this better matches the client's benchmarks, also mention the maximum amount (cap) that a blogger can receive for integration. Price {client_price}, Cap {cap}"
        )
        message_offer = HumanMessage(content=prompt_offer_price.format(
            client_price = (state.get("client_cpm")),
            cap = 12000 # get from State
        ))
        text = (await self.llm.ainvoke(message_offer.content)).content.strip()
        return {'message': text}

    async def _price_cpm_node(self, state: State):
        state = interrupt({
            "message": "Emprty"
        })  # equals value in resume (arg Command)

        prompt_find_price = PromptTemplate(
           input_variables = ["text"],
           template = "try to understand whether the blogger agrees to this system or not. if not, please state one of the reasons.: he doesn't like his cap or cpm. Message: {text}"
        )
        message = HumanMessage(content=prompt_find_price.format(text = state.get("message")))
        reason = (await self.llm.ainvoke(message.content)).content.strip()
        return {"message": reason}


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

        return state

    async def query(self, state, tg_id):

        state_data = await state.get_data()

        initial_state = {
            'message': state_data.get('message'),
            'client_cpm': state_data.get('client_cpm', 0),
            'influencer_price': state_data.get('influencer_price', 0),
            'views': state_data.get('views', 0)
        }
        config = {"configurable": {"thread_id": tg_id}}
        if not self.first_query:
            self.first_query = True
            return await self.app.ainvoke(initial_state, config=config)
        return await self.app.ainvoke(Command(resume=initial_state), config=config)

        # return should contain 'message' field for straightforward answer via bot
        # e.g. : {'message': 'example of message', ...}
