import asyncio

from langgraph.graph import StateGraph
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

from .nodes import *


class Engine:

	def __init__(self, api_key: str):

		self.llm = ChatOpenAI(model="gpt-4", api_key=api_key)
		self.interruption = False
		self.success = True
		self.cpm = False

		self.setup_prompts()
		self.setup_workflow()
		self.setup_auxiliary()

	def setup_workflow(self):

		self.workflow = StateGraph(State)
		self.workflow.set_entry_point("START")
		self.workflow.add_node("START", StartNode(self))
		self.workflow.add_node("NO_PRICE", NoPriceNode(self))
		self.workflow.add_node("PRICE_CPM", PriceCPMNode(self))
		self.workflow.add_node("PRICE_CPM_15", PriceCPM15Node(self))
		self.workflow.add_node("PRICE_CPM_CAP", PriceCPMCapNode(self))
		self.workflow.add_node("PRICE_FIX", PriceFixNode(self))
		self.workflow.add_node("PRICE_FIX_20", PriceFix20Node(self))
		self.workflow.add_node("PRICE_FIX_30", PriceFix30Node(self))
		self.workflow.add_node("END", EndNode(self))
		self.workflow.set_finish_point("END")

		self.app = self.workflow.compile(checkpointer=MemorySaver())

	def setup_prompts(self):

		self.prompt_find_views = PromptTemplate(
			input_variables=["text"],
			template=(
				"Analyze the following message and extract the minimum and maximum number of views (min_views and max_views) desired by the client. "
				"If a range is mentioned, use the lower bound as min_views and the upper bound as max_views. "
				"If only one number is mentioned, set min_views = max_views = that number. "
				"Ensure the response includes min_views and max_views as integers separated by space.\n\n"
				"Message: {text}\n\n"
				"Response (format: <int> <int>):"
			)
		)

		self.prompt_find_cpm = PromptTemplate(
			input_variables=["text"],
			template=(
				"Analyze the following message and extract the cost per mile rate (CPM) for advertisements. "
				"If the CPM is not explicitly mentioned in the message, return 0. "
				"Ensure the response is strictly an integer.\n\n"
				"Message: {text}\n\n"
				"Response:"
			)
		)

	def setup_auxiliary(self):

		async def find_data_views(text):

			message = HumanMessage(
				content = self.prompt_find_views.format(
					text = text
				)
			)
			response = (await self.llm.ainvoke(message.content)).content.strip()
			response = response.split()

			return response

		async def find_data_cpm(text):

			message = HumanMessage(
				content = self.prompt_find_cpm.format(
					text = text
				)
			)
			response = (await self.llm.ainvoke(message.content)).content.strip()
			
			return response

		self.find_data_views = find_data_views
		self.find_data_cpm = find_data_cpm

	async def query(self, state: State, user_id):
		initial_state = {
			'message': state.get('message'),
			'client_cpm': state.get('client_cpm'),
			'influencer_price': state.get('influencer_price'),
			'max_views': state.get('max_views'),
			'min_views': state.get('min_views')
		}

		config = {
			"configurable": {
				"thread_id": user_id
			}
		}

		if not self.interruption:
			self.interruption = True
			return await self.app.ainvoke(initial_state, config = config)

		return await self.app.ainvoke(Command(resume = initial_state), config = config)
