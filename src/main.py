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

	def __init__(self, settings):

		self.engine = core.services.Engine(api_key = settings.OPENAI_API_TOKEN.get_secret_value())
		self.bot = aiogram.Bot(token = settings.TELEGRAM_TOKEN.get_secret_value())
		self.dispatcher = aiogram.Dispatcher()

		self.handlers_setup()

	def handlers_setup(self):

		@self.dispatcher.message(aiogram.filters.Command('start'))
		async def handle_command_start(message: aiogram.types.Message, state: aiogram.fsm.context.FSMContext):

			await state.update_data(
				message = message.text,
				client_cpm = "0",
				influencer_price = "0",
				views = "0"
			)

			reflexion = await core.handlers.handle_command_start(message, state, self.engine)

		@self.dispatcher.message(aiogram.F.text)
		async def handle_message_text(message: aiogram.types.Message, state: aiogram.fsm.context.FSMContext):

			await state.update_data(
				message = message.text,
				client_cpm = "0",
				influencer_price = "0",
				views = "0"
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