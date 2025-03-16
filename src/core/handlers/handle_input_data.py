import aiogram


async def handle_client_cpm(message: aiogram.types.Message, state: aiogram.fsm.context.FSMContext, engine):
    try:
        await state.update_data(client_cpm=message.text)

        await message.answer("Nice, can you send preferred min-max views?")
        return {'handler': 'handle_cpm'}

    except Exception as exception:
        print(exception)
        await message.answer('Oops! Something is wrong.')


async def handle_views(message: aiogram.types.Message, state: aiogram.fsm.context.FSMContext, engine):
    try:
        min_views, max_views = message.text.split("-")
        await state.update_data(min_views=min_views, max_views=max_views)

        await message.answer(f"Perfect, your input data {await state.get_data()}, type /scenario for start a dialogue")
        return {'handler': 'handle_views'}

    except Exception as exception:
        print(exception)
        await message.answer('Oops! Something is wrong.')
