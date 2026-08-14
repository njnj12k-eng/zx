import asyncio
import json
import os
import platform
import random
import re
import socket
import sqlite3
import string
import subprocess
import time
from datetime import datetime, timedelta  # این خط رو اضافه کردم

import psutil
import pytz
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ContextTypes, filters, MessageHandler)
from telethon import TelegramClient, events
from telethon.errors import (FloodWaitError, PhoneCodeExpiredError,
                             PhoneCodeInvalidError, PhoneNumberInvalidError,
                             SessionPasswordNeededError)
from telethon.tl.functions.account import UpdateProfileRequest

TOKEN = "8961040480:AAHNKEnK7LZuCp9fSJ5td2_XdGFqPtwp_dY"
CHANNEL_USERNAME = "@ReaperSelfChannel"
ADMIN_IDS = [7803165903, 8831703400]

DB_FILE = "bot_database.db"

# ==================== دیتابیس ====================

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
        CREATE TABLE IF NOT EXISTS banned_users (
            user_id INTEGER PRIMARY KEY,
            banned_date TEXT,
            reason TEXT
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
pending_verify = {}
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
    cursor.execute('''
        INSERT INTO codes (code, days, expiry_date, created_date)
        VALUES (?, ?, ?, ?)
    ''', (code, days, expiry_date.isoformat(), datetime.now().isoformat()))
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
    if result and result[0] > 0:
        return result[0]
    return 0

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
    if result:
        return result[0] == 1
    return True

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
        return {
            'user_id': result[0],
            'session': result[1],
            'phone': result[2],
            'api_hash': result[3],
            'api_id': result[4],
            'created': result[5]
        }
    return None

def delete_user_session(user_id):
    db_delete_session(user_id)

def generate_code():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=15))

def create_new_code(days):
    while True:
        new_code = generate_code()
        existing = db_get_code(new_code)
        if not existing:
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
        remaining = user_data[0] or 0
        new_remaining = remaining + days
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
        session_data = get_user_session(user_id)
        if not session_data:
            return
        if not has_active_subscription(user_id):
            return
        clock_active = get_clock_status(user_id)
        panel_text = (
            "⚡ به پنل ریپر سلف خوش آمدید.\n"
            "📌 لطفا از منوی زیر انتخاب نمایید!"
        )
        keyboard = [
            [InlineKeyboardButton("⏰ ساعت اکانت غیرفعال" if clock_active else "⏰ ساعت اکانت فعال", callback_data=f"toggle_clock_salf_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await client.edit_message(
            event.message.peer_id,
            event.message.id,
            panel_text,
            parse_mode='html',
            reply_markup=reply_markup
        )
    except Exception as e:
        pass

async def handle_salf_toggle_clock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("toggle_clock_salf_"):
        user_id = int(data.split("_")[3])
        if is_user_banned(user_id):
            await query.edit_message_text("🚫 شما از طرف مدیریت مسدود شده اید!", parse_mode='HTML')
            return
        if not has_active_subscription(user_id):
            await query.edit_message_text("❌ شما اشتراک فعال ندارید!", parse_mode='HTML')
            return
        current_status = get_clock_status(user_id)
        new_status = not current_status
        if new_status:
            set_clock_status(user_id, True)
            await set_clock_on_profile(user_id)
            text = "✅ ساعت اکانت شما فعال شد!"
        else:
            set_clock_status(user_id, False)
            await remove_clock_from_profile(user_id)
            text = "✅ ساعت اکانت شما غیرفعال شد!"
        keyboard = [
            [InlineKeyboardButton("⏰ ساعت اکانت غیرفعال" if new_status else "⏰ ساعت اکانت فعال", callback_data=f"toggle_clock_salf_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

# ==================== کلاینت‌های سلف ====================

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
        client = TelegramClient(
            f"sessions/user_{user_id}",
            session_data['api_id'],
            session_data['api_hash']
        )
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
            if event.sender_id == user_id:
                if event.message and event.message.text and event.message.text.lower() == "پنل":
                    await show_self_panel(client, event)
        await client.run_until_disconnected()
        return True
    except Exception as e:
        return False

async def start_all_salf_clients():
    sessions = db_get_all_sessions()
    for session in sessions:
        user_id = session[0]
        asyncio.create_task(start_salf_client(user_id))

# ==================== تنظیم ساعت ====================

async def set_clock_on_profile(user_id):
    try:
        if not get_clock_status(user_id):
            return False
        session_data = get_user_session(user_id)
        if not session_data:
            return False
        if session_data['api_id'] > 2147483647:
            return False
        client = TelegramClient(
            f"sessions/user_{user_id}",
            session_data['api_id'],
            session_data['api_hash']
        )
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return False
        me = await client.get_me()
        first_name = me.first_name if me.first_name else ""
        last_name = me.last_name if me.last_name else ""
        current_name = f"{first_name} {last_name}".strip()
        if not current_name:
            current_name = me.username if me.username else "کاربر"
        iran_tz = pytz.timezone('Asia/Tehran')
        iran_time = datetime.now(iran_tz)
        time_str = iran_time.strftime('%H:%M')
        clean_name = re.sub(r'\s*\d{2}:\d{2}$', '', current_name).strip()
        new_name = f"{clean_name} {time_str}".strip()
        if new_name != current_name:
            try:
                await client(UpdateProfileRequest(first_name=new_name))
                await client.disconnect()
                return True
            except:
                await client.disconnect()
                return False
        await client.disconnect()
        return True
    except:
        return False

async def remove_clock_from_profile(user_id):
    try:
        session_data = get_user_session(user_id)
        if not session_data:
            return False
        if session_data['api_id'] > 2147483647:
            return False
        client = TelegramClient(
            f"sessions/user_{user_id}",
            session_data['api_id'],
            session_data['api_hash']
        )
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return False
        me = await client.get_me()
        first_name = me.first_name if me.first_name else ""
        last_name = me.last_name if me.last_name else ""
        current_name = f"{first_name} {last_name}".strip()
        if not current_name:
            current_name = me.username if me.username else "کاربر"
        clean_name = re.sub(r'\s*\d{2}:\d{2}$', '', current_name).strip()
        if clean_name != current_name:
            try:
                await client(UpdateProfileRequest(first_name=clean_name))
                await client.disconnect()
                return True
            except:
                await client.disconnect()
                return False
        await client.disconnect()
        return True
    except:
        return False

# ==================== اطلاعات سرور ====================

async def get_server_info():
    try:
        ping_time = None
        try:
            process = await asyncio.create_subprocess_exec(
                "ping", "-c", "3", "-W", "2", "8.8.8.8",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate(timeout=5)
            if process.returncode == 0:
                output = stdout.decode()
                avg_match = re.search(r'avg\s*=\s*(\d+\.?\d*)/(\d+\.?\d*)/(\d+\.?\d*)', output)
                if avg_match:
                    ping_time = float(avg_match.group(2))
                else:
                    ping_match = re.search(r'time[=<](\d+\.?\d*)\s*ms', output)
                    if ping_match:
                        ping_time = float(ping_match.group(1))
        except:
            ping_time = None
        if ping_time is None:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                start_time = time.time()
                sock.connect(("8.8.8.8", 53))
                end_time = time.time()
                sock.close()
                ping_time = (end_time - start_time) * 1000
            except:
                ping_time = None
        cpu_percent = f"{psutil.cpu_percent(interval=0.5):.1f}%"
        memory = psutil.virtual_memory()
        memory_info = f"{memory.percent:.1f}% ({memory.used // (1024**3)}GB / {memory.total // (1024**3)}GB)"
        disk = psutil.disk_usage('/')
        disk_info = f"{disk.percent:.1f}% ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)"
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        if days > 0:
            uptime = f"{days} روز، {hours} ساعت، {minutes} دقیقه"
        elif hours > 0:
            uptime = f"{hours} ساعت، {minutes} دقیقه"
        else:
            uptime = f"{minutes} دقیقه"
        if ping_time is None:
            status = "🔴 قطع"
        elif ping_time < 50:
            status = "🟢 عالی"
        elif ping_time < 100:
            status = "🟢 آنلاین"
        elif ping_time < 200:
            status = "🟡 هشدار"
        else:
            status = "🔴 ضعیف"
        return {
            'status': status,
            'ping': f"{ping_time:.1f} ms" if ping_time else "❌ نامشخص",
            'cpu': cpu_percent,
            'memory': memory_info,
            'disk': disk_info,
            'os': platform.system() + " " + platform.release(),
            'uptime': uptime
        }
    except:
        return {
            'status': "🟢 آنلاین",
            'ping': "📶 متصل",
            'cpu': "نامشخص",
            'memory': "نامشخص",
            'disk': "نامشخص",
            'os': platform.system(),
            'uptime': "نامشخص"
        }

def get_host_expiry():
    try:
        start_date = datetime(2026, 7, 28)
        total_days = 30
        today = datetime.now()
        days_passed = (today - start_date).days
        days_left = total_days - days_passed
        if days_left < 0:
            days_left = 0
        expiry_date = start_date + timedelta(days=total_days)
        return {
            'days_left': days_left,
            'total_days': total_days,
            'expiry_date': expiry_date.strftime('%Y-%m-%d'),
            'start_date': start_date.strftime('%Y-%m-%d'),
            'percent': (days_left / total_days) * 100 if days_left > 0 else 0
        }
    except:
        return {
            'days_left': 26,
            'total_days': 30,
            'expiry_date': "2026-08-27",
            'start_date': "2026-07-28",
            'percent': 86.6
        }

# ==================== استارت ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = update.effective_user
    db_add_user(user_id, user.username, user.first_name, user.last_name)
    if is_user_banned(user_id):
        await update.message.reply_text(
            "🚫 شما از طرف مدیریت مسدود شده اید!\n📌 در صورت نیاز با پشتیبانی تماس بگیرید.",
            parse_mode='HTML'
        )
        return
    user_mention = f"@{user.username}" if user.username else user.first_name
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_menu_mode:
        del user_menu_mode[user_id]
    if is_admin(user_id):
        text = (
            f"⚡ درود {user_mention} به پنل ریپر سلف خوش آمدید.\n\n"
            "📌 در این پنل میتوانید ربات را کنترل و مدیریت کنید.\n\n"
            "📌 لطفا از منوی زیر انتخاب نمایید."
        )
        keyboard = [
            [InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings")],
            [InlineKeyboardButton("📊 آمار کل", callback_data="admin_stats")],
            [InlineKeyboardButton("📡 بررسی پینگ", callback_data="admin_ping"), InlineKeyboardButton("⏳ اعتبار هاست", callback_data="admin_host")],
            [InlineKeyboardButton("👥 منوی کاربران", callback_data="admin_users_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
        return
    try:
        chat_member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if chat_member.status in ["member", "administrator", "creator"]:
            remaining_days = get_remaining_days(user_id)
            has_subscription = has_active_subscription(user_id)
            is_verified = is_user_verified(user_id)
            session_data = get_user_session(user_id)
            is_logged_in = session_data is not None
            expiry_date = get_expiry_date(user_id)
            text = (
                f"⚡ سلام {user_mention} به ربات ریپر سلف خوش آمدید!\n\n"
                "📌 در این ربات میتوانید از پشتیبانی، خرید، نصب ربات سلف بهره ببرید!\n\n"
                "📌 اگر سوالی دارید از بخش پشتیبانی استفاده کنید."
            )
            keyboard = []
            keyboard.append([InlineKeyboardButton("👨‍💻 پشتیبانی", callback_data="support")])
            keyboard.append([InlineKeyboardButton("🤔 سلف چیست؟", callback_data="what_is_self"), InlineKeyboardButton("📣 کانال ما", url="https://t.me/ReaperSelfChannel")])
            keyboard.append([InlineKeyboardButton(f"📅 انقضا شما: ({remaining_days} روز)", callback_data="expiry")])
            if is_verified:
                keyboard.append([InlineKeyboardButton("✅ احراز هویت شده", callback_data="verified_already")])
            else:
                keyboard.append([InlineKeyboardButton("✔️ احراز هویت", callback_data="verify")])
            keyboard.append([InlineKeyboardButton("💳 خرید اشتراک", callback_data="buy_subscription")])
            keyboard.append([InlineKeyboardButton("💶 خرید با کد", callback_data="buy_with_code")])
            if has_subscription:
                keyboard.append([InlineKeyboardButton("🔑 ورود سلف", callback_data="salf_login")])
            keyboard.append([InlineKeyboardButton("💎 نرخ", callback_data="rate")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
            return
    except:
        pass
    text = (
        "📌 برای دسترسی به خدمات ما، ابتدا باید در کانال زیر عضو شوید.\n"
        "📌 پس از عضویت، روی دکمه «عضو شدم» کلیک کنید."
    )
    keyboard = [
        [InlineKeyboardButton("🔗 ریپر سلف", url="https://t.me/ReaperSelfChannel")],
        [InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = query.from_user
    if is_user_banned(user_id):
        await query.edit_message_text(
            "🚫 شما از طرف مدیریت مسدود شده اید!\n📌 در صورت نیاز با پشتیبانی تماس بگیرید.",
            parse_mode='HTML'
        )
        return
    user_mention = f"@{user.username}" if user.username else user.first_name
    if is_admin(user_id):
        text = (
            f"⚡ درود {user_mention} به پنل ریپر سلف خوش آمدید.\n\n"
            "📌 در این پنل میتوانید ربات را کنترل و مدیریت کنید.\n\n"
            "📌 لطفا از منوی زیر انتخاب نمایید."
        )
        keyboard = [
            [InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings")],
            [InlineKeyboardButton("📊 آمار کل", callback_data="admin_stats")],
            [InlineKeyboardButton("📡 بررسی پینگ", callback_data="admin_ping"), InlineKeyboardButton("⏳ اعتبار هاست", callback_data="admin_host")],
            [InlineKeyboardButton("👥 منوی کاربران", callback_data="admin_users_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        return
    try:
        chat_member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if chat_member.status in ["member", "administrator", "creator"]:
            remaining_days = get_remaining_days(user_id)
            has_subscription = has_active_subscription(user_id)
            is_verified = is_user_verified(user_id)
            session_data = get_user_session(user_id)
            is_logged_in = session_data is not None
            expiry_date = get_expiry_date(user_id)
            text = (
                f"⚡ سلام {user_mention} به ربات ریپر سلف خوش آمدید!\n\n"
                "📌 در این ربات میتوانید از پشتیبانی، خرید، نصب ربات سلف بهره ببرید!\n\n"
                "📌 اگر سوالی دارید از بخش پشتیبانی استفاده کنید."
            )
            keyboard = []
            keyboard.append([InlineKeyboardButton("👨‍💻 پشتیبانی", callback_data="support")])
            keyboard.append([InlineKeyboardButton("🤔 سلف چیست؟", callback_data="what_is_self"), InlineKeyboardButton("📣 کانال ما", url="https://t.me/ReaperSelfChannel")])
            keyboard.append([InlineKeyboardButton(f"📅 انقضا شما: ({remaining_days} روز)", callback_data="expiry")])
            if is_verified:
                keyboard.append([InlineKeyboardButton("✅ احراز هویت شده", callback_data="verified_already")])
            else:
                keyboard.append([InlineKeyboardButton("✔️ احراز هویت", callback_data="verify")])
            keyboard.append([InlineKeyboardButton("💳 خرید اشتراک", callback_data="buy_subscription")])
            keyboard.append([InlineKeyboardButton("💶 خرید با کد", callback_data="buy_with_code")])
            if has_subscription:
                keyboard.append([InlineKeyboardButton("🔑 ورود سلف", callback_data="salf_login")])
            keyboard.append([InlineKeyboardButton("💎 نرخ", callback_data="rate")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        else:
            text = (
                "📌 شما هنوز عضو کانال زیر نشده اید!\n"
                "📌 ابتدا برای استفاده از ربات در کانال زیر عضو شوید!"
            )
            keyboard = [
                [InlineKeyboardButton("🔗 ریپر سلف", url="https://t.me/ReaperSelfChannel")],
                [InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    except Exception as e:
        await query.answer("❌ خطا در بررسی عضویت!", show_alert=True)

# ==================== پشتیبانی ====================

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if is_user_banned(user_id):
        await query.edit_message_text(
            "🚫 شما از طرف مدیریت مسدود شده اید!\n📌 در صورت نیاز با پشتیبانی تماس بگیرید.",
            parse_mode='HTML'
        )
        return
    support_mode[user_id] = True
    text = (
        "⚡ شما با موفقیت به بخش پشتیبانی متصل شدید.\n\n"
        "📌 از ارسال پیام‌های اسپم و تکراری خودداری کنید.\n"
        "📌 استفاده از دستورات سلف در این بخش ممنوع بوده و باعث مسدود شدن شما خواهد شد.\n\n"
        "📌 اکنون میتوانید پیام یا سوال خود را برای تیم پشتیبانی ارسال کنید."
    )
    keyboard = [
        [InlineKeyboardButton("💥 لغو اتصال", callback_data="disconnect_support")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def disconnect_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id in support_mode:
        del support_mode[user_id]
    text = (
        "⚡ اتصال شما با تیم پشتیبانی با موفقیت قطع شد.\n"
        "📌 با استفاده از دکمه زیر میتوانید به منوی اصلی بازگردید."
    )
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def handle_support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in support_mode:
        return
    if is_user_banned(user_id):
        await update.message.reply_text("🚫 شما از طرف مدیریت مسدود شده اید!", parse_mode='HTML')
        return
    user = update.effective_user
    user_mention = f"@{user.username}" if user.username else user.first_name
    user_id_str = str(user_id)
    message_text = update.message.text or update.message.caption or "پیام بدون متن"
    ticket_id = db_add_support_ticket(user_id, user_mention, message_text)
    iran_tz = pytz.timezone('Asia/Tehran')
    iran_time = datetime.now(iran_tz)
    time_str = iran_time.strftime('%H:%M')
    date_str = iran_time.strftime('%Y-%m-%d')
    for admin_id in ADMIN_IDS:
        try:
            admin_text = (
                f"📩 پیام جدید از بخش پشتیبانی\n\n"
                f"🆔 شماره تیکت: {ticket_id}\n"
                f"👤 نام کاربر: {user_mention}\n"
                f"🆔 آیدی عددی: {user_id_str}\n"
                f"📝 متن پیام:\n"
                f"<code>{message_text}</code>\n\n"
                f"🕐 ساعت: {time_str}\n"
                f"📅 تاریخ: {date_str}"
            )
            keyboard = [
                [InlineKeyboardButton("💬 پاسخ به کاربر", callback_data=f"reply_{user_id}")],
                [InlineKeyboardButton("🚫 مسدود کردن کاربر", callback_data=f"block_{user_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if update.message.photo:
                photo = update.message.photo[-1]
                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=photo.file_id,
                    caption=admin_text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            elif update.message.document:
                doc = update.message.document
                await context.bot.send_document(
                    chat_id=admin_id,
                    document=doc.file_id,
                    caption=admin_text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            elif update.message.video:
                video = update.message.video
                await context.bot.send_video(
                    chat_id=admin_id,
                    video=video.file_id,
                    caption=admin_text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            else:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=admin_text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
        except:
            pass
    await update.message.reply_text(
        "✅ پیام شما با موفقیت به تیم پشتیبانی ارسال شد.\n"
        "📌 لطفا صبور باشید و منتظر پاسخ بمانید.\n"
        "📌 از ارسال پیام‌های تکراری و اسپم خودداری فرمایید.",
        parse_mode='HTML'
    )

# ==================== پاسخ ادمین ====================

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("reply_"):
        user_id = int(data.split("_")[1])
        user_states[query.from_user.id] = f"replying_to_{user_id}"
        text = (
            "💬 پاسخ به کاربر\n\n"
            "📌 لطفا پاسخ خود را به صورت متن یا رسانه ارسال کنید."
        )
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    elif data.startswith("block_"):
        user_id = int(data.split("_")[1])
        if not is_user_banned(user_id):
            ban_user(user_id)
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="🚫 شما از طرف مدیریت مسدود شده اید!\n📌 در صورت نیاز با پشتیبانی تماس بگیرید.",
                    parse_mode='HTML'
                )
            except:
                pass
            await query.edit_message_text(
                f"✅ کاربر با آیدی {user_id} با موفقیت مسدود شد!",
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text(
                f"⚠️ کاربر با آیدی {user_id} قبلاً مسدود شده است!",
                parse_mode='HTML'
            )

async def handle_admin_reply_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or not str(user_states[user_id]).startswith("replying_to_"):
        return
    target_user_id = int(user_states[user_id].split("_")[2])
    try:
        if update.message.text:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"📩 پاسخ از تیم پشتیبانی:\n\n{update.message.text}",
                parse_mode='HTML'
            )
        elif update.message.photo:
            photo = update.message.photo[-1]
            caption = f"📩 پاسخ از تیم پشتیبانی:\n\n{update.message.caption if update.message.caption else ''}"
            await context.bot.send_photo(
                chat_id=target_user_id,
                photo=photo.file_id,
                caption=caption,
                parse_mode='HTML'
            )
        elif update.message.document:
            doc = update.message.document
            caption = f"📩 پاسخ از تیم پشتیبانی:\n\n{update.message.caption if update.message.caption else ''}"
            await context.bot.send_document(
                chat_id=target_user_id,
                document=doc.file_id,
                caption=caption,
                parse_mode='HTML'
            )
        elif update.message.video:
            video = update.message.video
            caption = f"📩 پاسخ از تیم پشتیبانی:\n\n{update.message.caption if update.message.caption else ''}"
            await context.bot.send_video(
                chat_id=target_user_id,
                video=video.file_id,
                caption=caption,
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text("❌ نوع پیام پشتیبانی نمیشود!", parse_mode='HTML')
            return
        await update.message.reply_text(
            f"✅ پاسخ شما با موفقیت برای کاربر {target_user_id} ارسال شد.",
            parse_mode='HTML'
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ خطا در ارسال پاسخ: {str(e)}",
            parse_mode='HTML'
        )
    del user_states[user_id]

# ==================== بخش ادمین ====================

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_verified = 1')
    verified_users = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_banned = 1')
    banned_users = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM codes')
    total_codes = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM codes WHERE used = 1')
    used_codes = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM sessions')
    total_sessions = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM support_tickets WHERE status = "open"')
    open_tickets = cursor.fetchone()[0]
    conn.close()
    text = (
        "📊 آمار کل ربات\n\n"
        f"👥 تعداد کل کاربران: {total_users}\n"
        f"✅ کاربران احراز هویت شده: {verified_users}\n"
        f"🚫 کاربران مسدود شده: {banned_users}\n"
        f"🔢 تعداد کل کدهای سلف: {total_codes}\n"
        f"✅ کدهای استفاده شده: {used_codes}\n"
        f"❌ کدهای استفاده نشده: {total_codes - used_codes}\n"
        f"👥 تعداد سشن‌های ذخیره شده: {total_sessions}\n"
        f"🎫 تیکت‌های باز پشتیبانی: {open_tickets}\n"
    )
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def admin_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    server_info = await get_server_info()
    if server_info:
        text = (
            "وضعیت پینگ هاست\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📡 وضعیت هاست: {server_info['status']}\n"
            f"⚡ پینگ: {server_info['ping']}\n"
            f"💻 سی‌پی‌یو: {server_info['cpu']}\n"
            f"🧠 رم: {server_info['memory']}\n"
            f"💾 هارد: {server_info['disk']}\n"
            f"🖥️ سیستم‌عامل: {server_info['os']}\n"
            f"⏱️ آپ‌تایم: {server_info['uptime']}\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        text = "❌ خطا در دریافت اطلاعات سرور!"
    keyboard = [
        [InlineKeyboardButton("🔄 بروزرسانی پینگ", callback_data="admin_ping")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    except:
        pass

async def admin_host(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    host_info = get_host_expiry()
    bar_length = 10
    percent = host_info['percent']
    filled = int((percent / 100) * bar_length) if percent > 0 else 0
    bar = "█" * filled + "░" * (bar_length - filled)
    text = (
        "⏳ اطلاعات اعتبار هاست\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 تاریخ شروع: {host_info['start_date']}\n"
        f"📆 تاریخ انقضا: {host_info['expiry_date']}\n"
        f"⏱️ روزهای باقی‌مانده: {host_info['days_left']} روز\n"
        f"📊 وضعیت: {bar} {percent:.1f}%\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
    )
    if host_info['days_left'] <= 0:
        text += "\n⚠️ هاست شما منقضی شده است! لطفا تمدید کنید."
    elif host_info['days_left'] <= 5:
        text += "\n⚠️ هاست شما به زودی منقضی میشود! لطفا تمدید کنید."
    else:
        text += "\n✅ هاست شما فعال است."
    keyboard = [
        [InlineKeyboardButton("🔄 بروزرسانی", callback_data="admin_host")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    except:
        pass

async def admin_users_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_menu_mode[user_id] = True
    user_mention = f"@{query.from_user.username}" if query.from_user.username else query.from_user.first_name
    text = (
        f"⚡ سلام {user_mention} به ربات ریپر سلف خوش آمدید!\n\n"
        "📌 در این ربات میتوانید از پشتیبانی، خرید، نصب ربات سلف بهره ببرید!\n\n"
        "📌 اگر سوالی دارید از بخش پشتیبانی استفاده کنید."
    )
    keyboard = [
        [InlineKeyboardButton("👨‍💻 پشتیبانی", callback_data="support")],
        [InlineKeyboardButton("🤔 سلف چیست؟", callback_data="what_is_self"), InlineKeyboardButton("📣 کانال ما", url="https://t.me/ReaperSelfChannel")],
        [InlineKeyboardButton("📅 انقضا شما: (0 روز)", callback_data="expiry")],
        [InlineKeyboardButton("✔️ احراز هویت", callback_data="verify")],
        [InlineKeyboardButton("💳 خرید اشتراک", callback_data="buy_subscription")],
        [InlineKeyboardButton("💶 خرید با کد", callback_data="buy_with_code")],
        [InlineKeyboardButton("🔑 ورود سلف", callback_data="salf_login")],
        [InlineKeyboardButton("💎 نرخ", callback_data="rate")],
        [InlineKeyboardButton("🎈 پنل مدیریت", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def admin_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_mention = f"@{query.from_user.username}" if query.from_user.username else query.from_user.first_name
    text = (
        f"⚡ درود {user_mention} به بخش تنظیمات پنل مدیریت خوش آمدید.\n\n"
        "📌 در این بخش میتوانید تمامی تنظیمات و مدیریت ربات را انجام دهید.\n\n"
        "📌 لطفا از منوی زیر یکی از گزینه‌های مورد نظر خود را انتخاب نمایید."
    )
    keyboard = [
        [InlineKeyboardButton("➕ ساختن کد سلف", callback_data="admin_create_code"), InlineKeyboardButton("❌ باطل کردن کد سلف", callback_data="admin_cancel_code")],
        [InlineKeyboardButton("🚫 مسدود کردن کاربر", callback_data="admin_block_user"), InlineKeyboardButton("✅ آزاد کردن کاربر", callback_data="admin_unblock_user")],
        [InlineKeyboardButton("📤 انتقال انقضا", callback_data="admin_transfer_credit"), InlineKeyboardButton("📉 کسر انقضا", callback_data="admin_deduct_credit")],
        [InlineKeyboardButton("🔑 ورود سلف", callback_data="admin_salf_login"), InlineKeyboardButton("🚪 خروج سلف", callback_data="admin_salf_logout")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings_back")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def admin_settings_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_mention = f"@{query.from_user.username}" if query.from_user.username else query.from_user.first_name
    text = (
        f"⚡ درود {user_mention} به بخش تنظیمات پنل مدیریت خوش آمدید.\n\n"
        "📌 در این بخش میتوانید تمامی تنظیمات و مدیریت ربات را انجام دهید.\n\n"
        "📌 لطفا از منوی زیر یکی از گزینه‌های مورد نظر خود را انتخاب نمایید."
    )
    keyboard = [
        [InlineKeyboardButton("➕ ساختن کد سلف", callback_data="admin_create_code"), InlineKeyboardButton("❌ باطل کردن کد سلف", callback_data="admin_cancel_code")],
        [InlineKeyboardButton("🚫 مسدود کردن کاربر", callback_data="admin_block_user"), InlineKeyboardButton("✅ آزاد کردن کاربر", callback_data="admin_unblock_user")],
        [InlineKeyboardButton("📤 انتقال انقضا", callback_data="admin_transfer_credit"), InlineKeyboardButton("📉 کسر انقضا", callback_data="admin_deduct_credit")],
        [InlineKeyboardButton("🔑 ورود سلف", callback_data="admin_salf_login"), InlineKeyboardButton("🚪 خروج سلف", callback_data="admin_salf_logout")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings_back")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def admin_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id in user_states:
        del user_states[query.from_user.id]
    if query.from_user.id in admin_salf_data:
        del admin_salf_data[query.from_user.id]
    user_mention = f"@{query.from_user.username}" if query.from_user.username else query.from_user.first_name
    if query.from_user.id in user_menu_mode and user_menu_mode[query.from_user.id]:
        text = (
            f"⚡ سلام {user_mention} به ربات ریپر سلف خوش آمدید!\n\n"
            "📌 در این ربات میتوانید از پشتیبانی، خرید، نصب ربات سلف بهره ببرید!\n\n"
            "📌 اگر سوالی دارید از بخش پشتیبانی استفاده کنید."
        )
        keyboard = [
            [InlineKeyboardButton("👨‍💻 پشتیبانی", callback_data="support")],
            [InlineKeyboardButton("🤔 سلف چیست؟", callback_data="what_is_self"), InlineKeyboardButton("📣 کانال ما", url="https://t.me/ReaperSelfChannel")],
            [InlineKeyboardButton("📅 انقضا شما: (0 روز)", callback_data="expiry")],
            [InlineKeyboardButton("✔️ احراز هویت", callback_data="verify")],
            [InlineKeyboardButton("💳 خرید اشتراک", callback_data="buy_subscription")],
            [InlineKeyboardButton("💶 خرید با کد", callback_data="buy_with_code")],
            [InlineKeyboardButton("🔑 ورود سلف", callback_data="salf_login")],
            [InlineKeyboardButton("💎 نرخ", callback_data="rate")],
            [InlineKeyboardButton("🎈 پنل مدیریت", callback_data="admin_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        return
    text = (
        f"⚡ درود {user_mention} به پنل ریپر سلف خوش آمدید.\n\n"
        "📌 در این پنل میتوانید ربات را کنترل و مدیریت کنید.\n\n"
        "📌 لطفا از منوی زیر انتخاب نمایید."
    )
    keyboard = [
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings")],
        [InlineKeyboardButton("📊 آمار کل", callback_data="admin_stats")],
        [InlineKeyboardButton("📡 بررسی پینگ", callback_data="admin_ping"), InlineKeyboardButton("⏳ اعتبار هاست", callback_data="admin_host")],
        [InlineKeyboardButton("👥 منوی کاربران", callback_data="admin_users_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

# ==================== بخش کاربران ====================

async def rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "⚡ نرخ سلف عبارت است از:\n\n"
        "📌 ماهانه: 100,000 هزار تومان\n\n"
        "📌 دو ماهه: 150,000 هزار تومان\n\n"
        "📌 سه ماهه: 200,000 هزار تومان\n\n"
        "📌 چهار ماهه: 250,000 هزار تومان\n\n"
        "📌 پنج ماهه: 300,000 هزار تومان\n\n"
        "📌 شش ماهه: 350,000 هزار تومان\n\n"
        "⚠️ سلف فقط بر روی اکانت‌هایی که با شماره ایران هستند نصب میشود.\n\n"
        "📍 @ReaperSelfChannel"
    )
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_from_user_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def what_is_self(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "سلف به رباتی گفته میشود که روی اکانت شما نصب میشود و امکانات خاصی را در اختیار شما میگذارد.\n\n"
        "از جمله امکانات:\n"
        "• گذاشتن ساعت با فونت‌های مختلف روی بیو و اسم\n"
        "• قابلیت تنظیم حالت خوانده شدن خودکار پیام‌ها\n"
        "• تنظیم حالت پاسخ خودکار\n"
        "• جواب دادن به شخصی که به شما توهین میکند\n"
        "• پیام انیمیشنی\n"
        "• منشی هوشمند\n"
        "• دریافت پنل و تنظیمات اکانت هوشمند\n"
        "• دو زبانه بودن دستورات و جواب‌ها\n"
        "• تغییر نام و کاور فایل‌ها\n"
        "• اعلان پیام ادیت و حذف شده در پیوی\n"
        "• ذخیره پروفایل‌های جدید و اعلان حذف پروفایل مخاطبین\n\n"
        "📍 @ReaperSelfChannel"
    )
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_from_user_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def buy_with_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_states[query.from_user.id] = "waiting_for_activation_code"
    text = "📌 لطفا کد انقضای خریداری شده خود را ارسال کنید."
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_from_user_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def handle_activation_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_for_activation_code":
        return
    code = update.message.text.strip().upper() if update.message.text else ""
    if not code:
        await update.message.reply_text("❌ لطفا کد را وارد کنید!", parse_mode='HTML')
        return
    code_data, error = validate_code(code)
    if code_data is None:
        await update.message.reply_text(f"{error}", parse_mode='HTML')
        return
    if use_code(code, user_id):
        days = code_data['days']
        remaining_days = get_remaining_days(user_id)
        expiry_date = get_expiry_date(user_id)
        text = (
            f"✅ کد با موفقیت فعال شد!\n\n"
            f"📅 {days} روز به اشتراک شما اضافه شد.\n"
            f"📅 تاریخ انقضا: {expiry_date}\n"
            f"⏳ روزهای باقی‌مانده: {remaining_days} روز"
        )
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_from_user_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
        del user_states[user_id]
    else:
        await update.message.reply_text("❌ خطا در فعال‌سازی کد!", parse_mode='HTML')

async def buy_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if not is_user_verified(user_id):
        text = "📌 برای خرید اشتراک سلف، ابتدا باید احراز هویت کنید."
        keyboard = [
            [InlineKeyboardButton("✔️ احراز هویت", callback_data="verify")],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        return
    text = "📌 لطفا از گزینه‌های زیر انتخاب نمایید که میخواهید ریپر سلف را برای چند ماه خریداری کنید."
    keyboard = [
        [InlineKeyboardButton("(1) ماه معادل 100 هزار (تومان)", callback_data="buy_1_month")],
        [InlineKeyboardButton("(2) ماه معادل 150 هزار (تومان)", callback_data="buy_2_month")],
        [InlineKeyboardButton("(3) ماه معادل 200 هزار (تومان)", callback_data="buy_3_month")],
        [InlineKeyboardButton("(4) ماه معادل 250 هزار (تومان)", callback_data="buy_4_month")],
        [InlineKeyboardButton("(5) ماه معادل 300 هزار (تومان)", callback_data="buy_5_month")],
        [InlineKeyboardButton("(6) ماه معادل 350 هزار (تومان)", callback_data="buy_6_month")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if is_user_verified(user_id):
        await query.answer("✅ شما قبلاً احراز هویت شده اید!", show_alert=True)
        return
    text = (
        "📌 به منوی احراز هویت خوش آمدید.\n\n"
        "📌 لطفا یکی از گزینه‌های زیر را انتخاب نمایید:"
    )
    keyboard = [
        [InlineKeyboardButton("❌ حذف کارت", callback_data="delete_card")],
        [InlineKeyboardButton("➕ کارت جدید", callback_data="new_card")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

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
        "به بخش احراز هویت خوش آمدید.\n\n"
        "نکات مهم:\n"
        "1) شماره کارت و نام صاحب کارت باید کاملا مشخص و خوانا باشد.\n"
        "2) لطفا تاریخ اعتبار و Cvv2 کارت خود را بپوشانید.\n"
        "3) فقط با کارتی که احراز هویت میکنید میتوانید خرید انجام دهید.\n"
        "4) در صورتی که توانایی ارسال عکس از کارت را ندارید، تنها راه حل ارسال عکس از کارت ملی یا شناسنامه صاحب کارت است.\n\n"
        "📌 لطفا عکس از کارتی که میخواهید با آن خرید انجام دهید ارسال کنید."
    )
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_verify")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def handle_verify_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_for_verify_photo":
        return
    if not update.message.photo:
        await update.message.reply_text("❌ لطفا فقط عکس ارسال کنید!", parse_mode='HTML')
        return
    user_states[user_id] = "waiting_for_card_number"
    await update.message.reply_text(
        "✅ عکس شما با موفقیت دریافت شد.\n"
        "📌 لطفا شماره کارت خود را به صورت اعداد انگلیسی وارد کنید.",
        parse_mode='HTML'
    )

async def handle_verify_card_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_for_card_number":
        return
    card_number = update.message.text.strip()
    card_number = re.sub(r'[^0-9]', '', card_number)
    if len(card_number) != 16:
        await update.message.reply_text(
            "❌ شماره کارت باید 16 رقم باشد.\n"
            "📌 لطفا شماره کارت خود را بدون فاصله و کاراکتر اضافی وارد کنید.",
            parse_mode='HTML'
        )
        return
    user = update.effective_user
    user_mention = f"@{user.username}" if user.username else user.first_name
    user_id_str = str(user_id)
    photo = None
    async for msg in context.bot.get_chat_history(chat_id=user_id, limit=5):
        if msg.photo:
            photo = msg.photo[-1]
            break
    request_id = db_add_verify_request(user_id, user_mention, card_number, photo.file_id if photo else None)
    iran_tz = pytz.timezone('Asia/Tehran')
    iran_time = datetime.now(iran_tz)
    time_str = iran_time.strftime('%H:%M')
    date_str = iran_time.strftime('%Y-%m-%d')
    for admin_id in ADMIN_IDS:
        try:
            admin_text = (
                f"🆔 درخواست جدید احراز هویت\n\n"
                f"🆔 شماره درخواست: {request_id}\n"
                f"👤 نام کاربر: {user_mention}\n"
                f"🆔 آیدی عددی: {user_id_str}\n"
                f"💳 شماره کارت: <code>{card_number}</code>\n\n"
                f"🕐 ساعت: {time_str}\n"
                f"📅 تاریخ: {date_str}"
            )
            keyboard = [
                [InlineKeyboardButton("✅ پذیرفتن", callback_data=f"accept_verify_{request_id}")],
                [InlineKeyboardButton("❌ نپذیرفتن", callback_data=f"reject_verify_{request_id}")],
                [InlineKeyboardButton("🚫 مسدود کردن کاربر", callback_data=f"block_{user_id}")],
                [InlineKeyboardButton("💬 پاسخ به کاربر", callback_data=f"reply_{user_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if photo:
                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=photo.file_id,
                    caption=admin_text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            else:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=admin_text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
        except:
            pass
    await update.message.reply_text(
        "✅ درخواست احراز هویت شما با موفقیت به تیم پشتیبانی ارسال شد.\n"
        "📌 لطفا صبور باشید و منتظر تایید از سوی تیم پشتیبانی بمانید.\n"
        "📌 از ارسال درخواست‌های تکراری خودداری فرمایید.",
        parse_mode='HTML'
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
                    chat_id=user_id,
                    text="✅ درخواست احراز هویت شما با موفقیت توسط مدیریت پذیرفته شد.\n\n📌 تبریک! شما اکنون احراز هویت شده اید.",
                    parse_mode='HTML'
                )
            except:
                pass
            await query.edit_message_text(
                f"✅ درخواست احراز هویت شماره {request_id} با موفقیت پذیرفته شد.",
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text(
                f"⚠️ کاربر قبلاً احراز هویت شده است!",
                parse_mode='HTML'
            )
    else:
        await query.edit_message_text("❌ درخواست یافت نشد!", parse_mode='HTML')

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
                chat_id=user_id,
                text="❌ درخواست احراز هویت شما توسط مدیریت پذیرفته نشد.\n\n📌 لطفا دوباره تلاش کنید و اطلاعات صحیح را ارسال نمایید.",
                parse_mode='HTML'
            )
        except:
            pass
        await query.edit_message_text(
            f"❌ درخواست احراز هویت شماره {request_id} رد شد.",
            parse_mode='HTML'
        )
    else:
        await query.edit_message_text("❌ درخواست یافت نشد!", parse_mode='HTML')

async def back_to_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id in user_states:
        del user_states[query.from_user.id]
    text = (
        "📌 به منوی احراز هویت خوش آمدید.\n\n"
        "📌 لطفا یکی از گزینه‌های زیر را انتخاب نمایید:"
    )
    keyboard = [
        [InlineKeyboardButton("❌ حذف کارت", callback_data="delete_card")],
        [InlineKeyboardButton("➕ کارت جدید", callback_data="new_card")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

# ==================== مسدود کردن و آزاد کردن ====================

async def admin_block_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_states[query.from_user.id] = "waiting_for_block_user"
    text = (
        "🚫 مسدود کردن کاربر\n\n"
        "📌 لطفا آیدی عددی کاربر مورد نظر برای مسدود سازی را وارد کنید.\n"
        "⚠️ پس از مسدود شدن، کاربر قادر به استفاده از ربات نخواهد بود."
    )
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def admin_unblock_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_states[query.from_user.id] = "waiting_for_unblock_user"
    text = (
        "✅ آزاد کردن کاربر\n\n"
        "📌 لطفا آیدی عددی کاربر مورد نظر برای آزاد سازی از مسدودیت را وارد کنید.\n"
        "⚠️ پس از آزاد سازی، کاربر دوباره میتواند از ربات استفاده کند."
    )
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def handle_block_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_for_block_user":
        return
    target_id = update.message.text.strip()
    try:
        target_id_int = int(target_id)
    except:
        await update.message.reply_text("❌ آیدی وارد شده صحیح نیست! لطفا یک عدد معتبر وارد کنید.", parse_mode='HTML')
        return
    if target_id_int in ADMIN_IDS:
        await update.message.reply_text("❌ شما نمی‌توانید یک ادمین را مسدود کنید!", parse_mode='HTML')
        return
    if not is_user_banned(target_id_int):
        ban_user(target_id_int)
        try:
            await context.bot.send_message(
                chat_id=target_id_int,
                text="🚫 شما از طرف مدیریت مسدود شده اید!\n📌 در صورت نیاز با پشتیبانی تماس بگیرید.",
                parse_mode='HTML'
            )
        except:
            pass
        await update.message.reply_text(
            f"✅ کاربر با آیدی {target_id_int} با موفقیت مسدود شد.\n"
            "📌 پیام مسدودیت برای کاربر ارسال شد.",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            f"⚠️ کاربر با آیدی {target_id_int} قبلاً در لیست مسدودین قرار دارد.",
            parse_mode='HTML'
        )
    del user_states[user_id]

async def handle_unblock_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_for_unblock_user":
        return
    target_id = update.message.text.strip()
    try:
        target_id_int = int(target_id)
    except:
        await update.message.reply_text("❌ آیدی وارد شده صحیح نیست! لطفا یک عدد معتبر وارد کنید.", parse_mode='HTML')
        return
    if is_user_banned(target_id_int):
        unban_user(target_id_int)
        try:
            await context.bot.send_message(
                chat_id=target_id_int,
                text="✅ تبریک! شما از طرف مدیریت از مسدودیت آزاد شدید.\n📌 ضمن پوزش از شما، خوشحالیم که دوباره به جمع ما برگشتید.",
                parse_mode='HTML'
            )
        except:
            pass
        await update.message.reply_text(
            f"✅ کاربر با آیدی {target_id_int} با موفقیت از مسدودیت آزاد شد.\n"
            "📌 پیام آزادی برای کاربر ارسال شد.",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            f"⚠️ کاربر با آیدی {target_id_int} در لیست مسدودین وجود ندارد.",
            parse_mode='HTML'
        )
    del user_states[user_id]

# ==================== ساخت و باطل کد ====================

async def admin_create_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_states[query.from_user.id] = "waiting_for_code_days"
    text = (
        "➕ ساختن کد سلف جدید\n\n"
        "📌 لطفا تعداد روز انقضا را به صورت عدد وارد کنید.\n"
        "⚠️ عدد وارد شده باید بین 1 تا 100000 باشد."
    )
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def admin_cancel_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_states[query.from_user.id] = "waiting_for_cancel_code"
    text = (
        "❌ باطل کردن کد سلف\n\n"
        "📌 لطفا کد سلف مورد نظر برای باطل شدن را وارد کنید.\n"
        "⚠️ کدهایی که قبلاً استفاده شده اند قابل باطل کردن نیستند."
    )
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def handle_code_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_for_code_days":
        return
    try:
        days = int(update.message.text.strip())
        if days < 1 or days > 100000:
            await update.message.reply_text("❌ عدد باید بین 1 تا 100000 باشد!", parse_mode='HTML')
            return
        new_code, expiry_date = create_new_code(days)
        text = (
            "✅ کد سلف شما با موفقیت ساخته شد\n\n"
            f"📝 کد سلف: <code>{new_code}</code>\n\n"
            f"📅 تاریخ انقضا: {expiry_date.strftime('%Y-%m-%d')}\n"
            f"⏱️ مدت اعتبار: {days} روز\n\n"
            "💡 برای کپی کردن روی کد کلیک کنید."
        )
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
        del user_states[user_id]
    except ValueError:
        await update.message.reply_text("❌ لطفا یک عدد معتبر وارد کنید!", parse_mode='HTML')

async def handle_cancel_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_for_cancel_code":
        return
    code = update.message.text.strip().upper()
    existing = db_get_code(code)
    if not existing:
        await update.message.reply_text("❌ کد وارد شده صحیح نیست!", parse_mode='HTML')
        return
    if existing[4] == 1:
        await update.message.reply_text("❌ این کد قبلاً استفاده شده و قابل باطل کردن نیست!", parse_mode='HTML')
    else:
        db_delete_code(code)
        await update.message.reply_text(f"✅ کد <code>{code}</code> با موفقیت باطل شد!", parse_mode='HTML')
    del user_states[user_id]

# ==================== انتقال و کسر انقضا ====================

async def admin_transfer_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_states[query.from_user.id] = "waiting_for_transfer_credit"
    text = (
        "📤 انتقال انقضا\n\n"
        "📌 لطفا آیدی عددی کاربر مبدا، آیدی عددی کاربر مقصد و مقدار روز را وارد کنید.\n"
        "⚠️ این عملیات غیرقابل بازگشت است.\n"
        "📌 مثال: 123456789 987654321 30"
    )
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def admin_deduct_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_states[query.from_user.id] = "waiting_for_deduct_credit"
    text = (
        "📉 کسر انقضا\n\n"
        "📌 لطفا آیدی عددی کاربر و مقدار روز مورد نظر برای کسر را وارد کنید.\n"
        "⚠️ این عملیات غیرقابل بازگشت است.\n"
        "📌 مثال: 123456789 10"
    )
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def handle_transfer_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_for_transfer_credit":
        return
    parts = update.message.text.strip().split()
    if len(parts) != 3:
        await update.message.reply_text(
            "❌ فرمت وارد شده صحیح نیست!\n"
            "📌 لطفا به این صورت وارد کنید: آیدی_مبدا آیدی_مقصد تعداد_روز",
            parse_mode='HTML'
        )
        return
    try:
        from_id = int(parts[0])
        to_id = int(parts[1])
        days = int(parts[2])
    except:
        await update.message.reply_text("❌ مقادیر وارد شده صحیح نیست! لطفا اعداد معتبر وارد کنید.", parse_mode='HTML')
        return
    if days <= 0:
        await update.message.reply_text("❌ تعداد روز باید بیشتر از صفر باشد.", parse_mode='HTML')
        return
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT remaining_days, expiry_date FROM users WHERE user_id = ?', (from_id,))
    from_data = cursor.fetchone()
    if not from_data or from_data[0] is None or from_data[0] < days:
        conn.close()
        await update.message.reply_text(
            f"⚠️ کاربر با آیدی {from_id} به اندازه {days} روز اشتراک فعال ندارد!",
            parse_mode='HTML'
        )
        return
    new_from_days = from_data[0] - days
    if new_from_days == 0:
        new_from_expiry = None
    else:
        new_from_expiry = (datetime.now() + timedelta(days=new_from_days)).isoformat()
    cursor.execute('UPDATE users SET remaining_days = ?, expiry_date = ? WHERE user_id = ?', 
                   (new_from_days, new_from_expiry, from_id))
    cursor.execute('SELECT remaining_days, expiry_date FROM users WHERE user_id = ?', (to_id,))
    to_data = cursor.fetchone()
    if to_data and to_data[0] is not None:
        new_to_days = to_data[0] + days
        new_to_expiry = (datetime.now() + timedelta(days=new_to_days)).isoformat()
        cursor.execute('UPDATE users SET remaining_days = ?, expiry_date = ? WHERE user_id = ?',
                       (new_to_days, new_to_expiry, to_id))
    else:
        new_to_days = days
        new_to_expiry = (datetime.now() + timedelta(days=days)).isoformat()
        cursor.execute('INSERT INTO users (user_id, remaining_days, expiry_date) VALUES (?, ?, ?)',
                       (to_id, new_to_days, new_to_expiry))
    conn.commit()
    conn.close()
    try:
        await context.bot.send_message(
            chat_id=from_id,
            text=f"📤 از طرف مدیریت، {days} روز از اشتراک شما کسر شد.\n📌 انقضای جدید: {new_from_expiry.split('T')[0] if new_from_expiry else 'اشتراک شما به پایان رسید'}",
            parse_mode='HTML'
        )
    except:
        pass
    try:
        await context.bot.send_message(
            chat_id=to_id,
            text=f"📤 از طرف مدیریت، {days} روز به اشتراک شما اضافه شد.\n📌 انقضای جدید: {new_to_expiry.split('T')[0]}",
            parse_mode='HTML'
        )
    except:
        pass
    await update.message.reply_text(
        f"✅ انتقال {days} روز از کاربر {from_id} به کاربر {to_id} با موفقیت انجام شد.",
        parse_mode='HTML'
    )
    del user_states[user_id]

async def handle_deduct_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_for_deduct_credit":
        return
    parts = update.message.text.strip().split()
    if len(parts) != 2:
        await update.message.reply_text(
            "❌ فرمت وارد شده صحیح نیست!\n"
            "📌 لطفا به این صورت وارد کنید: آیدی_کاربر تعداد_روز",
            parse_mode='HTML'
        )
        return
    try:
        target_id = int(parts[0])
        days = int(parts[1])
    except:
        await update.message.reply_text("❌ مقادیر وارد شده صحیح نیست! لطفا اعداد معتبر وارد کنید.", parse_mode='HTML')
        return
    if days <= 0:
        await update.message.reply_text("❌ تعداد روز باید بیشتر از صفر باشد.", parse_mode='HTML')
        return
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT remaining_days, expiry_date FROM users WHERE user_id = ?', (target_id,))
    target_data = cursor.fetchone()
    if not target_data or target_data[0] is None or target_data[0] == 0:
        conn.close()
        await update.message.reply_text(
            f"⚠️ کاربر با آیدی {target_id} اشتراک فعالی ندارد!",
            parse_mode='HTML'
        )
        return
    new_days = max(0, target_data[0] - days)
    if new_days == 0:
        new_expiry = None
    else:
        new_expiry = (datetime.now() + timedelta(days=new_days)).isoformat()
    cursor.execute('UPDATE users SET remaining_days = ?, expiry_date = ? WHERE user_id = ?',
                   (new_days, new_expiry, target_id))
    conn.commit()
    conn.close()
    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=f"📉 از طرف مدیریت، {days} روز از اشتراک شما کسر شد.\n📌 انقضای جدید: {new_expiry.split('T')[0] if new_expiry else 'اشتراک شما به پایان رسید'}",
            parse_mode='HTML'
        )
    except:
        pass
    await update.message.reply_text(
        f"✅ {days} روز از اشتراک کاربر {target_id} با موفقیت کسر شد.",
        parse_mode='HTML'
    )
    del user_states[user_id]

# ==================== ورود و خروج سلف در مدیریت ====================

async def admin_salf_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    admin_salf_data[query.from_user.id] = {}
    user_states[query.from_user.id] = "admin_waiting_phone"
    text = (
        "🔑 ورود سلف (مدیریت)\n\n"
        "📌 لطفا شماره موبایل کاربر را با کد کشور وارد کنید.\n"
        "مثال: +989123456789\n\n"
        "⚠️ این بخش مخصوص ورود سلف به اکانت کاربران دیگر توسط مدیریت است."
    )
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def admin_salf_logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_states[query.from_user.id] = "admin_waiting_logout_phone"
    text = (
        "🚪 خروج سلف\n\n"
        "📌 لطفا شماره تلفن مورد نظر برای خروج سلف را وارد کنید.\n"
        "⚠️ پس از خروج، سلف از اکانت کاربر خارج خواهد شد و ساعت از اسم او حذف میشود."
    )
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def admin_handle_salf_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "admin_waiting_phone":
        return
    phone = update.message.text.strip()
    if not phone or not re.match(r'^\+?[0-9]{10,15}$', phone):
        await update.message.reply_text(
            "❌ شماره وارد شده صحیح نیست! لطفا با کد کشور وارد کنید.\n"
            "مثال: +989123456789",
            parse_mode='HTML'
        )
        return
    admin_salf_data[user_id]['phone'] = phone
    user_states[user_id] = "admin_waiting_user_id"
    text = "🔑 مرحله 2 از 5\n\n📌 لطفا آیدی عددی کاربر مورد نظر را وارد کنید."
    await update.message.reply_text(text, parse_mode='HTML')

async def admin_handle_salf_logout_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "admin_waiting_logout_phone":
        return
    phone = update.message.text.strip()
    if not phone or not re.match(r'^\+?[0-9]{10,15}$', phone):
        await update.message.reply_text(
            "❌ شماره وارد شده صحیح نیست! لطفا با کد کشور وارد کنید.\n"
            "مثال: +989123456789",
            parse_mode='HTML'
        )
        return
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, api_hash, api_id FROM sessions WHERE phone = ?', (phone,))
    result = cursor.fetchone()
    conn.close()
    if not result:
        await update.message.reply_text("❌ هیچ کاربری با این شماره در سلف یافت نشد!", parse_mode='HTML')
        del user_states[user_id]
        return
    target_user_id = result[0]
    api_hash = result[1]
    api_id = result[2]
    try:
        client = TelegramClient(
            f"sessions/user_{target_user_id}",
            api_id,
            api_hash
        )
        await client.connect()
        if await client.is_user_authorized():
            me = await client.get_me()
            first_name = me.first_name if me.first_name else ""
            last_name = me.last_name if me.last_name else ""
            current_name = f"{first_name} {last_name}".strip()
            if not current_name:
                current_name = me.username if me.username else "کاربر"
            clean_name = re.sub(r'\s*\d{2}:\d{2}$', '', current_name).strip()
            if clean_name != current_name:
                try:
                    await client(UpdateProfileRequest(first_name=clean_name))
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
            chat_id=target_user_id,
            text="🚪 ریپر سلف از اکانت شما خارج شد.\n\n📌 ساعت از روی اسم شما حذف شد.\n📌 در صورت نیاز مجدداً وارد شوید.",
            parse_mode='HTML'
        )
    except:
        pass
    await update.message.reply_text(
        f"✅ خروج سلف از اکانت کاربر {target_user_id} با موفقیت انجام شد.\n"
        f"📱 شماره: {phone}\n"
        "📌 ساعت از اسم کاربر حذف شد.",
        parse_mode='HTML'
    )
    del user_states[user_id]

async def admin_handle_salf_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "admin_waiting_user_id":
        return
    target_id = update.message.text.strip()
    try:
        target_id_int = int(target_id)
    except:
        await update.message.reply_text("❌ آیدی وارد شده صحیح نیست! لطفا یک عدد معتبر وارد کنید.", parse_mode='HTML')
        return
    admin_salf_data[user_id]['target_user_id'] = target_id_int
    user_states[user_id] = "admin_waiting_api_id"
    text = (
        "🔑 مرحله 3 از 5\n\n"
        "📌 لطفا آیپی عددی (API ID) را وارد کنید.\n"
        "⚠️ API ID باید عددی بین 1 تا 2147483647 باشد."
    )
    await update.message.reply_text(text, parse_mode='HTML')

async def admin_handle_salf_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "admin_waiting_api_id":
        return
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("❌ لطفا یک عدد وارد کنید!", parse_mode='HTML')
        return
    try:
        api_id = int(text)
        if api_id > 2147483647:
            await update.message.reply_text(
                "❌ عدد وارد شده خیلی بزرگ است!\n"
                "⚠️ API ID باید عددی بین 1 تا 2147483647 باشد.",
                parse_mode='HTML'
            )
            return
    except:
        await update.message.reply_text("❌ آیپی عددی باید عدد باشد!", parse_mode='HTML')
        return
    admin_salf_data[user_id]['api_id'] = api_id
    user_states[user_id] = "admin_waiting_api_hash"
    text = "🔑 مرحله 4 از 5\n\n📌 لطفا آیپی هش (API Hash) را وارد کنید."
    await update.message.reply_text(text, parse_mode='HTML')

async def admin_handle_salf_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "admin_waiting_api_hash":
        return
    api_hash = update.message.text.strip()
    if not api_hash or len(api_hash) < 20:
        await update.message.reply_text(
            "❌ آیپی هش وارد شده صحیح نیست! لطفا دوباره وارد کنید.",
            parse_mode='HTML'
        )
        return
    admin_salf_data[user_id]['api_hash'] = api_hash
    user_states[user_id] = "admin_waiting_code"
    try:
        data = admin_salf_data[user_id]
        session_path = f"sessions/admin_{user_id}"
        client = TelegramClient(session_path, data['api_id'], data['api_hash'])
        await client.connect()
        if not await client.is_user_authorized():
            await client.send_code_request(data['phone'])
            admin_salf_data[user_id]['client'] = client
            text = (
                "🔑 مرحله 5 از 5\n\n"
                f"✅ کد تایید به شماره {data['phone']} ارسال شد.\n"
                "📌 لطفا کد را به این صورت بفرستید: <code>1.2.3.4.5</code>"
            )
            await update.message.reply_text(text, parse_mode='HTML')
        else:
            await client.disconnect()
            await update.message.reply_text("❌ این شماره قبلاً در سلف ثبت شده است!", parse_mode='HTML')
            del user_states[user_id]
            del admin_salf_data[user_id]
    except PhoneNumberInvalidError:
        await update.message.reply_text("❌ شماره وارد شده معتبر نیست!", parse_mode='HTML')
        del user_states[user_id]
        del admin_salf_data[user_id]
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ارسال کد تایید: {str(e)}", parse_mode='HTML')
        del user_states[user_id]
        del admin_salf_data[user_id]

async def admin_handle_salf_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "admin_waiting_code":
        return
    code_input = update.message.text.strip()
    code = code_input.replace('.', '').replace(' ', '').strip()
    if not code or not code.isdigit():
        await update.message.reply_text(
            "❌ لطفا کد را به این صورت بفرستید: <code>1.2.3.4.5</code>",
            parse_mode='HTML'
        )
        return
    try:
        data = admin_salf_data[user_id]
        client = data.get('client')
        if not client:
            await update.message.reply_text("❌ خطا در اتصال! لطفا دوباره تلاش کنید.", parse_mode='HTML')
            del user_states[user_id]
            del admin_salf_data[user_id]
            return
        try:
            await client.sign_in(data['phone'], code)
            me = await client.get_me()
            first_name = me.first_name if me.first_name else ""
            last_name = me.last_name if me.last_name else ""
            full_name = f"{first_name} {last_name}".strip()
            if not full_name:
                full_name = me.username if me.username else "کاربر"
            iran_tz = pytz.timezone('Asia/Tehran')
            iran_time = datetime.now(iran_tz)
            time_str = iran_time.strftime('%H:%M')
            session_string = client.session.save()
            save_user_session(data['target_user_id'], session_string, data['phone'], data['api_hash'], data['api_id'])
            await client.disconnect()
            set_clock_status(data['target_user_id'], True)
            asyncio.create_task(start_salf_client(data['target_user_id']))
            text = (
                "✅ ورود سلف به اکانت کاربر با موفقیت انجام شد!\n\n"
                f"👤 نام اکانت: {full_name}\n"
                f"📱 شماره: {data['phone']}\n"
                f"🕐 ساعت ورود: {time_str}\n"
                f"📅 تاریخ ورود: {iran_time.strftime('%Y-%m-%d')}\n"
                f"🆔 آیدی کاربر: {data['target_user_id']}\n\n"
                "⏰ ساعت روی اسم اکانت کاربر فعال شد!\n"
                "✅ پنل سلف فعال شد (با نوشتن کلمه \"پنل\" در هر جایی)"
            )
            keyboard = [
                [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
            del user_states[user_id]
            del admin_salf_data[user_id]
            return
        except PhoneCodeExpiredError:
            await update.message.reply_text("⏳ کد منقضی شده بود، در حال ارسال کد جدید...", parse_mode='HTML')
            await client.send_code_request(data['phone'])
            await update.message.reply_text(
                "✅ کد جدید به شماره شما ارسال شد.\n"
                "📌 لطفا کد را به این صورت بفرستید: <code>1.2.3.4.5</code>",
                parse_mode='HTML'
            )
            return
        except PhoneCodeInvalidError:
            await update.message.reply_text(
                "❌ کد وارد شده صحیح نیست! لطفا دوباره تلاش کنید.\n"
                "📌 لطفا کد را به این صورت بفرستید: <code>1.2.3.4.5</code>",
                parse_mode='HTML'
            )
            return
    except SessionPasswordNeededError:
        user_states[user_id] = "admin_waiting_password"
        await update.message.reply_text(
            "🔑 این اکانت دو مرحله‌ای فعال است.\n"
            "📌 لطفا پسورد را وارد کنید:",
            parse_mode='HTML'
        )
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ورود: {str(e)}", parse_mode='HTML')
        del user_states[user_id]
        del admin_salf_data[user_id]

async def admin_handle_salf_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "admin_waiting_password":
        return
    password = update.message.text.strip()
    if not password:
        await update.message.reply_text("❌ لطفا پسورد را وارد کنید!", parse_mode='HTML')
        return
    try:
        data = admin_salf_data[user_id]
        client = data.get('client')
        if not client:
            await update.message.reply_text("❌ خطا در اتصال! لطفا دوباره تلاش کنید.", parse_mode='HTML')
            del user_states[user_id]
            del admin_salf_data[user_id]
            return
        await client.sign_in(password=password)
        me = await client.get_me()
        first_name = me.first_name if me.first_name else ""
        last_name = me.last_name if me.last_name else ""
        full_name = f"{first_name} {last_name}".strip()
        if not full_name:
            full_name = me.username if me.username else "کاربر"
        iran_tz = pytz.timezone('Asia/Tehran')
        iran_time = datetime.now(iran_tz)
        time_str = iran_time.strftime('%H:%M')
        session_string = client.session.save()
        save_user_session(data['target_user_id'], session_string, data['phone'], data['api_hash'], data['api_id'])
        await client.disconnect()
        set_clock_status(data['target_user_id'], True)
        asyncio.create_task(start_salf_client(data['target_user_id']))
        text = (
            "✅ ورود سلف به اکانت کاربر با موفقیت انجام شد!\n\n"
            f"👤 نام اکانت: {full_name}\n"
            f"📱 شماره: {data['phone']}\n"
            f"🕐 ساعت ورود: {time_str}\n"
            f"📅 تاریخ ورود: {iran_time.strftime('%Y-%m-%d')}\n"
            f"🆔 آیدی کاربر: {data['target_user_id']}\n\n"
            "⏰ ساعت روی اسم اکانت کاربر فعال شد!\n"
            "✅ پنل سلف فعال شد (با نوشتن کلمه \"پنل\" در هر جایی)"
        )
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
        del user_states[user_id]
        del admin_salf_data[user_id]
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ورود با پسورد: {str(e)}", parse_mode='HTML')
        del user_states[user_id]
        del admin_salf_data[user_id]

# ==================== ورود سلف کاربر ====================

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
    existing_session = get_user_session(user_id)
    if existing_session:
        await query.answer("🔑 شما قبلاً وارد سلف شده اید!", show_alert=True)
        return
    user_states[user_id] = "waiting_salf_phone"
    salf_login_data[user_id] = {}
    text = (
        "🔑 ورود به سلف\n\n"
        "📌 لطفا شماره موبایل خود را با کد کشور وارد کنید.\n"
        "مثال: +989123456789\n\n"
        "در صورتی که منصرف شده‌اید دکمه زیر را کلیک کنید."
    )
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_from_user_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def handle_salf_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_salf_phone":
        return
    phone = update.message.text.strip() if update.message.text else ""
    if not phone or not re.match(r'^\+?[0-9]{10,15}$', phone):
        await update.message.reply_text(
            "❌ شماره وارد شده صحیح نیست! لطفا با کد کشور وارد کنید.\n"
            "مثال: +989123456789",
            parse_mode='HTML'
        )
        return
    salf_login_data[user_id]['phone'] = phone
    user_states[user_id] = "waiting_salf_api_id"
    await update.message.reply_text(
        "🔑 مرحله 2 از 4\n\n"
        "📌 لطفا آیپی عددی (API ID) خود را وارد کنید.\n"
        "⚠️ API ID باید عددی بین 1 تا 2147483647 باشد.",
        parse_mode='HTML'
    )

async def handle_salf_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_salf_api_id":
        return
    text = update.message.text.strip() if update.message.text else ""
    if not text:
        await update.message.reply_text("❌ لطفا یک عدد وارد کنید!", parse_mode='HTML')
        return
    try:
        api_id = int(text)
        if api_id > 2147483647:
            await update.message.reply_text(
                "❌ عدد وارد شده خیلی بزرگ است!\n"
                "⚠️ API ID باید عددی بین 1 تا 2147483647 باشد.\n"
                "📌 لطفا دوباره وارد کنید:",
                parse_mode='HTML'
            )
            return
    except:
        await update.message.reply_text("❌ آیپی عددی باید عدد باشد! لطفا دوباره وارد کنید.", parse_mode='HTML')
        return
    salf_login_data[user_id]['api_id'] = api_id
    user_states[user_id] = "waiting_salf_api_hash"
    await update.message.reply_text(
        "🔑 مرحله 3 از 4\n\n"
        "📌 لطفا آیپی هش (API Hash) خود را وارد کنید.",
        parse_mode='HTML'
    )

async def handle_salf_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_salf_api_hash":
        return
    api_hash = update.message.text.strip() if update.message.text else ""
    if not api_hash or len(api_hash) < 20:
        await update.message.reply_text(
            "❌ آیپی هش وارد شده صحیح نیست! لطفا دوباره وارد کنید.",
            parse_mode='HTML'
        )
        return
    salf_login_data[user_id]['api_hash'] = api_hash
    user_states[user_id] = "waiting_salf_code"
    try:
        data = salf_login_data[user_id]
        session_path = f"sessions/user_{user_id}"
        client = TelegramClient(session_path, data['api_id'], data['api_hash'])
        await client.connect()
        if not await client.is_user_authorized():
            await client.send_code_request(data['phone'])
            salf_login_data[user_id]['client'] = client
            await update.message.reply_text(
                "🔑 مرحله 4 از 4\n\n"
                "✅ کد تایید به شماره شما ارسال شد.\n"
                "📌 لطفا کد را به این صورت بفرستید: <code>1.2.3.4.5</code>",
                parse_mode='HTML'
            )
        else:
            await client.disconnect()
            await update.message.reply_text("❌ این شماره قبلاً در سلف ثبت شده است!", parse_mode='HTML')
            del user_states[user_id]
            del salf_login_data[user_id]
    except PhoneNumberInvalidError:
        await update.message.reply_text("❌ شماره وارد شده معتبر نیست!", parse_mode='HTML')
        del user_states[user_id]
        del salf_login_data[user_id]
    except FloodWaitError as e:
        await update.message.reply_text(f"⏳ لطفا {e.seconds} ثانیه صبر کنید و دوباره تلاش کنید.", parse_mode='HTML')
        del user_states[user_id]
        del salf_login_data[user_id]
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ارسال کد تایید: {str(e)}", parse_mode='HTML')
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
    code_input = update.message.text.strip() if update.message.text else ""
    code = code_input.replace('.', '').replace(' ', '').strip()
    if not code or not code.isdigit():
        await update.message.reply_text(
            "❌ لطفا کد را به این صورت بفرستید: <code>1.2.3.4.5</code>",
            parse_mode='HTML'
        )
        return
    try:
        data = salf_login_data[user_id]
        client = data.get('client')
        if not client:
            await update.message.reply_text("❌ خطا در اتصال! لطفا دوباره تلاش کنید.", parse_mode='HTML')
            del user_states[user_id]
            del salf_login_data[user_id]
            return
        try:
            await client.sign_in(data['phone'], code)
            me = await client.get_me()
            first_name = me.first_name if me.first_name else ""
            last_name = me.last_name if me.last_name else ""
            full_name = f"{first_name} {last_name}".strip()
            if not full_name:
                full_name = me.username if me.username else "کاربر"
            iran_tz = pytz.timezone('Asia/Tehran')
            iran_time = datetime.now(iran_tz)
            time_str = iran_time.strftime('%H:%M')
            session_string = client.session.save()
            save_user_session(user_id, session_string, data['phone'], data['api_hash'], data['api_id'])
            set_clock_status(user_id, True)
            asyncio.create_task(start_salf_client(user_id))
            text = (
                "✅ ورود سلف به اکانت شما با موفقیت انجام شد.\n\n"
                "📌 سلف برای شما نصب شد.\n"
                "📌 برای استفاده از سلف، کلمه \"پنل\" را در هر جایی بنویسید.\n"
                "📌 در صورت بروز مشکل با پشتیبانی تماس بگیرید."
            )
            keyboard = [
                [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_from_user_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
            del user_states[user_id]
            del salf_login_data[user_id]
            return
        except PhoneCodeExpiredError:
            await update.message.reply_text("⏳ کد منقضی شده بود، در حال ارسال کد جدید...", parse_mode='HTML')
            await client.send_code_request(data['phone'])
            await update.message.reply_text(
                "✅ کد جدید به شماره شما ارسال شد.\n"
                "📌 لطفا کد را به این صورت بفرستید: <code>1.2.3.4.5</code>",
                parse_mode='HTML'
            )
            return
        except PhoneCodeInvalidError:
            await update.message.reply_text(
                "❌ کد وارد شده صحیح نیست! لطفا دوباره تلاش کنید.\n"
                "📌 لطفا کد را به این صورت بفرستید: <code>1.2.3.4.5</code>",
                parse_mode='HTML'
            )
            return
    except SessionPasswordNeededError:
        user_states[user_id] = "waiting_salf_password"
        await update.message.reply_text(
            "🔑 این اکانت دو مرحله‌ای فعال است.\n"
            "📌 لطفا پسورد خود را وارد کنید:",
            parse_mode='HTML'
        )
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ورود: {str(e)}", parse_mode='HTML')
        del user_states[user_id]
        del salf_login_data[user_id]

async def handle_salf_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_salf_password":
        return
    password = update.message.text.strip() if update.message.text else ""
    if not password:
        await update.message.reply_text("❌ لطفا پسورد را وارد کنید!", parse_mode='HTML')
        return
    try:
        data = salf_login_data[user_id]
        client = data.get('client')
        if not client:
            await update.message.reply_text("❌ خطا در اتصال! لطفا دوباره تلاش کنید.", parse_mode='HTML')
            del user_states[user_id]
            del salf_login_data[user_id]
            return
        await client.sign_in(password=password)
        me = await client.get_me()
        first_name = me.first_name if me.first_name else ""
        last_name = me.last_name if me.last_name else ""
        full_name = f"{first_name} {last_name}".strip()
        if not full_name:
            full_name = me.username if me.username else "کاربر"
        iran_tz = pytz.timezone('Asia/Tehran')
        iran_time = datetime.now(iran_tz)
        time_str = iran_time.strftime('%H:%M')
        session_string = client.session.save()
        save_user_session(user_id, session_string, data['phone'], data['api_hash'], data['api_id'])
        set_clock_status(user_id, True)
        asyncio.create_task(start_salf_client(user_id))
        text = (
            "✅ ورود سلف به اکانت شما با موفقیت انجام شد.\n\n"
            "📌 سلف برای شما نصب شد.\n"
            "📌 برای استفاده از سلف، کلمه \"پنل\" را در هر جایی بنویسید.\n"
            "📌 در صورت بروز مشکل با پشتیبانی تماس بگیرید."
        )
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_from_user_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
        del user_states[user_id]
        del salf_login_data[user_id]
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ورود با پسورد: {str(e)}", parse_mode='HTML')
        del user_states[user_id]
        del salf_login_data[user_id]

# ==================== ناوبری ====================

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if is_user_banned(user_id):
        await query.edit_message_text(
            "🚫 شما از طرف مدیریت مسدود شده اید!\n📌 در صورت نیاز با پشتیبانی تماس بگیرید.",
            parse_mode='HTML'
        )
        return
    if user_id in support_mode:
        del support_mode[user_id]
    user_mention = f"@{query.from_user.username}" if query.from_user.username else query.from_user.first_name
    if user_id in user_states:
        del user_states[user_id]
    if user_id in salf_login_data:
        del salf_login_data[user_id]
    if is_admin(user_id):
        text = (
            f"⚡ درود {user_mention} به پنل ریپر سلف خوش آمدید.\n\n"
            "📌 در این پنل میتوانید ربات را کنترل و مدیریت کنید.\n\n"
            "📌 لطفا از منوی زیر انتخاب نمایید."
        )
        keyboard = [
            [InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings")],
            [InlineKeyboardButton("📊 آمار کل", callback_data="admin_stats")],
            [InlineKeyboardButton("📡 بررسی پینگ", callback_data="admin_ping"), InlineKeyboardButton("⏳ اعتبار هاست", callback_data="admin_host")],
            [InlineKeyboardButton("👥 منوی کاربران", callback_data="admin_users_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        return
    remaining_days = get_remaining_days(user_id)
    has_subscription = has_active_subscription(user_id)
    is_verified = is_user_verified(user_id)
    session_data = get_user_session(user_id)
    is_logged_in = session_data is not None
    expiry_date = get_expiry_date(user_id)
    text = (
        f"⚡ سلام {user_mention} به ربات ریپر سلف خوش آمدید!\n\n"
        "📌 در این ربات میتوانید از پشتیبانی، خرید، نصب ربات سلف بهره ببرید!\n\n"
        "📌 اگر سوالی دارید از بخش پشتیبانی استفاده کنید."
    )
    keyboard = []
    keyboard.append([InlineKeyboardButton("👨‍💻 پشتیبانی", callback_data="support")])
    keyboard.append([InlineKeyboardButton("🤔 سلف چیست؟", callback_data="what_is_self"), InlineKeyboardButton("📣 کانال ما", url="https://t.me/ReaperSelfChannel")])
    keyboard.append([InlineKeyboardButton(f"📅 انقضا شما: ({remaining_days} روز)", callback_data="expiry")])
    if is_verified:
        keyboard.append([InlineKeyboardButton("✅ احراز هویت شده", callback_data="verified_already")])
    else:
        keyboard.append([InlineKeyboardButton("✔️ احراز هویت", callback_data="verify")])
    keyboard.append([InlineKeyboardButton("💳 خرید اشتراک", callback_data="buy_subscription")])
    keyboard.append([InlineKeyboardButton("💶 خرید با کد", callback_data="buy_with_code")])
    if has_subscription:
        keyboard.append([InlineKeyboardButton("🔑 ورود سلف", callback_data="salf_login")])
    keyboard.append([InlineKeyboardButton("💎 نرخ", callback_data="rate")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def back_from_user_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_menu_mode and user_menu_mode[user_id]:
        user_mention = f"@{query.from_user.username}" if query.from_user.username else query.from_user.first_name
        text = (
            f"⚡ سلام {user_mention} به ربات ریپر سلف خوش آمدید!\n\n"
            "📌 در این ربات میتوانید از پشتیبانی، خرید، نصب ربات سلف بهره ببرید!\n\n"
            "📌 اگر سوالی دارید از بخش پشتیبانی استفاده کنید."
        )
        keyboard = [
            [InlineKeyboardButton("👨‍💻 پشتیبانی", callback_data="support")],
            [InlineKeyboardButton("🤔 سلف چیست؟", callback_data="what_is_self"), InlineKeyboardButton("📣 کانال ما", url="https://t.me/ReaperSelfChannel")],
            [InlineKeyboardButton("📅 انقضا شما: (0 روز)", callback_data="expiry")],
            [InlineKeyboardButton("✔️ احراز هویت", callback_data="verify")],
            [InlineKeyboardButton("💳 خرید اشتراک", callback_data="buy_subscription")],
            [InlineKeyboardButton("💶 خرید با کد", callback_data="buy_with_code")],
            [InlineKeyboardButton("🔑 ورود سلف", callback_data="salf_login")],
            [InlineKeyboardButton("💎 نرخ", callback_data="rate")],
            [InlineKeyboardButton("🎈 پنل مدیریت", callback_data="admin_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
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
    remaining_days = get_remaining_days(user_id)
    expiry_date = get_expiry_date(user_id)
    if remaining_days > 0:
        await query.answer(f"📅 انقضا: {expiry_date} ({remaining_days} روز باقی مانده)", show_alert=True)
    else:
        await query.answer("⏳ اشتراک شما فعال نمیباشد!", show_alert=True)

# ==================== هندلر پیام ====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_user_banned(user_id):
        await update.message.reply_text(
            "🚫 شما از طرف مدیریت مسدود شده اید!\n📌 در صورت نیاز با پشتیبانی تماس بگیرید.",
            parse_mode='HTML'
        )
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
            return
        elif state == "waiting_for_card_number":
            await handle_verify_card_number(update, context)
            return
        elif state == "waiting_for_activation_code":
            await handle_activation_code(update, context)
            return
        elif state == "waiting_salf_phone":
            await handle_salf_phone(update, context)
            return
        elif state == "waiting_salf_api_id":
            await handle_salf_api_id(update, context)
            return
        elif state == "waiting_salf_api_hash":
            await handle_salf_api_hash(update, context)
            return
        elif state == "waiting_salf_code":
            await handle_salf_code(update, context)
            return
        elif state == "waiting_salf_password":
            await handle_salf_password(update, context)
            return
        elif state == "waiting_for_block_user":
            await handle_block_user(update, context)
            return
        elif state == "waiting_for_unblock_user":
            await handle_unblock_user(update, context)
            return
        elif state == "waiting_for_transfer_credit":
            await handle_transfer_credit(update, context)
            return
        elif state == "waiting_for_deduct_credit":
            await handle_deduct_credit(update, context)
            return
        elif state == "waiting_for_code_days":
            await handle_code_days(update, context)
            return
        elif state == "waiting_for_cancel_code":
            await handle_cancel_code(update, context)
            return
        elif state == "admin_waiting_phone":
            await admin_handle_salf_phone(update, context)
            return
        elif state == "admin_waiting_user_id":
            await admin_handle_salf_user_id(update, context)
            return
        elif state == "admin_waiting_api_id":
            await admin_handle_salf_api_id(update, context)
            return
        elif state == "admin_waiting_api_hash":
            await admin_handle_salf_api_hash(update, context)
            return
        elif state == "admin_waiting_code":
            await admin_handle_salf_code(update, context)
            return
        elif state == "admin_waiting_password":
            await admin_handle_salf_password(update, context)
            return
        elif state == "admin_waiting_logout_phone":
            await admin_handle_salf_logout_phone(update, context)
            return

# ==================== اجرای اصلی ====================

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
    
    print("🤖 ربات در حال اجراست...")
    app.run_polling()

if __name__ == "__main__":
    main()
