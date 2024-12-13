from telethon import TelegramClient, events, Button
from datetime import datetime
import configparser
import MySQLdb
import traceback

# Initialize Configuration
print("Initializing configuration...")
config = configparser.ConfigParser()
config.read('config.ini')

API_ID = config.get('default', 'api_id')
API_HASH = config.get('default', 'api_hash')
BOT_TOKEN = config.get('default', 'bot_token')
session_name = "sessions/Bot"

HOSTNAME = config.get('default', 'hostname')
USERNAME = config.get('default', 'username')
PASSWORD = config.get('default', 'password')
DATABASE = config.get('default', 'database')
adding_options = False
current_question = 0 



# Initialize Telegram Client
client = TelegramClient(session_name, API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Global MySQL connection and cursor
try:
    conn = MySQLdb.connect(host=HOSTNAME, user=USERNAME, passwd=PASSWORD, db=DATABASE, charset='utf8mb4')
    crsr = conn.cursor()
    print("Database connected successfully.")
except MySQLdb.Error as e:
    print(f"Error connecting to MySQL: {e}")
    traceback.print_exc()
    exit(1)  # Exit if the database connection fails

# Admin ID (replace with your Telegram user ID)
ADMIN_ID = 1057648078  # Change this to your actual admin Telegram user ID

# Helper Function: Check if user is admin
def is_admin(user_id):
    return user_id == ADMIN_ID

# Helper Function: Generate Main Menu Buttons
def get_main_menu_buttons():
    return [
        [Button.inline("Create Vote", b"create_vote")],
        [Button.inline("View Votes", b"view_votes")],
        [Button.inline("Results", b"results")],
        [Button.inline("Delete Vote", b"delete_vote")],
    ]

# Command: /start
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    try:
        user_id = event.sender_id
        if is_admin(user_id):
            await event.respond(
                "Welcome, Admin! Choose an option:",
                buttons=get_main_menu_buttons(),
            )
        else:
            await event.respond("Welcome! Select a question to vote:", buttons=get_questions_buttons())
    except Exception as e:
        print(f"Error in /start command: {e}")
        traceback.print_exc()

# Helper Function: Fetch Questions for Users
def get_questions_buttons():
    try:
        crsr.execute("SELECT id, question_text FROM questions")
        questions = crsr.fetchall()
        buttons = [[Button.inline(q[1], f"vote_{q[0]}".encode())] for q in questions]
        return buttons if buttons else [[Button.inline("No questions available", b"none")]]
    except MySQLdb.Error as e:
        print(f"Error fetching questions: {e}")
        traceback.print_exc()
        return [[Button.inline("Error fetching questions", b"error")]]

# Inline Button: Create Vote (Admin)
@client.on(events.CallbackQuery(data=b"create_vote"))
# Global flag to track if we are done with adding options


async def create_vote(event):
    global adding_options
    try:
        if not is_admin(event.sender_id):
            await event.answer("Unauthorized!", alert=True)
            return
        await event.respond("Send me the question text (as a message).", buttons=[[Button.inline("Main Menu", b"main_menu")]])
        client.add_event_handler(create_question_step, events.NewMessage(incoming=True, from_users=ADMIN_ID))
    except Exception as e:
        print(f"Error in create_vote: {e}")
        traceback.print_exc()

async def create_question_step(event):
    global adding_options
    try:
        question_text = event.message.message
        crsr.execute("INSERT INTO questions (question_text, created_at) VALUES (%s, NOW())", (question_text,))
        conn.commit()
        question_id = crsr.lastrowid
        await event.respond("Question created! Now send options as separate messages (type 'done' when finished).", buttons=[[Button.inline("Main Menu", b"main_menu")]])
        
        # Flag to indicate options are being added
        adding_options = True
        
        client.remove_event_handler(create_question_step)  # Remove handler after processing the question
        client.add_event_handler(
            lambda e: add_options_step(e, question_id),
            events.NewMessage(incoming=True, from_users=ADMIN_ID)
        )
    except MySQLdb.Error as e:
        print(f"Error creating question: {e}")
        traceback.print_exc()
        await event.respond("An error occurred while creating the question.", buttons=[[Button.inline("Main Menu", b"main_menu")]])

async def add_options_step(event, question_id):
    global adding_options
    try:
        if not adding_options:
            return  # If we're not adding options, exit the function
        
        option_text = event.message.message
        if option_text.lower() == 'done':
            # Finish the option process
            adding_options = False  # Reset the flag
            await event.respond("Options saved successfully! Use /start to manage votes.", buttons=[[Button.inline("Main Menu", b"main_menu")]])
            client.remove_event_handler(add_options_step)  # Remove the event handler after "done"
            return
        
        # If it's an option, add it to the database
        crsr.execute("INSERT INTO options (question_id, option_text, vote_count) VALUES (%s, %s, 0)", (question_id, option_text))
        conn.commit()
        await event.respond(f"Option '{option_text}' added!", buttons=[[Button.inline("Main Menu", b"main_menu")]])
    except MySQLdb.Error as e:
        print(f"Error adding option: {e}")
        traceback.print_exc()
        await event.respond("An error occurred while adding the option.", buttons=[[Button.inline("Main Menu", b"main_menu")]])
# Inline Button: View Votes (Admin)
@client.on(events.CallbackQuery(data=b"view_votes"))
async def view_votes(event):
    try:
        if not is_admin(event.sender_id):
            await event.answer("Unauthorized!", alert=True)
            return
        
        # Fetch all questions (votes)
        crsr.execute("SELECT id, question_text FROM questions")
        questions = crsr.fetchall()
        
        if not questions:
            await event.respond("No votes available.", buttons=[[Button.inline("Main Menu", b"main_menu")]])
            return
        
        # Create buttons for each question
        buttons = [[Button.inline(q[1], f"view_{q[0]}".encode())] for q in questions]
        buttons.append([Button.inline("Main Menu", b"main_menu")])
        await event.respond("Select a vote to view:", buttons=buttons)
    
    except MySQLdb.Error as e:
        print(f"Error fetching votes: {e}")
        traceback.print_exc()
        await event.respond("An error occurred while fetching votes.", buttons=[[Button.inline("Main Menu", b"main_menu")]])

# Inline Button: Show Options for a Specific Vote
@client.on(events.CallbackQuery(pattern=b"view_(\d+)"))
async def view_vote_options(event):
    try:
        question_id = int(event.data.decode().split("_")[1])  # Extract the question_id
        
        # Fetch options for the selected question_id
        crsr.execute("SELECT option_text FROM options WHERE question_id = %s", (question_id,))
        options = crsr.fetchall()
        
        if not options:
            await event.respond("No options available for this vote.", buttons=[[Button.inline("Main Menu", b"main_menu")]])
            return
        
        # Create buttons for each option
        buttons = [[Button.inline(option[0], f"vote_{question_id}_{option[0]}".encode())] for option in options]
        buttons.append([Button.inline("Main Menu", b"main_menu")])
        
        # Send options as buttons
        await event.respond(f"Options for '{event.data.decode().split('_')[1]}':", buttons=buttons)
    
    except MySQLdb.Error as e:
        print(f"Error fetching options: {e}")
        traceback.print_exc()
        await event.respond("An error occurred while fetching options.", buttons=[[Button.inline("Main Menu", b"main_menu")]])


# Inline Button: Results (Admin)
@client.on(events.CallbackQuery(data=b"results"))
async def view_results(event):
    try:
        if not is_admin(event.sender_id):
            await event.answer("Unauthorized!", alert=True)
            return
        crsr.execute(
            """
            SELECT q.question_text, o.option_text, o.vote_count 
            FROM questions q JOIN options o ON q.id = o.question_id
            """
        )
        results = crsr.fetchall()
        if not results:
            await event.respond("No results available.", buttons=[[Button.inline("Main Menu", b"main_menu")]])
            return
        response = "\n".join([f"{row[0]}: {row[1]} - {row[2]} votes" for row in results])
        await event.respond(response, buttons=[[Button.inline("Main Menu", b"main_menu")]])
    except MySQLdb.Error as e:
        print(f"Error fetching results: {e}")
        traceback.print_exc()
        await event.respond("An error occurred while fetching results.", buttons=[[Button.inline("Main Menu", b"main_menu")]])

# Inline Button: Delete Vote (Admin)
@client.on(events.CallbackQuery(data=b"delete_vote"))
async def delete_vote(event):
    try:
        if not is_admin(event.sender_id):
            await event.answer("Unauthorized!", alert=True)
            return
        crsr.execute("SELECT id, question_text FROM questions")
        questions = crsr.fetchall()
        if not questions:
            await event.respond("No votes to delete.", buttons=[[Button.inline("Main Menu", b"main_menu")]])
            return
        buttons = [[Button.inline(q[1], f"delete_{q[0]}".encode())] for q in questions]
        buttons.append([Button.inline("Main Menu", b"main_menu")])
        await event.respond("Select a vote to delete:", buttons=buttons)
    except MySQLdb.Error as e:
        print(f"Error fetching votes for deletion: {e}")
        traceback.print_exc()
        await event.respond("An error occurred while fetching votes for deletion.", buttons=[[Button.inline("Main Menu", b"main_menu")]])
@client.on(events.CallbackQuery(pattern=b"delete_"))
async def confirm_delete(event):
    try:
        question_id = int(event.data.decode().split("_")[1])
        crsr.execute("DELETE FROM questions WHERE id = %s", (question_id,))
        crsr.execute("DELETE FROM options WHERE question_id = %s", (question_id,))  # Also delete options
        conn.commit()
        await event.respond("Vote deleted successfully!", buttons=[[Button.inline("Main Menu", b"main_menu")]])
    except MySQLdb.Error as e:
        print(f"Error deleting vote: {e}")
        traceback.print_exc()
        await event.respond("An error occurred while deleting the vote.", buttons=[[Button.inline("Main Menu", b"main_menu")]])
@client.on(events.CallbackQuery(pattern=b"vote_"))

async def handle_vote(event):
    global current_question
    try:
        question_id = int(event.data.decode().split("_")[1])
        crsr.execute("SELECT id, option_text FROM options WHERE question_id = %s", (question_id,))
        options = crsr.fetchall()
        buttons = [[Button.inline(opt[1], f"vote_opt_{opt[0]}".encode())] for opt in options]
        buttons.append([Button.inline("Main Menu", b"main_menu")])
        await event.respond("Choose an option:", buttons=buttons)
    except MySQLdb.Error as e:
        print(f"Error fetching options for voting: {e}")
        traceback.print_exc()
        await event.respond("An error occurred while fetching options.", buttons=[[Button.inline("Main Menu", b"main_menu")]])
@client.on(events.CallbackQuery(pattern=b"vote_opt_"))

async def vote_for_option(event):
    global current_question
    try:
        # Get the option ID from the callback data
        option_id = int(event.data.decode().split("_")[2])
        
        # Increment the vote count for the selected option
        crsr.execute("UPDATE options SET vote_count = vote_count + 1 WHERE id = %s", (option_id,))
        conn.commit()
        
        # Show a confirmation message to the user
        await event.answer("Vote registered!", alert=True)
        
        # Automatically proceed to the next question after the vote
        current_question += 1
        
        # Check if there are more questions
        if current_question < len(questions):
            # If there are more questions, ask the next one
            await ask_question(event)
        else:
            # If no more questions, end the voting session
            await event.respond("Thank you for voting! You've completed all the questions.", buttons=[[Button.inline("Main Menu", b"main_menu")]])
            current_question = 0  # Reset the counter after completing all questions
    except MySQLdb.Error as e:
        print(f"Error registering vote: {e}")
        traceback.print_exc()
        await event.respond("An error occurred while registering your vote.", buttons=[[Button.inline("Main Menu", b"main_menu")]])

async def ask_question(event):
    global current_question
    # Fetch the question and options for the current question
    crsr.execute("SELECT id, question_text FROM questions LIMIT %s, 1", (current_question,))
    question = crsr.fetchone()
    
    if question:
        # Fetch the options for the current question
        crsr.execute("SELECT id, option_text FROM options WHERE question_id = %s", (question[0],))
        options = crsr.fetchall()
        
        # Create buttons for each option
        buttons = [[Button.inline(opt[1], f"vote_opt_{opt[0]}".encode())] for opt in options]
        
        # Send the question and options
        await event.respond(f"Question {current_question + 1}: {question[1]}", buttons=buttons)
    else:
        await event.respond("No more questions available.", buttons=[[Button.inline("Main Menu", b"main_menu")]])


print("Bot is running...")
client.run_until_disconnected()
