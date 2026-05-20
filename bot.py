import requests
import json
import schedule
import time
import threading
import os
import re
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, ContextTypes

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "8687160226:AAHKPurDJS8kyxrblV0X8mZdSbFwFUV56Yw")
ADMIN_ID = os.getenv("ADMIN_ID", "1922522807")
GROUP_ID = os.getenv("GROUP_ID", "-1003862731449")

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
        {"options": ["Tina", "Gopal", "Mira"], "correct": 1},
        {"options": ["Lucky", "Harry", "Nobita"], "correct": 2},
        {"options": ["Lucky", "Elsa", "Moana"], "correct": 0},
        {"options": ["Mickey", "Doraemon", "Goofy"], "correct": 1},
        {"options": ["Shizuka", "Harry", "Lucky"], "correct": 0},
        {"options": ["Madhav", "Ariel", "Rapunzel"], "correct": 0},
    ],
    # Day 2
    [
        {"options": ["Shinchan", "Doraemon", "Gian"], "correct": 2},
        {"options": ["Pappu", "Nobita", "Titu"], "correct": 1},
        {"options": ["Tiana", "Diana", "Lucky"], "correct": 2},
        {"options": ["Doraemon", "Harry", "Mickey"], "correct": 0},
        {"options": ["Madhav", "Goofy", "Pluto"], "correct": 0},
        {"options": ["Cinderella", "Gopal", "Ariel"], "correct": 1},
    ],
    # Day 3
    [
        {"options": ["Madhav", "Cinderella", "Tiana"], "correct": 0},
        {"options": ["Doraemon", "Shizuka", "Harry"], "correct": 1},
        {"options": ["Mili", "Gopal", "Myra"], "correct": 1},
        {"options": ["Mickey", "Donald", "Nobita"], "correct": 2},
        {"options": ["Doraemon", "Nobita", "Shizuka"], "correct": 0},
        {"options": ["Tina", "Lucky", "Pinky"], "correct": 1},
    ],
    # Day 4
    [
        {"options": ["Lucky", "Elsa", "Anna"], "correct": 0},
        {"options": ["Harry", "Doraemon", "Mickey"], "correct": 1},
        {"options": ["Madhav", "Daisy", "Donald"], "correct": 0},
        {"options": ["Mickey", "Minnie", "Shizuka"], "correct": 2},
        {"options": ["Ariel", "Mulan", "Gopal"], "correct": 2},
        {"options": ["Nobita", "Goofy", "Pinky"], "correct": 0},
    ],
    # Day 5
    [
        {"options": ["Doraemon", "Mickey", "Donald"], "correct": 0},
        {"options": ["Gian", "Pluto", "Ariel"], "correct": 0},
        {"options": ["Radha", "Mili", "Madhav"], "correct": 2},
        {"options": ["Elsa", "Lucky", "Pinky"], "correct": 1},
        {"options": ["Pappu", "Nobita", "Pluto"], "correct": 1},
        {"options": ["Gopal", "Diana", "Daisy"], "correct": 0},
    ],
    # Day 6
    [
        {"options": ["Gopal", "Mili", "Minnie"], "correct": 0},
        {"options": ["Shizuka", "Lucky", "Elsa"], "correct": 1},
        {"options": ["Ariel", "Gian", "Shinchan"], "correct": 1},
        {"options": ["Madhav", "Dorami", "Doraemon"], "correct": 0},
        {"options": ["Harry", "Mickey", "Doraemon"], "correct": 2},
        {"options": ["Pluto", "Nobita", "Goofy"], "correct": 1},
    ],
    # Day 7
    [
        {"options": ["Ariel", "Lucky", "Moana"], "correct": 1},
        {"options": ["Doraemon", "Donald", "Mickey"], "correct": 0},
        {"options": ["Doraemon", "Dorami", "Nobita"], "correct": 2},
        {"options": ["Pinky", "Gian", "Hemawari"], "correct": 1},
        {"options": ["Doraemon", "Madhav", "Pluto"], "correct": 1},
        {"options": ["Gopal", "Daisy", "Donald"], "correct": 0},
    ],
    # Day 8
    [
        {"options": ["Tina", "Gopal", "Mira"], "correct": 1},
        {"options": ["Lucky", "Harry", "Nobita"], "correct": 2},
        {"options": ["Lucky", "Elsa", "Moana"], "correct": 0},
        {"options": ["Mickey", "Doraemon", "Goofy"], "correct": 1},
        {"options": ["Shizuka", "Harry", "Lucky"], "correct": 0},
        {"options": ["Madhav", "Ariel", "Rapunzel"], "correct": 0},
    ],
    # Day 9
    [
        {"options": ["Madhav", "Cinderella", "Tiana"], "correct": 0},
        {"options": ["Doraemon", "Shizuka", "Harry"], "correct": 1},
        {"options": ["Mili", "Gopal", "Myra"], "correct": 1},
        {"options": ["Mickey", "Donald", "Nobita"], "correct": 2},
        {"options": ["Doraemon", "Nobita", "Shizuka"], "correct": 0},
        {"options": ["Tina", "Lucky", "Pinky"], "correct": 1},
    ],
    # Day 10
    [
        {"options": ["Lucky", "Elsa", "Anna"], "correct": 0},
        {"options": ["Harry", "Doraemon", "Mickey"], "correct": 1},
        {"options": ["Madhav", "Daisy", "Donald"], "correct": 0},
        {"options": ["Mickey", "Minnie", "Shizuka"], "correct": 2},
        {"options": ["Ariel", "Mulan", "Gopal"], "correct": 2},
        {"options": ["Nobita", "Goofy", "Pinky"], "correct": 0},
    ],
    # Day 11
    [
        {"options": ["Shinchan", "Doraemon", "Gian"], "correct": 2},
        {"options": ["Pappu", "Nobita", "Titu"], "correct": 1},
        {"options": ["Tiana", "Diana", "Lucky"], "correct": 2},
        {"options": ["Doraemon", "Harry", "Mickey"], "correct": 0},
        {"options": ["Madhav", "Goofy", "Pluto"], "correct": 0},
        {"options": ["Cinderella", "Gopal", "Ariel"], "correct": 1},
    ],
    # Day 12
    [
        {"options": ["Doraemon", "Mickey", "Donald"], "correct": 0},
        {"options": ["Gian", "Pluto", "Ariel"], "correct": 0},
        {"options": ["Radha", "Mili", "Madhav"], "correct": 2},
        {"options": ["Elsa", "Lucky", "Pinky"], "correct": 1},
        {"options": ["Pappu", "Nobita", "Pluto"], "correct": 1},
        {"options": ["Gopal", "Diana", "Daisy"], "correct": 0},
    ],
    # Day 13
    [
        {"options": ["Gopal", "Mili", "Minnie"], "correct": 0},
        {"options": ["Shizuka", "Lucky", "Elsa"], "correct": 1},
        {"options": ["Ariel", "Gian", "Shinchan"], "correct": 1},
        {"options": ["Madhav", "Dorami", "Doraemon"], "correct": 0},
        {"options": ["Harry", "Mickey", "Doraemon"], "correct": 2},
        {"options": ["Pluto", "Nobita", "Goofy"], "correct": 1},
    ],
    # Day 14
    [
        {"options": ["Ariel", "Lucky", "Moana"], "correct": 1},
        {"options": ["Doraemon", "Donald", "Mickey"], "correct": 0},
        {"options": ["Doraemon", "Dorami", "Nobita"], "correct": 2},
        {"options": ["Pinky", "Gian", "Hemawari"], "correct": 1},
        {"options": ["Doraemon", "Madhav", "Pluto"], "correct": 1},
        {"options": ["Gopal", "Daisy", "Donald"], "correct": 0},
    ],
    # Day 15
    [
        {"options": ["Madhav", "Daisy", "Diana"], "correct": 0},
        {"options": ["Mili", "Gopal", "Ariel"], "correct": 1},
        {"options": ["Doraemon", "Pluto", "Goofy"], "correct": 0},
        {"options": ["Lucky", "Elsa", "Cinderella"], "correct": 0},
        {"options": ["Pinky", "Elsa", "Gian"], "correct": 2},
        {"options": ["Mickey", "Nobita", "Minnie"], "correct": 1},
    ],
]

# Store data
pending_users = {}
approved_users = {}
participants = {}
user_temp_data = {}

async def send_log(context, message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        if context:
            await context.bot.send_message(
                GROUP_ID,
                f"[{level}] {timestamp}\n{message}"
            )
    except Exception as e:
        print(f"Failed to send log: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id == ADMIN_ID:
        await update.message.reply_text(
            "Admin Panel\n\n"
            "Admin Commands:\n"
            "/pending - Show pending users\n"
            "/approve <user_id> - Approve a user\n"
            "/reject <user_id> - Reject a user\n"
            "/users - List approved users\n"
            "/broadcast <message> - Broadcast message\n"
            "/stats - Show statistics\n"
            "/logs - Show recent logs"
        )
        return ConversationHandler.END
    
    elif user_id in approved_users:
        await update.message.reply_text(
            "Welcome to Summertastic Contest Bot!\n\n"
            "Let's register you for the contest. Please enter your details:\n\n"
            "Step 1/4: What is your full name?\n\n"
            "Example: Rajesh Sharma"
        )
        return NAME
    
    elif user_id in pending_users:
        await update.message.reply_text(
            "Pending Approval\n\n"
            "Your access request has been sent to admin.\n"
            "You will be notified once approved."
        )
        return ConversationHandler.END
    
    else:
        keyboard = [[InlineKeyboardButton("Request Access", callback_data='request_access')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Access Restricted\n\n"
            "This bot is private. Click below to request access from admin.",
            reply_markup=reply_markup
        )
        return ConversationHandler.END

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    name = update.message.text.strip()
    
    if len(name) < 3 or not re.match(r'^[a-zA-Z\s\.]+$', name):
        await update.message.reply_text(
            "Invalid name! Use only letters and spaces (minimum 3 characters).\n"
            "Please enter your full name:"
        )
        return NAME
    
    user_temp_data[user_id] = {'name': name}
    
    await update.message.reply_text(
        f"Name saved: {name}\n\n"
        "Step 2/4: What is your email address?\n\n"
        "Example: yourname@gmail.com"
    )
    return EMAIL

async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    email = update.message.text.strip().lower()
    
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        await update.message.reply_text(
            "Invalid email format.\n"
            "Please enter a valid email address:"
        )
        return EMAIL
    
    user_temp_data[user_id]['email'] = email
    
    await update.message.reply_text(
        f"Email saved: {email}\n\n"
        "Step 3/4: What is your city?\n\n"
        "Example: Mumbai, Delhi, Bangalore"
    )
    return CITY

async def get_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    city = update.message.text.strip()
    
    if len(city) < 2:
        await update.message.reply_text(
            "Invalid city name.\n"
            "Please enter your city:"
        )
        return CITY
    
    user_temp_data[user_id]['city'] = city
    
    await update.message.reply_text(
        f"City saved: {city}\n\n"
        "Step 4/4: What is your phone number?\n\n"
        "Example: 9876543210 (10 digits)"
    )
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    phone = update.message.text.strip()
    
    if not re.match(r'^[6-9]\d{9}$', phone):
        await update.message.reply_text(
            "Invalid phone number.\n"
            "Please enter a valid 10-digit phone number (starting with 6,7,8,9):"
        )
        return PHONE
    
    user_temp_data[user_id]['phone'] = phone
    data = user_temp_data[user_id]
    
    summary = f"""
Please confirm your details:

Name: {data['name']}
Email: {data['email']}
City: {data['city']}
Phone: {data['phone']}

Consent: Agreed to all terms

Reply with YES to register or NO to cancel.
"""
    
    await update.message.reply_text(summary)
    return CONFIRM

async def register_on_website(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    answer = update.message.text.strip().upper()
    
    if answer != 'YES':
        await update.message.reply_text(
            "Registration Cancelled\n\n"
            "Use /start to begin again."
        )
        if user_id in user_temp_data:
            del user_temp_data[user_id]
        return ConversationHandler.END
    
    data = user_temp_data[user_id]
    
    processing_msg = await update.message.reply_text(
        "Registering you on the website...\n\n"
        "Please wait, this may take a few seconds."
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
Registration Successful!

Your Participant ID: {participant_id}

Registered Details:
Name: {data['name']}
Email: {data['email']}
City: {data['city']}
Phone: {data['phone']}

Automated Submission Active!

- Bot will auto-submit correct answers
- Every 30 minutes from 10:00 AM - 1:00 PM IST
- Duration: 15 days
- 6 questions per slot
- 100% correct answers guaranteed

You're all set! No manual work needed.

Use /status to check your registration.
"""
                
                await processing_msg.edit_text(success_msg)
                
                await send_log(context, f"New registration: {data['name']} (ID: {participant_id})", "REGISTER")
                
                await context.bot.send_message(
                    ADMIN_ID,
                    f"New Registration\n\n"
                    f"Name: {data['name']}\n"
                    f"Email: {data['email']}\n"
                    f"City: {data['city']}\n"
                    f"Phone: {data['phone']}\n"
                    f"ID: {participant_id}"
                )
            else:
                await processing_msg.edit_text(
                    f"Registration Failed\n\n"
                    f"Could not get participant ID from server.\n\n"
                    f"Please try again later."
                )
        else:
            await processing_msg.edit_text(
                f"Registration Failed\n\n"
                f"Server error: {response.status_code}\n\n"
                f"Please try again later."
            )
    
    except Exception as e:
        await processing_msg.edit_text(
            f"Registration Failed\n\n"
            f"Error: {str(e)[:100]}\n\n"
            f"Please try again later."
        )
    
    if user_id in user_temp_data:
        del user_temp_data[user_id]
    
    return ConversationHandler.END

async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id in user_temp_data:
        del user_temp_data[user_id]
    
    await update.message.reply_text(
        "Registration Cancelled\n\n"
        "Use /start to begin again."
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
            await query.edit_message_text("You already have access! Use /start to register.")
        elif user_id in pending_users:
            await query.edit_message_text("Your request is already pending.")
        else:
            pending_users[user_id] = {
                'username': username,
                'name': first_name,
                'requested_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            keyboard = [
                [InlineKeyboardButton("Approve", callback_data=f'approve_{user_id}'),
                 InlineKeyboardButton("Reject", callback_data=f'reject_{user_id}')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                ADMIN_ID,
                f"New Access Request!\n\n"
                f"User ID: {user_id}\n"
                f"Name: {first_name}\n"
                f"Username: @{username}",
                reply_markup=reply_markup
            )
            
            await query.edit_message_text(
                "Request Sent!\n\n"
                "You will be notified once approved.\n"
                "Use /start again after approval to register."
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
                "Access Granted!\n\n"
                "Welcome! Please use /start to register for the contest."
            )
            
            await query.edit_message_text(f"User {target_user} has been approved!")
            await send_log(context, f"Admin approved user {target_user}", "APPROVE")
    
    elif query.data.startswith('reject_'):
        if str(query.from_user.id) != ADMIN_ID:
            await query.answer("Only admin can do this!", show_alert=True)
            return
        
        target_user = query.data.split('_')[1]
        
        if target_user in pending_users:
            del pending_users[target_user]
            
            await context.bot.send_message(
                target_user,
                "Access Denied\n\n"
                "Your request has been rejected by admin."
            )
            
            await query.edit_message_text(f"User {target_user} has been rejected!")
            await send_log(context, f"Admin rejected user {target_user}", "REJECT")

def submit_answer(participant_id, email, phone, contest_day, slot_index, question_index, question_data):
    slot = SLOTS[slot_index - 1]
    correct_index = question_data['correct']
    correct_value = question_data['options'][correct_index]
    
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
        return response.status_code == 200, response.text
    except Exception as e:
        return False, str(e)

def run_contest_submission_sync():
    """AUTOMATIC SUBMISSION - Runs every 30 minutes"""
    now = datetime.now()
    
    if now.hour < 10 or now.hour >= 13:
        return
    
    start_date = datetime(2026, 5, 20)
    contest_day = (now - start_date).days + 1
    
    if contest_day < 1 or contest_day > 15:
        return
    
    current_time = now.strftime("%H:%M")
    current_slot = None
    
    for slot in SLOTS:
        if current_time >= slot['time']:
            current_slot = slot['slot']
    
    if not current_slot or current_slot > 6:
        return
    
    print(f"\nAUTOMATIC SUBMISSION - {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Day {contest_day}, Slot {current_slot} ({SLOTS[current_slot-1]['label']})")
    print(f"Total participants: {len(participants)}")
    
    day_questions = QUESTIONS[contest_day - 1]
    
    for user_id, data in participants.items():
        print(f"\nSubmitting for {data['name']} (ID: {data['participant_id']})")
        success_count = 0
        
        for q_index, question in enumerate(day_questions, 1):
            success, response = submit_answer(
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
                print(f"  Question {q_index}: Correct answer submitted")
            else:
                print(f"  Question {q_index}: Failed")
            
            time.sleep(0.5)
        
        print(f"  Result: {success_count}/6 correct")
    
    print(f"\nAutomatic submission completed for Slot {current_slot}\n")

def schedule_contest():
    print("=" * 50)
    print("SUMMERTASTIC AUTO BOT STARTED")
    print("=" * 50)
    print("Contest Duration: 15 days")
    print("Active Hours: 10:00 AM - 1:00 PM IST")
    print("Submissions every 30 minutes:")
    print("   10:00 AM - Slot 1")
    print("   10:30 AM - Slot 2")
    print("   11:00 AM - Slot 3")
    print("   11:30 AM - Slot 4")
    print("   12:00 PM - Slot 5")
    print("   12:30 PM - Slot 6")
    print("=" * 50)
    print("Bot will automatically submit correct answers!")
    print("=" * 50)
    
    schedule.every().day.at("10:00").do(run_contest_submission_sync)
    schedule.every().day.at("10:30").do(run_contest_submission_sync)
    schedule.every().day.at("11:00").do(run_contest_submission_sync)
    schedule.every().day.at("11:30").do(run_contest_submission_sync)
    schedule.every().day.at("12:00").do(run_contest_submission_sync)
    schedule.every().day.at("12:30").do(run_contest_submission_sync)
    
    while True:
        schedule.run_pending()
        time.sleep(30)

# Admin Commands
async def pending_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("Admin only!")
        return
    
    if not pending_users:
        await update.message.reply_text("No pending requests.")
        return
    
    message = "Pending Users:\n\n"
    for uid, data in pending_users.items():
        message += f"ID: {uid} - {data['name']} (@{data['username']})\n"
        message += f"Time: {data['requested_at']}\n\n"
    
    await update.message.reply_text(message)

async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("Admin only!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /approve <user_id>")
        return
    
    target_user = context.args[0]
    
    if target_user in pending_users:
        approved_users[target_user] = pending_users[target_user]
        del pending_users[target_user]
        
        await context.bot.send_message(
            target_user,
            "Access Granted! Please use /start to register."
        )
        
        await update.message.reply_text(f"User {target_user} approved!")
        await send_log(context, f"Admin approved user {target_user}", "APPROVE")
    else:
        await update.message.reply_text("User not found!")

async def reject_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("Admin only!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /reject <user_id>")
        return
    
    target_user = context.args[0]
    
    if target_user in pending_users:
        del pending_users[target_user]
        
        await context.bot.send_message(
            target_user,
            "Access Denied. Your request has been rejected."
        )
        
        await update.message.reply_text(f"User {target_user} rejected!")
        await send_log(context, f"Admin rejected user {target_user}", "REJECT")
    else:
        await update.message.reply_text("User not found!")

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("Admin only!")
        return
    
    if not approved_users:
        await update.message.reply_text("No approved users.")
        return
    
    message = "Approved Users:\n\n"
    for uid, data in approved_users.items():
        if uid in participants:
            message += f"ID: {uid} - {data['name']} (Registered: Yes, ID: {participants[uid]['participant_id']})\n"
        else:
            message += f"ID: {uid} - {data['name']} (Registered: No)\n"
    
    await update.message.reply_text(message)

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("Admin only!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    
    message = ' '.join(context.args)
    
    sent = 0
    for user_id in approved_users:
        try:
            await context.bot.send_message(user_id, f"Announcement: {message}")
            sent += 1
            time.sleep(0.1)
        except:
            pass
    
    await update.message.reply_text(f"Broadcast sent to {sent} users!")
    await send_log(context, f"Broadcast sent to {sent} users", "BROADCAST")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("Admin only!")
        return
    
    stats_text = f"""Bot Statistics:

Approved Users: {len(approved_users)}
Pending Requests: {len(pending_users)}
Registered for Contest: {len(participants)}
Active Hours: 10:00 AM - 1:00 PM IST
Auto-submit: Active
Correct Answers: 100%"""
    
    await update.message.reply_text(stats_text)

async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("Admin only!")
        return
    
    await update.message.reply_text(f"Logs are sent to the log group.\n\nGroup ID: {GROUP_ID}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id in participants:
        data = participants[user_id]
        await update.message.reply_text(
            f"Registration Status:\n\n"
            f"Name: {data['name']}\n"
            f"Participant ID: {data['participant_id']}\n"
            f"Email: {data['email']}\n"
            f"Phone: {data['phone']}\n"
            f"Auto-submit: Enabled"
        )
    else:
        await update.message.reply_text("Not registered. Use /start to register.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """Summertastic Contest Bot Help

How to Register:
1. Send /start
2. Enter your full name
3. Enter your email address
4. Enter your city
5. Enter your phone number
6. Confirm your details

Bot Features:
- Auto-submits correct answers every 30 min
- Active hours: 10:00 AM - 1:00 PM IST
- Duration: 15 days
- 6 questions per slot
- 100% correct answers

Commands:
/start - Start registration
/status - Check registration status
/help - Show this help

Admin Commands:
/pending - View pending requests
/approve <id> - Approve a user
/reject <id> - Reject a user
/users - List approved users
/broadcast <msg> - Send announcement
/stats - View statistics
/logs - View logs"""
    
    await update.message.reply_text(help_text)

def main():
    # Start schedule in background thread
    schedule_thread = threading.Thread(target=schedule_contest, daemon=True)
    schedule_thread.start()
    
    # Create bot application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Conversation handler for registration
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_city)],
           
