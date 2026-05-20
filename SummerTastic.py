import os
import logging
import random
import asyncio
import sqlite3
import base64
import json
import functools
import requests
from datetime import datetime, timedelta, timezone
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

BOT_TOKEN = os.environ.get(
    "TELEGRAM_BOT_TOKEN",
    "8468565516:AAEYOmmIUOOjP2LBp5bBSeGA9X4u1oXh75A",
)
API_BASE = "https://api.almondwin.com"
ADMIN_IDS = [
    int(x.strip())
    for x in os.environ.get("ADMIN_IDS", "1922522807").split(",")
    if x.strip().isdigit()
]

DEFAULT_MIN_DELAY = 30
DEFAULT_MAX_EXTRA = 30
DEFAULT_COOLDOWN = 15
DEFAULT_MAX_ROUNDS = 20
DAILY_POINTS_FREE = 5
PREMIUM_COST_POINTS = 10
LOG_GROUP_ID = -1003918355970

DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")

MOBILE, OTP, ROUNDS = range(3)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BENEFITS = [
    {
        "title": "Bone Health Collected",
        "description": "Almonds have Calcium, Magnesium and Phosphorus that contribute to keeping bones strong for epic shots.",
        "pts": 50,
    },
    {
        "title": "Muscle Strength Collected",
        "description": "Almonds have Protein, Vitamin E, and Good Fats that support muscle strength and recovery for epic shots.",
        "pts": 50,
    },
    {
        "title": "Muscle Strength Collected",
        "description": "Almonds have Protein, Vitamin E, and Good Fats that support muscle strength and recovery for epic catches.",
        "pts": 50,
    },
    {
        "title": "Sustained Energy Collected",
        "description": "The nutrient-dense structure of almonds slows digestion and supports longer-lasting energy for epic catches.",
        "pts": 50,
    },
    {
        "title": "Heart Health Collected",
        "description": "Almonds contain Good Fats that help keep the heart healthy, perfect for those quick runs between the wickets!",
        "pts": 50,
    },
    {
        "title": "Manage Stress Collected",
        "description": "Almonds are a rich source of Magnesium that helps the body manage stress and supports better sleep, exactly what players need to stay calm in the last over!",
        "pts": 50,
    },
    {
        "title": "Sustained Energy Collected",
        "description": "The nutrient-dense structure of almonds slows digestion and supports longer-lasting energy for long innings.",
        "pts": 50,
    },
    {
        "title": "Manage Stress Collected",
        "description": "Almonds are a rich source of Magnesium that helps the body manage stress, exactly what players need to make the right call under DRS pressure!",
        "pts": 50,
    },
    {
        "title": "Heart Health Collected",
        "description": "Almonds contain Good Fats that help keep the heart healthy, perfect for the endurance and grit to keep batting, over after over!",
        "pts": 50,
    },
]


# ── Database ──────────────────────────────────────────────────────────────────

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id     INTEGER PRIMARY KEY,
                username        TEXT    DEFAULT '',
                mobile          TEXT,
                token           TEXT,
                token_expiry    TEXT,
                name            TEXT,
                is_premium      INTEGER DEFAULT 0,
                premium_expiry  TEXT,
                is_banned       INTEGER DEFAULT 0,
                points          INTEGER DEFAULT 0,
                custom_delay    INTEGER,
                cooldown_on     INTEGER DEFAULT 1,
                last_run_at     TEXT,
                daily_credited  TEXT,
                total_runs      INTEGER DEFAULT 0,
                created_at      TEXT    DEFAULT (datetime('now'))
            )
        """)
        conn.commit()


def upsert_user(telegram_id: int, **kwargs):
    with get_conn() as conn:
        exists = conn.execute(
            "SELECT 1 FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()
        if exists:
            if kwargs:
                sets = ", ".join(f"{k} = ?" for k in kwargs)
                conn.execute(
                    f"UPDATE users SET {sets} WHERE telegram_id = ?",
                    (*kwargs.values(), telegram_id),
                )
        else:
            kwargs["telegram_id"] = telegram_id
            cols = ", ".join(kwargs.keys())
            placeholders = ", ".join("?" * len(kwargs))
            conn.execute(
                f"INSERT INTO users ({cols}) VALUES ({placeholders})",
                tuple(kwargs.values()),
            )
        conn.commit()


def get_user(telegram_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()


def get_all_users():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users").fetchall()


# ── JWT helpers ───────────────────────────────────────────────────────────────

def decode_jwt_expiry(token: str) -> datetime | None:
    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.b64decode(payload_b64))
        exp = payload.get("exp")
        if exp:
            return datetime.fromtimestamp(exp, tz=timezone.utc)
    except Exception:
        pass
    return None


def is_token_valid(token: str) -> bool:
    expiry = decode_jwt_expiry(token)
    if not expiry:
        return False
    return datetime.now(tz=timezone.utc) < expiry - timedelta(minutes=5)


# ── Status helpers ────────────────────────────────────────────────────────────

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def check_banned(user_id: int) -> bool:
    u = get_user(user_id)
    return bool(u and u["is_banned"])


def check_premium(user_id: int) -> bool:
    u = get_user(user_id)
    if not u or not u["is_premium"]:
        return False
    if u["premium_expiry"]:
        expiry = datetime.fromisoformat(u["premium_expiry"])
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if datetime.now(tz=timezone.utc) > expiry:
            upsert_user(user_id, is_premium=0, premium_expiry=None)
            return False
    return True


# ── Delay helpers ─────────────────────────────────────────────────────────────

def get_user_delay(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    u = get_user(user_id)
    if u and u["custom_delay"]:
        min_d = u["custom_delay"]
    else:
        min_d = context.bot_data.get("min_delay", DEFAULT_MIN_DELAY)
    max_e = context.bot_data.get("max_extra", DEFAULT_MAX_EXTRA)
    return min_d, max_e


# ── API helpers ───────────────────────────────────────────────────────────────

COMMON_HEADERS = {
    "Content-Type": "application/json",
    "Origin": "https://almondwin.com",
    "Referer": "https://almondwin.com/",
}


def api_login(mobile: str) -> dict:
    r = requests.post(
        f"{API_BASE}/api/user/register",
        json={"mobile": mobile, "flow": "login", "token": ""},
        headers=COMMON_HEADERS,
        timeout=15,
    )
    return r.json()


def api_verify_otp(mobile: str, otp: str) -> dict:
    r = requests.post(
        f"{API_BASE}/api/user/verify-otp",
        json={"mobile": mobile, "verification_code": otp},
        headers=COMMON_HEADERS,
        timeout=15,
    )
    return r.json()


def api_submit_benefit(token: str, benefit: dict) -> tuple[bool, str, dict]:
    headers = {**COMMON_HEADERS, "Authorization": f"Bearer {token}"}
    payload = {
        "pointsEarned": benefit["pts"],
        "benefit": {
            "id": benefit["title"],
            "benefit": benefit["description"],
            "pts": benefit["pts"],
        },
    }
    try:
        r = requests.post(
            f"{API_BASE}/api/gameplay/progress/submit",
            json=payload,
            headers=headers,
            timeout=15,
        )
        try:
            data = r.json()
        except Exception:
            data = {}
        if r.status_code == 200:
            return True, "ok", {
                "overallPoints": data.get("overallPoints"),
                "weeklyPoints": data.get("weeklyPoints"),
            }
        msg = data.get("message", f"HTTP {r.status_code}")
        return False, msg, {}
    except Exception as e:
        return False, str(e), {}


# ── Group logger ──────────────────────────────────────────────────────────────

async def log_group(context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    try:
        await context.bot.send_message(chat_id=LOG_GROUP_ID, text=text)
    except Exception:
        pass


# ── Submission engine ─────────────────────────────────────────────────────────

async def submit_all_benefits(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    token: str,
    user_id: int,
    rounds: int = 1,
) -> None:
    stop_requests: set = context.bot_data.setdefault("stop_requests", set())
    min_d, max_e = get_user_delay(context, user_id)

    u_info = get_user(user_id)
    display_name = (u_info and u_info["name"]) or str(user_id)

    total_benefits = len(BENEFITS)
    total_submissions = total_benefits * rounds
    total_earned = 0
    global_index = 0

    await log_group(
        context,
        f"▶️ Run started\n"
        f"👤 {display_name} (ID: {user_id})\n"
        f"🔄 Rounds: {rounds} × {total_benefits} benefits = {total_submissions} submissions",
    )

    for round_num in range(rounds):
        if rounds > 1:
            await update.message.reply_text(
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔄  ROUND {round_num + 1} / {rounds}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━"
            )

        shuffled = BENEFITS.copy()
        random.shuffle(shuffled)

        for i, benefit in enumerate(shuffled):
            if user_id in stop_requests:
                stop_requests.discard(user_id)
                await update.message.reply_text(
                    f"🛑 Submission Stopped!\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📍  Stopped at  :  Round {round_num + 1} › Step {i + 1}\n"
                    f"🏆  Earned      :  {total_earned} pts\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"Type /start to begin again."
                )
                await log_group(
                    context,
                    f"🛑 Stopped early\n"
                    f"👤 {display_name} (ID: {user_id})\n"
                    f"🏆 Earned: {total_earned} pts",
                )
                return

            if global_index > 0:
                wait_secs = random.randint(min_d, min_d + max_e)
                await update.message.reply_text(
                    f"⏳ [{global_index}/{total_submissions}] Cooling down... {wait_secs}s"
                )
                for _ in range(wait_secs):
                    if user_id in stop_requests:
                        break
                    await asyncio.sleep(1)

                if user_id in stop_requests:
                    stop_requests.discard(user_id)
                    await update.message.reply_text(
                        f"🛑 Submission Stopped!\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"📍  Stopped at  :  Round {round_num + 1} › Step {i + 1}\n"
                        f"🏆  Earned      :  {total_earned} pts\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"Type /start to begin again."
                    )
                    await log_group(
                        context,
                        f"🛑 Stopped early\n"
                        f"👤 {display_name} (ID: {user_id})\n"
                        f"🏆 Earned: {total_earned} pts",
                    )
                    return

            global_index += 1
            success, msg, pts_data = api_submit_benefit(token, benefit)

            if success:
                total_earned += benefit["pts"]
                overall = pts_data.get("overallPoints")
                weekly = pts_data.get("weeklyPoints")
                pts_extra = ""
                if overall is not None or weekly is not None:
                    pts_extra = f"\n   📊  Total: {overall}  |  Weekly: {weekly}"
                await update.message.reply_text(
                    f"✅ [{global_index:02d}/{total_submissions}] {benefit['title']}\n"
                    f"   💰 +{benefit['pts']} pts{pts_extra}"
                )
                await log_group(
                    context,
                    f"✅ [{global_index}/{total_submissions}] {benefit['title']}\n"
                    f"👤 {display_name} | +{benefit['pts']} pts{pts_extra}",
                )
            elif "Unable to process score right now" in msg:
                await update.message.reply_text(
                    f"⏳ [{global_index:02d}/{total_submissions}] Server busy — retrying in 20s..."
                )
                await asyncio.sleep(20)
                success2, msg2, pts_data2 = api_submit_benefit(token, benefit)
                if success2:
                    total_earned += benefit["pts"]
                    overall = pts_data2.get("overallPoints")
                    weekly = pts_data2.get("weeklyPoints")
                    pts_extra = ""
                    if overall is not None or weekly is not None:
                        pts_extra = f"\n   📊  Total: {overall}  |  Weekly: {weekly}"
                    await update.message.reply_text(
                        f"✅ [{global_index:02d}/{total_submissions}] {benefit['title']} ↩ retry ok\n"
                        f"   💰 +{benefit['pts']} pts{pts_extra}"
                    )
                    await log_group(
                        context,
                        f"✅ [{global_index}/{total_submissions}] {benefit['title']} (retry)\n"
                        f"👤 {display_name} | +{benefit['pts']} pts{pts_extra}",
                    )
                else:
                    await update.message.reply_text(
                        f"⚠️ [{global_index:02d}/{total_submissions}] {benefit['title']} — retry failed\n"
                        f"   {msg2}"
                    )
                    await log_group(
                        context,
                        f"⚠️ [{global_index}/{total_submissions}] {benefit['title']} FAILED\n"
                        f"👤 {display_name} | {msg2}",
                    )
            else:
                await update.message.reply_text(
                    f"⚠️ [{global_index:02d}/{total_submissions}] {benefit['title']}\n"
                    f"   {msg}"
                )
                await log_group(
                    context,
                    f"⚠️ [{global_index}/{total_submissions}] {benefit['title']} FAILED\n"
                    f"👤 {display_name} | {msg}",
                )

    u = get_user(user_id)
    cur_pts = u["points"] if u else 0
    cur_runs = u["total_runs"] if u else 0
    upsert_user(
        user_id,
        points=cur_pts + total_earned,
        last_run_at=datetime.now(tz=timezone.utc).isoformat(),
        total_runs=cur_runs + 1,
    )

    u = get_user(user_id)
    new_balance = (u["points"] if u else 0) + total_earned
    await update.message.reply_text(
        f"🏁 Run Complete!\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔄  Rounds done    :  {rounds}\n"
        f"📦  Submissions    :  {total_submissions}\n"
        f"🏆  Points earned  :  {total_earned} pts\n"
        f"💰  New balance    :  {new_balance} pts\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"/start to run again  |  /mypoints for stats"
    )
    await log_group(
        context,
        f"🏁 Run completed\n"
        f"👤 {display_name} (ID: {user_id})\n"
        f"🔄 Rounds: {rounds} | 🏆 Earned: {total_earned} pts | 💰 Balance: {new_balance} pts",
    )


# ── /stop ─────────────────────────────────────────────────────────────────────

async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    context.bot_data.setdefault("stop_requests", set()).add(user_id)
    await update.message.reply_text(
        "🛑 Stop signal sent. Will stop after the current step finishes."
    )


# ── /start & conversation ─────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    tg_user = update.effective_user
    user_id = tg_user.id

    if check_banned(user_id):
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return ConversationHandler.END

    if context.bot_data.get("locked") and not is_admin(user_id):
        await update.message.reply_text(
            "🔐 The bot is currently locked and under maintenance.\n"
            "Please try again later."
        )
        return ConversationHandler.END

    upsert_user(user_id, username=tg_user.username or "")

    if not is_admin(user_id) and not check_premium(user_id):
        await update.message.reply_text(
            "🔒 This bot is for Premium members only.\n\n"
            "To get access, contact:\n"
            "💬 @xrishna (https://t.me/xrishna)\n"
            "💬 @krsnax_bot (https://t.me/krsnax_bot)\n\n"
            "Get Premium instantly and start earning points! 🏆"
        )
        return ConversationHandler.END
    context.user_data.clear()

    db_user = get_user(user_id)
    if db_user and db_user["token"] and is_token_valid(db_user["token"]):
        context.user_data["pending_token"] = db_user["token"]
        context.user_data["pending_name"] = db_user["name"] or "Player"
        max_r = context.bot_data.get("max_rounds", DEFAULT_MAX_ROUNDS)
        limit_line = f"Max {max_r} rounds per session" if not is_admin(user_id) else "No limit (admin)"
        await update.message.reply_text(
            f"🏏 AlmondWin Bot\n\n"
            f"⚡ Session Active — No OTP Needed!\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤  Player  :  {db_user['name'] or 'Player'}\n"
            f"🔑  Status  :  Logged In ✓\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔢 How many rounds to submit?\n"
            f"Each round = {len(BENEFITS)} benefits in random order\n"
            f"📌 {limit_line}\n\n"
            f"➤ Reply with a number:"
        )
        return ROUNDS

    await update.message.reply_text(
        "🏏 AlmondWin Bot\n\n"
        "👋 Welcome! Please enter your\n"
        "10-digit mobile number to login:",
        reply_markup=ReplyKeyboardRemove(),
    )
    return MOBILE


async def autologin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await start(update, context)


async def get_mobile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    mobile = update.message.text.strip()
    if not mobile.isdigit() or len(mobile) != 10:
        await update.message.reply_text("❌ Please enter a valid 10-digit mobile number.")
        return MOBILE

    context.user_data["mobile"] = mobile
    await update.message.reply_text("⏳ Checking your account...")

    try:
        data = api_login(mobile)
        msg = data.get("message", "")
        if "OTP sent" in msg:
            await update.message.reply_text(
                f"✅ OTP sent to {mobile}.\n\nPlease enter the OTP:"
            )
            return OTP
        elif "not registered" in msg.lower() or "sign-up" in msg.lower():
            await update.message.reply_text(
                "❌ This number is not registered.\n\n"
                "Please sign up at https://almondwin.com first, then use /start."
            )
            return ConversationHandler.END
        else:
            await update.message.reply_text(f"⚠️ {msg}\n\nTry again with /start.")
            return ConversationHandler.END
    except requests.exceptions.Timeout:
        await update.message.reply_text("⏱️ Server timeout. Please try again.")
        return MOBILE
    except Exception as e:
        logger.error(f"Login error: {e}")
        await update.message.reply_text("❌ Could not connect. Please try again.")
        return MOBILE


async def verify_otp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    otp = update.message.text.strip()
    mobile = context.user_data.get("mobile")
    user_id = update.effective_user.id

    if not mobile:
        await update.message.reply_text(
            "❌ Session expired. Please restart with /start."
        )
        return ConversationHandler.END

    await update.message.reply_text("⏳ Verifying OTP...")

    try:
        data = api_verify_otp(mobile, otp)
        logger.info(f"OTP verify response keys: {list(data.keys()) if isinstance(data, dict) else data}")
        token = data.get("token")

        # Try multiple possible field names the API might use
        user_obj = data.get("user") or data.get("userData") or data.get("data") or {}
        name = (
            data.get("name")
            or data.get("playerName")
            or data.get("username")
            or (user_obj.get("name") if isinstance(user_obj, dict) else None)
            or "Player"
        )
        score = (
            data.get("score")
            or data.get("overallPoints")
            or data.get("totalPoints")
            or data.get("points")
            or (user_obj.get("score") if isinstance(user_obj, dict) else None)
            or (user_obj.get("overallPoints") if isinstance(user_obj, dict) else None)
            or 0
        )

        if not token:
            await update.message.reply_text("❌ Invalid or expired OTP. Please try again:")
            return OTP

        expiry = decode_jwt_expiry(token)
        upsert_user(
            user_id,
            mobile=mobile,
            token=token,
            token_expiry=expiry.isoformat() if expiry else None,
            name=name,
        )

        context.user_data["pending_token"] = token
        context.user_data["pending_name"] = name
        max_r = context.bot_data.get("max_rounds", DEFAULT_MAX_ROUNDS)
        limit_line = f"Max {max_r} rounds per session" if not is_admin(user_id) else "No limit (admin)"

        await update.message.reply_text(
            f"🏏 AlmondWin Bot\n\n"
            f"✅ Login Successful!\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤  Player  :  {name}\n"
            f"🏆  Score   :  {score} pts\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔢 How many rounds to submit?\n"
            f"Each round = {len(BENEFITS)} benefits in random order\n"
            f"📌 {limit_line}\n\n"
            f"➤ Reply with a number:"
        )
        return ROUNDS

    except requests.exceptions.Timeout:
        await update.message.reply_text("⏱️ Server timeout. Please try again.")
        return OTP
    except Exception as e:
        logger.error(f"OTP error: {e}")
        await update.message.reply_text("❌ Error verifying OTP. Please try again:")
        return OTP


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "❌ Cancelled. Type /start to begin again.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def get_rounds(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if not text.isdigit() or int(text) < 1:
        await update.message.reply_text(
            "❌ Please enter a valid number (e.g. 3):"
        )
        return ROUNDS

    rounds = int(text)
    max_r = context.bot_data.get("max_rounds", DEFAULT_MAX_ROUNDS)

    if not is_admin(user_id) and rounds > max_r:
        await update.message.reply_text(
            f"❌ Maximum allowed is {max_r} rounds.\n"
            f"Please enter a number between 1 and {max_r}:"
        )
        return ROUNDS

    token = context.user_data.get("pending_token")
    name = context.user_data.get("pending_name", "User")

    if not token:
        await update.message.reply_text(
            "❌ Session expired. Please use /start again."
        )
        return ConversationHandler.END

    min_d, max_e = get_user_delay(context, user_id)
    total_submissions = len(BENEFITS) * rounds
    est_min = (total_submissions - 1) * min_d
    est_max = (total_submissions - 1) * (min_d + max_e)

    await update.message.reply_text(
        f"🚀 Run Starting!\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔄  Rounds       :  {rounds}\n"
        f"📦  Submissions  :  {total_submissions} total\n"
        f"⏱  Delay        :  {min_d} – {min_d + max_e}s\n"
        f"⏰  Est. Time    :  {est_min // 60}m {est_min % 60}s – {est_max // 60}m {est_max % 60}s\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Send /stop anytime to cancel."
    )

    await submit_all_benefits(update, context, token, user_id, rounds=rounds)
    return ConversationHandler.END


# ── User commands ─────────────────────────────────────────────────────────────

async def mypoints(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    u = get_user(user_id)
    if not u:
        await update.message.reply_text("❌ No account found. Use /start to login first.")
        return
    premium_str = "👑 Premium" if check_premium(user_id) else "Free"
    await update.message.reply_text(
        f"💰 Your Points Balance\n\n"
        f"🏆 Points: {u['points']} pts\n"
        f"📊 Total Runs: {u['total_runs']}\n"
        f"⭐ Status: {premium_str}\n"
        f"👤 Name: {u['name'] or 'N/A'}"
    )


async def myreferral(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    u = get_user(user_id)
    if not u or not u["mobile"]:
        await update.message.reply_text("❌ No account found. Use /start to login first.")
        return
    link = f"https://almondwin.com/?ref={u['mobile']}"
    await update.message.reply_text(
        f"🔗 Your Referral Link\n\n"
        f"📱 Mobile: {u['mobile']}\n"
        f"🌐 {link}\n\n"
        f"Share this link to earn rewards!"
    )


async def buypremium(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if check_premium(user_id):
        await update.message.reply_text("✅ You already have Premium!")
        return
    await update.message.reply_text(
        "👑 Get Premium Access\n\n"
        "Contact us to get Premium instantly:\n"
        "💬 @xrishna (https://t.me/xrishna)\n"
        "💬 @krsnax_bot (https://t.me/krsnax_bot)"
    )


async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg = update.effective_user
    user_id = tg.id
    u = get_user(user_id)
    premium_str = "👑 Premium" if check_premium(user_id) else "Free"
    await update.message.reply_text(
        f"👤 Your Profile\n\n"
        f"🆔 Telegram ID: {user_id}\n"
        f"👤 Name: {(u and u['name']) or tg.full_name or 'N/A'}\n"
        f"📱 Mobile: {(u and u['mobile']) or 'N/A'}\n"
        f"🏆 Points: {(u and u['points']) or 0}\n"
        f"⭐ Status: {premium_str}\n"
        f"🔑 Admin: {'✅ Yes' if is_admin(user_id) else 'No'}\n"
        f"🚫 Banned: {'Yes' if (u and u['is_banned']) else 'No'}"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = (
        "🤖 How it works:\n\n"
        "1️⃣ Send /start\n"
        "2️⃣ Enter your mobile number\n"
        "3️⃣ Enter the OTP you receive\n"
        "4️⃣ Your score is submitted automatically 🎉\n\n"
        "Other commands:\n"
        "• /autologin — skip OTP if session is still valid\n"
        "• /mypoints — check your points balance\n"
        "• /myreferral — get your referral link\n"
        "• /buypremium — get Premium access (contact admin)\n"
        "• /whoami — show your Telegram ID & status\n"
        "• /stop — stop the current submission run\n"
        "• /cancel — stop the current flow\n"
    )
    if is_admin(user_id):
        text += (
            "\n👑 Admin commands:\n"
            "• /stats — usage stats & top users\n"
            "• /listusers — list all users with IDs\n"
            "• /cooldown [on|off|seconds] — manage global cooldown\n"
            "• /setdelay <min> [extra] — set global delay\n"
            "• /setdelay <user_id> <seconds> — custom delay per user\n"
            "• /cleardelay <user_id> — remove custom delay\n"
            "• /ban <user_id> — ban a user\n"
            "• /unban <user_id> — unban a user\n"
            "• /setcooldown <user_id> [on|off] — toggle cooldown per user\n"
            "• /userinfo <user_id> — full profile card\n"
            "• /turbo — 40s cooldown for 5 min, then resets to 15s\n"
            "• /addpoints <user_id> <amount> — add points\n"
            "• /deductpoints <user_id> <amount> — deduct points\n"
            "• /resetpoints [confirm] — reset ALL users' points to 0\n"
            "• /givepoints <amount> — add points to ALL users\n"
            "• /creditdaily — manually credit daily points to free users\n"
            "• /addpremium <user_id> [weeks] — grant premium\n"
            "• /removepremium <user_id> — revoke premium\n"
            "• /premiumusers — list all premium users\n"
            "• /broadcast <msg> — message all users\n"
            "• /msg <user_id> <text> — send a direct message to a user\n"
            "• /users — total user count\n"
            "• /admins — list admin IDs\n"
            "• /resetcooldown [user_id] — clear cooldown timer\n"
            "• /lock — lock bot for all non-admin users\n"
            "• /unlock — unlock bot for all users\n"
            "• /setmax <number> — set max rounds per run for users\n"
        )
    text += "\n⚡ Powered by @xrishna"
    await update.message.reply_text(text)


# ── Admin guard ───────────────────────────────────────────────────────────────

def admin_only(func):
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_admin(update.effective_user.id):
            await update.message.reply_text("🚫 Admin only command.")
            return
        return await func(update, context)
    return wrapper


# ── Admin commands ────────────────────────────────────────────────────────────

@admin_only
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    users = get_all_users()
    total = len(users)
    premium_count = sum(1 for u in users if u["is_premium"])
    banned_count = sum(1 for u in users if u["is_banned"])
    top = sorted(users, key=lambda u: u["points"], reverse=True)[:5]
    top_str = "\n".join(
        f"  {i + 1}. {u['name'] or 'Unknown'} — {u['points']} pts (ID: {u['telegram_id']})"
        for i, u in enumerate(top)
    ) or "  No data yet"
    await update.message.reply_text(
        f"📊 Bot Stats\n\n"
        f"👥 Total users: {total}\n"
        f"👑 Premium users: {premium_count}\n"
        f"🚫 Banned users: {banned_count}\n\n"
        f"🏆 Top Users:\n{top_str}"
    )


@admin_only
async def listusers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    users = get_all_users()
    if not users:
        await update.message.reply_text("No users yet.")
        return
    lines = []
    for u in users[:50]:
        flags = ("👑" if u["is_premium"] else "") + ("🚫" if u["is_banned"] else "")
        lines.append(
            f"{flags} {u['name'] or 'Unknown'} | {u['telegram_id']} | {u['points']} pts"
        )
    await update.message.reply_text(
        f"👥 Users ({len(users)} total):\n\n" + "\n".join(lines)
    )


@admin_only
async def cooldown_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        enabled = context.bot_data.get("cooldown_global_enabled", True)
        secs = context.bot_data.get("global_cooldown_seconds", DEFAULT_COOLDOWN)
        await update.message.reply_text(
            f"⏱ Global Cooldown\n"
            f"Status: {'on' if enabled else 'off'}\n"
            f"Duration: {secs}s\n\n"
            f"Usage: /cooldown on|off|<seconds>"
        )
        return
    val = args[0].lower()
    if val == "on":
        context.bot_data["cooldown_global_enabled"] = True
        await update.message.reply_text("✅ Global cooldown enabled.")
    elif val == "off":
        context.bot_data["cooldown_global_enabled"] = False
        await update.message.reply_text("✅ Global cooldown disabled.")
    else:
        try:
            secs = int(val)
            context.bot_data["global_cooldown_seconds"] = secs
            context.bot_data["cooldown_global_enabled"] = True
            await update.message.reply_text(f"✅ Global cooldown set to {secs}s.")
        except ValueError:
            await update.message.reply_text("❌ Usage: /cooldown on|off|<seconds>")


@admin_only
async def setdelay(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        min_d = context.bot_data.get("min_delay", DEFAULT_MIN_DELAY)
        max_e = context.bot_data.get("max_extra", DEFAULT_MAX_EXTRA)
        await update.message.reply_text(
            f"⏱ Current global delay: {min_d}–{min_d + max_e}s\n\n"
            f"Usage:\n"
            f"  /setdelay <min> [extra]    — global\n"
            f"  /setdelay <user_id> <sec>  — per-user (user_id > 10000)"
        )
        return

    if len(args) >= 2 and args[0].isdigit() and int(args[0]) > 10000:
        try:
            target_id = int(args[0])
            delay = int(args[1])
            upsert_user(target_id, custom_delay=delay)
            await update.message.reply_text(
                f"✅ Custom delay for {target_id} set to {delay}s."
            )
        except ValueError:
            await update.message.reply_text("❌ Usage: /setdelay <user_id> <seconds>")
        return

    try:
        min_d = int(args[0])
        if min_d < 10:
            await update.message.reply_text("❌ Minimum delay must be at least 10s.")
            return
        max_e = int(args[1]) if len(args) >= 2 else DEFAULT_MAX_EXTRA
        context.bot_data["min_delay"] = min_d
        context.bot_data["max_extra"] = max_e
        await update.message.reply_text(
            f"✅ Global delay: {min_d}–{min_d + max_e}s"
        )
    except ValueError:
        await update.message.reply_text("❌ Use numbers only. E.g. /setdelay 45 20")


@admin_only
async def cleardelay(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /cleardelay <user_id>")
        return
    try:
        target_id = int(context.args[0])
        upsert_user(target_id, custom_delay=None)
        await update.message.reply_text(f"✅ Custom delay cleared for {target_id}.")
    except ValueError:
        await update.message.reply_text("❌ Invalid user_id.")


@admin_only
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /ban <user_id>")
        return
    try:
        target_id = int(context.args[0])
        upsert_user(target_id, is_banned=1)
        await update.message.reply_text(f"🚫 User {target_id} has been banned.")
    except ValueError:
        await update.message.reply_text("❌ Invalid user_id.")


@admin_only
async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /unban <user_id>")
        return
    try:
        target_id = int(context.args[0])
        upsert_user(target_id, is_banned=0)
        await update.message.reply_text(f"✅ User {target_id} has been unbanned.")
    except ValueError:
        await update.message.reply_text("❌ Invalid user_id.")


@admin_only
async def setcooldown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /setcooldown <user_id> [on|off]")
        return
    try:
        target_id = int(args[0])
        val = (args[1].lower() if len(args) >= 2 else "on")
        enabled = 0 if val == "off" else 1
        upsert_user(target_id, cooldown_on=enabled)
        await update.message.reply_text(
            f"✅ Cooldown for {target_id} set to {'on' if enabled else 'off'}."
        )
    except ValueError:
        await update.message.reply_text("❌ Invalid user_id.")


@admin_only
async def userinfo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /userinfo <user_id>")
        return
    try:
        target_id = int(context.args[0])
        u = get_user(target_id)
        if not u:
            await update.message.reply_text(f"❌ User {target_id} not found.")
            return
        premium_str = "👑 Premium"
        if u["is_premium"] and u["premium_expiry"]:
            premium_str += f"\n   Expires: {u['premium_expiry'][:10]}"
        elif not u["is_premium"]:
            premium_str = "Free"
        await update.message.reply_text(
            f"👤 User Profile — {target_id}\n\n"
            f"Name: {u['name'] or 'N/A'}\n"
            f"Mobile: {u['mobile'] or 'N/A'}\n"
            f"Username: @{u['username'] or 'N/A'}\n"
            f"Points: {u['points']} pts\n"
            f"Total Runs: {u['total_runs']}\n"
            f"Status: {premium_str}\n"
            f"Banned: {'Yes 🚫' if u['is_banned'] else 'No'}\n"
            f"Custom Delay: {str(u['custom_delay']) + 's' if u['custom_delay'] else 'Default'}\n"
            f"Cooldown: {'on' if u['cooldown_on'] else 'off'}\n"
            f"Last Run: {(u['last_run_at'] or 'Never')[:16]}\n"
            f"Joined: {(u['created_at'] or 'N/A')[:10]}"
        )
    except ValueError:
        await update.message.reply_text("❌ Invalid user_id.")


@admin_only
async def turbo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    turbo_key = "turbo_active_since"
    context.bot_data["min_delay"] = 40
    context.bot_data["max_extra"] = 0
    ts = datetime.now(tz=timezone.utc).isoformat()
    context.bot_data[turbo_key] = ts
    await update.message.reply_text(
        "⚡ TURBO mode ON!\n⏱ Delay: 40s fixed\n⏰ Resets to 15s in 5 minutes."
    )

    async def _reset_turbo():
        await asyncio.sleep(300)
        if context.bot_data.get(turbo_key) == ts:
            context.bot_data["min_delay"] = 15
            context.bot_data["max_extra"] = DEFAULT_MAX_EXTRA
            context.bot_data.pop(turbo_key, None)
            try:
                await update.message.reply_text("🔄 TURBO mode ended. Delay reset to 15s.")
            except Exception:
                pass

    asyncio.create_task(_reset_turbo())


@admin_only
async def addpoints(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text("Usage: /addpoints <user_id> <amount>")
        return
    try:
        target_id = int(args[0])
        amount = int(args[1])
        u = get_user(target_id)
        if not u:
            await update.message.reply_text(f"❌ User {target_id} not found.")
            return
        new_pts = u["points"] + amount
        upsert_user(target_id, points=new_pts)
        await update.message.reply_text(
            f"✅ +{amount} pts to {target_id}\nNew balance: {new_pts} pts"
        )
    except ValueError:
        await update.message.reply_text("❌ Invalid arguments.")


@admin_only
async def deductpoints(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text("Usage: /deductpoints <user_id> <amount>")
        return
    try:
        target_id = int(args[0])
        amount = int(args[1])
        u = get_user(target_id)
        if not u:
            await update.message.reply_text(f"❌ User {target_id} not found.")
            return
        new_pts = max(0, u["points"] - amount)
        upsert_user(target_id, points=new_pts)
        await update.message.reply_text(
            f"✅ -{amount} pts from {target_id}\nNew balance: {new_pts} pts"
        )
    except ValueError:
        await update.message.reply_text("❌ Invalid arguments.")


@admin_only
async def resetpoints(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args or args[0].lower() != "confirm":
        await update.message.reply_text(
            "⚠️ This resets ALL users' points to 0.\n\nType /resetpoints confirm to proceed."
        )
        return
    with get_conn() as conn:
        conn.execute("UPDATE users SET points = 0")
        conn.commit()
    await update.message.reply_text("✅ All users' points reset to 0.")


@admin_only
async def givepoints(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /givepoints <amount>")
        return
    try:
        amount = int(context.args[0])
        with get_conn() as conn:
            conn.execute("UPDATE users SET points = points + ?", (amount,))
            conn.commit()
        await update.message.reply_text(f"✅ +{amount} pts added to ALL users.")
    except ValueError:
        await update.message.reply_text("❌ Invalid amount.")


@admin_only
async def creditdaily(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    users = get_all_users()
    credited = 0
    for u in users:
        if not u["is_premium"] and u["daily_credited"] != today:
            upsert_user(
                u["telegram_id"],
                points=u["points"] + DAILY_POINTS_FREE,
                daily_credited=today,
            )
            credited += 1
    await update.message.reply_text(
        f"✅ Daily credit done!\n👥 Credited: {credited} users\n+{DAILY_POINTS_FREE} pts each"
    )


@admin_only
async def addpremium(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /addpremium <user_id> [weeks]")
        return
    try:
        target_id = int(args[0])
        weeks = int(args[1]) if len(args) >= 2 else 1
        expiry = datetime.now(tz=timezone.utc) + timedelta(weeks=weeks)
        upsert_user(target_id, is_premium=1, premium_expiry=expiry.isoformat())
        await update.message.reply_text(
            f"👑 Premium granted to {target_id}\n"
            f"Expires: {expiry.strftime('%d %b %Y')} ({weeks} week{'s' if weeks > 1 else ''})"
        )
    except ValueError:
        await update.message.reply_text("❌ Invalid arguments.")


@admin_only
async def removepremium(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /removepremium <user_id>")
        return
    try:
        target_id = int(context.args[0])
        upsert_user(target_id, is_premium=0, premium_expiry=None)
        await update.message.reply_text(f"✅ Premium removed from {target_id}.")
    except ValueError:
        await update.message.reply_text("❌ Invalid user_id.")


@admin_only
async def premiumusers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    users = get_all_users()
    premium = [u for u in users if u["is_premium"]]
    if not premium:
        await update.message.reply_text("No premium users.")
        return
    lines = [
        f"👑 {u['name'] or 'Unknown'} | {u['telegram_id']} | Exp: {(u['premium_expiry'] or '')[:10]}"
        for u in premium
    ]
    await update.message.reply_text(
        f"👑 Premium Users ({len(premium)}):\n\n" + "\n".join(lines)
    )


@admin_only
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    msg = " ".join(context.args)
    users = get_all_users()
    sent = failed = 0
    for u in users:
        try:
            await context.bot.send_message(chat_id=u["telegram_id"], text=msg)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
    await update.message.reply_text(
        f"📢 Broadcast done!\n✅ Sent: {sent}\n❌ Failed: {failed}"
    )


@admin_only
async def msg_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text("Usage: /msg <user_id> <text>")
        return
    try:
        target_id = int(args[0])
        text = " ".join(args[1:])
        await context.bot.send_message(
            chat_id=target_id, text=f"📨 Message from Admin:\n\n{text}"
        )
        await update.message.reply_text(f"✅ Sent to {target_id}.")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {e}")


@admin_only
async def users_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    users = get_all_users()
    await update.message.reply_text(f"👥 Total users: {len(users)}")


@admin_only
async def admins_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not ADMIN_IDS:
        await update.message.reply_text(
            "No admin IDs configured.\nSet the ADMIN_IDS environment variable."
        )
        return
    await update.message.reply_text(
        "🔑 Admins:\n" + "\n".join(f"• {aid}" for aid in ADMIN_IDS)
    )


@admin_only
async def resetcooldown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if args:
        try:
            target_id = int(args[0])
            upsert_user(target_id, last_run_at=None)
            await update.message.reply_text(f"✅ Cooldown cleared for {target_id}.")
        except ValueError:
            await update.message.reply_text("❌ Invalid user_id.")
    else:
        with get_conn() as conn:
            conn.execute("UPDATE users SET last_run_at = NULL")
            conn.commit()
        await update.message.reply_text("✅ Cooldown cleared for all users.")


@admin_only
async def setmax(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        cur = context.bot_data.get("max_rounds", DEFAULT_MAX_ROUNDS)
        await update.message.reply_text(
            f"🔢 Current max rounds for users: {cur}\n\n"
            f"Usage: /setmax <number>\n"
            f"Admins always have no limit."
        )
        return
    try:
        val = int(context.args[0])
        if val < 1:
            await update.message.reply_text("❌ Must be at least 1.")
            return
        context.bot_data["max_rounds"] = val
        await update.message.reply_text(
            f"✅ Max rounds per run set to {val}.\n"
            f"Users can now submit 1–{val} rounds per session."
        )
    except ValueError:
        await update.message.reply_text("❌ Usage: /setmax <number>")


@admin_only
async def lock_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.bot_data["locked"] = True
    await update.message.reply_text(
        "🔐 Bot is now LOCKED.\n"
        "All users are blocked. Only admins can still use it.\n\n"
        "Use /unlock to open it again."
    )


@admin_only
async def unlock_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.bot_data["locked"] = False
    await update.message.reply_text(
        "🔓 Bot is now UNLOCKED.\n"
        "All premium users can access it again."
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()
    app.bot_data.setdefault("min_delay", DEFAULT_MIN_DELAY)
    app.bot_data.setdefault("max_extra", DEFAULT_MAX_EXTRA)
    app.bot_data.setdefault("stop_requests", set())

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("autologin", autologin_cmd),
        ],
        states={
            MOBILE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_mobile)],
            OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_otp)],
            ROUNDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_rounds)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("stop", stop_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("mypoints", mypoints))
    app.add_handler(CommandHandler("myreferral", myreferral))
    app.add_handler(CommandHandler("buypremium", buypremium))
    app.add_handler(CommandHandler("whoami", whoami))

    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("listusers", listusers))
    app.add_handler(CommandHandler("cooldown", cooldown_cmd))
    app.add_handler(CommandHandler("setdelay", setdelay))
    app.add_handler(CommandHandler("cleardelay", cleardelay))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("unban", unban_user))
    app.add_handler(CommandHandler("setcooldown", setcooldown))
    app.add_handler(CommandHandler("userinfo", userinfo))
    app.add_handler(CommandHandler("turbo", turbo))
    app.add_handler(CommandHandler("addpoints", addpoints))
    app.add_handler(CommandHandler("deductpoints", deductpoints))
    app.add_handler(CommandHandler("resetpoints", resetpoints))
    app.add_handler(CommandHandler("givepoints", givepoints))
    app.add_handler(CommandHandler("creditdaily", creditdaily))
    app.add_handler(CommandHandler("addpremium", addpremium))
    app.add_handler(CommandHandler("removepremium", removepremium))
    app.add_handler(CommandHandler("premiumusers", premiumusers))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("msg", msg_user))
    app.add_handler(CommandHandler("users", users_count))
    app.add_handler(CommandHandler("admins", admins_list))
    app.add_handler(CommandHandler("resetcooldown", resetcooldown))
    app.add_handler(CommandHandler("lock", lock_bot))
    app.add_handler(CommandHandler("unlock", unlock_bot))
    app.add_handler(CommandHandler("setmax", setmax))

    logger.info("Bot is starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
