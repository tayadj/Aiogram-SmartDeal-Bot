import config
import core

import aiogram
import asyncio



class Bot():

	class UserState(aiogram.fsm.state.StatesGroup):

		message = aiogram.fsm.state.State()
		client_cpm = aiogram.fsm.state.State()
		influencer_price = aiogram.fsm.state.State()
		views = aiogram.fsm.state.State()
		min_views = aiogram.fsm.state.State()
		max_views = aiogram.fsm.state.State()

	def __init__(self, settings):

		self.engine = core.services.Engine(api_key = settings.OPENAI_API_TOKEN.get_secret_value())
		self.bot = aiogram.Bot(token = settings.TELEGRAM_TOKEN.get_secret_value())
		self.dispatcher = aiogram.Dispatcher()

		self.handlers_setup()
		self.commands_setup()

	def commands_setup(self):

		async def run():

			commands = [
				aiogram.types.BotCommand(command = '/start', description = 'Input user\'s metrics')
				aiogram.types.BotCommand(command = '/scenario', description = 'Influencer dialogue start')
			]
			await self.bot.set_my_commands(commands = commands)

		asyncio.create_task(run())

	def handlers_setup(self):

		@self.dispatcher.message(aiogram.filters.Command('start'))
		async def handle_command_start(message: aiogram.types.Message, state: aiogram.fsm.context.FSMContext):

			reflexion = await core.handlers.handle_command_start(message, state, self.engine)

			await state.set_state(self.UserState.client_cpm)

		@self.dispatcher.message(self.UserState.client_cpm)
		async def handle_input_cpm(message: aiogram.types.Message, state: aiogram.fsm.context.FSMContext):

			reflexion = await core.handlers.handle_input_cpm(message, state, self.engine)

			await state.set_state(self.UserState.views)

		@self.dispatcher.message(self.UserState.views)
		async def handle_input_views(message: aiogram.types.Message, state: aiogram.fsm.context.FSMContext):

			reflexion = await core.handlers.handle_input_views(message, state, self.engine)

			await state.set_state(None)

		@self.dispatcher.message(aiogram.filters.Command('scenario'))
		async def handle_command_scenario(message: aiogram.types.Message, state: aiogram.fsm.context.FSMContext):

			state_data = await state.get_data()

			await state.update_data(
				message = message.text,
				client_cpm = state_data.get("client_cpm"),
				influencer_price = state_data.get("influencer_price", "0"),
				max_views = state_data.get("max_views"),
				min_views = state_data.get("min_views")
			)
			reflexion = await core.handlers.handle_command_scenario(message, state, self.engine)

		@self.dispatcher.message(aiogram.F.text)
		async def handle_message_text(message: aiogram.types.Message, state: aiogram.fsm.context.FSMContext):

			await state.update_data(
				message = message.text
			)

			reflexion = await core.handlers.handle_message_text(message, state, self.engine)

	async def run(self):

		await self.dispatcher.start_polling(self.bot)



if __name__ == '__main__':

	async def main():

		settings = config.Settings()
		bot = Bot(settings)
		await bot.run()

	asyncio.run(main())
