import requests
import threading
import time
import re
import asyncio
import random
from datetime import datetime, timezone, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, ContextTypes

BOT_TOKEN = "8687160226:AAHKPurDJS8kyxrblV0X8mZdSbFwFUV56Yw"
ADMIN_ID = "1922522807"
GROUP_ID = "-1003862731449"

NAME, EMAIL, CITY, PHONE, CONFIRM = range(5)

REGISTER_API = "https://summertasticcontest.com/api/register.php"
SUBMIT_API = "https://summertasticcontest.com/api/submit.php"

HEADERS = {
    "Host": "summertasticcontest.com",
    "Sec-Ch-Ua-Platform": "Windows",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Origin": "https://summertasticcontest.com",
    "Referer": "https://summertasticcontest.com/"
}

CONSENT = {"consent_a": "yes", "consent_b": "yes", "consent_c": "yes"}

SLOTS = [
    {"slot": 1, "label": "10:00 am - 10:30 am", "hour": 10, "minute": 0},
    {"slot": 2, "label": "10:30 am - 11:00 am", "hour": 10, "minute": 30},
    {"slot": 3, "label": "11:00 am - 11:30 am", "hour": 11, "minute": 0},
    {"slot": 4, "label": "11:30 am - 12:00 pm", "hour": 11, "minute": 30},
    {"slot": 5, "label": "12:00 pm - 12:30 pm", "hour": 12, "minute": 0},
    {"slot": 6, "label": "12:30 pm - 1:00 pm", "hour": 12, "minute": 30},
]

# Day 1 questions only for testing
QUESTIONS = [
    {"options": ["Tina", "Gopal", "Mira"], "correct": 1, "correct_value": "Gopal"},
    {"options": ["Lucky", "Harry", "Nobita"], "correct": 2, "correct_value": "Nobita"},
    {"options": ["Lucky", "Elsa", "Moana"], "correct": 0, "correct_value": "Lucky"},
    {"options": ["Mickey", "Doraemon", "Goofy"], "correct": 1, "correct_value": "Doraemon"},
    {"options": ["Shizuka", "Harry", "Lucky"], "correct": 0, "correct_value": "Shizuka"},
    {"options": ["Madhav", "Ariel", "Rapunzel"], "correct": 0, "correct_value": "Madhav"},
]

pending_users = {}
approved_users = {}
participants = {}
user_temp_data = {}
bot_app = None

def send_log(message):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")

def get_current_slot():
    now = datetime.now()
    for slot in SLOTS:
        slot_start = now.replace(hour=slot['hour'], minute=slot['minute'], second=0, microsecond=0)
        slot_end = slot_start + timedelta(minutes=30)
        if slot_start <= now <= slot_end:
            return slot
    return None

def submit_answer_sync(participant_id, email, phone, slot_index, question_data):
    slot = SLOTS[slot_index - 1]
    correct_index = question_data['correct']
    correct_value = question_data['correct_value']
    options = question_data['options']
    options_prompt = f"A: {options[0]} | B: {options[1]} | C: {options[2]}"
    submitted_at = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    
    payload = {
        "contest_date": datetime.now().strftime("%Y-%m-%d"),
        "contest_day": 1,
        "slot_index": slot_index,
        "slot_label": slot['label'],
        "question_text": "Which character did you spot right now?",
        "options_prompt": options_prompt,
        "selected_option": ["A", "B", "C"][correct_index],
        "selected_value": correct_value,
        "correct_value": correct_value,
        "is_correct": 1,
        "submitted_at": submitted_at,
        "participant_id": int(participant_id),
        "phone": phone,
        "email": email
    }
    
    try:
        response = requests.post(SUBMIT_API, json=payload, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            result = response.json()
            return result.get('ok') == True, "Submitted"
        return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id == ADMIN_ID:
        await update.message.reply_text(
            "Admin Panel\n\n"
            "Commands:\n"
            "/pending - Pending users\n"
            "/approve <id> - Approve user\n"
            "/reject <id> - Reject user\n"
            "/users - List users\n"
            "/stats - Statistics"
        )
        return ConversationHandler.END
    elif user_id in participants:
        await update.message.reply_text("You are already registered! Use /status to check.")
        return ConversationHandler.END
    elif user_id in approved_users:
        await update.message.reply_text("Welcome! Use /register to start registration.")
        return ConversationHandler.END
    elif user_id in pending_users:
        await update.message.reply_text("Pending approval. Wait for admin.")
        return ConversationHandler.END
    else:
        keyboard = [[InlineKeyboardButton("Request Access", callback_data='request_access')]]
        await update.message.reply_text("Access Restricted. Click below to request access.", reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END

async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id == ADMIN_ID or user_id in approved_users:
        await update.message.reply_text("Step 1/4: What is your full name?")
        return NAME
    else:
        await update.message.reply_text("No access. Use /start first.")
        return ConversationHandler.END

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    name = update.message.text.strip()
    if len(name) < 3:
        await update.message.reply_text("Invalid name. Enter again:")
        return NAME
    user_temp_data[user_id] = {'name': name}
    await update.message.reply_text("Step 2/4: What is your email?")
    return EMAIL

async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    email = update.message.text.strip()
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        await update.message.reply_text("Invalid email. Enter again:")
        return EMAIL
    user_temp_data[user_id]['email'] = email
    await update.message.reply_text("Step 3/4: What is your city?")
    return CITY

async def get_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    city = update.message.text.strip()
    if len(city) < 2:
        await update.message.reply_text("Invalid city. Enter again:")
        return CITY
    user_temp_data[user_id]['city'] = city
    await update.message.reply_text("Step 4/4: What is your phone number (10 digits)?")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    phone = update.message.text.strip()
    if not re.match(r'^[6-9]\d{9}$', phone):
        await update.message.reply_text("Invalid phone. Enter 10 digits:")
        return PHONE
    user_temp_data[user_id]['phone'] = phone
    data = user_temp_data[user_id]
    await update.message.reply_text(f"Confirm:\nName: {data['name']}\nEmail: {data['email']}\nCity: {data['city']}\nPhone: {data['phone']}\n\nReply YES to register.")
    return CONFIRM

async def register_on_website(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if update.message.text.upper() != 'YES':
        await update.message.reply_text("Registration cancelled.")
        if user_id in user_temp_data:
            del user_temp_data[user_id]
        return ConversationHandler.END
    
    data = user_temp_data[user_id]
    await update.message.reply_text("Registering...")
    
    payload = {"name": data['name'], "email": data['email'], "city": data['city'], "phone": data['phone'], **CONSENT}
    
    try:
        response = requests.post(REGISTER_API, json=payload, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            result = response.json()
            participant_id = result.get('participant_id')
            if participant_id:
                participants[user_id] = {'participant_id': str(participant_id), 'name': data['name'], 'email': data['email'], 'city': data['city'], 'phone': data['phone']}
                await update.message.reply_text(f"Registration Successful!\n\nYour Participant ID: {participant_id}\n\nBot will auto-submit answers.")
                await context.bot.send_message(ADMIN_ID, f"New registration: {data['name']} (ID: {participant_id})")
                
                # Immediate submission if active slot
                current_slot = get_current_slot()
                if current_slot:
                    await update.message.reply_text(f"Active slot detected! Submitting answers for Slot {current_slot['slot']}...")
                    for q_index, q in enumerate(QUESTIONS, 1):
                        success, msg = submit_answer_sync(participant_id, data['email'], data['phone'], current_slot['slot'], q)
                        if success:
                            await update.message.reply_text(f"Question {q_index}: Correct answer submitted!")
                        else:
                            await update.message.reply_text(f"Question {q_index}: Failed - {msg}")
                        await asyncio.sleep(0.5)
                    await update.message.reply_text("All answers submitted for current slot!")
            else:
                await update.message.reply_text("Registration failed: No participant ID")
        else:
            await update.message.reply_text(f"Registration failed: HTTP {response.status_code}")
    except Exception as e:
        await update.message.reply_text(f"Registration failed: {str(e)[:100]}")
    
    if user_id in user_temp_data:
        del user_temp_data[user_id]
    return ConversationHandler.END

async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id in user_temp_data:
        del user_temp_data[user_id]
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    
    if query.data == 'request_access':
        if user_id in pending_users:
            await query.edit_message_text("Already pending.")
        else:
            pending_users[user_id] = {'name': query.from_user.first_name, 'username': query.from_user.username or "No username"}
            await context.bot.send_message(ADMIN_ID, f"New request from: {query.from_user.first_name}\nID: {user_id}\nUse /approve {user_id}")
            await query.edit_message_text("Request sent to admin!")

async def pending_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("Admin only!")
        return
    if not pending_users:
        await update.message.reply_text("No pending users.")
        return
    msg = "Pending:\n"
    for uid, data in pending_users.items():
        msg += f"ID: {uid} - {data['name']}\n"
    await update.message.reply_text(msg)

async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("Admin only!")
        return
    if not context.args:
        await update.message.reply_text("Usage: /approve <user_id>")
        return
    target = context.args[0]
    if target in pending_users:
        approved_users[target] = pending_users[target]
        del pending_users[target]
        await context.bot.send_message(target, "Access Granted! Use /register to start.")
        await update.message.reply_text(f"User {target} approved!")

async def reject_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("Admin only!")
        return
    if not context.args:
        await update.message.reply_text("Usage: /reject <user_id>")
        return
    target = context.args[0]
    if target in pending_users:
        del pending_users[target]
        await context.bot.send_message(target, "Access Denied.")
        await update.message.reply_text(f"User {target} rejected!")

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("Admin only!")
        return
    msg = "Approved Users:\n"
    for uid, data in approved_users.items():
        registered = "Yes" if uid in participants else "No"
        msg += f"ID: {uid} - {data['name']} (Registered: {registered})\n"
    await update.message.reply_text(msg)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("Admin only!")
        return
    await update.message.reply_text(f"Approved: {len(approved_users)}\nPending: {len(pending_users)}\nRegistered: {len(participants)}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id in participants:
        data = participants[user_id]
        await update.message.reply_text(f"Registered!\nName: {data['name']}\nID: {data['participant_id']}\nAuto-submit: Active")
    else:
        await update.message.reply_text("Not registered. Use /register")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Commands:\n/start - Menu\n/register - Register\n/status - Check status\n/help - Help")

def main():
    global bot_app
    app = Application.builder().token(BOT_TOKEN).build()
    bot_app = app
    
    conv = ConversationHandler(
        entry_points=[CommandHandler('register', register_command)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_city)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_on_website)],
        },
        fallbacks=[CommandHandler('cancel', cancel_registration)],
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("pending", pending_command))
    app.add_handler(CommandHandler("approve", approve_command))
    app.add_handler(CommandHandler("reject", reject_command))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("help", help_command))
    
    print("Bot started successfully!")
    app.run_polling()

if __name__ == '__main__':
    main()
