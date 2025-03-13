import asyncio
from langgraph.graph import StateGraph, END
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
from langchain_openai import ChatOpenAI
from typing import TypedDict


# exact same aiogram.FSMContext
class State(TypedDict):
    message: str
    client_cpm: str
    influencer_price: str
    views: str


class Engine:
    def __init__(self, api_key: str):
        self.llm = ChatOpenAI(model="gpt-4", api_key=api_key)
        self.setup_engine()

    def setup_engine(self):
        workflow = StateGraph(State)
        workflow.add_node("START", self._start_node)
        workflow.set_entry_point("START")
        workflow.add_edge("START", END)
        self.app = workflow.compile()

    async def _start_node(self, state: State):
        prompt = PromptTemplate(
           input_variables=["text"],
           template="Find in this message price for advertisements and return integer, and if it's not there then return 0. Message: {text}\nPrice: "
        )
        message = HumanMessage(content=prompt.format(text=state["message"]))
        influencer_price = (await self.llm.ainvoke(message.content)).content.strip()
        return {"influencer_price": influencer_price}

    async def query(self, text: str):
        return await self.app.ainvoke({"message": text, "client_cpm": 0, "influencer_price": 0, "views": ""})
