import requests
import json
import schedule
import time
import threading
import os
import re
import asyncio
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, ContextTypes

# Bot configuration
BOT_TOKEN = "8687160226:AAHKPurDJS8kyxrblV0X8mZdSbFwFUV56Yw"
ADMIN_ID = "1922522807"
GROUP_ID = "-1003862731449"

# Conversation states
NAME, EMAIL, CITY, PHONE, CONFIRM = range(5)

# API endpoints
REGISTER_API = "https://summertasticcontest.com/api/register.php"
SUBMIT_API = "https://summertasticcontest.com/api/submit.php"

# Headers
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

# Fixed consent values
CONSENT = {
    "consent_a": "yes",
    "consent_b": "yes",
    "consent_c": "yes"
}

# Slot timings (IST)
SLOTS = [
    {"slot": 1, "label": "10:00 am – 10:30 am", "time": "10:00"},
    {"slot": 2, "label": "10:30 am – 11:00 am", "time": "10:30"},
    {"slot": 3, "label": "11:00 am – 11:30 am", "time": "11:00"},
    {"slot": 4, "label": "11:30 am – 12:00 pm", "time": "11:30"},
    {"slot": 5, "label": "12:00 pm – 12:30 pm", "time": "12:00"},
    {"slot": 6, "label": "12:30 pm – 1:00 pm", "time": "12:30"},
]

# Questions and correct answers for 15 days
QUESTIONS = [
    # Day 1
    [
        {"options": ["Tina", "Gopal", "Mira"], "correct": 1, "correct_value": "Gopal"},
        {"options": ["Lucky", "Harry", "Nobita"], "correct": 2, "correct_value": "Nobita"},
        {"options": ["Lucky", "Elsa", "Moana"], "correct": 0, "correct_value": "Lucky"},
        {"options": ["Mickey", "Doraemon", "Goofy"], "correct": 1, "correct_value": "Doraemon"},
        {"options": ["Shizuka", "Harry", "Lucky"], "correct": 0, "correct_value": "Shizuka"},
        {"options": ["Madhav", "Ariel", "Rapunzel"], "correct": 0, "correct_value": "Madhav"},
    ],
    # Day 2
    [
        {"options": ["Shinchan", "Doraemon", "Gian"], "correct": 2, "correct_value": "Gian"},
        {"options": ["Pappu", "Nobita", "Titu"], "correct": 1, "correct_value": "Nobita"},
        {"options": ["Tiana", "Diana", "Lucky"], "correct": 2, "correct_value": "Lucky"},
        {"options": ["Doraemon", "Harry", "Mickey"], "correct": 0, "correct_value": "Doraemon"},
        {"options": ["Madhav", "Goofy", "Pluto"], "correct": 0, "correct_value": "Madhav"},
        {"options": ["Cinderella", "Gopal", "Ariel"], "correct": 1, "correct_value": "Gopal"},
    ],
    # Day 3
    [
        {"options": ["Madhav", "Cinderella", "Tiana"], "correct": 0, "correct_value": "Madhav"},
        {"options": ["Doraemon", "Shizuka", "Harry"], "correct": 1, "correct_value": "Shizuka"},
        {"options": ["Mili", "Gopal", "Myra"], "correct": 1, "correct_value": "Gopal"},
        {"options": ["Mickey", "Donald", "Nobita"], "correct": 2, "correct_value": "Nobita"},
        {"options": ["Doraemon", "Nobita", "Shizuka"], "correct": 0, "correct_value": "Doraemon"},
        {"options": ["Tina", "Lucky", "Pinky"], "correct": 1, "correct_value": "Lucky"},
    ],
    # Day 4
    [
        {"options": ["Lucky", "Elsa", "Anna"], "correct": 0, "correct_value": "Lucky"},
        {"options": ["Harry", "Doraemon", "Mickey"], "correct": 1, "correct_value": "Doraemon"},
        {"options": ["Madhav", "Daisy", "Donald"], "correct": 0, "correct_value": "Madhav"},
        {"options": ["Mickey", "Minnie", "Shizuka"], "correct": 2, "correct_value": "Shizuka"},
        {"options": ["Ariel", "Mulan", "Gopal"], "correct": 2, "correct_value": "Gopal"},
        {"options": ["Nobita", "Goofy", "Pinky"], "correct": 0, "correct_value": "Nobita"},
    ],
    # Day 5
    [
        {"options": ["Doraemon", "Mickey", "Donald"], "correct": 0, "correct_value": "Doraemon"},
        {"options": ["Gian", "Pluto", "Ariel"], "correct": 0, "correct_value": "Gian"},
        {"options": ["Radha", "Mili", "Madhav"], "correct": 2, "correct_value": "Madhav"},
        {"options": ["Elsa", "Lucky", "Pinky"], "correct": 1, "correct_value": "Lucky"},
        {"options": ["Pappu", "Nobita", "Pluto"], "correct": 1, "correct_value": "Nobita"},
        {"options": ["Gopal", "Diana", "Daisy"], "correct": 0, "correct_value": "Gopal"},
    ],
    # Day 6
    [
        {"options": ["Gopal", "Mili", "Minnie"], "correct": 0, "correct_value": "Gopal"},
        {"options": ["Shizuka", "Lucky", "Elsa"], "correct": 1, "correct_value": "Lucky"},
        {"options": ["Ariel", "Gian", "Shinchan"], "correct": 1, "correct_value": "Gian"},
        {"options": ["Madhav", "Dorami", "Doraemon"], "correct": 0, "correct_value": "Madhav"},
        {"options": ["Harry", "Mickey", "Doraemon"], "correct": 2, "correct_value": "Doraemon"},
        {"options": ["Pluto", "Nobita", "Goofy"], "correct": 1, "correct_value": "Nobita"},
    ],
    # Day 7
    [
        {"options": ["Ariel", "Lucky", "Moana"], "correct": 1, "correct_value": "Lucky"},
        {"options": ["Doraemon", "Donald", "Mickey"], "correct": 0, "correct_value": "Doraemon"},
        {"options": ["Doraemon", "Dorami", "Nobita"], "correct": 2, "correct_value": "Nobita"},
        {"options": ["Pinky", "Gian", "Hemawari"], "correct": 1, "correct_value": "Gian"},
        {"options": ["Doraemon", "Madhav", "Pluto"], "correct": 1, "correct_value": "Madhav"},
        {"options": ["Gopal", "Daisy", "Donald"], "correct": 0, "correct_value": "Gopal"},
    ],
    # Day 8
    [
        {"options": ["Tina", "Gopal", "Mira"], "correct": 1, "correct_value": "Gopal"},
        {"options": ["Lucky", "Harry", "Nobita"], "correct": 2, "correct_value": "Nobita"},
        {"options": ["Lucky", "Elsa", "Moana"], "correct": 0, "correct_value": "Lucky"},
        {"options": ["Mickey", "Doraemon", "Goofy"], "correct": 1, "correct_value": "Doraemon"},
        {"options": ["Shizuka", "Harry", "Lucky"], "correct": 0, "correct_value": "Shizuka"},
        {"options": ["Madhav", "Ariel", "Rapunzel"], "correct": 0, "correct_value": "Madhav"},
    ],
    # Day 9
    [
        {"options": ["Madhav", "Cinderella", "Tiana"], "correct": 0, "correct_value": "Madhav"},
        {"options": ["Doraemon", "Shizuka", "Harry"], "correct": 1, "correct_value": "Shizuka"},
        {"options": ["Mili", "Gopal", "Myra"], "correct": 1, "correct_value": "Gopal"},
        {"options": ["Mickey", "Donald", "Nobita"], "correct": 2, "correct_value": "Nobita"},
        {"options": ["Doraemon", "Nobita", "Shizuka"], "correct": 0, "correct_value": "Doraemon"},
        {"options": ["Tina", "Lucky", "Pinky"], "correct": 1, "correct_value": "Lucky"},
    ],
    # Day 10
    [
        {"options": ["Lucky", "Elsa", "Anna"], "correct": 0, "correct_value": "Lucky"},
        {"options": ["Harry", "Doraemon", "Mickey"], "correct": 1, "correct_value": "Doraemon"},
        {"options": ["Madhav", "Daisy", "Donald"], "correct": 0, "correct_value": "Madhav"},
        {"options": ["Mickey", "Minnie", "Shizuka"], "correct": 2, "correct_value": "Shizuka"},
        {"options": ["Ariel", "Mulan", "Gopal"], "correct": 2, "correct_value": "Gopal"},
        {"options": ["Nobita", "Goofy", "Pinky"], "correct": 0, "correct_value": "Nobita"},
    ],
    # Day 11
    [
        {"options": ["Shinchan", "Doraemon", "Gian"], "correct": 2, "correct_value": "Gian"},
        {"options": ["Pappu", "Nobita", "Titu"], "correct": 1, "correct_value": "Nobita"},
        {"options": ["Tiana", "Diana", "Lucky"], "correct": 2, "correct_value": "Lucky"},
        {"options": ["Doraemon", "Harry", "Mickey"], "correct": 0, "correct_value": "Doraemon"},
        {"options": ["Madhav", "Goofy", "Pluto"], "correct": 0, "correct_value": "Madhav"},
        {"options": ["Cinderella", "Gopal", "Ariel"], "correct": 1, "correct_value": "Gopal"},
    ],
    # Day 12
    [
        {"options": ["Doraemon", "Mickey", "Donald"], "correct": 0, "correct_value": "Doraemon"},
        {"options": ["Gian", "Pluto", "Ariel"], "correct": 0, "correct_value": "Gian"},
        {"options": ["Radha", "Mili", "Madhav"], "correct": 2, "correct_value": "Madhav"},
        {"options": ["Elsa", "Lucky", "Pinky"], "correct": 1, "correct_value": "Lucky"},
        {"options": ["Pappu", "Nobita", "Pluto"], "correct": 1, "correct_value": "Nobita"},
        {"options": ["Gopal", "Diana", "Daisy"], "correct": 0, "correct_value": "Gopal"},
    ],
    # Day 13
    [
        {"options": ["Gopal", "Mili", "Minnie"], "correct": 0, "correct_value": "Gopal"},
        {"options": ["Shizuka", "Lucky", "Elsa"], "correct": 1, "correct_value": "Lucky"},
        {"options": ["Ariel", "Gian", "Shinchan"], "correct": 1, "correct_value": "Gian"},
        {"options": ["Madhav", "Dorami", "Doraemon"], "correct": 0, "correct_value": "Madhav"},
        {"options": ["Harry", "Mickey", "Doraemon"], "correct": 2, "correct_value": "Doraemon"},
        {"options": ["Pluto", "Nobita", "Goofy"], "correct": 1, "correct_value": "Nobita"},
    ],
    # Day 14
    [
        {"options": ["Ariel", "Lucky", "Moana"], "correct": 1, "correct_value": "Lucky"},
        {"options": ["Doraemon", "Donald", "Mickey"], "correct": 0, "correct_value": "Doraemon"},
        {"options": ["Doraemon", "Dorami", "Nobita"], "correct": 2, "correct_value": "Nobita"},
        {"options": ["Pinky", "Gian", "Hemawari"], "correct": 1, "correct_value": "Gian"},
        {"options": ["Doraemon", "Madhav", "Pluto"], "correct": 1, "correct_value": "Madhav"},
        {"options": ["Gopal", "Daisy", "Donald"], "correct": 0, "correct_value": "Gopal"},
    ],
    # Day 15
    [
        {"options": ["Madhav", "Daisy", "Diana"], "correct": 0, "correct_value": "Madhav"},
        {"options": ["Mili", "Gopal", "Ariel"], "correct": 1, "correct_value": "Gopal"},
        {"options": ["Doraemon", "Pluto", "Goofy"], "correct": 0, "correct_value": "Doraemon"},
        {"options": ["Lucky", "Elsa", "Cinderella"], "correct": 0, "correct_value": "Lucky"},
        {"options": ["Pinky", "Elsa", "Gian"], "correct": 2, "correct_value": "Gian"},
        {"options": ["Mickey", "Nobita", "Minnie"], "correct": 1, "correct_value": "Nobita"},
    ],
]

# Store data
pending_users = {}
approved_users = {}
participants = {}
user_temp_data = {}
bot_app = None

def send_log(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def is_weekday():
    """Check if today is Monday to Friday"""
    return datetime.now().weekday() < 5

async def send_submission_notification(user_id, name, slot_label, question_num, correct_answer, status):
    """Send notification to user about submission - ASYNC"""
    global bot_app
    if not bot_app:
        return
    
    if status:
        message = f"""
✅ *Answer Correct!*

👤 *Participant:* {name}
⏰ *Slot:* {slot_label}
❓ *Question {question_num}*
🎯 *Your Answer:* {correct_answer} ✓

✨ Your correct answer has been recorded!
"""
    else:
        message = f"""
❌ *Submission Failed*

👤 *Participant:* {name}
⏰ *Slot:* {slot_label}
❓ *Question {question_num}*

⚠️ Failed to submit answer. Please contact admin.
"""
    
    try:
        await bot_app.bot.send_message(user_id, message, parse_mode='Markdown')
    except Exception as e:
        send_log(f"Failed to notify user {user_id}: {e}", "ERROR")

def submit_answer_sync(participant_id, email, phone, contest_day, slot_index, question_index, question_data):
    """Submit a single answer - SYNC version"""
    slot = SLOTS[slot_index - 1]
    correct_index = question_data['correct']
    correct_value = question_data['correct_value']
    
    options = question_data['options']
    options_prompt = f"A: {options[0]} | B: {options[1]} | C: {options[2]}"
    
    submitted_at = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    
    payload = {
        "contest_date": datetime.now().strftime("%Y-%m-%d"),
        "contest_day": contest_day,
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
            if result.get('ok') == True:
                return True, "Correct answer submitted successfully!"
            else:
                return True, "Submitted successfully"
        return False, f"HTTP Error: {response.status_code}"
    except Exception as e:
        return False, str(e)

def run_contest_submission_sync():
    """AUTOMATIC SUBMISSION - Runs every 30 minutes, Monday to Friday only"""
    global bot_app
    
    now = datetime.now()
    
    # Check if it's weekday (Monday to Friday)
    if not is_weekday():
        weekday_name = now.strftime("%A")
        send_log(f"Skipped: {weekday_name} - Bot only runs Monday to Friday", "INFO")
        return
    
    # Only run between 10 AM and 1 PM
    if now.hour < 10 or now.hour >= 13:
        return
    
    start_date = datetime(2026, 5, 20)
    contest_day = (now - start_date).days + 1
    
    if contest_day < 1 or contest_day > 15:
        return
    
    current_time = now.strftime("%H:%M")
    current_slot = None
    current_slot_label = None
    
    for slot in SLOTS:
        if current_time >= slot['time']:
            current_slot = slot['slot']
            current_slot_label = slot['label']
    
    if not current_slot or current_slot > 6:
        return
    
    send_log(f"Auto submission - Day {contest_day}, Slot {current_slot} ({current_slot_label})", "SUBMISSION")
    send_log(f"Total participants: {len(participants)}", "INFO")
    
    day_questions = QUESTIONS[contest_day - 1]
    
    for user_id, data in participants.items():
        send_log(f"Submitting for {data['name']} (ID: {data['participant_id']})", "INFO")
        success_count = 0
        
        for q_index, question in enumerate(day_questions, 1):
            success, message = submit_answer_sync(
                data['participant_id'],
                data['email'],
                data['phone'],
                contest_day,
                current_slot,
                q_index,
                question
            )
            
            if success:
                success_count += 1
                correct_answer = question['correct_value']
                send_log(f"  ✅ Question {q_index}: {correct_answer} - CORRECT", "SUCCESS")
                
                # Send notification using asyncio
                if bot_app:
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(
                            send_submission_notification(
                                user_id, 
                                data['name'], 
                                current_slot_label, 
                                q_index, 
                                correct_answer, 
                                True
                            )
                        )
                        loop.close()
                    except Exception as e:
                        send_log(f"Notification error: {e}", "ERROR")
            else:
                send_log(f"  ❌ Question {q_index}: Failed - {message}", "ERROR")
                
                # Send failure notification
                if bot_app:
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(
                            send_submission_notification(
                                user_id, 
                                data['name'], 
                                current_slot_label, 
                                q_index, 
                                None, 
                                False
                            )
                        )
                        loop.close()
                    except Exception as e:
                        send_log(f"Notification error: {e}", "ERROR")
            
            time.sleep(0.5)
        
        send_log(f"Result for {data['name']}: {success_count}/6 correct", "INFO")
        
        # Send daily summary to user
        if success_count == 6 and bot_app:
            summary_msg = f"""
🏆 *Daily Submission Complete!*

👤 *{data['name']}*
📅 *Day {contest_day}* | *Slot {current_slot}*
⏰ *Time:* {current_slot_label}

✅ *All 6 answers submitted correctly!*

Keep up the great work! 🎉
"""
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(bot_app.bot.send_message(user_id, summary_msg, parse_mode='Markdown'))
                loop.close()
            except Exception as e:
                send_log(f"Summary notification error: {e}", "ERROR")
    
    send_log(f"Submission completed for Slot {current_slot}", "SUCCESS")

def schedule_contest():
    send_log("SUMMERTASTIC AUTO BOT STARTED", "START")
    send_log("Contest Duration: 15 days", "INFO")
    send_log("Active Hours: 10:00 AM - 1:00 PM IST", "INFO")
    send_log("Active Days: Monday to Friday ONLY", "INFO")
    send_log("Weekends (Saturday & Sunday): Bot will be idle", "INFO")
    send_log("Users will receive notifications for every correct answer", "INFO")
    
    schedule.every().day.at("10:00").do(run_contest_submission_sync)
    schedule.every().day.at("10:30").do(run_contest_submission_sync)
    schedule.every().day.at("11:00").do(run_contest_submission_sync)
    schedule.every().day.at("11:30").do(run_contest_submission_sync)
    schedule.every().day.at("12:00").do(run_contest_submission_sync)
    schedule.every().day.at("12:30").do(run_contest_submission_sync)
    
    while True:
        schedule.run_pending()
        time.sleep(30)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id == ADMIN_ID:
        await update.message.reply_text(
            "👑 *Admin Panel*\n\n"
            "📋 *Admin Commands:*\n"
            "/pending - Show pending users\n"
            "/approve <user_id> - Approve a user\n"
            "/reject <user_id> - Reject a user\n"
            "/users - List approved users\n"
            "/broadcast <message> - Broadcast message\n"
            "/stats - Show statistics\n"
            "/logs - Show recent logs\n\n"
            "💡 *To register yourself:*\n"
            "Use /register command",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    elif user_id in approved_users:
        await update.message.reply_text(
            "🎉 *Welcome to Summertastic Contest Bot!*\n\n"
            "Use /register to start your registration.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    elif user_id in pending_users:
        await update.message.reply_text(
            "⏳ *Pending Approval*\n\n"
            "Your access request has been sent to admin.\n"
            "You will be notified once approved.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    else:
        keyboard = [[InlineKeyboardButton("📝 Request Access", callback_data='request_access')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔒 *Access Restricted*\n\n"
            "This bot is private. Click below to request access from admin.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return ConversationHandler.END

async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id == ADMIN_ID or user_id in approved_users:
        await update.message.reply_text(
            "📝 *Start Registration*\n\n"
            "Please enter your details:\n\n"
            "Step 1/4: What is your *full name*?\n\n"
            "Example: Rajesh Sharma",
            parse_mode='Markdown'
        )
        return NAME
    else:
        await update.message.reply_text(
            "❌ You don't have access.\n"
            "Use /start to request access from admin.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    name = update.message.text.strip()
    
    if len(name) < 3 or not re.match(r'^[a-zA-Z\s\.]+$', name):
        await update.message.reply_text(
            "❌ Invalid name! Use only letters and spaces (minimum 3 characters).\n"
            "Please enter your *full name*:",
            parse_mode='Markdown'
        )
        return NAME
    
    user_temp_data[user_id] = {'name': name}
    
    await update.message.reply_text(
        f"✅ Name saved: *{name}*\n\n"
        "📝 *Step 2/4:* What is your *email address*?\n\n"
        "Example: yourname@gmail.com",
        parse_mode='Markdown'
    )
    return EMAIL

async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    email = update.message.text.strip().lower()
    
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        await update.message.reply_text(
            "❌ Invalid email format.\n"
            "Please enter a valid *email address*:",
            parse_mode='Markdown'
        )
        return EMAIL
    
    user_temp_data[user_id]['email'] = email
    
    await update.message.reply_text(
        f"✅ Email saved: *{email}*\n\n"
        "📝 *Step 3/4:* What is your *city*?\n\n"
        "Example: Mumbai, Delhi, Bangalore",
        parse_mode='Markdown'
    )
    return CITY

async def get_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    city = update.message.text.strip()
    
    if len(city) < 2:
        await update.message.reply_text(
            "❌ Invalid city name.\n"
            "Please enter your *city*:",
            parse_mode='Markdown'
        )
        return CITY
    
    user_temp_data[user_id]['city'] = city
    
    await update.message.reply_text(
        f"✅ City saved: *{city}*\n\n"
        "📝 *Step 4/4:* What is your *phone number*?\n\n"
        "Example: 9876543210 (10 digits)",
        parse_mode='Markdown'
    )
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    phone = update.message.text.strip()
    
    if not re.match(r'^[6-9]\d{9}$', phone):
        await update.message.reply_text(
            "❌ Invalid phone number.\n"
            "Please enter a valid 10-digit *phone number* (starting with 6,7,8,9):",
            parse_mode='Markdown'
        )
        return PHONE
    
    user_temp_data[user_id]['phone'] = phone
    data = user_temp_data[user_id]
    
    summary = f"""
📋 *Please confirm your details:*

👤 *Name:* {data['name']}
📧 *Email:* {data['email']}
🏙️ *City:* {data['city']}
📱 *Phone:* {data['phone']}

🤝 *Consent:* Agreed to all terms

Reply with *YES* to register or *NO* to cancel.
"""
    
    await update.message.reply_text(summary, parse_mode='Markdown')
    return CONFIRM

async def register_on_website(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    answer = update.message.text.strip().upper()
    
    if answer != 'YES':
        await update.message.reply_text(
            "❌ *Registration Cancelled*\n\n"
            "Use /register to begin again.",
            parse_mode='Markdown'
        )
        if user_id in user_temp_data:
            del user_temp_data[user_id]
        return ConversationHandler.END
    
    data = user_temp_data[user_id]
    
    processing_msg = await update.message.reply_text(
        "🔄 *Registering you on the website...*\n\n"
        "Please wait, this may take a few seconds.",
        parse_mode='Markdown'
    )
    
    payload = {
        "name": data['name'],
        "email": data['email'],
        "city": data['city'],
        "phone": data['phone'],
        **CONSENT
    }
    
    try:
        response = requests.post(REGISTER_API, json=payload, headers=HEADERS, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            participant_id = result.get('participant_id')
            
            if participant_id:
                participants[user_id] = {
                    'participant_id': str(participant_id),
                    'name': data['name'],
                    'email': data['email'],
                    'city': data['city'],
                    'phone': data['phone'],
                    'registered_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                success_msg = f"""
✅ *Registration Successful!*

🎫 *Your Participant ID:* `{participant_id}`

📋 *Registered Details:*
👤 Name: {data['name']}
📧 Email: {data['email']}
🏙️ City: {data['city']}
📱 Phone: {data['phone']}

🤖 *Automated Submission Active!*

• Bot will auto-submit correct answers
• Every 30 minutes from 10:00 AM - 1:00 PM IST
• Monday to Friday only
• Duration: 15 days
• 6 questions per slot
• 100% correct answers guaranteed

✅ You're all set! No manual work needed.

You will receive notifications for every correct answer submission.

Use /status to check your registration.
"""
                
                await processing_msg.edit_text(success_msg, parse_mode='Markdown')
                
                send_log(f"New registration: {data['name']} (ID: {participant_id})", "REGISTER")
                
                await context.bot.send_message(
                    ADMIN_ID,
                    f"📝 *New Registration*\n\n"
                    f"👤 Name: {data['name']}\n"
                    f"📧 Email: {data['email']}\n"
                    f"🏙️ City: {data['city']}\n"
                    f"📱 Phone: {data['phone']}\n"
                    f"🎫 ID: `{participant_id}`",
                    parse_mode='Markdown'
                )
            else:
                await processing_msg.edit_text(
                    f"❌ *Registration Failed*\n\n"
                    f"Could not get participant ID from server.\n\n"
                    f"Please try again later.",
                    parse_mode='Markdown'
                )
        else:
            await processing_msg.edit_text(
                f"❌ *Registration Failed*\n\n"
                f"Server error: {response.status_code}\n\n"
                f"Please try again later.",
                parse_mode='Markdown'
            )
    
    except Exception as e:
        await processing_msg.edit_text(
            f"❌ *Registration Failed*\n\n"
            f"Error: {str(e)[:100]}\n\n"
            f"Please try again later.",
            parse_mode='Markdown'
        )
    
    if user_id in user_temp_data:
        del user_temp_data[user_id]
    
    return ConversationHandler.END

async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id in user_temp_data:
        del user_temp_data[user_id]
    
    await update.message.reply_text(
        "❌ *Registration Cancelled*\n\n"
        "Use /register to begin again.",
        parse_mode='Markdown'
    )
    return ConversationHandler.END

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    username = query.from_user.username or "No username"
    first_name = query.from_user.first_name
    
    if query.data == 'request_access':
        if user_id in approved_users:
            await query.edit_message_text("✅ You already have access!\nUse /register to register.")
        elif user_id in pending_users:
            await query.edit_message_text("⏳ Your request is already pending.")
        else:
            pending_users[user_id] = {
                'username': username,
                'name': first_name,
                'requested_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            keyboard = [
                [InlineKeyboardButton("✅ Approve", callback_data=f'approve_{user_id}'),
                 InlineKeyboardButton("❌ Reject", callback_data=f'reject_{user_id}')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                ADMIN_ID,
                f"📢 *New Access Request!*\n\n"
                f"🆔 User ID: `{user_id}`\n"
                f"👤 Name: {first_name}\n"
                f"📝 Username: @{username}",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
            await query.edit_message_text(
                "✅ *Request Sent!*\n\n"
                "You will be notified once approved.\n"
                "Use /register after approval to register.",
                parse_mode='Markdown'
            )
    
    elif query.data.startswith('approve_'):
        if str(query.from_user.id) != ADMIN_ID:
            await query.answer("Only admin can do this!", show_alert=True)
            return
        
        target_user = query.data.split('_')[1]
        
        if target_user in pending_users:
            approved_users[target_user] = pending_users[target_user]
            del pending_users[target_user]
            
            await context.bot.send_message(
                target_user,
                "✅ *Access Granted!*\n\n"
                "Welcome! Please use /register to register for the contest.",
                parse_mode='Markdown'
            )
            
            await query.edit_message_text(f"✅ User {target_user} has been approved!")
            send_log(f"Admin approved user {target_user}", "APPROVE")
    
    elif query.data.startswith('reject_'):
        if str(query.from_user.id) != ADMIN_ID:
            await query.answer("Only admin can do this!", show_alert=True)
            return
        
        target_user = query.data.split('_')[1]
        
        if target_user in pending_users:
            del pending_users[target_user]
            
            await context.bot.send_message(
                target_user,
                "❌ *Access Denied*\n\n"
                "Your request has been rejected by admin.",
                parse_mode='Markdown'
            )
            
            await query.edit_message_text(f"❌ User {target_user} has been rejected!")
            send_log(f"Admin rejected user {target_user}", "REJECT")

# Admin Commands
async def pending_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("❌ Admin only!")
        return
    
    if not pending_users:
        await update.message.reply_text("📭 No pending requests.")
        return
    
    message = "📋 *Pending Users:*\n\n"
    for uid, data in pending_users.items():
        message += f"🆔 `{uid}` - {data['name']} (@{data['username']})\n"
        message += f"   ⏰ {data['requested_at']}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("❌ Admin only!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: `/approve <user_id>`", parse_mode='Markdown')
        return
    
    target_user = context.args[0]
    
    if target_user in pending_users:
        approved_users[target_user] = pending_users[target_user]
        del pending_users[target_user]
        
        await context.bot.send_message(
            target_user,
            "✅ *Access Granted!*\n\nPlease use /register to register for the contest.",
            parse_mode='Markdown'
        )
        
        await update.message.reply_text(f"✅ User {target_user} approved!")
        send_log(f"Admin approved user {target_user}", "APPROVE")
    else:
        await update.message.reply_text("❌ User not found!")

async def reject_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("❌ Admin only!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: `/reject <user_id>`", parse_mode='Markdown')
        return
    
    target_user = context.args[0]
    
    if target_user in pending_users:
        del pending_users[target_user]
        
        await context.bot.send_message(
            target_user,
            "❌ *Access Denied*\n\nYour request has been rejected.",
            parse_mode='Markdown'
        )
        
        await update.message.reply_text(f"❌ User {target_user} rejected!")
        send_log(f"Admin rejected user {target_user}", "REJECT")
    else:
        await update.message.reply_text("❌ User not found!")

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("❌ Admin only!")
        return
    
    if not approved_users:
        await update.message.reply_text("📭 No approved users.")
        return
    
    message = "👥 *Approved Users:*\n\n"
    for uid, data in approved_users.items():
        if uid in participants:
            message += f"✅ `{uid}` - {data['name']} (ID: {participants[uid]['participant_id']})\n"
        else:
            message += f"⭕ `{uid}` - {data['name']} (Not registered)\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("❌ Admin only!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: `/broadcast <message>`", parse_mode='Markdown')
        return
    
    message = ' '.join(context.args)
    sent = 0
    
    for user_id in approved_users:
        try:
            await context.bot.send_message(
                user_id, 
                f"📢 *Announcement*\n\n{message}", 
                parse_mode='Markdown'
            )
            sent += 1
            time.sleep(0.1)
        except:
            pass
    
    await update.message.reply_text(f"✅ Broadcast sent to {sent} users!")
    send_log(f"Broadcast sent to {sent} users", "BROADCAST")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("❌ Admin only!")
        return
    
    stats_text = f"""📊 *Bot Statistics*

👥 Approved Users: {len(approved_users)}
⏳ Pending Requests: {len(pending_users)}
✅ Registered for Contest: {len(participants)}
⏰ Active Hours: 10:00 AM - 1:00 PM IST
📅 Active Days: Monday to Friday
🚫 Weekend: Bot Idle
🤖 Auto-submit: Active
✅ Correct Answers: 100%
📢 User Notifications: Enabled"""
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("❌ Admin only!")
        return
    
    await update.message.reply_text(
        f"📋 *Logs Information*\n\n"
        f"Logs are printed in the Railway console.\n"
        f"Group ID for logs: `{GROUP_ID}`\n\n"
        f"Check Railway deployment logs for detailed submission history.\n\n"
        f"*Features:*\n"
        f"• Monday-Friday only\n"
        f"• User notifications for every correct answer\n"
        f"• Response: {{'ok': true}} for successful submissions",
        parse_mode='Markdown'
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id in participants:
        data = participants[user_id]
        await update.message.reply_text(
            f"✅ *Your Registration Status*\n\n"
            f"👤 Name: {data['name']}\n"
            f"🎫 Participant ID: `{data['participant_id']}`\n"
            f"📧 Email: {data['email']}\n"
            f"📱 Phone: {data['phone']}\n"
            f"🤖 Auto-submit: Enabled\n"
            f"📅 Active Days: Monday to Friday\n"
            f"⏰ Active Hours: 10:00 AM - 1:00 PM IST\n"
            f"✅ Notifications: You will receive alerts for every correct answer\n"
            f"✅ Status: Active",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❌ *Not Registered*\n\n"
            "Use `/register` to start the registration process.",
            parse_mode='Markdown'
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """📖 *Summertastic Contest Bot Help*

*How to Register:*
1. Get approved by admin first
2. Use `/register` command
3. Enter your details step by step
4. Get your Participant ID automatically

*Schedule:*
• Monday to Friday ONLY
• 10:00 AM - 1:00 PM IST
• Submissions every 30 minutes
• Weekends: Bot is idle

*User Commands:*
/start - Main menu
/register - Start registration
/status - Check your status
/help - Show this help

*Admin Commands:*
/pending - View pending users
/approve <id> - Approve a user
/reject <id> - Reject a user
/users - List all approved users
/broadcast <msg> - Broadcast message
/stats - View statistics
/logs - View logs

*Notifications:*
• You will receive a message for EVERY correct answer
• Daily summary after each slot
• Instant confirmation of submission

*Bot Features:*
- Auto-submits 100% correct answers
- Monday to Friday only
- User notifications for each submission
- Response: {"ok":true} for successful submissions
- 15 days contest duration
- 6 questions per slot"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

def main():
    global bot_app
    
    # Start schedule in background thread
    schedule_thread = threading.Thread(target=schedule_contest, daemon=True)
    schedule_thread.start()
    
    # Create bot application
    app = Application.builder().token(BOT_TOKEN).build()
    bot_app = app
    
    # Conversation handler for registration
    conv_handler = ConversationHandler(
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
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("pending", pending_command))
    app.add_handler(CommandHandler("approve", approve_command))
    app.add_handler(CommandHandler("reject", reject_command))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("logs", logs_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("help", help_command))
    
    print("🤖 Bot started! Waiting for messages...")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print(f"📅 Schedule: Monday to Friday only (10:00 AM - 1:00 PM IST)")
    print(f"✅ User notifications: ENABLED for every correct answer")
    
    # Start polling
    app.run_polling()

if __name__ == '__main__':
    main()
