import aiogram



async def handle_command_scenario(message: aiogram.types.Message, state: aiogram.fsm.context.FSMContext, engine):

	try:

		await message.answer("""
		I'm Dasha from Dream X-Company, where we connect outstanding creators like you with top-tier brands for impactful collaborations. Hope this message finds you well!

		We've been following your YouTube journey, and are impressed by your unique ability to connect with your audience. That's why we're thrilled to pitch with you an exciting partnership opportunity with Dream X-Company!

		Deliverables:

		- A 60-90 second YouTube integration within 0:45-1:30 of the video.
		- A tracking link included in both the description box and a pinned comment.
		- A QR code placed during the ad time.

		Launch Window: March 2025

		If you're interested, please let us know your rate for the specified format and which release dates work for you.

		Looking forward to hearing your thoughts.
		""")

		return {'handler': 'handle_command_scenario'}

	except Exception as exception:

		await message.answer('Oops! Something is wrong.')