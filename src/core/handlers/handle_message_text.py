import aiogram
import asyncio



async def handle_message_text(message: aiogram.types.Message, state: aiogram.fsm.context.FSMContext, engine):

	try:

		await message.answer('Hi!')

		# deal-strategy implementation

		return {'handler': 'handle_message_text'}

	except Exception as exception:

		await message.answer('Oops! Something is wrong.')