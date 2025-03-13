import config
import core

import aiogram
import asyncio



class Bot():

	def __init__(self, settings):

		#self.engine = core.services.Engine()
		self.bot = aiogram.Bot(token = settings.TELEGRAM_TOKEN.get_secret_value())
		self.dispatcher = aiogram.Dispatcher()

		self.handlers_setup()

	def handlers_setup(self):

		@self.dispatcher.message(aiogram.filters.Command('start'))
		async def handle_command_start(message: aiogram.types.Message):

			reflexion = await core.handlers.handle_command_start(message)

		@self.dispatcher.message(aiogram.F.text)
		async def handle_message_text(message: aiogram.types.Message):
		#param to add: engine

			reflexion = await core.handlers.handle_message_text(message)

	async def run(self):

		await self.dispatcher.start_polling(self.bot)



if __name__ == '__main__':

	async def main():

		settings = config.Settings()
		bot = Bot(settings)
		await bot.run()

	asyncio.run(main())