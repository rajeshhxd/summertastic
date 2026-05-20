import requests
import threading
import time
import re
import asyncio
import random
from datetime import datetime, timezone, timedelta
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
    {"slot": 1, "label": "10:00 am - 10:30 am", "time": "10:00", "hour": 10, "minute": 0},
    {"slot": 2, "label": "10:30 am - 11:00 am", "time": "10:30", "hour": 10, "minute": 30},
    {"slot": 3, "label": "11:00 am - 11:30 am", "time": "11:00", "hour": 11, "minute": 0},
    {"slot": 4, "label": "11:30 am - 12:00 pm", "time": "11:30", "hour": 11, "minute": 30},
    {"slot": 5, "label": "12:00 pm - 12:30 pm", "time": "12:00", "hour": 12, "minute": 0},
    {"slot": 6, "label": "12:30 pm - 1:00 pm", "time": "12:30", "hour": 12, "minute": 30},
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
scheduled_jobs = {}
submitted_slots = set()
main_event_loop = None


def send_log(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


def is_weekday():
    return datetime.now().weekday() < 5


def get_current_slot():
    now = datetime.now()
    for slot in SLOTS:
        slot_start = now.replace(hour=slot['hour'], minute=slot['minute'], second=0, microsecond=0)
        slot_end = slot_start + timedelta(minutes=30)
        if slot_start <= now <= slot_end:
            return slot
    return None


def get_contest_day():
    start_date = datetime(2026, 5, 20)
    now = datetime.now()
    contest_day = (now - start_date).days + 1
    if contest_day < 1 or contest_day > 15:
        return None
    return contest_day


async def send_submission_notification(user_id, name, slot_label, question_num, correct_answer, status, is_immediate=False):
    global bot_app
    if not bot_app:
        return

    if status:
        immediate_text = " (IMMEDIATE SUBMISSION)" if is_immediate else ""
        message = (
            f"[✓] Answer Correct!{immediate_text}\n\n"
            f"[👤] Participant: {name}\n"
            f"[⏰] Slot: {slot_label}\n"
            f"[❓] Question {question_num}\n"
            f"[🎯] Your Answer: {correct_answer} ✓\n\n"
            f"[✨] Your correct answer has been recorded!"
        )
    else:
        message = (
            f"[✗] Submission Failed\n\n"
            f"[👤] Participant: {name}\n"
            f"[⏰] Slot: {slot_label}\n"
            f"[❓] Question {question_num}\n\n"
            f"[⚠️] Failed to submit answer. Please contact admin."
        )

    try:
        await bot_app.bot.send_message(user_id, message)
    except Exception as e:
        send_log(f"Failed to notify user {user_id}: {e}", "ERROR")


def _run_coroutine_in_main_loop(coro):
    global main_event_loop
    if main_event_loop is None:
        send_log("main_event_loop not set — cannot send notification", "ERROR")
        return None
    return asyncio.run_coroutine_threadsafe(coro, main_event_loop)


def submit_answer_sync(participant_id, email, phone, contest_day, slot_index, question_index, question_data):
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
            if result.get('ok') is True:
                return True, "Correct answer submitted successfully!"
            else:
                return True, "Submitted successfully"
        return False, f"HTTP Error: {response.status_code}"
    except Exception as e:
        return False, str(e)


def submit_all_questions_for_user_sync(user_id, data, contest_day, slot_index, slot_label, is_immediate=False):
    slot_key = f"{user_id}_{contest_day}_{slot_index}"
    if slot_key in submitted_slots:
        send_log(f"User {data['name']} already submitted for Slot {slot_index}", "SKIP")
        return 6

    send_log(f"Submitting for {data['name']} (ID: {data['participant_id']}) - {'IMMEDIATE' if is_immediate else 'SCHEDULED'}", "INFO")

    day_questions = QUESTIONS[contest_day - 1]
    success_count = 0

    for q_index, question in enumerate(day_questions, 1):
        success, message = submit_answer_sync(
            data['participant_id'],
            data['email'],
            data['phone'],
            contest_day,
            slot_index,
            q_index,
            question
        )

        if success:
            success_count += 1
            correct_answer = question['correct_value']
            send_log(f"  [✓] Question {q_index}: {correct_answer} - CORRECT", "SUCCESS")

            future = _run_coroutine_in_main_loop(
                send_submission_notification(
                    user_id,
                    data['name'],
                    slot_label,
                    q_index,
                    correct_answer,
                    True,
                    is_immediate
                )
            )
            if future:
                try:
                    future.result(timeout=10)
                except Exception as e:
                    send_log(f"Notification error: {e}", "ERROR")
        else:
            send_log(f"  [✗] Question {q_index}: Failed - {message}", "ERROR")

        time.sleep(0.5)

    if success_count == 6:
        submitted_slots.add(slot_key)
        send_log(f"[✓] {data['name']}: All 6 answers submitted successfully!", "SUCCESS")
    else:
        send_log(f"[⚠️] {data['name']}: Only {success_count}/6 answers submitted!", "WARNING")

    if bot_app:
        mode_label = "IMMEDIATE" if is_immediate else "AUTO"
        footer_text = (
            "You registered during this active slot! Answers submitted immediately."
            if is_immediate else
            "Bot will continue submitting for future slots."
        )
        summary_msg = (
            f"[🏆] {mode_label} SUBMISSION COMPLETE!\n\n"
            f"[👤] {data['name']}\n"
            f"[📅] Day {contest_day} | Slot {slot_index}\n"
            f"[⏰] Time: {slot_label}\n\n"
            f"[✓] {success_count}/6 answers submitted correctly!\n\n"
            f"{footer_text}"
        )
        _run_coroutine_in_main_loop(
            bot_app.bot.send_message(user_id, summary_msg)
        )

    return success_count


def process_slot_submission(slot_index, slot_label, contest_day):
    send_log(f"[🕐] Processing scheduled submission for Slot {slot_index} ({slot_label})", "SUBMISSION")

    current_participants = dict(participants)
    send_log(f"[📊] Total participants: {len(current_participants)}", "INFO")

    for user_id, data in current_participants.items():
        submit_all_questions_for_user_sync(user_id, data, contest_day, slot_index, slot_label, is_immediate=False)

    send_log(f"[✓] Scheduled submission completed for Slot {slot_index}", "SUCCESS")


def schedule_slot_submission(slot):
    now = datetime.now()
    slot_start = now.replace(hour=slot['hour'], minute=slot['minute'], second=0, microsecond=0)
    random_minutes = random.randint(1, 10)
    submit_time = slot_start + timedelta(minutes=random_minutes)

    if submit_time < now:
        send_log(f"[⏭️] Slot {slot['slot']} ({slot['label']}) already passed, skipping", "SKIP")
        return

    send_log(f"[📅] Scheduled Slot {slot['slot']} ({slot['label']}) at {submit_time.strftime('%H:%M:%S')} (delay: {random_minutes} min)", "SCHEDULE")

    seconds_delay = (submit_time - datetime.now()).total_seconds()

    timer = threading.Timer(
        seconds_delay,
        lambda: process_slot_submission(slot['slot'], slot['label'], get_contest_day())
    )
    timer.daemon = True
    timer.start()

    scheduled_jobs[slot['slot']] = timer


def schedule_all_slots():
    now = datetime.now()

    if not is_weekday():
        weekday_name = now.strftime("%A")
        send_log(f"[📅] Today is {weekday_name} - No submissions (Monday-Friday only)", "INFO")
        return

    contest_day = get_contest_day()
    if not contest_day:
        send_log("[📅] Contest not active or completed", "INFO")
        return

    for timer in scheduled_jobs.values():
        timer.cancel()
    scheduled_jobs.clear()

    for slot in SLOTS:
        slot_time = now.replace(hour=slot['hour'], minute=slot['minute'], second=0, microsecond=0)
        if slot_time > now:
            schedule_slot_submission(slot)

    send_log(f"[📅] Scheduled submissions for Day {contest_day}", "INFO")


def background_scheduler():
    while True:
        now = datetime.now()
        if now.hour == 0 and now.minute == 0:
            schedule_all_slots()
            time.sleep(60)

        if len(scheduled_jobs) == 0 and 9 <= now.hour < 13:
            schedule_all_slots()

        time.sleep(30)


# Bot Command Handlers
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
            "/logs - Show recent logs\n"
            "/schedule - Show current schedule\n\n"
            "To register yourself:\n"
            "Use /register command"
        )
        return ConversationHandler.END

    elif user_id in participants:
        data = participants[user_id]
        await update.message.reply_text(
            f"Welcome back, {data['name']}!\n\n"
            f"Participant ID: {data['participant_id']}\n"
            f"Auto-submit is active.\n\n"
            "Use /status for full details."
        )
        return ConversationHandler.END

    elif user_id in approved_users:
        await update.message.reply_text(
            "Welcome to Summertastic Contest Bot!\n\n"
            "Use /register to start your registration."
        )
        return ConversationHandler.END

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


async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if user_id == ADMIN_ID or user_id in approved_users:
        await update.message.reply_text(
            "Start Registration\n\n"
            "Please enter your details:\n\n"
            "Step 1/4: What is your full name?\n\n"
            "Example: Rajesh Sharma"
        )
        return NAME
    else:
        await update.message.reply_text(
            "You don't have access.\n"
            "Use /start to request access from admin."
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

    summary = (
        f"Please confirm your details:\n\n"
        f"Name: {data['name']}\n"
        f"Email: {data['email']}\n"
        f"City: {data['city']}\n"
        f"Phone: {data['phone']}\n\n"
        f"Consent: Agreed to all terms\n\n"
        "Reply with YES to register or NO to cancel."
    )

    await update.message.reply_text(summary)
    return CONFIRM


async def register_on_website(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global participants, submitted_slots

    user_id = str(update.effective_user.id)
    answer = update.message.text.strip().upper()

    if answer != 'YES':
        await update.message.reply_text(
            "Registration Cancelled\n\n"
            "Use /register to begin again."
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

                current_slot = get_current_slot()
                contest_day = get_contest_day()

                immediate_result = ""
                if current_slot and contest_day:
                    await processing_msg.edit_text(
                        f"Registration Successful!\n\n"
                        f"Participant ID: {participant_id}\n\n"
                        f"Registered Details:\n"
                        f"Name: {data['name']}\n"
                        f"Email: {data['email']}\n"
                        f"City: {data['city']}\n"
                        f"Phone: {data['phone']}\n\n"
                        f"Current slot active! Submitting answers immediately..."
                    )

                    send_log(f"Immediate submission for new user {data['name']} - Slot {current_slot['slot']}", "IMMEDIATE")

                    day_questions = QUESTIONS[contest_day - 1]
                    success_count = 0
                    slot_key = f"{user_id}_{contest_day}_{current_slot['slot']}"

                    for q_index, question in enumerate(day_questions, 1):
                        success, msg = submit_answer_sync(
                            participant_id,
                            data['email'],
                            data['phone'],
                            contest_day,
                            current_slot['slot'],
                            q_index,
                            question
                        )

                        if success:
                            success_count += 1
                            correct_answer = question['correct_value']
                            send_log(f"  Question {q_index}: {correct_answer} - CORRECT (Immediate)", "SUCCESS")
                            await send_submission_notification(
                                user_id,
                                data['name'],
                                current_slot['label'],
                                q_index,
                                correct_answer,
                                True,
                                True
                            )
                        else:
                            send_log(f"  Question {q_index}: Failed - {msg}", "ERROR")

                        await asyncio.sleep(0.5)

                    if success_count == 6:
                        submitted_slots.add(slot_key)
                        immediate_result = "\n\nAll 6 answers submitted successfully for current slot! You're all caught up!"
                    else:
                        immediate_result = f"\n\nPartial submission: {success_count}/6 answers submitted. Please contact admin if issues persist."

                    summary_msg = (
                        f"IMMEDIATE SUBMISSION COMPLETE!\n\n"
                        f"{data['name']}\n"
                        f"Day {contest_day} | Slot {current_slot['slot']}\n"
                        f"Time: {current_slot['label']}\n\n"
                        f"{success_count}/6 answers submitted correctly!\n\n"
                        f"You registered during this active slot! Answers submitted immediately.\n"
                        f"Bot will continue submitting for future slots automatically."
                    )
                    await context.bot.send_message(user_id, summary_msg)

                success_msg = (
                    f"Registration Successful!\n\n"
                    f"Your Participant ID: {participant_id}\n\n"
                    f"Registered Details:\n"
                    f"Name: {data['name']}\n"
                    f"Email: {data['email']}\n"
                    f"City: {data['city']}\n"
                    f"Phone: {data['phone']}\n\n"
                    f"Automated Submission Active!\n\n"
                    f"- Bot will auto-submit correct answers\n"
                    f"- Random delay: 1-10 minutes after each slot start\n"
                    f"- Monday to Friday only\n"
                    f"- Duration: 15 days\n"
                    f"- 6 questions per slot\n"
                    f"- 100% correct answers guaranteed"
                    f"{immediate_result}\n\n"
                    f"You're all set! No manual work needed.\n\n"
                    f"Use /status to check your registration."
                )

                await processing_msg.edit_text(success_msg)

                send_log(f"New registration: {data['name']} (ID: {participant_id})", "REGISTER")

                await context.bot.send_message(
                    ADMIN_ID,
                    f"New Registration\n\n"
                    f"Name: {data['name']}\n"
                    f"Email: {data['email']}\n"
                    f"City: {data['city']}\n"
                    f"Phone: {data['phone']}\n"
                    f"ID: {participant_id}\n"
                    f"Immediate submission: {'Yes' if current_slot else 'No'}"
                )
            else:
                await processing_msg.edit_text(
                    "Registration Failed\n\n"
                    "Could not get participant ID from server.\n\n"
                    "Please try again later."
                )
        else:
            await processing_msg.edit_text(
                f"Registration Failed\n\n"
                f"Server error: {response.status_code}\n\n"
                "Please try again later."
            )

    except Exception as e:
        await processing_msg.edit_text(
            f"Registration Failed\n\n"
            f"Error: {str(e)[:100]}\n\n"
            "Please try again later."
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
        "Use /register to begin again."
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
            await query.edit_message_text("You already have access! Use /register to register.")
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
                "Use /register after approval to register."
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
                "Welcome! Please use /register to register for the contest."
            )

            await query.edit_message_text(f"User {target_user} has been approved!")
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
                "Access Denied\n\n"
                "Your request has been rejected by admin."
            )

            await query.edit_message_text(f"User {target_user} has been rejected!")
            send_log(f"Admin rejected user {target_user}", "REJECT")


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
            "Access Granted!\n\nPlease use /register to register for the contest."
        )

        await update.message.reply_text(f"User {target_user} approved!")
        send_log(f"Admin approved user {target_user}", "APPROVE")
    else:
        await update.message.reply_text("User not found in pending list!")


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
            "Access Denied\n\nYour request has been rejected."
        )

        await update.message.reply_text(f"User {target_user} rejected!")
        send_log(f"Admin rejected user {target_user}", "REJECT")
    else:
        await update.message.reply_text("User not found in pending list!")


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
            message += f"✓ {uid} - {data['name']} (ID: {participants[uid]['participant_id']})\n"
        else:
            message += f"○ {uid} - {data['name']} (Not registered)\n"

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
            await context.bot.send_message(user_id, f"Announcement\n\n{message}")
            sent += 1
            await asyncio.sleep(0.1)
        except Exception:
            pass

    await update.message.reply_text(f"Broadcast sent to {sent} users!")
    send_log(f"Broadcast sent to {sent} users", "BROADCAST")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("Admin only!")
        return

    stats_text = (
        f"Bot Statistics\n\n"
        f"Approved Users: {len(approved_users)}\n"
        f"Pending Requests: {len(pending_users)}\n"
        f"Registered for Contest: {len(participants)}\n"
        f"Total Submissions Tracked: {len(submitted_slots)}\n"
        f"Active Hours: 10:00 AM - 1:00 PM IST\n"
        f"Active Days: Monday to Friday\n"
        f"Weekend: Bot Idle\n"
        f"Auto-submit: Active (Random delay 1-10 min)\n"
        f"Correct Answers: 100%\n"
        f"User Notifications: Enabled\n"
        f"Immediate Submission: Yes (on registration)"
    )

    await update.message.reply_text(stats_text)


async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("Admin only!")
        return

    now = datetime.now()
    current_slot = get_current_slot()
    current_slot_text = f"Current Slot: {current_slot['slot']} ({current_slot['label']})" if current_slot else "No active slot"

    schedule_text = (
        f"Current Schedule\n\n"
        f"Today: {now.strftime('%A, %B %d, %Y')}\n"
        f"{current_slot_text}\n"
        f"Active Days: Monday to Friday\n"
        f"Current Time: {now.strftime('%H:%M:%S')} IST\n\n"
        f"Slot Schedule (with random delays):\n\n"
        f"Slot 1: 10:00 AM -> Submit at 10:01-10:10\n"
        f"Slot 2: 10:30 AM -> Submit at 10:31-10:40\n"
        f"Slot 3: 11:00 AM -> Submit at 11:01-11:10\n"
        f"Slot 4: 11:30 AM -> Submit at 11:31-11:40\n"
        f"Slot 5: 12:00 PM -> Submit at 12:01-12:10\n"
        f"Slot 6: 12:30 PM -> Submit at 12:31-12:40\n\n"
        f"Features:\n"
        f"- Random delay: 1-10 minutes after slot start\n"
        f"- Immediate submission on registration\n"
        f"- All answers 100% correct\n"
        f"- User notifications for every submission"
    )

    await update.message.reply_text(schedule_text)


async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("Admin only!")
        return

    await update.message.reply_text(
        f"Logs Information\n\n"
        f"Logs are printed to the console.\n"
        f"Group ID for logs: {GROUP_ID}\n\n"
        f"Features:\n"
        f"- Monday-Friday only\n"
        f"- Random delay: 1-10 min per slot\n"
        f"- Immediate submission on registration\n"
        f"- User notifications for every correct answer\n"
        f"- Response: {{'ok': true}} for successful submissions"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if user_id in participants:
        data = participants[user_id]
        await update.message.reply_text(
            f"Your Registration Status\n\n"
            f"Name: {data['name']}\n"
            f"Participant ID: {data['participant_id']}\n"
            f"Email: {data['email']}\n"
            f"Phone: {data['phone']}\n"
            f"Auto-submit: Enabled\n"
            f"Active Days: Monday to Friday\n"
            f"Active Hours: 10:00 AM - 1:00 PM IST\n"
            f"Random delay: 1-10 min per slot\n"
            f"Notifications: You will receive alerts for every correct answer\n"
            f"Status: Active"
        )
    else:
        await update.message.reply_text(
            "Not Registered\n\n"
            "Use /register to start the registration process."
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Summertastic Contest Bot Help\n\n"
        "How to Register:\n"
        "1. Get approved by admin first\n"
        "2. Use /register command\n"
        "3. Enter your details step by step\n"
        "4. Get your Participant ID automatically\n\n"
        "Submission Schedule:\n"
        "- Monday to Friday ONLY\n"
        "- 10:00 AM - 1:00 PM IST\n"
        "- Random delay: 1-10 minutes after each slot start\n"
        "- If you register during active slot -> IMMEDIATE submission\n"
        "- Weekends: Bot is idle\n\n"
        "Slot Timings:\n"
        "Slot 1: 10:00 AM (Submit 10:01-10:10)\n"
        "Slot 2: 10:30 AM (Submit 10:31-10:40)\n"
        "Slot 3: 11:00 AM (Submit 11:01-11:10)\n"
        "Slot 4: 11:30 AM (Submit 11:31-11:40)\n"
        "Slot 5: 12:00 PM (Submit 12:01-12:10)\n"
        "Slot 6: 12:30 PM (Submit 12:31-12:40)\n\n"
        "User Commands:\n"
        "/start - Main menu\n"
        "/register - Start registration\n"
        "/status - Check your status\n"
        "/help - Show this help\n\n"
        "Admin Commands:\n"
        "/pending - View pending users\n"
        "/approve <id> - Approve a user\n"
        "/reject <id> - Reject a user\n"
        "/users - List all approved users\n"
        "/broadcast <msg> - Broadcast message\n"
        "/stats - View statistics\n"
        "/schedule - Show current schedule\n"
        "/logs - View logs\n\n"
        "Notifications:\n"
        "- You will receive a message for EVERY correct answer\n"
        "- Daily summary after each slot\n"
        "- Instant confirmation of submission\n"
        "- IMMEDIATE SUBMISSION tag for registration-time submissions\n\n"
        "Bot Features:\n"
        "- Auto-submits 100% correct answers\n"
        "- Monday to Friday only\n"
        "- Random delay (1-10 min) to avoid detection\n"
        "- Immediate submission on registration\n"
        "- User notifications for each submission\n"
        "- 15 days contest duration\n"
        "- 6 questions per slot"
    )

    await update.message.reply_text(help_text)


async def post_init(application: Application) -> None:
    global main_event_loop
    main_event_loop = asyncio.get_running_loop()
    send_log("Main event loop captured — background notifications enabled", "INFO")


def main():
    global bot_app

    # Start background scheduler thread
    scheduler_thread = threading.Thread(target=background_scheduler, daemon=True)
    scheduler_thread.start()

    # Initial schedule
    schedule_all_slots()

    # Create bot application
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
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

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("pending", pending_command))
    app.add_handler(CommandHandler("approve", approve_command))
    app.add_handler(CommandHandler("reject", reject_command))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("schedule", schedule_command))
    app.add_handler(CommandHandler("logs", logs_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("help", help_command))

    print("=" * 50)
    print("SUMMERTASTIC BOT STARTED")
    print("=" * 50)
    print(f"Admin ID: {ADMIN_ID}")
    print(f"Schedule: Monday to Friday only (10:00 AM - 1:00 PM IST)")
    print(f"Random delay: 1-10 minutes after each slot start")
    print(f"Immediate submission: ON for new registrations during active slots")
    print(f"User notifications: ENABLED for every correct answer")
    print("=" * 50)

    app.run_polling()


if __name__ == '__main__':
    main()
