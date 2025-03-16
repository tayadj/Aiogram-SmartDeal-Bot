import aiogram



async def handle_command_start(message: aiogram.types.Message, state: aiogram.fsm.context.FSMContext, engine):

    try:

        await message.answer("Hello, i'm smart deal bot, please send me your preferred cpm!")
        return {'handler': 'handle_command_start'}

    except Exception as exception:

        print(exception)
        await message.answer('Oops! Something is wrong.')