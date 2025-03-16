import asyncio
from langgraph.graph import StateGraph
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
		min_views: str
		max_views: str

	def __init__(self, api_key: str):

		self.llm = ChatOpenAI(model="gpt-4", api_key=api_key)
		self.interruption = False
		self.success = True
		self.cpm = False

		self._calc_cap = lambda state: str(int(int(state.get('client_cpm')) / 4000 * (int(state.get('min_views')) + 3 * int(state.get('max_views')))))

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

		self.prompt_find_views = PromptTemplate(
			input_variables=["text"],
			template=(
				"Analyze the following message and extract the minimum and maximum number of views (min_views and max_views) desired by the client. "
				"If a range is mentioned, use the lower bound as min_views and the upper bound as max_views. "
				"If only one number is mentioned, set min_views = max_views = that number. "
				"Ensure the response includes min_views and max_views as integers.\n\n"
				"Message: {text}\n\n"
				"Response (format: <int>,<int>):"
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

		self.prompt_find_price = PromptTemplate(
			input_variables=["text"],
			template=(
				"Analyze the following message and extract the price for advertisements. "
				"If the price is not explicitly mentioned in the message, return 0. "
				"Ensure the response is strictly an integer.\n\n"
				"Message: {text}\n\n"
				"Response:"
			)
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

		self.prompt_detect_behaviour_cpm_cap = PromptTemplate(
			input_variables=['text'],
			template=(
				"Analyze the following message to determine the response regarding the new maximum payout (cap) offer in the CPM collaboration. "
				"Based on the analysis, return one of the following options:\n"
				"- AGREEMENT: If the message indicates full agreement with the new maximum payout (cap).\n"
				"- LOW_CAP: If the message indicates dissatisfaction with the new maximum payout (cap).\n"
				"Message: {text}\n\n"
				"Response:"
			)
		)

		self.prompt_detect_behaviour_fix_price = PromptTemplate(
			input_variables=["text"],
			template=(
				"Analyze the following message to determine the response regarding the fixed-price collaboration offer. "
				"Based on the analysis, return one of the following options:\n"
				"- AGREEMENT: If the message indicates full agreement with the fixed-price terms.\n"
				"- LOW_FIX_PRICE: If the message indicates dissatisfaction with the fixed price or a desire for further negotiation.\n"
				"Message: {text}\n\n"
				"Response:"
			)
		)

		self.prompt_detect_behaviour_fix_price_20 = PromptTemplate(
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

		self.prompt_detect_behaviour_fix_price_30 = PromptTemplate(
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

		self.prompt_offer_cpm_cap = PromptTemplate(
			input_variables=["client_price", "text", "new_cap"],
			template=(
				"Compose a professional and persuasive message to the influencer, offering a payment based on the system's cost-per-mile (CPM) model. "
				"Emphasize that the maximum payout (cap) has been increased by 30% to reflect their value and ensure a stronger collaboration. "
				"Highlight how this adjustment demonstrates the commitment to achieving a mutually beneficial partnership.\n\n"
				"Details:\n"
				"- Suggested CPM Price: {client_price}\n"
				"- Updated Maximum Payout (Cap +30%): {new_cap}\n"
				"- Previous user's message: {text}\n\n"
				"Response:"
			)
		)

		self.prompt_offer_fix_price = PromptTemplate(
			input_variables=["fix_price", "text"],
			template=(
				"Compose a professional and persuasive message to the influencer, offering a collaboration based on a fixed-price model. "
				"Highlight the advantages of this payment structure and emphasize that it reflects their value and ensures a reliable and transparent partnership. "
				"Clearly specify the fixed price for the collaboration.\n\n"
				"Details:\n"
				"- Fixed Price: {fix_price}\n"
				"- Previous user's message: {text}\n\n"
				"Response:"
			)
		)

		self.prompt_offer_fix_price_20 = PromptTemplate(
			input_variables=["original_price", "text", "new_fix_price"],
			template=(
				"Compose a professional and persuasive message to the influencer, offering a new fixed-price payment model with a 20% increase. "
				"Emphasize that this updated rate reflects their exceptional value and showcases a commitment to building a successful partnership. "
				"Clearly outline the new fixed price for the collaboration.\n\n"
				"Details:\n"
				"- Original Fixed Price: {original_price}\n"
				"- New Fixed Price (+20%): {new_fix_price}\n"
				"- Previous user's message: {text}\n\n"
				"Response:"
			)
		)

		self.prompt_offer_fix_price_30 = PromptTemplate(
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

		self.prompt_send_confirmation = PromptTemplate(
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

	def setup_conditions(self):

		def condition_start_price(state):

			client_cpm = int(state.get("client_cpm", 0))
			min_views = int(state.get("min_views", 0))
			influencer_price = int(state.get("influencer_price", 0))

			return influencer_price <= (client_cpm * min_views) / 1000

		self.condition_start_price = condition_start_price
			


	async def _start_node(self, state: State) -> Command[Literal['END', 'PRICE_CPM']]: #NO_PRICE, END, PRICE_CPM

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
						cap = self._calc_cap(state),
						text = state.get('message')
					)
				)
				text = (await self.llm.ainvoke(message.content)).content.strip()
				state.update({'message': text, 'influencer_price': self._calc_cap(state)})
				return Command(update = state, goto = 'PRICE_CPM')

	async def _price_cpm_node(self, state: State) -> Command[Literal['END', 'PRICE_CPM_CAP', 'PRICE_CPM_15', 'PRICE_FIX']]:

		response = interrupt({})
		state.update({'message': response.get('message', state['message'])})

		message = HumanMessage(
			content = self.prompt_detect_behaviour_cpm.format(
				text = state.get("message")
			)
		)

		match (await self.llm.ainvoke(message.content)).content.strip():

			case 'AGREEMENT':

				self.cpm = True
				return Command(update = state, goto = 'END')

			case 'NO_CPM':

				message = HumanMessage(
					content = self.prompt_offer_fix_price.format(
						fix_price = self._calc_cap(state),
						text = state.get('message')
					)
				)
				text = (await self.llm.ainvoke(message.content)).content.strip()
				state.update({'message': text})

				return Command(update = state, goto = 'PRICE_FIX')

			case 'LOW_CAP':

				message = HumanMessage(
					content = self.prompt_offer_cpm_cap.format(
						client_price = int(state.get('client_cpm')),
						new_cap = 1.3 * int(self._calc_cap(state)),
						text = state.get('message')
					)
				)
				text = (await self.llm.ainvoke(message.content)).content.strip()
				state.update({'message': text})

				return Command(update = state, goto = 'PRICE_CPM_CAP')

			case 'LOW_CPM':

				message = HumanMessage(
					content = self.prompt_offer_cpm_15.format(
						client_price = int(state.get('client_cpm')),
						cap = 1.15 * int(self._calc_cap(state)),
						text = state.get('message'),
						new_cpm = int(state.get('client_cpm')) * 1.15
					)
				)
				text = (await self.llm.ainvoke(message.content)).content.strip()
				state.update(
					{
						'message': text,
						'client_cpm': str(int(state.get('client_cpm')) * 1.15),
						'influencer_price': str(1.15 * int(self._calc_cap(state)))
					}
				)

				return Command(update = state, goto = 'PRICE_CPM_15')

	async def _price_cpm_15_node(self, state: State) -> Command[Literal['END', 'PRICE_FIX']]:

		response = interrupt({})
		state.update({'message': response.get('message', state['message'])})

		message = HumanMessage(
			content = self.prompt_detect_behaviour_cpm_15.format(
				text = state.get("message")
			)
		)

		match (await self.llm.ainvoke(message.content)).content.strip():

			case 'AGREEMENT':

				self.cpm = True
				return Command(update = state, goto = 'END')

			case 'LOW_CPM':

				return Command(update = state, goto = 'PRICE_FIX')

	async def _price_cpm_cap_node(self, state: State) -> Command[Literal['END', 'PRICE_FIX']]:

		response = interrupt({})
		state.update({'message': response.get('message', state['message'])})

		message = HumanMessage(
			content = self.prompt_detect_behaviour_cpm_cap.format(
				text = state.get("message")
			)
		)

		match (await self.llm.ainvoke(message.content)).content.strip():

			case 'AGREEMENT':

				self.cpm = True
				return Command(update = state, goto = 'END')

			case 'LOW_CAP':

				message = HumanMessage(
					content = self.prompt_offer_fix_price.format(
						fix_price = int(self._calc_cap(state)),
						text = state.get('message')
					)
				)
				text = (await self.llm.ainvoke(message.content)).content.strip()
				state.update({'message': text, 'influencer_price': self._calc_cap(state)})

				return Command(update = state, goto = 'PRICE_FIX')

	async def _price_fix_node(self, state: State) -> Command[Literal['END', 'PRICE_FIX_20']]:

		response = interrupt({})
		state.update({'message': response.get('message', state['message'])})

		message = HumanMessage(
			content = self.prompt_detect_behaviour_fix_price.format(
				text = state.get("message")
			)
		)

		match (await self.llm.ainvoke(message.content)).content.strip():

			case 'AGREEMENT':

				return Command(update = state, goto = 'END')

			case 'LOW_FIX_PRICE':

				message = HumanMessage(
					content = self.prompt_offer_fix_price_20.format(
						original_price = int(state.get('client_cpm')) / 4000 * (int(state.get('min_views')) + 3*int(state.get('max_views'))),
						text = state.get('message'),
						new_fix_price = 1.2*int(self._calc_cap(state))
					)
				)
				text = (await self.llm.ainvoke(message.content)).content.strip()
				state.update({'message': text, 'influencer_price': str(1.2*int(self._calc_cap(state)))})

				return Command(update = state, goto = 'PRICE_FIX_20')

	async def _price_fix_20_node(self, state: State) -> Command[Literal['END', 'PRICE_FIX_30']]:

		response = interrupt({})
		state.update({'message': response.get('message', state['message'])})

		message = HumanMessage(
			content = self.prompt_detect_behaviour_fix_price_20.format(
				text = state.get("message")
			)
		)

		match (await self.llm.ainvoke(message.content)).content.strip():

			case 'AGREEMENT':

				return Command(update = state, goto = 'END')

			case 'LOW_FIX_PRICE':

				message = HumanMessage(
					content = self.prompt_offer_fix_price_30.format(
						original_price = int(self._calc_cap(state)),
						text = state.get('message'),
						new_fix_price = 1.3*int(self._calc_cap(state)),
					)
				)
				text = (await self.llm.ainvoke(message.content)).content.strip()
				state.update({'message': text, 'influencer_price': str(1.3*int(self._calc_cap(state)))})

				return Command(update = state, goto = 'PRICE_FIX_30')

	async def _price_fix_30_node(self, state: State) -> Command[Literal['END']]:

		response = interrupt({})
		state.update({'message': response.get('message', state['message'])})

		message = HumanMessage(
			content = self.prompt_detect_behaviour_fix_price_30.format(
				text = state.get("message")
			)
		)

		match (await self.llm.ainvoke(message.content)).content.strip():

			case 'AGREEMENT':

				return Command(update = state, goto = 'END')

			case 'LOW_FIX_PRICE':
			
				self.success = False

				return Command(update = state, goto = 'END')

	async def _end_node(self, state: State):

		print(state)

		message = HumanMessage(
			content = self.prompt_send_confirmation.format(
				text = state.get('message'),
				price = state.get('influencer_price'),
				status = self.success,
				cpm = self.cpm
			)
		)
		
		confirmation = (await self.llm.ainvoke(message.content)).content.strip()

		return {'message': confirmation}

	async def query(self, state, user_id):

		state_data = await state.get_data()

		initial_state = {
			'message': state_data.get('message'),
			'client_cpm': state_data.get('client_cpm'),
			'influencer_price': state_data.get('influencer_price'),
			'max_views': state_data.get('max_views'),
			'min_views': state_data.get('min_views')
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