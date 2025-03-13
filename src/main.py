import config
import core

import aiogram
import asyncio



class Bot():

	def __init__(self, settings):

		self.bot = aiogram.Bot(token = settings.TELEGRAM_TOKEN.get_secret_value())
		self.dispatcher = aiogram.Dispatcher()

		self.handlers_setup()

	def handlers_setup(self):

		@self.dispatcher.message(aiogram.filters.Command('start'))
		async def handle_command_start(message: aiogram.types.Message):

			reflexion = await core.handlers.handle_command_start(message)

	async def run(self):

		await self.dispatcher.start_polling(self.bot)



if __name__ == '__main__':

	async def main():

		settings = config.Settings()
		bot = Bot(settings)
		await bot.run()

	asyncio.run(main())