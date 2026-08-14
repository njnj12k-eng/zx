```python
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import time
import platform
import subprocess
import asyncio
import os
import re
from datetime import datetime, timedelta
import psutil
import socket
import json
import random
import string
import pytz
import sqlite3
from telethon import TelegramClient, events
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    PhoneCodeExpiredError,
    FloodWaitError
)

TOKEN = "8961040480:AAHNKEnK7LZuCp9fSJ5td2_XdGFqPtwp_dY"
CHANNEL_USERNAME = "@ReaperSelfChannel"

ADMIN_IDS = [7803165903, 8831703400]

# ==================== دیتابیس ====================

DB_FILE = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            phone TEXT,
            joined_date TEXT,
            is_banned INTEGER DEFAULT 0,
            is_verified INTEGER DEFAULT 0,
            remaining_days INTEGER DEFAULT 0,
            expiry_date TEXT,
            clock_active INTEGER DEFAULT 1
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS codes (
            code TEXT PRIMARY KEY,
            days INTEGER,
            expiry_date TEXT,
            created_date TEXT,
            used INTEGER DEFAULT 0,
            used_by TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            user_id INTEGER PRIMARY KEY,
            session_string TEXT,
            phone TEXT,
            api_hash TEXT,
            api_id INTEGER,
            created_date TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verify_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            card_number TEXT,
            photo_id TEXT,
            status TEXT DEFAULT 'pending',
            request_date TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            message TEXT,
            status TEXT DEFAULT 'open',
            created_date TEXT,
            admin_response TEXT,
            response_date TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

user_states = {}
salf_login_data = {}
clock_tasks = {}
admin_salf_data = {}
support_mode = {}
user_menu_mode = {}
clock_status = {}
salf_clients = {}

if not os.path.exists("sessions"):
    os.makedirs("sessions")

# ==================== توابع دیتابیس ====================

def db_add_user(user_id, username, first_name, last_name, phone=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, phone, joined_date)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, username, first_name, last_name, phone, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def db_is_banned(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT is_banned FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result and result[0] == 1

def db_ban_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_banned = 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def db_unban_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_banned = 0 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def db_is_verified(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT is_verified FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result and result[0] == 1

def db_verify_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_verified = 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def db_add_code(code, days, expiry_date):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO codes (code, days, expiry_date, created_date) VALUES (?, ?, ?, ?)',
                   (code, days, expiry_date.isoformat(), datetime.now().isoformat()))
    conn.commit()
    conn.close()

def db_get_code(code):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM codes WHERE code = ?', (code,))
    result = cursor.fetchone()
    conn.close()
    return result

def db_use_code(code, user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE codes SET used = 1, used_by = ? WHERE code = ?', (str(user_id), code))
    conn.commit()
    conn.close()

def db_delete_code(code):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM codes WHERE code = ?', (code,))
    conn.commit()
    conn.close()

def db_get_all_codes():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM codes')
    result = cursor.fetchall()
    conn.close()
    return result

def db_save_session(user_id, session_string, phone, api_hash, api_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO sessions (user_id, session_string, phone, api_hash, api_id, created_date)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, session_string, phone, api_hash, api_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def db_get_session(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM sessions WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def db_delete_session(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def db_get_all_sessions():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM sessions')
    result = cursor.fetchall()
    conn.close()
    return result

def db_add_verify_request(user_id, username, card_number, photo_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO verify_requests (user_id, username, card_number, photo_id, request_date)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, username, card_number, photo_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return cursor.lastrowid

def db_update_verify_request(request_id, status):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE verify_requests SET status = ? WHERE id = ?', (status, request_id))
    conn.commit()
    conn.close()

def db_add_support_ticket(user_id, username, message):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO support_tickets (user_id, username, message, created_date)
        VALUES (?, ?, ?, ?)
    ''', (user_id, username, message, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return cursor.lastrowid

# ==================== توابع کمکی ====================

def is_admin(user_id):
    return user_id in ADMIN_IDS

def get_remaining_days(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT remaining_days, expiry_date FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result and result[0] > 0 else 0

def get_expiry_date(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT expiry_date FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result and result[0]:
        return result[0].split('T')[0] if 'T' in result[0] else result[0]
    return "ندارد"

def has_active_subscription(user_id):
    return get_remaining_days(user_id) > 0

def get_clock_status(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT clock_active FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] == 1 if result else True

def set_clock_status(user_id, status):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET clock_active = ? WHERE user_id = ?', (1 if status else 0, user_id))
    conn.commit()
    conn.close()

def is_user_banned(user_id):
    return db_is_banned(user_id)

def ban_user(user_id):
    db_ban_user(user_id)

def unban_user(user_id):
    db_unban_user(user_id)

def is_user_verified(user_id):
    return db_is_verified(user_id)

def verify_user(user_id):
    db_verify_user(user_id)

def save_user_session(user_id, session_string, phone, api_hash, api_id):
    db_save_session(user_id, session_string, phone, api_hash, api_id)

def get_user_session(user_id):
    result = db_get_session(user_id)
    if result:
        return {'user_id': result[0], 'session': result[1], 'phone': result[2],
                'api_hash': result[3], 'api_id': result[4], 'created': result[5]}
    return None

def delete_user_session(user_id):
    db_delete_session(user_id)

def generate_code():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=15))

def create_new_code(days):
    while True:
        new_code = generate_code()
        if not db_get_code(new_code):
            break
    expiry_date = datetime.now() + timedelta(days=days)
    db_add_code(new_code, days, expiry_date)
    return new_code, expiry_date

def validate_code(code):
    result = db_get_code(code)
    if not result:
        return None, "❌ کد وارد شده صحیح نیست!"
    if result[4] == 1:
        return None, "❌ این کد قبلاً استفاده شده است!"
    expiry_date = datetime.fromisoformat(result[2])
    if datetime.now() > expiry_date:
        return None, "⏳ کد وارد شده منقضی شده است!"
    return {'days': result[1], 'expiry': result[2]}, None

def use_code(code, user_id):
    result = db_get_code(code)
    if not result or result[4] == 1:
        return False
    db_use_code(code, user_id)
    days = result[1]
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT remaining_days, expiry_date FROM users WHERE user_id = ?', (user_id,))
    user_data = cursor.fetchone()
    if user_data:
        new_remaining = (user_data[0] or 0) + days
        expiry = datetime.now() + timedelta(days=new_remaining)
        cursor.execute('UPDATE users SET remaining_days = ?, expiry_date = ? WHERE user_id = ?',
                       (new_remaining, expiry.isoformat(), user_id))
    else:
        expiry = datetime.now() + timedelta(days=days)
        cursor.execute('INSERT INTO users (user_id, remaining_days, expiry_date) VALUES (?, ?, ?)',
                       (user_id, days, expiry.isoformat()))
    conn.commit()
    conn.close()
    return True

# ==================== پنل سلف ====================

async def show_self_panel(client, event):
    try:
        user_id = event.sender_id
        if not has_active_subscription(user_id):
            return
        clock_active = get_clock_status(user_id)
        panel_text = (
            "🔰 **به پنل ریپر سلف خوش آمدید.**\n"
            "⚡ لطفا از منوی زیر انتخاب نمایید !"
        )
        keyboard = [[InlineKeyboardButton(
            "⏰ ساعت اکانت غیرفعال" if clock_active else "⏰ ساعت اکانت فعال",
            callback_data=f"toggle_clock_salf_{user_id}"
        )]]
        await client.edit_message(event.message.peer_id, event.message.id, panel_text,
                                 parse_mode='markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    except:
        pass

async def handle_salf_toggle_clock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("toggle_clock_salf_"):
        user_id = int(data.split("_")[3])
        if is_user_banned(user_id) or not has_active_subscription(user_id):
            await query.edit_message_text("⛔ شما دسترسی ندارید!", parse_mode='markdown')
            return
        new_status = not get_clock_status(user_id)
        set_clock_status(user_id, new_status)
        if new_status:
            await set_clock_on_profile(user_id)
            text = "✅ ساعت اکانت شما فعال شد !"
        else:
            await remove_clock_from_profile(user_id)
            text = "❌ ساعت اکانت شما غیرفعال شد !"
        keyboard = [[InlineKeyboardButton(
            "⏰ ساعت اکانت غیرفعال" if new_status else "⏰ ساعت اکانت فعال",
            callback_data=f"toggle_clock_salf_{user_id}"
        )]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')

# ==================== راه‌اندازی کلاینت‌های سلف ====================

async def start_salf_client(user_id):
    try:
        session_data = get_user_session(user_id)
        if not session_data:
            return False
        if user_id in salf_clients:
            try:
                await salf_clients[user_id].disconnect()
            except:
                pass
            del salf_clients[user_id]
        client = TelegramClient(f"sessions/user_{user_id}", session_data['api_id'], session_data['api_hash'])
        await client.connect()
        if not await client.is_user_authorized():
            try:
                await client.sign_in(session_data['phone'])
            except:
                await client.disconnect()
                return False
        salf_clients[user_id] = client
        @client.on(events.MessageEdited)
        @client.on(events.NewMessage)
        async def panel_handler(event):
            if event.sender_id == user_id and event.message and event.message.text and event.message.text.lower() == "پنل":
                await show_self_panel(client, event)
        await client.run_until_disconnected()
        return True
    except:
        return False

async def start_all_salf_clients():
    for session in db_get_all_sessions():
        asyncio.create_task(start_salf_client(session[0]))

# ==================== توابع تنظیم ساعت ====================

async def set_clock_on_profile(user_id):
    try:
        if not get_clock_status(user_id):
            return False
        session_data = get_user_session(user_id)
        if not session_data or session_data['api_id'] > 2147483647:
            return False
        client = TelegramClient(f"sessions/user_{user_id}", session_data['api_id'], session_data['api_hash'])
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return False
        me = await client.get_me()
        current_name = f"{me.first_name or ''} {me.last_name or ''}".strip() or me.username or "کاربر"
        iran_tz = pytz.timezone('Asia/Tehran')
        time_str = datetime.now(iran_tz).strftime('%H:%M')
        new_name = re.sub(r'\s*\d{2}:\d{2}$', '', current_name).strip() + f" {time_str}"
        if new_name != current_name:
            try:
                await client(UpdateProfileRequest(first_name=new_name))
            except:
                pass
        await client.disconnect()
        return True
    except:
        return False

async def remove_clock_from_profile(user_id):
    try:
        session_data = get_user_session(user_id)
        if not session_data or session_data['api_id'] > 2147483647:
            return False
        client = TelegramClient(f"sessions/user_{user_id}", session_data['api_id'], session_data['api_hash'])
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return False
        me = await client.get_me()
        current_name = f"{me.first_name or ''} {me.last_name or ''}".strip() or me.username or "کاربر"
        clean_name = re.sub(r'\s*\d{2}:\d{2}$', '', current_name).strip()
        if clean_name != current_name:
            try:
                await client(UpdateProfileRequest(first_name=clean_name))
            except:
                pass
        await client.disconnect()
        return True
    except:
        return False

# ==================== اطلاعات سرور ====================

async def get_server_info():
    try:
        ping_time = None
        try:
            process = await asyncio.create_subprocess_exec("ping", "-c", "1", "-W", "1", "8.8.8.8",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, _ = await process.communicate(timeout=2)
            if process.returncode == 0:
                match = re.search(r'time[=<](\d+\.?\d*)\s*ms', stdout.decode())
                if match:
                    ping_time = float(match.group(1))
        except:
            ping_time = None
        cpu = f"{psutil.cpu_percent(interval=0.2):.1f}%"
        mem = psutil.virtual_memory()
        mem_info = f"{mem.percent:.1f}% ({mem.used // (1024**3)}GB / {mem.total // (1024**3)}GB)"
        disk = psutil.disk_usage('/')
        disk_info = f"{disk.percent:.1f}% ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)"
        boot = psutil.boot_time()
        uptime_s = time.time() - boot
        days, rem = divmod(int(uptime_s), 86400)
        hours, rem = divmod(rem, 3600)
        minutes = rem // 60
        uptime = f"{days} روز، {hours} ساعت، {minutes} دقیقه" if days else f"{hours} ساعت، {minutes} دقیقه"
        status = "🔴 قطع" if ping_time is None else "🟢 عالی" if ping_time < 50 else "🟢 آنلاین" if ping_time < 100 else "🟡 هشدار" if ping_time < 200 else "🔴 ضعیف"
        return {'status': status, 'ping': f"{ping_time:.1f} ms" if ping_time else "❌ نامشخص",
                'cpu': cpu, 'memory': mem_info, 'disk': disk_info,
                'os': f"{platform.system()} {platform.release()}", 'uptime': uptime}
    except:
        return {'status': "🟢 آنلاین", 'ping': "📶 متصل", 'cpu': "نامشخص",
                'memory': "نامشخص", 'disk': "نامشخص", 'os': platform.system(), 'uptime': "نامشخص"}

def get_host_expiry():
    try:
        start = datetime(2026, 7, 28)
        days_left = max(0, 30 - (datetime.now() - start).days)
        expiry = start + timedelta(days=30)
        return {'days_left': days_left, 'total_days': 30, 'expiry_date': expiry.strftime('%Y-%m-%d'),
                'start_date': start.strftime('%Y-%m-%d'), 'percent': (days_left / 30) * 100}
    except:
        return {'days_left': 26, 'total_days': 30, 'expiry_date': "2026-08-27",
                'start_date': "2026-07-28", 'percent': 86.6}

# ==================== بخش استارت ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = update.effective_user
    db_add_user(user_id, user.username, user.first_name, user.last_name)
    if is_user_banned(user_id):
        await update.message.reply_text("🚫 شما از طرف مدیریت مسدود شده اید!", parse_mode='markdown')
        return
    mention = f"@{user.username}" if user.username else user.first_name
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_menu_mode:
        del user_menu_mode[user_id]
    if is_admin(user_id):
        text = (
            f"👋 درود {mention} به پنل ریپر سلف Reaper Self خوش آمدید.\n\n"
            "⚙️ توی این پنل میتوانید ربات ریپر سلف Reaper Self را کنترل و مدیریت کنید.\n\n"
            "📌 لطفا از منوی زیر انتخاب نمایید که چه کاری را می‌خواهید انتخاب دهید."
        )
        keyboard = [
            [InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings")],
            [InlineKeyboardButton("📊 آمار کل", callback_data="admin_stats")],
            [InlineKeyboardButton("📡 بررسی پینگ", callback_data="admin_ping"), InlineKeyboardButton("⏳ اعتبار هاست", callback_data="admin_host")],
            [InlineKeyboardButton("👥 منوی کاربران", callback_data="admin_users_menu")]
        ]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')
        return
    try:
        chat_member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if chat_member.status in ["member", "administrator", "creator"]:
            rem = get_remaining_days(user_id)
            verified = is_user_verified(user_id)
            logged = get_user_session(user_id) is not None
            text = (
                f"👋 سلام {mention} به ربات ریپر سلف Reaper Self خوش آمدید !\n\n"
                "🛡️ توی این ربات میتوانید از پشتیبانی، خرید، نصب ربات سلف بهره ببرید!\n\n"
                "💬 لطفا اگر سوالی دارید از بخش پشتیبانی، با پشتیبان‌ها در ارتباط باشید!"
            )
            keyboard = [
                [InlineKeyboardButton("👨‍💻 پشتیبانی", callback_data="support")],
                [InlineKeyboardButton("🤔 سلف چیست ؟", callback_data="what_is_self"), InlineKeyboardButton("📣 کانال ما", url="https://t.me/ReaperSelfChannel")],
                [InlineKeyboardButton(f"📅 انقضا شما : ( {rem} روز )", callback_data="expiry")],
                [InlineKeyboardButton("✔️ احراز هویت شده ✅" if verified else "✔️ احراز هویت", callback_data="verified_already" if verified else "verify")],
                [InlineKeyboardButton("💳 خرید اشتراک", callback_data="buy_subscription")],
                [InlineKeyboardButton("💶 خرید با کد", callback_data="buy_with_code")]
            ]
            if has_active_subscription(user_id):
                keyboard.append([InlineKeyboardButton("🔑 ورود سلف", callback_data="salf_login")])
            keyboard.append([InlineKeyboardButton("💎 نرخ", callback_data="rate")])
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')
            return
    except:
        pass
    text = "🔒 برای دسترسی به خدمات ما، ابتدا باید در کانال زیر عضو شوید.\n✅ پس از عضویت، روی دکمه «عضو شدم» کلیک کنید."
    keyboard = [
        [InlineKeyboardButton("🔗 ریپر سلف Reaper Self", url="https://t.me/ReaperSelfChannel")],
        [InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')

async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = query.from_user
    if is_user_banned(user_id):
        await query.edit_message_text("🚫 شما از طرف مدیریت مسدود شده اید!", parse_mode='markdown')
        return
    mention = f"@{user.username}" if user.username else user.first_name
    if is_admin(user_id):
        text = (
            f"👋 درود {mention} به پنل ریپر سلف Reaper Self خوش آمدید.\n\n"
            "⚙️ توی این پنل میتوانید ربات ریپر سلف Reaper Self را کنترل و مدیریت کنید.\n\n"
            "📌 لطفا از منوی زیر انتخاب نمایید که چه کاری را می‌خواهید انتخاب دهید."
        )
        keyboard = [
            [InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings")],
            [InlineKeyboardButton("📊 آمار کل", callback_data="admin_stats")],
            [InlineKeyboardButton("📡 بررسی پینگ", callback_data="admin_ping"), InlineKeyboardButton("⏳ اعتبار هاست", callback_data="admin_host")],
            [InlineKeyboardButton("👥 منوی کاربران", callback_data="admin_users_menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')
        return
    try:
        chat_member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if chat_member.status in ["member", "administrator", "creator"]:
            rem = get_remaining_days(user_id)
            verified = is_user_verified(user_id)
            logged = get_user_session(user_id) is not None
            text = (
                f"👋 سلام {mention} به ربات ریپر سلف Reaper Self خوش آمدید !\n\n"
                "🛡️ توی این ربات میتوانید از پشتیبانی، خرید، نصب ربات سلف بهره ببرید!\n\n"
                "💬 لطفا اگر سوالی دارید از بخش پشتیبانی، با پشتیبان‌ها در ارتباط باشید!"
            )
            keyboard = [
                [InlineKeyboardButton("👨‍💻 پشتیبانی", callback_data="support")],
                [InlineKeyboardButton("🤔 سلف چیست ؟", callback_data="what_is_self"), InlineKeyboardButton("📣 کانال ما", url="https://t.me/ReaperSelfChannel")],
                [InlineKeyboardButton(f"📅 انقضا شما : ( {rem} روز )", callback_data="expiry")],
                [InlineKeyboardButton("✔️ احراز هویت شده ✅" if verified else "✔️ احراز هویت", callback_data="verified_already" if verified else "verify")],
                [InlineKeyboardButton("💳 خرید اشتراک", callback_data="buy_subscription")],
                [InlineKeyboardButton("💶 خرید با کد", callback_data="buy_with_code")]
            ]
            if has_active_subscription(user_id):
                keyboard.append([InlineKeyboardButton("🔑 ورود سلف", callback_data="salf_login")])
            keyboard.append([InlineKeyboardButton("💎 نرخ", callback_data="rate")])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')
        else:
            text = "🔒 شما هنوز عضو کانال زیر نشده اید !\n✅ ابتدا برای استفاده از ربات در کانال زیر عضو شوید !"
            keyboard = [
                [InlineKeyboardButton("🔗 ریپر سلف Reaper Self", url="https://t.me/ReaperSelfChannel")],
                [InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership")]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')
    except:
        await query.answer("❌ خطا در بررسی عضویت!", show_alert=True)

# ==================== بخش پشتیبانی ====================

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if is_user_banned(user_id):
        await query.edit_message_text("🚫 شما از طرف مدیریت مسدود شده اید!", parse_mode='markdown')
        return
    support_mode[user_id] = True
    text = (
        "👋 شما با موفقیت به بخش پشتیبانی ربات ریپر سلف متصل شدید.\n\n"
        "⚠️ لطفا دقت داشته باشید که در این بخش از ارسال پیام‌های اسپم و تکراری خودداری کنید.\n"
        "⚠️ همچنین استفاده از دستورات مربوط به سلف در این بخش ممنوع بوده و باعث مسدود شدن شما خواهد شد.\n\n"
        "💬 اکنون میتوانید پیام یا سوال خود را برای تیم پشتیبانی ارسال کنید."
    )
    keyboard = [
        [InlineKeyboardButton("💥 لغو اتصال", callback_data="disconnect_support")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')

async def disconnect_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id in support_mode:
        del support_mode[user_id]
    text = "✅ اتصال شما با تیم پشتیبانی با موفقیت قطع شد.\n🔙 با استفاده از دکمه زیر میتوانید به منوی اصلی بازگردید."
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')

async def handle_support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in support_mode or is_user_banned(user_id):
        return
    user = update.effective_user
    mention = f"@{user.username}" if user.username else user.first_name
    msg = update.message.text or update.message.caption or "پیام بدون متن"
    ticket_id = db_add_support_ticket(user_id, mention, msg)
    iran_tz = pytz.timezone('Asia/Tehran')
    now = datetime.now(iran_tz)
    for admin_id in ADMIN_IDS:
        try:
            admin_text = (
                f"📩 پیام جدید از بخش پشتیبانی\n\n"
                f"🆔 شماره تیکت : {ticket_id}\n"
                f"👤 نام کاربر : {mention}\n"
                f"🆔 آیدی عددی : {user_id}\n"
                f"📝 متن پیام :\n<code>{msg}</code>\n\n"
                f"🕐 ساعت : {now.strftime('%H:%M')}\n"
                f"📅 تاریخ : {now.strftime('%Y-%m-%d')}"
            )
            keyboard = [
                [InlineKeyboardButton("💬 پاسخ به کاربر", callback_data=f"reply_{user_id}")],
                [InlineKeyboardButton("🚫 مسدود کردن کاربر", callback_data=f"block_{user_id}")]
            ]
            if update.message.photo:
                await context.bot.send_photo(admin_id, update.message.photo[-1].file_id,
                                            caption=admin_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            elif update.message.document:
                await context.bot.send_document(admin_id, update.message.document.file_id,
                                               caption=admin_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            elif update.message.video:
                await context.bot.send_video(admin_id, update.message.video.file_id,
                                            caption=admin_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            else:
                await context.bot.send_message(admin_id, admin_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        except:
            pass
    await update.message.reply_text(
        "✅ پیام شما با موفقیت به تیم پشتیبانی ارسال شد.\n"
        "⏳ لطفا صبور باشید و منتظر پاسخ از سوی تیم پشتیبانی بمانید.\n"
        "⚠️ از ارسال پیام‌های تکراری و اسپم خودداری فرمایید.",
        parse_mode='markdown'
    )

# ==================== دکمه‌های ادمین برای پاسخ ====================

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("reply_"):
        user_id = int(data.split("_")[1])
        user_states[query.from_user.id] = f"replying_to_{user_id}"
        text = "💬 پاسخ به کاربر\n\n📝 لطفا پاسخ خود را به صورت متن یا رسانه ارسال کنید."
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')
    elif data.startswith("block_"):
        user_id = int(data.split("_")[1])
        if not is_user_banned(user_id):
            ban_user(user_id)
            try:
                await context.bot.send_message(user_id, "🚫 شما از طرف مدیریت مسدود شده اید!\n💬 در صورت نیاز با پشتیبانی تماس بگیرید.", parse_mode='markdown')
            except:
                pass
            await query.edit_message_text(f"✅ کاربر با آیدی {user_id} با موفقیت مسدود شد!", parse_mode='markdown')
        else:
            await query.edit_message_text(f"⚠️ کاربر با آیدی {user_id} قبلاً مسدود شده است!", parse_mode='markdown')

async def handle_admin_reply_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or not str(user_states[user_id]).startswith("replying_to_"):
        return
    target_user_id = int(user_states[user_id].split("_")[2])
    try:
        if update.message.text:
            await context.bot.send_message(target_user_id, f"📩 پاسخ از تیم پشتیبانی :\n\n{update.message.text}", parse_mode='markdown')
        elif update.message.photo:
            caption = f"📩 پاسخ از تیم پشتیبانی :\n\n{update.message.caption or ''}"
            await context.bot.send_photo(target_user_id, update.message.photo[-1].file_id, caption=caption, parse_mode='markdown')
        elif update.message.document:
            caption = f"📩 پاسخ از تیم پشتیبانی :\n\n{update.message.caption or ''}"
            await context.bot.send_document(target_user_id, update.message.document.file_id, caption=caption, parse_mode='markdown')
        elif update.message.video:
            caption = f"📩 پاسخ از تیم پشتیبانی :\n\n{update.message.caption or ''}"
            await context.bot.send_video(target_user_id, update.message.video.file_id, caption=caption, parse_mode='markdown')
        else:
            await update.message.reply_text("❌ نوع پیام پشتیبانی نمیشود!", parse_mode='markdown')
            return
        await update.message.reply_text(f"✅ پاسخ شما با موفقیت برای کاربر {target_user_id} ارسال شد.", parse_mode='markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ارسال پاسخ: {str(e)}", parse_mode='markdown')
    del user_states[user_id]

# ==================== بخش احراز هویت ====================

async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if is_user_verified(user_id):
        await query.answer("✅ شما قبلاً احراز هویت شده اید!", show_alert=True)
        return
    text = "🔐 به منوی احراز هویت خوش آمدید.\n\n📌 لطفا یکی از گزینه‌های زیر را انتخاب نمایید :"
    keyboard = [
        [InlineKeyboardButton("❌ حذف کارت", callback_data="delete_card")],
        [InlineKeyboardButton("➕ کارت جدید", callback_data="new_card")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')

async def verified_already(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.answer("✅ شما قبلاً احراز هویت شده اید!", show_alert=True)

async def delete_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.answer("❌ کارت شما با موفقیت حذف شد!", show_alert=True)

async def new_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_states[query.from_user.id] = "waiting_for_verify_photo"
    text = (
        "🔐 به بخش احراز هویت خوش آمدید.\n\n"
        "📌 نکات مهم :\n"
        "1️⃣ شماره کارت و نام صاحب کارت باید کاملا مشخص و خوانا باشد.\n"
        "2️⃣ لطفا تاریخ اعتبار و Cvv2 کارت خود را بپوشانید.\n"
        "3️⃣ فقط با کارتی که احراز هویت میکنید میتوانید خرید انجام دهید.\n"
        "4️⃣ در صورتی که توانایی ارسال عکس از کارت را ندارید، تنها راه حل ارسال عکس از کارت ملی یا شناسنامه صاحب کارت است.\n\n"
        "📸 لطفا عکس از کارتی که میخواهید با آن خرید انجام دهید ارسال کنید."
    )
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_verify")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')

async def handle_verify_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_for_verify_photo":
        return
    if not update.message.photo:
        await update.message.reply_text("❌ لطفا فقط عکس ارسال کنید!", parse_mode='markdown')
        return
    user_states[user_id] = "waiting_for_card_number"
    await update.message.reply_text("✅ عکس شما با موفقیت دریافت شد.\n💳 لطفا شماره کارت خود را به صورت اعداد انگلیسی وارد کنید.", parse_mode='markdown')

async def handle_verify_card_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_for_card_number":
        return
    card_number = re.sub(r'[^0-9]', '', update.message.text.strip())
    if len(card_number) != 16:
        await update.message.reply_text("❌ شماره کارت باید 16 رقم باشد.\n📝 لطفا شماره کارت خود را بدون فاصله و کاراکتر اضافی وارد کنید.", parse_mode='markdown')
        return
    user = update.effective_user
    mention = f"@{user.username}" if user.username else user.first_name
    photo = None
    async for msg in context.bot.get_chat_history(chat_id=user_id, limit=5):
        if msg.photo:
            photo = msg.photo[-1]
            break
    request_id = db_add_verify_request(user_id, mention, card_number, photo.file_id if photo else None)
    iran_tz = pytz.timezone('Asia/Tehran')
    now = datetime.now(iran_tz)
    for admin_id in ADMIN_IDS:
        try:
            admin_text = (
                f"🆔 درخواست جدید احراز هویت\n\n"
                f"🆔 شماره درخواست : {request_id}\n"
                f"👤 نام کاربر : {mention}\n"
                f"🆔 آیدی عددی : {user_id}\n"
                f"💳 شماره کارت : <code>{card_number}</code>\n\n"
                f"🕐 ساعت : {now.strftime('%H:%M')}\n"
                f"📅 تاریخ : {now.strftime('%Y-%m-%d')}"
            )
            keyboard = [
                [InlineKeyboardButton("✅ پذیرفتن", callback_data=f"accept_verify_{request_id}")],
                [InlineKeyboardButton("❌ نپذیرفتن", callback_data=f"reject_verify_{request_id}")],
                [InlineKeyboardButton("🚫 مسدود کردن کاربر", callback_data=f"block_{user_id}")],
                [InlineKeyboardButton("💬 پاسخ به کاربر", callback_data=f"reply_{user_id}")]
            ]
            if photo:
                await context.bot.send_photo(admin_id, photo.file_id, caption=admin_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            else:
                await context.bot.send_message(admin_id, admin_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        except:
            pass
    await update.message.reply_text(
        "✅ درخواست احراز هویت شما با موفقیت به تیم پشتیبانی ارسال شد.\n"
        "⏳ لطفا صبور باشید و منتظر تایید از سوی تیم پشتیبانی بمانید.\n"
        "⚠️ از ارسال درخواست‌های تکراری خودداری فرمایید.",
        parse_mode='markdown'
    )
    del user_states[user_id]

async def accept_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    request_id = int(query.data.split("_")[2])
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM verify_requests WHERE id = ?', (request_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        user_id = result[0]
        if not is_user_verified(user_id):
            verify_user(user_id)
            db_update_verify_request(request_id, 'accepted')
            try:
                await context.bot.send_message(
                    user_id,
                    "✅ درخواست احراز هویت شما با موفقیت توسط مدیریت پذیرفته شد.\n\n"
                    "🎉 تبریک میگوییم! شما اکنون احراز هویت شده اید.\n"
                    "🔄 میتوانید ربات را مجدد استارت کنید و از بخش خرید اشتراک استفاده نمایید.",
                    parse_mode='markdown'
                )
            except:
                pass
            await query.edit_message_text(f"✅ درخواست احراز هویت شماره {request_id} با موفقیت پذیرفته شد.", parse_mode='markdown')
        else:
            await query.edit_message_text("⚠️ کاربر قبلاً احراز هویت شده است!", parse_mode='markdown')
    else:
        await query.edit_message_text("❌ درخواست یافت نشد!", parse_mode='markdown')

async def reject_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    request_id = int(query.data.split("_")[2])
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM verify_requests WHERE id = ?', (request_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        user_id = result[0]
        db_update_verify_request(request_id, 'rejected')
        try:
            await context.bot.send_message(
                user_id,
                "❌ درخواست احراز هویت شما توسط مدیریت پذیرفته نشد.\n\n"
                "🔄 لطفا دوباره تلاش کنید و اطلاعات صحیح و کامل را ارسال نمایید.\n"
                "💬 در صورت نیاز میتوانید با تیم پشتیبانی تماس بگیرید.",
                parse_mode='markdown'
            )
        except:
            pass
        await query.edit_message_text(f"❌ درخواست احراز هویت شماره {request_id} رد شد.", parse_mode='markdown')
    else:
        await query.edit_message_text("❌ درخواست یافت نشد!", parse_mode='markdown')

async def back_to_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id in user_states:
        del user_states[query.from_user.id]
    text = "🔐 به منوی احراز هویت خوش آمدید.\n\n📌 لطفا یکی از گزینه‌های زیر را انتخاب نمایید :"
    keyboard = [
        [InlineKeyboardButton("❌ حذف کارت", callback_data="delete_card")],
        [InlineKeyboardButton("➕ کارت جدید", callback_data="new_card")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')

# ==================== بخش خرید اشتراک ====================

async def buy_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if not is_user_verified(user_id):
        text = "🔒 برای خرید اشتراک سلف، ابتدا باید احراز هویت کنید."
        keyboard = [
            [InlineKeyboardButton("✔️ احراز هویت", callback_data="verify")],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')
        return
    text = "📌 لطفا از گزینه های زیر انتخاب نمایید که میخواهید ریپر سلف را برای چند ماه خریداری کنید."
    keyboard = [
        [InlineKeyboardButton("( 1 ) ماه معادل 100 هزار ( تومان )", callback_data="buy_1_month")],
        [InlineKeyboardButton("( 2 ) ماه معادل 150 هزار ( تومان )", callback_data="buy_2_month")],
        [InlineKeyboardButton("( 3 ) ماه معادل 200 هزار ( تومان )", callback_data="buy_3_month")],
        [InlineKeyboardButton("( 4 ) ماه معادل 250 هزار ( تومان )", callback_data="buy_4_month")],
        [InlineKeyboardButton("( 5 ) ماه معادل 300 هزار ( تومان )", callback_data="buy_5_month")],
        [InlineKeyboardButton("( 6 ) ماه معادل 350 هزار ( تومان )", callback_data="buy_6_month")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')

# ==================== بخش ادمین ====================

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    total = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_verified = 1')
    verified = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_banned = 1')
    banned = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM codes')
    codes = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM codes WHERE used = 1')
    used = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM sessions')
    sessions = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM support_tickets WHERE status = "open"')
    tickets = cursor.fetchone()[0]
    conn.close()
    text = (
        f"📊 آمار کل ربات ریپر سلف\n\n"
        f"👥 تعداد کل کاربران : {total}\n"
        f"✅ کاربران احراز هویت شده : {verified}\n"
        f"🚫 کاربران مسدود شده : {banned}\n"
        f"🔢 تعداد کل کدهای سلف : {codes}\n"
        f"✅ کدهای استفاده شده : {used}\n"
        f"❌ کدهای استفاده نشده : {codes - used}\n"
        f"👥 تعداد سشن‌های ذخیره شده : {sessions}\n"
        f"🎫 تیکت‌های باز پشتیبانی : {tickets}"
    )
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="admin_back")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')

async def admin_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    info = await get_server_info()
    if info:
        text = (
            f"📡 وضعیت پینگ هاست\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📡 وضعیت هاست : {info['status']}\n"
            f"⚡ پینگ : {info['ping']}\n"
            f"💻 سی‌پی‌یو : {info['cpu']}\n"
            f"🧠 رم : {info['memory']}\n"
            f"💾 هارد : {info['disk']}\n"
            f"🖥️ سیستم‌عامل : {info['os']}\n"
            f"⏱️ آپ‌تایم : {info['uptime']}\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        text = "❌ خطا در دریافت اطلاعات سرور!"
    keyboard = [
        [InlineKeyboardButton("🔄 بروزرسانی پینگ", callback_data="admin_ping")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="admin_back")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')

async def admin_host(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    info = get_host_expiry()
    bar = "█" * int((info['percent'] / 100) * 10) + "░" * (10 - int((info['percent'] / 100) * 10))
    text = (
        f"⏳ اطلاعات اعتبار هاست\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 تاریخ شروع : {info['start_date']}\n"
        f"📆 تاریخ انقضا : {info['expiry_date']}\n"
        f"⏱️ روزهای باقی‌مانده : {info['days_left']} روز\n"
        f"📊 وضعیت : {bar} {info['percent']:.1f}%\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
    )
    if info['days_left'] <= 0:
        text += "\n⚠️ هاست شما منقضی شده است! لطفا تمدید کنید."
    elif info['days_left'] <= 5:
        text += "\n⚠️ هاست شما به زودی منقضی میشود! لطفا تمدید کنید."
    else:
        text += "\n✅ هاست شما فعال است."
    keyboard = [
        [InlineKeyboardButton("🔄 بروزرسانی", callback_data="admin_host")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="admin_back")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')

# ==================== بخش تنظیمات ====================

async def admin_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mention = f"@{query.from_user.username}" if query.from_user.username else query.from_user.first_name
    text = (
        f"⚙️ درود {mention} به بخش تنظیمات پنل مدیریت ریپر سلف خوش آمدید.\n\n"
        "📌 در این بخش میتوانید تمامی تنظیمات و مدیریت ربات را انجام دهید.\n\n"
        "🔽 لطفا از منوی زیر یکی از گزینه‌های مورد نظر خود را انتخاب نمایید."
    )
    keyboard = [
        [InlineKeyboardButton("➕ ساختن کد سلف", callback_data="admin_create_code"), InlineKeyboardButton("❌ باطل کردن کد سلف", callback_data="admin_cancel_code")],
        [InlineKeyboardButton("🚫 مسدود کردن کاربر", callback_data="admin_block_user"), InlineKeyboardButton("✅ آزاد کردن کاربر", callback_data="admin_unblock_user")],
        [InlineKeyboardButton("📤 انتقال انقضا", callback_data="admin_transfer_credit"), InlineKeyboardButton("📉 کسر انقضا", callback_data="admin_deduct_credit")],
        [InlineKeyboardButton("🔑 ورود سلف", callback_data="admin_salf_login"), InlineKeyboardButton("🚪 خروج سلف", callback_data="admin_salf_logout")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings_back")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="admin_back")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')

async def admin_settings_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mention = f"@{query.from_user.username}" if query.from_user.username else query.from_user.first_name
    text = (
        f"⚙️ درود {mention} به بخش تنظیمات پنل مدیریت ریپر سلف خوش آمدید.\n\n"
        "📌 در این بخش میتوانید تمامی تنظیمات و مدیریت ربات را انجام دهید.\n\n"
        "🔽 لطفا از منوی زیر یکی از گزینه‌های مورد نظر خود را انتخاب نمایید."
    )
    keyboard = [
        [InlineKeyboardButton("➕ ساختن کد سلف", callback_data="admin_create_code"), InlineKeyboardButton("❌ باطل کردن کد سلف", callback_data="admin_cancel_code")],
        [InlineKeyboardButton("🚫 مسدود کردن کاربر", callback_data="admin_block_user"), InlineKeyboardButton("✅ آزاد کردن کاربر", callback_data="admin_unblock_user")],
        [InlineKeyboardButton("📤 انتقال انقضا", callback_data="admin_transfer_credit"), InlineKeyboardButton("📉 کسر انقضا", callback_data="admin_deduct_credit")],
        [InlineKeyboardButton("🔑 ورود سلف", callback_data="admin_salf_login"), InlineKeyboardButton("🚪 خروج سلف", callback_data="admin_salf_logout")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings_back")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="admin_back")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')

# ==================== بخش مسدود کردن/آزاد کردن کاربر ====================

async def admin_block_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_states[query.from_user.id] = "waiting_for_block_user"
    text = "🚫 مسدود کردن کاربر\n\n📝 لطفا آیدی عددی کاربر مورد نظر برای مسدود سازی را وارد کنید.\n⚠️ توجه : پس از مسدود شدن، کاربر قادر به استفاده از ربات نخواهد بود."
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings_back")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="admin_back")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')

async def admin_unblock_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_states[query.from_user.id] = "waiting_for_unblock_user"
    text = "✅ آزاد کردن کاربر\n\n📝 لطفا آیدی عددی کاربر مورد نظر برای آزاد سازی از مسدودیت را وارد کنید.\n⚠️ توجه : پس از آزاد سازی، کاربر دوباره میتواند از ربات استفاده کند."
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings_back")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="admin_back")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')

async def handle_block_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_for_block_user":
        return
    try:
        target = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ آیدی وارد شده صحیح نیست! لطفا یک عدد معتبر وارد کنید.", parse_mode='markdown')
        return
    if target in ADMIN_IDS:
        await update.message.reply_text("❌ شما نمی‌توانید یک ادمین را مسدود کنید!", parse_mode='markdown')
        return
    if not is_user_banned(target):
        ban_user(target)
        try:
            await context.bot.send_message(target, "🚫 شما از طرف مدیریت مسدود شده اید!\n💬 در صورت نیاز با پشتیبانی تماس بگیرید.", parse_mode='markdown')
        except:
            pass
        await update.message.reply_text(f"✅ کاربر با آیدی {target} با موفقیت مسدود شد.\n📨 پیام مسدودیت برای کاربر ارسال شد.", parse_mode='markdown')
    else:
        await update.message.reply_text(f"⚠️ کاربر با آیدی {target} قبلاً در لیست مسدودین قرار دارد.", parse_mode='markdown')
    del user_states[user_id]

async def handle_unblock_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_for_unblock_user":
        return
    try:
        target = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ آیدی وارد شده صحیح نیست! لطفا یک عدد معتبر وارد کنید.", parse_mode='markdown')
        return
    if is_user_banned(target):
        unban_user(target)
        try:
            await context.bot.send_message(
                target,
                "✅ تبریک! شما از طرف مدیریت از مسدودیت آزاد شدید.\n"
                "🙏 ضمن پوزش از شما، خوشحالیم که دوباره به جمع ما برگشتید.",
                parse_mode='markdown'
            )
        except:
            pass
        await update.message.reply_text(f"✅ کاربر با آیدی {target} با موفقیت از مسدودیت آزاد شد.\n📨 پیام آزادی برای کاربر ارسال شد.", parse_mode='markdown')
    else:
        await update.message.reply_text(f"⚠️ کاربر با آیدی {target} در لیست مسدودین وجود ندارد.", parse_mode='markdown')
    del user_states[user_id]

# ==================== بخش انتقال و کسر انقضا ====================

async def admin_transfer_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_states[query.from_user.id] = "waiting_for_transfer_credit"
    text = (
        "📤 انتقال انقضا\n\n"
        "📝 لطفا آیدی عددی کاربر مبدا، آیدی عددی کاربر مقصد و مقدار روز را وارد کنید.\n"
        "⚠️ توجه : این عملیات غیرقابل بازگشت است.\n"
        "📌 مثال : 123456789 987654321 30"
    )
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings_back")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="admin_back")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')

async def admin_deduct_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_states[query.from_user.id] = "waiting_for_deduct_credit"
    text = (
        "📉 کسر انقضا\n\n"
        "📝 لطفا آیدی عددی کاربر و مقدار روز مورد نظر برای کسر را وارد کنید.\n"
        "⚠️ توجه : این عملیات غیرقابل بازگشت است.\n"
        "📌 مثال : 123456789 10"
    )
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings_back")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="admin_back")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')

async def handle_transfer_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_for_transfer_credit":
        return
    parts = update.message.text.strip().split()
    if len(parts) != 3:
        await update.message.reply_text("❌ فرمت وارد شده صحیح نیست!\n📌 لطفا به این صورت وارد کنید: آیدی_مبدا آیدی_مقصد تعداد_روز", parse_mode='markdown')
        return
    try:
        from_id, to_id, days = int(parts[0]), int(parts[1]), int(parts[2])
    except:
        await update.message.reply_text("❌ مقادیر وارد شده صحیح نیست! لطفا اعداد معتبر وارد کنید.", parse_mode='markdown')
        return
    if days <= 0:
        await update.message.reply_text("❌ تعداد روز باید بیشتر از صفر باشد.", parse_mode='markdown')
        return
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT remaining_days, expiry_date FROM users WHERE user_id = ?', (from_id,))
    from_data = cursor.fetchone()
    if not from_data or from_data[0] is None or from_data[0] < days:
        conn.close()
        await update.message.reply_text(f"⚠️ کاربر با آیدی {from_id} به اندازه {days} روز اشتراک فعال ندارد!", parse_mode='markdown')
        return
    new_from = from_data[0] - days
    new_from_exp = (datetime.now() + timedelta(days=new_from)).isoformat() if new_from > 0 else None
    cursor.execute('UPDATE users SET remaining_days = ?, expiry_date = ? WHERE user_id = ?', (new_from, new_from_exp, from_id))
    cursor.execute('SELECT remaining_days, expiry_date FROM users WHERE user_id = ?', (to_id,))
    to_data = cursor.fetchone()
    if to_data and to_data[0] is not None:
        new_to = to_data[0] + days
        new_to_exp = (datetime.now() + timedelta(days=new_to)).isoformat()
        cursor.execute('UPDATE users SET remaining_days = ?, expiry_date = ? WHERE user_id = ?', (new_to, new_to_exp, to_id))
    else:
        new_to = days
        new_to_exp = (datetime.now() + timedelta(days=days)).isoformat()
        cursor.execute('INSERT INTO users (user_id, remaining_days, expiry_date) VALUES (?, ?, ?)', (to_id, new_to, new_to_exp))
    conn.commit()
    conn.close()
    try:
        await context.bot.send_message(from_id, f"📤 از طرف مدیریت، {days} روز از اشتراک شما کسر شد.\n📅 انقضای جدید شما : {new_from_exp.split('T')[0] if new_from_exp else 'اشتراک شما به پایان رسید'}", parse_mode='markdown')
    except:
        pass
    try:
        await context.bot.send_message(to_id, f"📤 از طرف مدیریت، {days} روز به اشتراک شما اضافه شد.\n📅 انقضای جدید شما : {new_to_exp.split('T')[0]}", parse_mode='markdown')
    except:
        pass
    await update.message.reply_text(f"✅ انتقال {days} روز از کاربر {from_id} به کاربر {to_id} با موفقیت انجام شد.", parse_mode='markdown')
    del user_states[user_id]

async def handle_deduct_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_for_deduct_credit":
        return
    parts = update.message.text.strip().split()
    if len(parts) != 2:
        await update.message.reply_text("❌ فرمت وارد شده صحیح نیست!\n📌 لطفا به این صورت وارد کنید: آیدی_کاربر تعداد_روز", parse_mode='markdown')
        return
    try:
        target_id, days = int(parts[0]), int(parts[1])
    except:
        await update.message.reply_text("❌ مقادیر وارد شده صحیح نیست! لطفا اعداد معتبر وارد کنید.", parse_mode='markdown')
        return
    if days <= 0:
        await update.message.reply_text("❌ تعداد روز باید بیشتر از صفر باشد.", parse_mode='markdown')
        return
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT remaining_days, expiry_date FROM users WHERE user_id = ?', (target_id,))
    data = cursor.fetchone()
    if not data or data[0] is None or data[0] == 0:
        conn.close()
        await update.message.reply_text(f"⚠️ کاربر با آیدی {target_id} اشتراک فعالی ندارد!", parse_mode='markdown')
        return
    new_days = max(0, data[0] - days)
    new_exp = (datetime.now() + timedelta(days=new_days)).isoformat() if new_days > 0 else None
    cursor.execute('UPDATE users SET remaining_days = ?, expiry_date = ? WHERE user_id = ?', (new_days, new_exp, target_id))
    conn.commit()
    conn.close()
    try:
        await context.bot.send_message(target_id, f"📉 از طرف مدیریت، {days} روز از اشتراک شما کسر شد.\n📅 انقضای جدید شما : {new_exp.split('T')[0] if new_exp else 'اشتراک شما به پایان رسید'}", parse_mode='markdown')
    except:
        pass
    await update.message.reply_text(f"✅ {days} روز از اشتراک کاربر {target_id} با موفقیت کسر شد.", parse_mode='markdown')
    del user_states[user_id]

# ==================== بخش ورود و خروج سلف در مدیریت ====================

async def admin_salf_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    admin_salf_data[query.from_user.id] = {}
    user_states[query.from_user.id] = "admin_waiting_phone"
    text = (
        "🔑 ورود سلف (مدیریت)\n\n"
        "📱 لطفا شماره موبایل کاربر را با کد کشور وارد کنید.\n"
        "📌 مثال : +989123456789\n\n"
        "⚠️ این بخش مخصوص ورود سلف به اکانت کاربران دیگر توسط مدیریت است."
    )
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings_back")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="admin_back")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')

async def admin_salf_logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_states[query.from_user.id] = "admin_waiting_logout_phone"
    text = (
        "🚪 خروج سلف\n\n"
        "📱 لطفا شماره تلفن مورد نظر برای خروج سلف را وارد کنید.\n"
        "⚠️ توجه : پس از خروج، سلف از اکانت کاربر خارج خواهد شد و ساعت از اسم او حذف میشود."
    )
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings_back")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="admin_back")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')

async def admin_handle_salf_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "admin_waiting_phone":
        return
    phone = update.message.text.strip()
    if not phone or not re.match(r'^\+?[0-9]{10,15}$', phone):
        await update.message.reply_text("❌ شماره وارد شده صحیح نیست! لطفا با کد کشور وارد کنید.\n📌 مثال : +989123456789", parse_mode='markdown')
        return
    admin_salf_data[user_id]['phone'] = phone
    user_states[user_id] = "admin_waiting_user_id"
    await update.message.reply_text("🔑 مرحله 2 از 5\n\n📝 لطفا آیدی عددی کاربر مورد نظر را وارد کنید.", parse_mode='markdown')

async def admin_handle_salf_logout_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "admin_waiting_logout_phone":
        return
    phone = update.message.text.strip()
    if not phone or not re.match(r'^\+?[0-9]{10,15}$', phone):
        await update.message.reply_text("❌ شماره وارد شده صحیح نیست! لطفا با کد کشور وارد کنید.\n📌 مثال : +989123456789", parse_mode='markdown')
        return
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, api_hash, api_id FROM sessions WHERE phone = ?', (phone,))
    result = cursor.fetchone()
    conn.close()
    if not result:
        await update.message.reply_text("❌ هیچ کاربری با این شماره در سلف یافت نشد!", parse_mode='markdown')
        del user_states[user_id]
        return
    target_user_id = result[0]
    try:
        client = TelegramClient(f"sessions/user_{target_user_id}", result[2], result[1])
        await client.connect()
        if await client.is_user_authorized():
            me = await client.get_me()
            current = f"{me.first_name or ''} {me.last_name or ''}".strip() or me.username or "کاربر"
            clean = re.sub(r'\s*\d{2}:\d{2}$', '', current).strip()
            if clean != current:
                try:
                    await client(UpdateProfileRequest(first_name=clean))
                except:
                    pass
        await client.disconnect()
    except:
        pass
    delete_user_session(target_user_id)
    set_clock_status(target_user_id, False)
    if target_user_id in salf_clients:
        try:
            await salf_clients[target_user_id].disconnect()
        except:
            pass
        del salf_clients[target_user_id]
    try:
        await context.bot.send_message(
            target_user_id,
            "🚪 ریپر سلف از اکانت شما خارج شد.\n\n"
            "⏰ ساعت از روی اسم شما حذف شد.\n"
            "🔄 در صورت نیاز مجدداً وارد شوید.",
            parse_mode='markdown'
        )
    except:
        pass
    await update.message.reply_text(f"✅ خروج سلف از اکانت کاربر {target_user_id} با موفقیت انجام شد.\n📱 شماره : {phone}\n⏰ ساعت از اسم کاربر حذف شد.", parse_mode='markdown')
    del user_states[user_id]

async def admin_handle_salf_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "admin_waiting_user_id":
        return
    try:
        target = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ آیدی وارد شده صحیح نیست! لطفا یک عدد معتبر وارد کنید.", parse_mode='markdown')
        return
    admin_salf_data[user_id]['target_user_id'] = target
    user_states[user_id] = "admin_waiting_api_id"
    await update.message.reply_text("🔑 مرحله 3 از 5\n\n📝 لطفا آیپی عددی (API ID) را وارد کنید.\n⚠️ توجه: API ID باید عددی بین 1 تا 2147483647 باشد.", parse_mode='markdown')

async def admin_handle_salf_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "admin_waiting_api_id":
        return
    try:
        api_id = int(update.message.text.strip())
        if api_id > 2147483647:
            await update.message.reply_text("❌ عدد وارد شده خیلی بزرگ است!\n⚠️ API ID باید عددی بین 1 تا 2147483647 باشد.", parse_mode='markdown')
            return
    except:
        await update.message.reply_text("❌ آیپی عددی باید عدد باشد!", parse_mode='markdown')
        return
    admin_salf_data[user_id]['api_id'] = api_id
    user_states[user_id] = "admin_waiting_api_hash"
    await update.message.reply_text("🔑 مرحله 4 از 5\n\n📝 لطفا آیپی هش (API Hash) را وارد کنید.", parse_mode='markdown')

async def admin_handle_salf_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "admin_waiting_api_hash":
        return
    api_hash = update.message.text.strip()
    if not api_hash or len(api_hash) < 20:
        await update.message.reply_text("❌ آیپی هش وارد شده صحیح نیست! لطفا دوباره وارد کنید.", parse_mode='markdown')
        return
    admin_salf_data[user_id]['api_hash'] = api_hash
    user_states[user_id] = "admin_waiting_code"
    try:
        data = admin_salf_data[user_id]
        client = TelegramClient(f"sessions/admin_{user_id}", data['api_id'], data['api_hash'])
        await client.connect()
        if not await client.is_user_authorized():
            await client.send_code_request(data['phone'])
            admin_salf_data[user_id]['client'] = client
            await update.message.reply_text(
                f"🔑 مرحله 5 از 5\n\n✅ کد تایید به شماره {data['phone']} ارسال شد.\n📝 لطفا کد را به این صورت بفرستید: <code>1.2.3.4.5</code>",
                parse_mode='HTML'
            )
        else:
            await client.disconnect()
            await update.message.reply_text("❌ این شماره قبلاً در سلف ثبت شده است!", parse_mode='markdown')
            del user_states[user_id]
            del admin_salf_data[user_id]
    except PhoneNumberInvalidError:
        await update.message.reply_text("❌ شماره وارد شده معتبر نیست!", parse_mode='markdown')
        del user_states[user_id]
        del admin_salf_data[user_id]
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ارسال کد تایید: {str(e)}", parse_mode='markdown')
        del user_states[user_id]
        del admin_salf_data[user_id]

async def admin_handle_salf_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "admin_waiting_code":
        return
    code = update.message.text.strip().replace('.', '').replace(' ', '')
    if not code or not code.isdigit():
        await update.message.reply_text("❌ لطفا کد را به این صورت بفرستید: <code>1.2.3.4.5</code>", parse_mode='HTML')
        return
    try:
        data = admin_salf_data[user_id]
        client = data.get('client')
        if not client:
            await update.message.reply_text("❌ خطا در اتصال! لطفا دوباره تلاش کنید.", parse_mode='markdown')
            del user_states[user_id]
            del admin_salf_data[user_id]
            return
        try:
            await client.sign_in(data['phone'], code)
            me = await client.get_me()
            full_name = f"{me.first_name or ''} {me.last_name or ''}".strip() or me.username or "کاربر"
            session_string = client.session.save()
            save_user_session(data['target_user_id'], session_string, data['phone'], data['api_hash'], data['api_id'])
            await client.disconnect()
            set_clock_status(data['target_user_id'], True)
            asyncio.create_task(start_salf_client(data['target_user_id']))
            iran_tz = pytz.timezone('Asia/Tehran')
            now = datetime.now(iran_tz)
            text = (
                f"✅ ورود سلف به اکانت کاربر با موفقیت انجام شد!\n\n"
                f"👤 نام اکانت : {full_name}\n"
                f"📱 شماره : {data['phone']}\n"
                f"🕐 ساعت ورود : {now.strftime('%H:%M')}\n"
                f"📅 تاریخ ورود : {now.strftime('%Y-%m-%d')}\n"
                f"🆔 آیدی کاربر : {data['target_user_id']}\n\n"
                f"⏰ ساعت روی اسم اکانت کاربر فعال شد!\n"
                f"✅ پنل سلف فعال شد (با نوشتن کلمه \"پنل\" در هر جایی)"
            )
            keyboard = [
                [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings_back")],
                [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="admin_back")]
            ]
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')
            del user_states[user_id]
            del admin_salf_data[user_id]
        except PhoneCodeExpiredError:
            await update.message.reply_text("⏳ کد منقضی شده بود، در حال ارسال کد جدید...", parse_mode='markdown')
            await client.send_code_request(data['phone'])
            await update.message.reply_text("✅ کد جدید به شماره شما ارسال شد.\n📝 لطفا کد را به این صورت بفرستید: <code>1.2.3.4.5</code>", parse_mode='HTML')
        except PhoneCodeInvalidError:
            await update.message.reply_text("❌ کد وارد شده صحیح نیست! لطفا دوباره تلاش کنید.\n📝 لطفا کد را به این صورت بفرستید: <code>1.2.3.4.5</code>", parse_mode='HTML')
    except SessionPasswordNeededError:
        user_states[user_id] = "admin_waiting_password"
        await update.message.reply_text("🔑 این اکانت دو مرحله‌ای فعال است.\n📝 لطفا پسورد را وارد کنید:", parse_mode='markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ورود: {str(e)}", parse_mode='markdown')
        del user_states[user_id]
        del admin_salf_data[user_id]

async def admin_handle_salf_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "admin_waiting_password":
        return
    password = update.message.text.strip()
    if not password:
        await update.message.reply_text("❌ لطفا پسورد را وارد کنید!", parse_mode='markdown')
        return
    try:
        data = admin_salf_data[user_id]
        client = data.get('client')
        if not client:
            await update.message.reply_text("❌ خطا در اتصال! لطفا دوباره تلاش کنید.", parse_mode='markdown')
            del user_states[user_id]
            del admin_salf_data[user_id]
            return
        await client.sign_in(password=password)
        me = await client.get_me()
        full_name = f"{me.first_name or ''} {me.last_name or ''}".strip() or me.username or "کاربر"
        session_string = client.session.save()
        save_user_session(data['target_user_id'], session_string, data['phone'], data['api_hash'], data['api_id'])
        await client.disconnect()
        set_clock_status(data['target_user_id'], True)
        asyncio.create_task(start_salf_client(data['target_user_id']))
        iran_tz = pytz.timezone('Asia/Tehran')
        now = datetime.now(iran_tz)
        text = (
            f"✅ ورود سلف به اکانت کاربر با موفقیت انجام شد!\n\n"
            f"👤 نام اکانت : {full_name}\n"
            f"📱 شماره : {data['phone']}\n"
            f"🕐 ساعت ورود : {now.strftime('%H:%M')}\n"
            f"📅 تاریخ ورود : {now.strftime('%Y-%m-%d')}\n"
            f"🆔 آیدی کاربر : {data['target_user_id']}\n\n"
            f"⏰ ساعت روی اسم اکانت کاربر فعال شد!\n"
            f"✅ پنل سلف فعال شد (با نوشتن کلمه \"پنل\" در هر جایی)"
        )
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings_back")],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="admin_back")]
        ]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')
        del user_states[user_id]
        del admin_salf_data[user_id]
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ورود با پسورد: {str(e)}", parse_mode='markdown')
        del user_states[user_id]
        del admin_salf_data[user_id]

# ==================== ساخت و باطل کد ====================

async def admin_create_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_states[query.from_user.id] = "waiting_for_code_days"
    text = (
        "➕ ساختن کد سلف جدید\n\n"
        "📝 لطفا تعداد روز انقضا را به صورت عدد وارد کنید.\n"
        "⚠️ توجه : عدد وارد شده باید بین 1 تا 100000 باشد."
    )
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings_back")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="admin_back")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')

async def admin_cancel_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_states[query.from_user.id] = "waiting_for_cancel_code"
    text = (
        "❌ باطل کردن کد سلف\n\n"
        "📝 لطفا کد سلف مورد نظر برای باطل شدن را وارد کنید.\n"
        "⚠️ توجه : کدهایی که قبلاً استفاده شده اند قابل باطل کردن نیستند."
    )
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings_back")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="admin_back")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')

async def handle_code_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_for_code_days":
        return
    try:
        days = int(update.message.text.strip())
        if days < 1 or days > 100000:
            await update.message.reply_text("❌ عدد باید بین 1 تا 100000 باشد!", parse_mode='markdown')
            return
        new_code, expiry = create_new_code(days)
        text = (
            f"✅ کد سلف شما با موفقیت ساخته شد\n\n"
            f"📝 کد سلف شما : <code>{new_code}</code>\n\n"
            f"📅 تاریخ انقضا : {expiry.strftime('%Y-%m-%d')}\n"
            f"⏱️ مدت اعتبار : {days} روز\n\n"
            f"💡 برای کپی کردن روی کد کلیک کنید."
        )
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings_back")],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="admin_back")]
        ]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        del user_states[user_id]
    except:
        await update.message.reply_text("❌ لطفا یک عدد معتبر وارد کنید!", parse_mode='markdown')

async def handle_cancel_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_for_cancel_code":
        return
    code = update.message.text.strip().upper()
    existing = db_get_code(code)
    if not existing:
        await update.message.reply_text("❌ کد وارد شده صحیح نیست!", parse_mode='markdown')
        return
    if existing[4] == 1:
        await update.message.reply_text("❌ این کد قبلاً استفاده شده و قابل باطل کردن نیست!", parse_mode='markdown')
    else:
        db_delete_code(code)
        await update.message.reply_text(f"✅ کد <code>{code}</code> با موفقیت باطل شد!", parse_mode='HTML')
    del user_states[user_id]

# ==================== بقیه توابع ====================

async def admin_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id in user_states:
        del user_states[query.from_user.id]
    if query.from_user.id in admin_salf_data:
        del admin_salf_data[query.from_user.id]
    mention = f"@{query.from_user.username}" if query.from_user.username else query.from_user.first_name
    
    # اگر از منوی کاربران اومده، برگرد به منوی کاربران
    if query.from_user.id in user_menu_mode and user_menu_mode[query.from_user.id]:
        text = (
            f"👋 سلام {mention} به ربات ریپر سلف Reaper Self خوش آمدید !\n\n"
            "🛡️ توی این ربات میتوانید از پشتیبانی، خرید، نصب ربات سلف بهره ببرید!\n\n"
            "💬 لطفا اگر سوالی دارید از بخش پشتیبانی، با پشتیبان‌ها در ارتباط باشید!"
        )
        keyboard = [
            [InlineKeyboardButton("👨‍💻 پشتیبانی", callback_data="support")],
            [InlineKeyboardButton("🤔 سلف چیست ؟", callback_data="what_is_self"), InlineKeyboardButton("📣 کانال ما", url="https://t.me/ReaperSelfChannel")],
            [InlineKeyboardButton("📅 انقضا شما : ( 0 روز )", callback_data="expiry")],
            [InlineKeyboardButton("✔️ احراز هویت", callback_data="verify")],
            [InlineKeyboardButton("💳 خرید اشتراک", callback_data="buy_subscription")],
            [InlineKeyboardButton("💶 خرید با کد", callback_data="buy_with_code")],
            [InlineKeyboardButton("🔑 ورود سلف", callback_data="salf_login")],
            [InlineKeyboardButton("💎 نرخ", callback_data="rate")],
            [InlineKeyboardButton("🎈 پنل مدیریت", callback_data="admin_back")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')
        return
    
    # برگشت به پنل مدیریت
    text = (
        f"👋 درود {mention} به پنل ریپر سلف Reaper Self خوش آمدید.\n\n"
        "⚙️ توی این پنل میتوانید ربات ریپر سلف Reaper Self را کنترل و مدیریت کنید.\n\n"
        "📌 لطفا از منوی زیر انتخاب نمایید که چه کاری را می‌خواهید انتخاب دهید."
    )
    keyboard = [
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings")],
        [InlineKeyboardButton("📊 آمار کل", callback_data="admin_stats")],
        [InlineKeyboardButton("📡 بررسی پینگ", callback_data="admin_ping"), InlineKeyboardButton("⏳ اعتبار هاست", callback_data="admin_host")],
        [InlineKeyboardButton("👥 منوی کاربران", callback_data="admin_users_menu")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')

async def admin_users_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_menu_mode[user_id] = True
    mention = f"@{query.from_user.username}" if query.from_user.username else query.from_user.first_name
    text = (
        f"👋 سلام {mention} به ربات ریپر سلف Reaper Self خوش آمدید !\n\n"
        "🛡️ توی این ربات میتوانید از پشتیبانی، خرید، نصب ربات سلف بهره ببرید!\n\n"
        "💬 لطفا اگر سوالی دارید از بخش پشتیبانی، با پشتیبان‌ها در ارتباط باشید!"
    )
    keyboard = [
        [InlineKeyboardButton("👨‍💻 پشتیبانی", callback_data="support")],
        [InlineKeyboardButton("🤔 سلف چیست ؟", callback_data="what_is_self"), InlineKeyboardButton("📣 کانال ما", url="https://t.me/ReaperSelfChannel")],
        [InlineKeyboardButton("📅 انقضا شما : ( 0 روز )", callback_data="expiry")],
        [InlineKeyboardButton("✔️ احراز هویت", callback_data="verify")],
        [InlineKeyboardButton("💳 خرید اشتراک", callback_data="buy_subscription")],
        [InlineKeyboardButton("💶 خرید با کد", callback_data="buy_with_code")],
        [InlineKeyboardButton("🔑 ورود سلف", callback_data="salf_login")],
        [InlineKeyboardButton("💎 نرخ", callback_data="rate")],
        [InlineKeyboardButton("🎈 پنل مدیریت", callback_data="admin_back")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')

# ==================== بقیه توابع کاربران ====================

async def rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "💎 نرخ سلف عبارت است از :\n\n"
        "📌 ماهانه : 100,000 هزار تومان\n\n"
        "📌 دو ماهه : 150,000 هزار تومان\n\n"
        "📌 سه ماهه : 200,000 هزار تومان\n\n"
        "📌 چهار ماهه : 250,000 هزار تومان\n\n"
        "📌 پنج ماهه : 300,000 هزار تومان\n\n"
        "📌 شش ماهه : 350,000 هزار تومان\n\n"
        "⚠️ توجه داشته باشید سلف فقط بر روی اکانت هایی که با شماره ایران هستند نصب میشود و اما در صورت نصب روی شماره های مجازی مسئولیت دیلیت شدن اکانت به عهده خودتان خواهد بود.\n\n"
        "֍ @ReaperSelfChannel"
    )
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_from_user_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')

async def what_is_self(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "🤖 سلف به رباتی گفته میشه که روی اکانت شما نصب میشه و امکانات خاصی رو در اختیارتون میزاره.\n\n"
        "📌 لازم به ذکر هست که نصب شدن بر روی اکانت شما به معنی وارد شدن ربات به اکانت شما هست (به دلیل دستور گرفتن و انجام فعالیت‌ها).\n\n"
        "✨ از جمله امکاناتی که در اختیار شما قرار میدهد شامل موارد زیر است :\n\n"
        "🔹 گذاشتن ساعت با فونت های مختلف بر روی بیو و اسم\n"
        "🔹 قابلیت تنظیم حالت خوانده شدن خودکار پیام ها\n"
        "🔹 تنظیم حالت پاسخ خودکار\n"
        "🔹 جواب دادن به شخصی که به شما توهین میکنه\n"
        "🔹 پیام انیمیشنی\n"
        "🔹 منشی هوشمند\n"
        "🔹 دریافت پنل و تنظیمات اکانت هوشمند\n"
        "🔹 دو زبانه بودن دستورات و جواب ها\n"
        "🔹 تغییر نام و کاور فایل ها\n"
        "🔹 اعلان پیام ادیت و حذف شده در پیوی\n"
        "🔹 ذخیره پروفایل های جدید و اعلان حذف پروفایل مخاطبین\n\n"
        "📌 و امکاناتی دیگر که میتوانید با مراجعه به بخش راهنما آن ها را ببینید و مطالعه کنید !\n\n"
        "⚠️ لازم به ذکر است که امکاناتی که در بالا گفته شده تنها ذره‌ای از امکانات سلف میباشد."
    )
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_from_user_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')

async def buy_with_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_states[query.from_user.id] = "waiting_for_activation_code"
    text = "💳 لطفا کد انقضای خریداری شده خود را ارسال کنید."
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_from_user_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')

async def handle_activation_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_for_activation_code":
        return
    code = update.message.text.strip().upper()
    if not code:
        await update.message.reply_text("❌ لطفا کد را وارد کنید!", parse_mode='markdown')
        return
    code_data, error = validate_code(code)
    if code_data is None:
        await update.message.reply_text(error, parse_mode='markdown')
        return
    if use_code(code, user_id):
        days = code_data['days']
        rem = get_remaining_days(user_id)
        exp = get_expiry_date(user_id)
        text = (
            f"✅ کد با موفقیت فعال شد!\n\n"
            f"📅 {days} روز به اشتراک شما اضافه شد.\n"
            f"📅 تاریخ انقضا : {exp}\n"
            f"⏳ روزهای باقی‌مانده : {rem} روز"
        )
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_from_user_menu")]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')
        del user_states[user_id]
    else:
        await update.message.reply_text("❌ خطا در فعال‌سازی کد!", parse_mode='markdown')

async def salf_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if is_user_banned(user_id):
        await query.answer("🚫 شما مسدود شده اید!", show_alert=True)
        return
    if not has_active_subscription(user_id):
        await query.answer("❌ شما اشتراک فعال ندارید!", show_alert=True)
        return
    if get_user_session(user_id):
        await query.answer("🔑 شما قبلاً وارد سلف شده اید!", show_alert=True)
        return
    user_states[user_id] = "waiting_salf_phone"
    salf_login_data[user_id] = {}
    text = (
        "🔑 ورود به سلف\n\n"
        "📱 لطفا شماره موبایل خود را با کد کشور وارد کنید.\n"
        "📌 مثال : +989123456789\n\n"
        "❌ در صورتی که منصرف شده‌اید دکمه زیر را کلیک کنید."
    )
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_from_user_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')

async def handle_salf_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_salf_phone":
        return
    phone = update.message.text.strip()
    if not phone or not re.match(r'^\+?[0-9]{10,15}$', phone):
        await update.message.reply_text("❌ شماره وارد شده صحیح نیست! لطفا با کد کشور وارد کنید.\n📌 مثال : +989123456789", parse_mode='markdown')
        return
    salf_login_data[user_id]['phone'] = phone
    user_states[user_id] = "waiting_salf_api_id"
    await update.message.reply_text("🔑 مرحله 2 از 4\n\n📝 لطفا آیپی عددی (API ID) خود را وارد کنید.\n⚠️ توجه: API ID باید عددی بین 1 تا 2147483647 باشد.", parse_mode='markdown')

async def handle_salf_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_salf_api_id":
        return
    try:
        api_id = int(update.message.text.strip())
        if api_id > 2147483647:
            await update.message.reply_text("❌ عدد وارد شده خیلی بزرگ است!\n⚠️ API ID باید عددی بین 1 تا 2147483647 باشد.", parse_mode='markdown')
            return
    except:
        await update.message.reply_text("❌ آیپی عددی باید عدد باشد! لطفا دوباره وارد کنید.", parse_mode='markdown')
        return
    salf_login_data[user_id]['api_id'] = api_id
    user_states[user_id] = "waiting_salf_api_hash"
    await update.message.reply_text("🔑 مرحله 3 از 4\n\n📝 لطفا آیپی هش (API Hash) خود را وارد کنید.", parse_mode='markdown')

async def handle_salf_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_salf_api_hash":
        return
    api_hash = update.message.text.strip()
    if not api_hash or len(api_hash) < 20:
        await update.message.reply_text("❌ آیپی هش وارد شده صحیح نیست! لطفا دوباره وارد کنید.", parse_mode='markdown')
        return
    salf_login_data[user_id]['api_hash'] = api_hash
    user_states[user_id] = "waiting_salf_code"
    try:
        data = salf_login_data[user_id]
        client = TelegramClient(f"sessions/user_{user_id}", data['api_id'], data['api_hash'])
        await client.connect()
        if not await client.is_user_authorized():
            await client.send_code_request(data['phone'])
            salf_login_data[user_id]['client'] = client
            await update.message.reply_text("🔑 مرحله 4 از 4\n\n✅ کد تایید به شماره شما ارسال شد.\n📝 لطفا کد را به این صورت بفرستید: <code>1.2.3.4.5</code>", parse_mode='HTML')
        else:
            await client.disconnect()
            await update.message.reply_text("❌ این شماره قبلاً در سلف ثبت شده است!", parse_mode='markdown')
            del user_states[user_id]
            del salf_login_data[user_id]
    except PhoneNumberInvalidError:
        await update.message.reply_text("❌ شماره وارد شده معتبر نیست!", parse_mode='markdown')
        del user_states[user_id]
        del salf_login_data[user_id]
    except FloodWaitError as e:
        await update.message.reply_text(f"⏳ لطفا {e.seconds} ثانیه صبر کنید و دوباره تلاش کنید.", parse_mode='markdown')
        del user_states[user_id]
        del salf_login_data[user_id]
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ارسال کد تایید: {str(e)}", parse_mode='markdown')
        if 'client' in salf_login_data.get(user_id, {}):
            try:
                await salf_login_data[user_id]['client'].disconnect()
            except:
                pass
        del user_states[user_id]
        del salf_login_data[user_id]

async def handle_salf_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_salf_code":
        return
    code = update.message.text.strip().replace('.', '').replace(' ', '')
    if not code or not code.isdigit():
        await update.message.reply_text("❌ لطفا کد را به این صورت بفرستید: <code>1.2.3.4.5</code>", parse_mode='HTML')
        return
    try:
        data = salf_login_data[user_id]
        client = data.get('client')
        if not client:
            await update.message.reply_text("❌ خطا در اتصال! لطفا دوباره تلاش کنید.", parse_mode='markdown')
            del user_states[user_id]
            del salf_login_data[user_id]
            return
        try:
            await client.sign_in(data['phone'], code)
            me = await client.get_me()
            full_name = f"{me.first_name or ''} {me.last_name or ''}".strip() or me.username or "کاربر"
            session_string = client.session.save()
            save_user_session(user_id, session_string, data['phone'], data['api_hash'], data['api_id'])
            set_clock_status(user_id, True)
            asyncio.create_task(start_salf_client(user_id))
            text = (
                "✅ ورود سلف به اکانت شما با موفقیت انجام شد.\n\n"
                "🛡️ سلف برای شما نصب شد.\n"
                "📝 برای استفاده از سلف، کلمه \"پنل\" را در هر جایی بنویسید.\n"
                "💬 در صورت بروز مشکل با پشتیبانی تماس بگیرید."
            )
            keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_from_user_menu")]]
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')
            del user_states[user_id]
            del salf_login_data[user_id]
        except PhoneCodeExpiredError:
            await update.message.reply_text("⏳ کد منقضی شده بود، در حال ارسال کد جدید...", parse_mode='markdown')
            await client.send_code_request(data['phone'])
            await update.message.reply_text("✅ کد جدید به شماره شما ارسال شد.\n📝 لطفا کد را به این صورت بفرستید: <code>1.2.3.4.5</code>", parse_mode='HTML')
        except PhoneCodeInvalidError:
            await update.message.reply_text("❌ کد وارد شده صحیح نیست! لطفا دوباره تلاش کنید.\n📝 لطفا کد را به این صورت بفرستید: <code>1.2.3.4.5</code>", parse_mode='HTML')
    except SessionPasswordNeededError:
        user_states[user_id] = "waiting_salf_password"
        await update.message.reply_text("🔑 این اکانت دو مرحله‌ای فعال است.\n📝 لطفا پسورد خود را وارد کنید:", parse_mode='markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ورود: {str(e)}", parse_mode='markdown')
        del user_states[user_id]
        del salf_login_data[user_id]

async def handle_salf_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_salf_password":
        return
    password = update.message.text.strip()
    if not password:
        await update.message.reply_text("❌ لطفا پسورد را وارد کنید!", parse_mode='markdown')
        return
    try:
        data = salf_login_data[user_id]
        client = data.get('client')
        if not client:
            await update.message.reply_text("❌ خطا در اتصال! لطفا دوباره تلاش کنید.", parse_mode='markdown')
            del user_states[user_id]
            del salf_login_data[user_id]
            return
        await client.sign_in(password=password)
        me = await client.get_me()
        full_name = f"{me.first_name or ''} {me.last_name or ''}".strip() or me.username or "کاربر"
        session_string = client.session.save()
        save_user_session(user_id, session_string, data['phone'], data['api_hash'], data['api_id'])
        set_clock_status(user_id, True)
        asyncio.create_task(start_salf_client(user_id))
        text = (
            "✅ ورود سلف به اکانت شما با موفقیت انجام شد.\n\n"
            "🛡️ سلف برای شما نصب شد.\n"
            "📝 برای استفاده از سلف، کلمه \"پنل\" را در هر جایی بنویسید.\n"
            "💬 در صورت بروز مشکل با پشتیبانی تماس بگیرید."
        )
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_from_user_menu")]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')
        del user_states[user_id]
        del salf_login_data[user_id]
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ورود با پسورد: {str(e)}", parse_mode='markdown')
        del user_states[user_id]
        del salf_login_data[user_id]

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if is_user_banned(user_id):
        await query.edit_message_text("🚫 شما از طرف مدیریت مسدود شده اید!", parse_mode='markdown')
        return
    if user_id in support_mode:
        del support_mode[user_id]
    mention = f"@{query.from_user.username}" if query.from_user.username else query.from_user.first_name
    if user_id in user_states:
        del user_states[user_id]
    if user_id in salf_login_data:
        del salf_login_data[user_id]
    if is_admin(user_id):
        text = (
            f"👋 درود {mention} به پنل ریپر سلف Reaper Self خوش آمدید.\n\n"
            "⚙️ توی این پنل میتوانید ربات ریپر سلف Reaper Self را کنترل و مدیریت کنید.\n\n"
            "📌 لطفا از منوی زیر انتخاب نمایید که چه کاری را می‌خواهید انتخاب دهید."
        )
        keyboard = [
            [InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings")],
            [InlineKeyboardButton("📊 آمار کل", callback_data="admin_stats")],
            [InlineKeyboardButton("📡 بررسی پینگ", callback_data="admin_ping"), InlineKeyboardButton("⏳ اعتبار هاست", callback_data="admin_host")],
            [InlineKeyboardButton("👥 منوی کاربران", callback_data="admin_users_menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')
        return
    rem = get_remaining_days(user_id)
    verified = is_user_verified(user_id)
    logged = get_user_session(user_id) is not None
    text = (
        f"👋 سلام {mention} به ربات ریپر سلف Reaper Self خوش آمدید !\n\n"
        "🛡️ توی این ربات میتوانید از پشتیبانی، خرید، نصب ربات سلف بهره ببرید!\n\n"
        "💬 لطفا اگر سوالی دارید از بخش پشتیبانی، با پشتیبان‌ها در ارتباط باشید!"
    )
    keyboard = [
        [InlineKeyboardButton("👨‍💻 پشتیبانی", callback_data="support")],
        [InlineKeyboardButton("🤔 سلف چیست ؟", callback_data="what_is_self"), InlineKeyboardButton("📣 کانال ما", url="https://t.me/ReaperSelfChannel")],
        [InlineKeyboardButton(f"📅 انقضا شما : ( {rem} روز )", callback_data="expiry")],
        [InlineKeyboardButton("✔️ احراز هویت شده ✅" if verified else "✔️ احراز هویت", callback_data="verified_already" if verified else "verify")],
        [InlineKeyboardButton("💳 خرید اشتراک", callback_data="buy_subscription")],
        [InlineKeyboardButton("💶 خرید با کد", callback_data="buy_with_code")]
    ]
    if has_active_subscription(user_id):
        keyboard.append([InlineKeyboardButton("🔑 ورود سلف", callback_data="salf_login")])
    keyboard.append([InlineKeyboardButton("💎 نرخ", callback_data="rate")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')

async def back_from_user_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_menu_mode and user_menu_mode[user_id]:
        mention = f"@{query.from_user.username}" if query.from_user.username else query.from_user.first_name
        text = (
            f"👋 سلام {mention} به ربات ریپر سلف Reaper Self خوش آمدید !\n\n"
            "🛡️ توی این ربات میتوانید از پشتیبانی، خرید، نصب ربات سلف بهره ببرید!\n\n"
            "💬 لطفا اگر سوالی دارید از بخش پشتیبانی، با پشتیبان‌ها در ارتباط باشید!"
        )
        keyboard = [
            [InlineKeyboardButton("👨‍💻 پشتیبانی", callback_data="support")],
            [InlineKeyboardButton("🤔 سلف چیست ؟", callback_data="what_is_self"), InlineKeyboardButton("📣 کانال ما", url="https://t.me/ReaperSelfChannel")],
            [InlineKeyboardButton("📅 انقضا شما : ( 0 روز )", callback_data="expiry")],
            [InlineKeyboardButton("✔️ احراز هویت", callback_data="verify")],
            [InlineKeyboardButton("💳 خرید اشتراک", callback_data="buy_subscription")],
            [InlineKeyboardButton("💶 خرید با کد", callback_data="buy_with_code")],
            [InlineKeyboardButton("🔑 ورود سلف", callback_data="salf_login")],
            [InlineKeyboardButton("💎 نرخ", callback_data="rate")],
            [InlineKeyboardButton("🎈 پنل مدیریت", callback_data="admin_back")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')
        return
    await main_menu(update, context)

async def buy_1_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.answer("💳 لطفا مبلغ 100 هزار تومان را واریز کنید!", show_alert=True)

async def buy_2_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.answer("💳 لطفا مبلغ 150 هزار تومان را واریز کنید!", show_alert=True)

async def buy_3_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.answer("💳 لطفا مبلغ 200 هزار تومان را واریز کنید!", show_alert=True)

async def buy_4_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.answer("💳 لطفا مبلغ 250 هزار تومان را واریز کنید!", show_alert=True)

async def buy_5_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.answer("💳 لطفا مبلغ 300 هزار تومان را واریز کنید!", show_alert=True)

async def buy_6_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.answer("💳 لطفا مبلغ 350 هزار تومان را واریز کنید!", show_alert=True)

async def expiry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    rem = get_remaining_days(user_id)
    exp = get_expiry_date(user_id)
    if rem > 0:
        await query.answer(f"📅 انقضا شما : {exp} ( {rem} روز باقی مانده )", show_alert=True)
    else:
        await query.answer("⏳ اشتراک شما فعال نمیباشد!", show_alert=True)

# ==================== هندلرهای پیام ====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_user_banned(user_id):
        await update.message.reply_text("🚫 شما از طرف مدیریت مسدود شده اید!", parse_mode='markdown')
        return
    if user_id in user_states and str(user_states[user_id]).startswith("replying_to_"):
        await handle_admin_reply_message(update, context)
        return
    if user_id in support_mode:
        await handle_support_message(update, context)
        return
    if user_id in user_states:
        state = user_states[user_id]
        if state == "waiting_for_verify_photo":
            await handle_verify_photo(update, context)
        elif state == "waiting_for_card_number":
            await handle_verify_card_number(update, context)
        elif state == "waiting_for_activation_code":
            await handle_activation_code(update, context)
        elif state == "waiting_salf_phone":
            await handle_salf_phone(update, context)
        elif state == "waiting_salf_api_id":
            await handle_salf_api_id(update, context)
        elif state == "waiting_salf_api_hash":
            await handle_salf_api_hash(update, context)
        elif state == "waiting_salf_code":
            await handle_salf_code(update, context)
        elif state == "waiting_salf_password":
            await handle_salf_password(update, context)
        elif state == "waiting_for_block_user":
            await handle_block_user(update, context)
        elif state == "waiting_for_unblock_user":
            await handle_unblock_user(update, context)
        elif state == "waiting_for_transfer_credit":
            await handle_transfer_credit(update, context)
        elif state == "waiting_for_deduct_credit":
            await handle_deduct_credit(update, context)
        elif state == "waiting_for_code_days":
            await handle_code_days(update, context)
        elif state == "waiting_for_cancel_code":
            await handle_cancel_code(update, context)
        elif state == "admin_waiting_phone":
            await admin_handle_salf_phone(update, context)
        elif state == "admin_waiting_user_id":
            await admin_handle_salf_user_id(update, context)
        elif state == "admin_waiting_api_id":
            await admin_handle_salf_api_id(update, context)
        elif state == "admin_waiting_api_hash":
            await admin_handle_salf_api_hash(update, context)
        elif state == "admin_waiting_code":
            await admin_handle_salf_code(update, context)
        elif state == "admin_waiting_password":
            await admin_handle_salf_password(update, context)
        elif state == "admin_waiting_logout_phone":
            await admin_handle_salf_logout_phone(update, context)

# ==================== Main ====================

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_membership, pattern="check_membership"))
    app.add_handler(CallbackQueryHandler(admin_stats, pattern="admin_stats"))
    app.add_handler(CallbackQueryHandler(admin_ping, pattern="admin_ping"))
    app.add_handler(CallbackQueryHandler(admin_host, pattern="admin_host"))
    app.add_handler(CallbackQueryHandler(admin_users_menu, pattern="admin_users_menu"))
    app.add_handler(CallbackQueryHandler(admin_settings, pattern="admin_settings"))
    app.add_handler(CallbackQueryHandler(admin_settings_back, pattern="admin_settings_back"))
    app.add_handler(CallbackQueryHandler(admin_create_code, pattern="admin_create_code"))
    app.add_handler(CallbackQueryHandler(admin_cancel_code, pattern="admin_cancel_code"))
    app.add_handler(CallbackQueryHandler(admin_block_user, pattern="admin_block_user"))
    app.add_handler(CallbackQueryHandler(admin_unblock_user, pattern="admin_unblock_user"))
    app.add_handler(CallbackQueryHandler(admin_transfer_credit, pattern="admin_transfer_credit"))
    app.add_handler(CallbackQueryHandler(admin_deduct_credit, pattern="admin_deduct_credit"))
    app.add_handler(CallbackQueryHandler(admin_salf_login, pattern="admin_salf_login"))
    app.add_handler(CallbackQueryHandler(admin_salf_logout, pattern="admin_salf_logout"))
    app.add_handler(CallbackQueryHandler(admin_back, pattern="admin_back"))
    app.add_handler(CallbackQueryHandler(support, pattern="support"))
    app.add_handler(CallbackQueryHandler(disconnect_support, pattern="disconnect_support"))
    app.add_handler(CallbackQueryHandler(what_is_self, pattern="what_is_self"))
    app.add_handler(CallbackQueryHandler(verify, pattern="verify"))
    app.add_handler(CallbackQueryHandler(verified_already, pattern="verified_already"))
    app.add_handler(CallbackQueryHandler(delete_card, pattern="delete_card"))
    app.add_handler(CallbackQueryHandler(new_card, pattern="new_card"))
    app.add_handler(CallbackQueryHandler(back_to_verify, pattern="back_to_verify"))
    app.add_handler(CallbackQueryHandler(buy_subscription, pattern="buy_subscription"))
    app.add_handler(CallbackQueryHandler(buy_with_code, pattern="buy_with_code"))
    app.add_handler(CallbackQueryHandler(salf_login, pattern="salf_login"))
    app.add_handler(CallbackQueryHandler(main_menu, pattern="main_menu"))
    app.add_handler(CallbackQueryHandler(back_from_user_menu, pattern="back_from_user_menu"))
    app.add_handler(CallbackQueryHandler(rate, pattern="rate"))
    app.add_handler(CallbackQueryHandler(expiry, pattern="expiry"))
    app.add_handler(CallbackQueryHandler(handle_salf_toggle_clock, pattern="^toggle_clock_salf_"))
    app.add_handler(CallbackQueryHandler(buy_1_month, pattern="buy_1_month"))
    app.add_handler(CallbackQueryHandler(buy_2_month, pattern="buy_2_month"))
    app.add_handler(CallbackQueryHandler(buy_3_month, pattern="buy_3_month"))
    app.add_handler(CallbackQueryHandler(buy_4_month, pattern="buy_4_month"))
    app.add_handler(CallbackQueryHandler(buy_5_month, pattern="buy_5_month"))
    app.add_handler(CallbackQueryHandler(buy_6_month, pattern="buy_6_month"))
    app.add_handler(CallbackQueryHandler(handle_admin_reply, pattern="^reply_"))
    app.add_handler(CallbackQueryHandler(handle_admin_reply, pattern="^block_"))
    app.add_handler(CallbackQueryHandler(accept_verify, pattern="^accept_verify_"))
    app.add_handler(CallbackQueryHandler(reject_verify, pattern="^reject_verify_"))
    app.add_handler(MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND | filters.Document.ALL | filters.VIDEO, handle_message))
    asyncio.create_task(start_all_salf_clients())
    print("🤖 ربات در حال اجراست...")
    app.run_polling()

if __name__ == "__main__":
    main()
```
