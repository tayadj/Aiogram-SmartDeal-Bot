import aiogram
import asyncio



async def handle_message_text(message: aiogram.types.Message, state: aiogram.fsm.context.FSMContext, engine):

	try:
		state_data = await state.get_data()
		response = await engine.query(state_data, message.from_user.id)
		await message.answer(response.get('message', '__no_message__'))

		return {'handler': 'handle_message_text'}

	except Exception as exception:

		print(exception)
		await message.answer('Oops! Something is wrong.')