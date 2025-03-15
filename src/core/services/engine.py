import asyncio
from langgraph.graph import StateGraph, END
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from typing import TypedDict, Literal



class Engine:

	class State(TypedDict):

		message: str
		client_cpm: str
		influencer_price: str
		views: str

	def __init__(self, api_key: str):

		self.llm = ChatOpenAI(model="gpt-4", api_key=api_key)
		self.interruption = False

		self.setup_conditions()
		self.setup_prompts()
		self.setup_workflow()

	def setup_workflow(self):

		self.workflow = StateGraph(self.State)

		self.workflow.set_entry_point("START")
		self.workflow.add_node("START", self._start_node)
		self.workflow.add_node("PRICE_CPM", self._price_cpm_node)
		self.workflow.add_node("PRICE_CPM_15", self._price_cpm_15_node)
		self.workflow.add_node("PRICE_CPM_CAP", self._price_cpm_cap_node)
		self.workflow.add_node("PRICE_FIX", self._price_fix_node)
		self.workflow.add_node("PRICE_FIX_20", self._price_fix_20_node)
		self.workflow.add_node("PRICE_FIX_30", self._price_fix_30_node)
		self.workflow.add_node("END", self._end_node)
		self.workflow.set_finish_point("END")

		self.app = self.workflow.compile(checkpointer=MemorySaver())

	def setup_prompts(self):

		self.prompt_find_price = PromptTemplate(
			input_variables = ['text'],
			template = 'Extract the price for advertisements from the message. If not found, return 0. Message: {text}. Response must be as an integer.'
		)

		self.prompt_detect_behaviour_cpm = PromptTemplate(
			input_variables=['text'],
			template=(
				"Analyze the following message to determine the response regarding CPM collaboration. "
				"Based on the analysis, return one of the following options:\n"
				"- AGREEMENT: If the message indicates full agreement with CPM terms.\n"
				"- LOW_CAP: If the message indicates dissatisfaction with the cap (maximum payout).\n"
				"- LOW_CPM: If the message indicates dissatisfaction with the CPM rate itself.\n"
				"- NO_CPM: If the message indicates the influencer completely rejects the CPM system.\n"
				"Message: {text}\n\n"
				"Response:"
			)
		)

		self.prompt_detect_behaviour_cpm_15 = PromptTemplate(
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

		self.prompt_offer_cpm = PromptTemplate(
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

		self.prompt_offer_cpm_15 = PromptTemplate(
			input_variables=["client_price", "cap", "text", "new_cpm"],
			template=(
				"Compose a professional and compelling message to the influencer, offering an increased payment based on the system's cost-per-mile (CPM) model. "
				"Highlight that this new rate includes a 15% increase in CPM to align better with their value and ensure a mutually beneficial partnership. "
				"Also, mention the updated maximum payout (cap) that they could receive for the integration.\n\n"
				"Details:\n"
				"- Original CPM Price: {client_price}\n"
				"- Increased CPM Price (+15%): {new_cpm}\n"
				"- Updated Maximum Payout (Cap): {cap}\n"
				"- Previous user's message: {text}\n\n"
				"Response:"
			)
		)

		self.prompt_send_confirmation = PromptTemplate(
			input_variables = ['text'],
			template = 'Send a confirmational message of agreement as a manager\'s answer to the next message: {text}'
		)

	def setup_conditions(self):

		def condition_start_price(state):

			client_cpm = int(state.get("client_cpm", 0))
			views = int(state.get("views", 0))
			influencer_price = int(state.get("influencer_price", 0))

			return influencer_price <= (client_cpm * views) / 1000

		self.condition_start_price = condition_start_price
			


	async def _start_node(self, state: State) -> Command[Literal['END', 'PRICE_CPM']]:

		print("_start_node")

		message = HumanMessage(
			content = self.prompt_find_price.format(
				text = state.get('message')
			)
		)
		influencer_price = (await self.llm.ainvoke(message.content)).content.strip()
		state.update({'influencer_price': influencer_price})

		match self.condition_start_price(state):

			case True:

				return Command(update = state, goto = 'END')

			case False:

				message = HumanMessage(
					content = self.prompt_offer_cpm.format(
						client_price = int(state.get('client_cpm')),
						cap = int(state.get('client_cpm')) * int(state.get('views')) * 1.5 / 1000, # true formula should be (CPM*(((min views + max views) / 2) + max views)/2 ) / 1000
						text = state.get('message')
					)
				)
				text = (await self.llm.ainvoke(message.content)).content.strip()
				state.update({'message': text})

				return Command(update = state, goto = 'PRICE_CPM')

	async def _price_cpm_node(self, state: State) -> Command[Literal['END', 'PRICE_CPM_CAP', 'PRICE_CPM_15', 'PRICE_FIX']]:

		print("_price_cpm_node")

		response = interrupt({})
		state.update({'message': response.get('message', state['message'])})

		message = HumanMessage(
			content = self.prompt_detect_behaviour_cpm.format(
				text = state.get("message")
			)
		)

		match (await self.llm.ainvoke(message.content)).content.strip():

			case 'AGREEMENT':

				return Command(update = state, goto = 'END')

			case 'NO_CPM':

				return Command(update = state, goto = 'PRICE_FIX')

			case 'LOW_CAP':

				return Command(update = state, goto = 'PRICE_CPM_CAP')

			case 'LOW_CPM':

				message = HumanMessage(
					content = self.prompt_offer_cpm_15.format(
						client_price = int(state.get('client_cpm')),
						cap = int(state.get('client_cpm')) * 1.15 * int(state.get('views')) * 1.5 / 1000, # true formula should be (CPM*(((min views + max views) / 2) + max views)/2 ) / 1000
						text = state.get('message'),
						new_cpm = int(state.get('client_cpm')) * 1.15,
					)
				)
				text = (await self.llm.ainvoke(message.content)).content.strip()
				state.update({'message': text})

				return Command(update = state, goto = 'PRICE_CPM_15')

	async def _price_cpm_15_node(self, state: State):

		print("_price_cpm_15_node")

		response = interrupt({})
		state.update({'message': response.get('message', state['message'])})

		message = HumanMessage(
			content = self.prompt_detect_behaviour_cpm_15.format(
				text = state.get("message")
			)
		)

		match (await self.llm.ainvoke(message.content)).content.strip():

			case 'AGREEMENT':

				return Command(update = state, goto = 'END')

			case 'LOW_CPM':

				return Command(update = state, goto = 'PRICE_FIX')


	async def _price_cpm_cap_node(self, state: State):

		print("_price_cpm_cap_node")

	async def _price_fix_node(self, state: State):

		print("_price_fix_node")

	async def _price_fix_20_node(self, state: State):

		print("_price_fix_20_node")

	async def _price_fix_30_node(self, state: State):

		print("_price_fix_30_node")

	async def _end_node(self, state: State):

		print("_end_node")

		message = HumanMessage(
			content = self.prompt_send_confirmation.format(
				text = state.get('message')
			)
		)
		
		confirmation = (await self.llm.ainvoke(message.content)).content.strip()

		return {'message': confirmation}



	async def query(self, state, tg_id):

		state_data = await state.get_data()

		initial_state = {
			'message': state_data.get('message'),
			'client_cpm': state_data.get('client_cpm'),
			'influencer_price': state_data.get('influencer_price'),
			'views': state_data.get('views')
		}

		config = {
			"configurable": {
				"thread_id": tg_id
			}
		}

		if not self.interruption:

			self.interruption = True
			return await self.app.ainvoke(initial_state, config = config)

		return await self.app.ainvoke(Command(resume = initial_state), config = config)