import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from sqlalchemy.orm import Session
from connection import get_db  # Import the session and database connection
from database import Questionnaire, Option  # Import models

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_text(
        f"Hello {user.first_name}, use /create_poll <title> to create a new questionnaire."
    )

# Create poll command handler
async def create_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db: Session = next(get_db())  # Get a new session
    title = " ".join(context.args)  # Get the title of the questionnaire from the command input
    
    if not title:
        await update.message.reply_text("Please provide a title for the questionnaire.")
        return
    
    # Get the admin ID (the user creating the poll)
    admin_id = update.effective_user.id
    
    # Create a new questionnaire, setting the admin ID as the owner
    new_questionnaire = Questionnaire(title=title, owner_id=admin_id)
    
    db.add(new_questionnaire)
    db.commit()
    db.refresh(new_questionnaire)

    await update.message.reply_text(f"Your questionnaire '{title}' has been created.")

# Vote command handler
async def vote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db: Session = next(get_db())
    
    try:
        questionnaire_id = int(context.args[0])
        option_text = " ".join(context.args[1:])
    except (IndexError, ValueError):
        await update.message.reply_text("Please provide the questionnaire ID and option text.")
        return

    questionnaire = db.query(Questionnaire).filter(Questionnaire.id == questionnaire_id).first()
    
    if not questionnaire:
        await update.message.reply_text("Questionnaire not found.")
        return

    option = db.query(Option).filter(
        Option.questionnaire_id == questionnaire.id,
        Option.text == option_text
    ).first()
    
    if not option:
        await update.message.reply_text("Option not found.")
        return

    # Update the vote count
    option.votes += 1
    db.commit()
    
    await update.message.reply_text(f"Your vote for '{option_text}' has been counted.")

# Results command handler
async def results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db: Session = next(get_db())
    
    try:
        questionnaire_id = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("Please provide the questionnaire ID.")
        return
    
    questionnaire = db.query(Questionnaire).filter(Questionnaire.id == questionnaire_id).first()
    
    if not questionnaire:
        await update.message.reply_text("Questionnaire not found.")
        return
    
    options = db.query(Option).filter(Option.questionnaire_id == questionnaire.id).all()
    
    if not options:
        await update.message.reply_text("No options found for this questionnaire.")
        return

    result_text = f"Results for questionnaire: {questionnaire.title}\n"
    for option in options:
        result_text += f"{option.text}: {option.votes} votes\n"
    
    await update.message.reply_text(result_text)

# Bot token
BOT_TOKEN = "8197123228:AAFOxifjwe4JfkvucdMrqq5WN2Q-1y2Xn5Q"

# Main function to set up the bot
def main() -> None:
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("create_poll", create_poll))
    application.add_handler(CommandHandler("vote", vote))
    application.add_handler(CommandHandler("results", results))

    # Start the bot
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
