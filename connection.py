from aiogram import Bot, Dispatcher, types
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils import executor
from aiogram.dispatcher.filters import Text


API_TOKEN = "8197123228:AAEzJWUr-zSYJkzAn-Xo9fuEXtHB_xSi3zk"

# Initialize the bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Store the admin ID (replace with your Telegram ID)
ADMIN_ID = 1057648078

# main tast 
@dp.message_handler(commands=["start"])
async def start_command(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.reply("Welcome, Admin! Use /create to create a questionnaire.")
    else:
        await message.reply("Welcome to the voting bot! You can vote when questionnaires are created.")

@dp.message_handler(commands=["create"])
async def create_questionnaire(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.reply("Send me the title of the questionnaire.")
        await QuestionnaireStates.waiting_for_title.set()

@dp.message_handler(state=QuestionnaireStates.waiting_for_title)
async def set_title(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["title"] = message.text
    await message.reply("Now send the options, one per message. Send /done when finished.")
    await QuestionnaireStates.waiting_for_options.set()

@dp.message_handler(state=QuestionnaireStates.waiting_for_options, commands="done")
async def finish_options(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        title = data["title"]
        options = data.get("options", [])
        
        # Save to database
        db = next(get_db())
        questionnaire = Questionnaire(title=title, owner_id=ADMIN_ID)
        db.add(questionnaire)
        db.commit()

        for option_text in options:
            option = Option(text=option_text, questionnaire_id=questionnaire.id)
            db.add(option)
        
        db.commit()
        db.close()

    await message.reply("Questionnaire created!")
    await state.finish()

@dp.message_handler(state=QuestionnaireStates.waiting_for_options)
async def add_option(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if "options" not in data:
            data["options"] = []
        data["options"].append(message.text)
    await message.reply("Option added. Send another or /done to finish.")
    

@dp.message_handler(commands=["vote"])
async def show_questionnaires(message: types.Message):
    db = next(get_db())
    questionnaires = db.query(Questionnaire).all()
    db.close()

    if not questionnaires:
        await message.reply("No questionnaires available.")
        return

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for q in questionnaires:
        keyboard.add(KeyboardButton(f"Vote: {q.title}"))

    await message.reply("Select a questionnaire to vote:", reply_markup=keyboard)

@dp.message_handler(Text(startswith="Vote:"))
async def vote(message: types.Message):
    title = message.text[6:]
    db = next(get_db())
    questionnaire = db.query(Questionnaire).filter_by(title=title).first()
    db.close()

    if not questionnaire:
        await message.reply("Questionnaire not found.")
        return

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for option in questionnaire.options:
        keyboard.add(KeyboardButton(option.text))

    await message.reply("Choose an option:", reply_markup=keyboard)


@dp.message_handler(commands=["results"])
async def show_results(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("Only the admin can view results.")
        return

    db = next(get_db())
    questionnaires = db.query(Questionnaire).all()
    db.close()

    if not questionnaires:
        await message.reply("No questionnaires available.")
        return

    results = ""
    for q in questionnaires:
        results += f"Questionnaire: {q.title}\n"
        for option in q.options:
            results += f" - {option.text}: {option.votes} votes\n"
        results += "\n"

    await message.reply(results)

