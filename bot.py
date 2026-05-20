import requests
import json
import schedule
import time
import threading
import os
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Bot configuration from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN", "8687160226:AAHKPurDJS8kyxrblV0X8mZdSbFwFUV56Yw")
ADMIN_ID = os.getenv("ADMIN_ID", "1922522807")
GROUP_ID = os.getenv("GROUP_ID", "-1003862731449")

# API endpoint
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
submission_logs = []

async def send_log(context, message, level="INFO"):
    """Send log to group and store in memory"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {
        'timestamp': timestamp,
        'level': level,
        'message': message
    }
    
    submission_logs.append(log_entry)
    if len(submission_logs) > 100:
        submission_logs.pop(0)
    
    try:
        if context:
            await context.bot.send_message(
                GROUP_ID,
                f"📋 *LOG* [{level}]\n`{timestamp}`\n{message}",
                parse_mode='Markdown'
            )
    except Exception as e:
        print(f"Failed to send log: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or "No username"
    
    await send_log(context, f"User {username} ({user_id}) started the bot", "INFO")
    
    if user_id == ADMIN_ID:
        await update.message.reply_text(
            "👑 *Admin Panel*\n\n"
            "You have full access to the bot.\n\n"
            "*Admin Commands:*\n"
            "/pending - Show pending users\n"
            "/approve <user_id> - Approve a user\n"
            "/reject <user_id> - Reject a user\n"
            "/users - List all approved users\n"
            "/broadcast <message> - Send message to all users\n"
            "/stats - Show bot statistics\n"
            "/logs - Show recent logs",
            parse_mode='Markdown'
        )
    elif user_id in approved_users:
        await update.message.reply_text(
            "✅ *Welcome Back!*\n\n"
            "You are already approved. Use these commands:\n"
            "/register - Register for contest\n"
            "/status - Check your status\n"
            "/help - Show help",
            parse_mode='Markdown'
        )
    elif user_id in pending_users:
        await update.message.reply_text(
            "⏳ *Pending Approval*\n\n"
            "Your request has been sent to admin. Please wait for approval.",
            parse_mode='Markdown'
        )
    else:
        keyboard = [[InlineKeyboardButton("📝 Request Access", callback_data='request_access')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔒 *Access Restricted*\n\n"
            "This bot is private. Only approved users can use it.\n\n"
            "Click the button below to request access.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    username = query.from_user.username or "No username"
    first_name = query.from_user.first_name
    
    if query.data == 'request_access':
        if user_id in approved_users:
            await query.edit_message_text("✅ You already have access!")
        elif user_id in pending_users:
            await query.edit_message_text("⏳ Your request is already pending.")
        else:
            pending_users[user_id] = {
                'username': username,
                'name': first_name,
                'requested_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            await send_log(context, f"Access request from {first_name} (@{username})", "REQUEST")
            
            keyboard = [
                [InlineKeyboardButton("✅ Approve", callback_data=f'approve_{user_id}'),
                 InlineKeyboardButton("❌ Reject", callback_data=f'reject_{user_id}')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                ADMIN_ID,
                f"📢 *New Access Request!*\n\n"
                f"User ID: `{user_id}`\n"
                f"Name: {first_name}\n"
                f"Username: @{username}",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
            await query.edit_message_text(
                "✅ *Request Sent!*\n\n"
                "You'll be notified once approved.",
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
            
            await send_log(context, f"Admin approved user {target_user}", "APPROVE")
            
            await context.bot.send_message(
                target_user,
                "✅ *Access Granted!*\n\nUse /start to begin!",
                parse_mode='Markdown'
            )
            
            await query.edit_message_text(f"✅ User {target_user} approved!")
    
    elif query.data.startswith('reject_'):
        if str(query.from_user.id) != ADMIN_ID:
            await query.answer("Only admin can do this!", show_alert=True)
            return
        
        target_user = query.data.split('_')[1]
        
        if target_user in pending_users:
            del pending_users[target_user]
            
            await send_log(context, f"Admin rejected user {target_user}", "REJECT")
            
            await context.bot.send_message(
                target_user,
                "❌ *Access Denied*\n\nYour request was rejected.",
                parse_mode='Markdown'
            )
            
            await query.edit_message_text(f"❌ User {target_user} rejected!")

async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in approved_users and user_id != ADMIN_ID:
        await update.message.reply_text("❌ You don't have access.")
        return
    
    if len(context.args) < 4:
        await update.message.reply_text(
            "❌ *Usage:* `/register name email phone participant_id`\n\n"
            "Example: `/register Rajesh rajesh@gmail.com 9876543210 4187`",
            parse_mode='Markdown'
        )
        return
    
    name = context.args[0]
    email = context.args[1]
    phone = context.args[2]
    participant_id = context.args[3]
    
    participants[user_id] = {
        'participant_id': participant_id,
        'name': name,
        'email': email,
        'phone': phone,
        'registered_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    await send_log(context, f"User {name} ({user_id}) registered with ID: {participant_id}", "REGISTER")
    
    await update.message.reply_text(
        f"✅ *Registration Successful!*\n\n"
        f"👤 Name: {name}\n"
        f"🎫 Participant ID: `{participant_id}`\n"
        f"🤖 Bot will auto-submit correct answers!",
        parse_mode='Markdown'
    )

def submit_answer(participant_id, email, phone, contest_day, slot_index, question_index, question_data):
    """Submit a single answer - ALWAYS CORRECT"""
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

async def run_contest_submission(context: ContextTypes.DEFAULT_TYPE = None):
    """Submit answers for current day and slot"""
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
    
    log_msg = f"🤖 Starting submission - Day {contest_day}, Slot {current_slot}"
    print(log_msg)
    
    if context:
        await send_log(context, log_msg, "SUBMISSION")
    
    day_questions = QUESTIONS[contest_day - 1]
    
    for user_id, data in participants.items():
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
            
            time.sleep(0.5)
        
        if success_count == 6 and context:
            await send_log(context, f"✅ {data['name']} - All 6 answers correct!", "SUCCESS")

def schedule_contest():
    """Schedule submissions every 30 minutes"""
    schedule.every().day.at("10:00").do(lambda: asyncio.run(run_contest_submission(None)))
    schedule.every().day.at("10:30").do(lambda: asyncio.run(run_contest_submission(None)))
    schedule.every().day.at("11:00").do(lambda: asyncio.run(run_contest_submission(None)))
    schedule.every().day.at("11:30").do(lambda: asyncio.run(run_contest_submission(None)))
    schedule.every().day.at("12:00").do(lambda: asyncio.run(run_contest_submission(None)))
    schedule.every().day.at("12:30").do(lambda: asyncio.run(run_contest_submission(None)))
    
    while True:
        schedule.run_pending()
        time.sleep(60)

# Admin Commands
async def pending_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("❌ Admin only!")
        return
    
    if not pending_users:
        await update.message.reply_text("📭 No pending requests.")
        return
    
    message = "📋 *Pending Users:*\n\n"
    for uid, data in pending_users.items():
        message += f"🆔 `{uid}` - {data['name']} (@{data['username']})\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("❌ Admin only!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /approve <user_id>")
        return
    
    target_user = context.args[0]
    
    if target_user in pending_users:
        approved_users[target_user] = pending_users[target_user]
        del pending_users[target_user]
        
        await send_log(context, f"Admin approved user {target_user}", "APPROVE")
        
        await context.bot.send_message(
            target_user,
            "✅ *Access Granted!* Use /start to begin.",
            parse_mode='Markdown'
        )
        
        await update.message.reply_text(f"✅ User {target_user} approved!")

async def reject_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("❌ Admin only!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /reject <user_id>")
        return
    
    target_user = context.args[0]
    
    if target_user in pending_users:
        del pending_users[target_user]
        
        await send_log(context, f"Admin rejected user {target_user}", "REJECT")
        
        await context.bot.send_message(
            target_user,
            "❌ *Access Denied*",
            parse_mode='Markdown'
        )
        
        await update.message.reply_text(f"❌ User {target_user} rejected!")

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("❌ Admin only!")
        return
    
    if not approved_users:
        await update.message.reply_text("📭 No approved users.")
        return
    
    message = "👥 *Approved Users:*\n\n"
    for uid, data in approved_users.items():
        registered = "✅" if uid in participants else "⭕"
        message += f"{registered} `{uid}` - {data['name']}\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("❌ Admin only!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    
    message = ' '.join(context.args)
    
    await send_log(context, f"Broadcast: {message[:50]}", "BROADCAST")
    
    sent = 0
    for user_id in approved_users:
        try:
            await context.bot.send_message(user_id, f"📢 *Announcement*\n\n{message}", parse_mode='Markdown')
            sent += 1
            time.sleep(0.1)
        except:
            pass
    
    await update.message.reply_text(f"✅ Broadcast sent to {sent} users!")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("❌ Admin only!")
        return
    
    stats = f"📊 *Statistics*\n\n"
    stats += f"👥 Approved: {len(approved_users)}\n"
    stats += f"⏳ Pending: {len(pending_users)}\n"
    stats += f"✅ Registered: {len(participants)}\n"
    stats += f"📝 Logs: {len(submission_logs)}"
    
    await update.message.reply_text(stats, parse_mode='Markdown')

async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("❌ Admin only!")
        return
    
    if not submission_logs:
        await update.message.reply_text("📭 No logs.")
        return
    
    recent_logs = submission_logs[-10:]
    message = "📋 *Recent Logs:*\n\n"
    
    for log in recent_logs:
        emoji = "📝"
        if log['level'] == "SUCCESS":
            emoji = "✅"
        elif log['level'] == "ERROR":
            emoji = "❌"
        message += f"{emoji} *{log['level']}* `{log['timestamp']}`\n   {log['message'][:50]}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in approved_users and user_id != ADMIN_ID:
        await update.message.reply_text("❌ No access.")
        return
    
    if user_id in participants:
        await update.message.reply_text(
            f"✅ *Active*\n\n"
            f"👤 {participants[user_id]['name']}\n"
            f"🎫 ID: `{participants[user_id]['participant_id']}`\n"
            f"🤖 Auto-submit: Enabled",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("⚠️ Not registered. Use /register")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Commands*\n\n"
        "/start - Main menu\n"
        "/register - Register for contest\n"
        "/status - Check status\n"
        "/help - This help",
        parse_mode='Markdown'
    )

import asyncio

async def main():
    # Start schedule in background
    schedule_thread = threading.Thread(target=schedule_contest, daemon=True)
    schedule_thread.start()
    
    # Start bot
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("register", register_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("pending", pending_users_command))
    app.add_handler(CommandHandler("approve", approve_command))
    app.add_handler(CommandHandler("reject", reject_command))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("logs", logs_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("🤖 Bot started on Railway!")
    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
