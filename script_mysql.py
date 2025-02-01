from telethon import TelegramClient, events, Button
from datetime import datetime
import configparser
import MySQLdb
import traceback

# Konfiguratsiyani o'rnatish
print("Konfiguratsiya yuklanmoqda...")
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

# Telegram Clientni ishga tushirish
client = TelegramClient(session_name, API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# MySQL bilan ulanish
try:
    conn = MySQLdb.connect(host=HOSTNAME, user=USERNAME, passwd=PASSWORD, db=DATABASE, charset='utf8mb4')
    crsr = conn.cursor()
    print("Ma'lumotlar bazasi muvaffaqiyatli ulandi.")
except MySQLdb.Error as e:
    print(f"MySQL bilan bog'lanishda xato: {e}")
    traceback.print_exc()
    exit(1)

# Admin ID (o'zgartiring o'zingizning Telegram ID raqamingizga)
ADMIN_ID = 1057648078

# Helper funksiyalar
def is_admin(user_id):
    return user_id == ADMIN_ID

def get_main_menu_buttons():
    return [
        [Button.inline("Ovoz yaratish", b"create_vote")],
        [Button.inline("Ovozlarni ko'rish", b"view_votes")],
        [Button.inline("Natijalar", b"results")],
        [Button.inline("Ovoz o'chirish", b"delete_vote")],
    ]

# /start komandasi
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    try:
        user_id = event.sender_id
        if is_admin(user_id):
            await event.respond(
                "Xush kelibsiz, Admin! Quyidagi variantlardan birini tanlang:",
                buttons=get_main_menu_buttons(),
            )
        else:
            await event.respond(
                "Xush kelibsiz! Ovoz berish uchun savolni tanlang:",
                buttons=get_questions_buttons()
            )
    except Exception as e:
        print(f"/start komandasi xatosi: {e}")
        traceback.print_exc()

# Savollarni olish uchun yordamchi funksiya
def get_questions_buttons():
    try:
        crsr.execute("SELECT id, question_text FROM questions")
        questions = crsr.fetchall()
        buttons = [[Button.inline(q[1], f"vote_{q[0]}".encode())] for q in questions]
        return buttons if buttons else [[Button.inline("Savollar mavjud emas", b"none")]]
    except MySQLdb.Error as e:
        print(f"Savollarni olishda xato: {e}")
        traceback.print_exc()
        return [[Button.inline("Savollarni olishda xato yuz berdi", b"error")]]

# Ovoz yaratish
@client.on(events.CallbackQuery(data=b"create_vote"))
async def create_vote(event):
    try:
        if not is_admin(event.sender_id):
            await event.answer("Sizga ruxsat berilmagan!", alert=True)
            return
        await event.respond(
            "Savol matnini xabar sifatida yuboring.",
            buttons=[[Button.inline("Asosiy Menyu", b"main_menu")]]
        )
        client.add_event_handler(create_question_step, events.NewMessage(incoming=True, from_users=ADMIN_ID))
    except Exception as e:
        print(f"Ovoz yaratishda xato: {e}")
        traceback.print_exc()

async def create_question_step(event):
    try:
        question_text = event.message.message
        crsr.execute("INSERT INTO questions (question_text, created_at) VALUES (%s, NOW())", (question_text,))
        conn.commit()
        question_id = crsr.lastrowid
        await event.respond(
            "Savol yaratildi! Variantlarni alohida xabarlar sifatida yuboring (yakunlash uchun 'done' deb yozing).",
            buttons=[[Button.inline("Asosiy Menyu", b"main_menu")]]
        )
        client.remove_event_handler(create_question_step)
        client.add_event_handler(
            lambda e: add_options_step(e, question_id),
            events.NewMessage(incoming=True, from_users=ADMIN_ID)
        )
    except MySQLdb.Error as e:
        print(f"Savol yaratishda xato: {e}")
        traceback.print_exc()

# Variantlarni qo'shish bosqichi
async def add_options_step(event, question_id):
    try:
        option_text = event.message.message
        if option_text.lower() == 'done':
            await event.respond(
                "Variantlar saqlandi! /start buyrug'i orqali boshqaruvni qayta boshlang.",
                buttons=[[Button.inline("Asosiy Menyu", b"main_menu")]]
            )
            client.remove_event_handler(add_options_step)
            return
        
        crsr.execute("INSERT INTO options (question_id, option_text, vote_count) VALUES (%s, %s, 0)", (question_id, option_text))
        conn.commit()
        await event.respond(f"Variant '{option_text}' qo'shildi!", buttons=[[Button.inline("Asosiy Menyu", b"main_menu")]])
    except MySQLdb.Error as e:
        print(f"Variantlarni qo'shishda xato: {e}")
        traceback.print_exc()

# Keyingi kodlarni o'zgartirish ham yuqoridagidek davom etadi...
# Savollarni ko'rish
@client.on(events.CallbackQuery(data=b"view_votes"))
async def view_votes(event):
    try:
        if not is_admin(event.sender_id):
            await event.answer("Sizga ruxsat berilmagan!", alert=True)
            return
        
        crsr.execute("SELECT id, question_text FROM questions")
        questions = crsr.fetchall()
        if not questions:
            await event.respond(
                "Hozircha savollar mavjud emas.",
                buttons=[[Button.inline("Asosiy Menyu", b"main_menu")]]
            )
        else:
            buttons = [[Button.inline(q[1], f"view_{q[0]}".encode())] for q in questions]
            await event.respond(
                "Savollar ro'yxati:",
                buttons=buttons + [[Button.inline("Asosiy Menyu", b"main_menu")]]
            )
    except MySQLdb.Error as e:
        print(f"Savollarni ko'rishda xato: {e}")
        traceback.print_exc()

# Natijalarni ko'rish
@client.on(events.CallbackQuery(data=b"results"))
async def view_results(event):
    try:
        if not is_admin(event.sender_id):
            await event.answer("Sizga ruxsat berilmagan!", alert=True)
            return
        
        crsr.execute("SELECT id, question_text FROM questions")
        questions = crsr.fetchall()
        if not questions:
            await event.respond(
                "Hozircha natijalar mavjud emas.",
                buttons=[[Button.inline("Asosiy Menyu", b"main_menu")]]
            )
        else:
            buttons = [[Button.inline(f"Natija: {q[1]}", f"result_{q[0]}".encode())] for q in questions]
            await event.respond(
                "Natijalar ro'yxati:",
                buttons=buttons + [[Button.inline("Asosiy Menyu", b"main_menu")]]
            )
    except MySQLdb.Error as e:
        print(f"Natijalarni ko'rishda xato: {e}")
        traceback.print_exc()

@client.on(events.CallbackQuery(pattern=r"^result_\d+$"))
async def display_results(event):
    try:
        question_id = int(event.data.decode().split("_")[1])
        crsr.execute("SELECT option_text, vote_count FROM options WHERE question_id = %s", (question_id,))
        options = crsr.fetchall()
        if not options:
            await event.respond(
                "Natijalar topilmadi.",
                buttons=[[Button.inline("Asosiy Menyu", b"main_menu")]]
            )
        else:
            result_text = "Natijalar:\n\n" + "\n".join([f"{o[0]}: {o[1]} ovoz" for o in options])
            await event.respond(
                result_text,
                buttons=[[Button.inline("Asosiy Menyu", b"main_menu")]]
            )
    except MySQLdb.Error as e:
        print(f"Natijalarni ko'rsatishda xato: {e}")
        traceback.print_exc()

# Savolni o'chirish
@client.on(events.CallbackQuery(data=b"delete_vote"))
async def delete_vote(event):
    try:
        if not is_admin(event.sender_id):
            await event.answer("Sizga ruxsat berilmagan!", alert=True)
            return
        
        crsr.execute("SELECT id, question_text FROM questions")
        questions = crsr.fetchall()
        if not questions:
            await event.respond(
                "O'chirish uchun savollar mavjud emas.",
                buttons=[[Button.inline("Asosiy Menyu", b"main_menu")]]
            )
        else:
            buttons = [[Button.inline(q[1], f"delete_{q[0]}".encode())] for q in questions]
            await event.respond(
                "O'chiriladigan savolni tanlang:",
                buttons=buttons + [[Button.inline("Asosiy Menyu", b"main_menu")]]
            )
    except MySQLdb.Error as e:
        print(f"Savolni o'chirishda xato: {e}")
        traceback.print_exc()

@client.on(events.CallbackQuery(pattern=r"^delete_\d+$"))
async def confirm_delete(event):
    try:
        question_id = int(event.data.decode().split("_")[1])
        crsr.execute("DELETE FROM questions WHERE id = %s", (question_id,))
        crsr.execute("DELETE FROM options WHERE question_id = %s", (question_id,))
        conn.commit()
        await event.respond(
            "Savol va unga tegishli barcha variantlar muvaffaqiyatli o'chirildi.",
            buttons=[[Button.inline("Asosiy Menyu", b"main_menu")]]
        )
    except MySQLdb.Error as e:
        print(f"Savolni o'chirishda xato: {e}")
        traceback.print_exc()

# Asosiy Menyu
@client.on(events.CallbackQuery(data=b"main_menu"))
async def main_menu(event):
    try:
        if is_admin(event.sender_id):
            await event.respond(
                "Asosiy menyuga qaytdingiz:",
                buttons=get_main_menu_buttons()
            )
        else:
            await event.respond(
                "Ovoz berish uchun quyidagi savollardan birini tanlang:",
                buttons=get_questions_buttons()
            )
    except Exception as e:
        print(f"Asosiy menyuga qaytishda xato: {e}")
        traceback.print_exc()

# Foydalanuvchi ovoz berishi
@client.on(events.CallbackQuery(pattern=r"^vote_\d+$"))
async def cast_vote(event):
    try:
        question_id = int(event.data.decode().split("_")[1])
        crsr.execute("SELECT id, option_text FROM options WHERE question_id = %s", (question_id,))
        options = crsr.fetchall()
        if not options:
            await event.respond(
                "Ushbu savol uchun variantlar topilmadi.",
                buttons=[[Button.inline("Asosiy Menyu", b"main_menu")]]
            )
        else:
            buttons = [[Button.inline(o[1], f"cast_{o[0]}".encode())] for o in options]
            await event.respond(
                "Ovoz berish uchun variantni tanlang:",
                buttons=buttons + [[Button.inline("Asosiy Menyu", b"main_menu")]]
            )
    except MySQLdb.Error as e:
        print(f"Ovoz berishda xato: {e}")
        traceback.print_exc()

@client.on(events.CallbackQuery(pattern=r"^cast_\d+$"))
async def register_vote(event):
    try:
        option_id = int(event.data.decode().split("_")[1])
        crsr.execute("UPDATE options SET vote_count = vote_count + 1 WHERE id = %s", (option_id,))
        conn.commit()
        await event.answer("Ovoz muvaffaqiyatli berildi!", alert=True)
    except MySQLdb.Error as e:
        print(f"Ovozlarni ro'yxatga olishda xato: {e}")
        traceback.print_exc()

# Xatolarni qayta ishlash
@client.on(events.CallbackQuery())
async def unknown_action(event):
    await event.answer("Noma'lum amal. Iltimos, qayta urinib ko'ring.", alert=True)

# Botni ishga tushirish
print("Bot ishga tushdi!")
client.run_until_disconnected()
