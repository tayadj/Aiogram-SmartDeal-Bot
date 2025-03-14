import aiogram



async def handle_command_start(message: aiogram.types.Message, state: aiogram.fsm.context.FSMContext, engine):

	try:

		await message.answer('Hi!')

		return {'handler': 'handle_command_start'}

	except Exception as exception:

		await message.answer('Oops! Something is wrong.')