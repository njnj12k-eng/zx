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
from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    PhoneCodeExpiredError,
    FloodWaitError
)

TOKEN = "8961040480:AAHNKEnK7LZuCp9fSJ5td2_XdGFqPtwp_dY"
CHANNEL_USERNAME = "@ReaperSelfChannel"

# لیست آیدی ادمین‌ها
ADMIN_IDS = [7803165903, 8831703400]

user_states = {}
CODES_FILE = "codes_data.json"
SESSIONS_FILE = "sessions_data.json"
salf_login_data = {}
clock_tasks = {}

if not os.path.exists("sessions"):
    os.makedirs("sessions")

# ==================== دیتابیس سشن‌ها ====================

def load_sessions():
    try:
        if os.path.exists(SESSIONS_FILE):
            with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except:
        return {}

def save_sessions(sessions):
    try:
        with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(sessions, f, ensure_ascii=False, indent=4)
    except:
        pass

def save_user_session(user_id, session_string, phone, api_hash, api_id):
    sessions = load_sessions()
    sessions[str(user_id)] = {
        'session': session_string,
        'phone': phone,
        'api_hash': api_hash,
        'api_id': api_id,
        'created': datetime.now().isoformat()
    }
    save_sessions(sessions)

def get_user_session(user_id):
    sessions = load_sessions()
    return sessions.get(str(user_id))

# ==================== دیتابیس کدها ====================

def load_codes():
    try:
        if os.path.exists(CODES_FILE):
            with open(CODES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except:
        return {}

def save_codes(codes):
    try:
        with open(CODES_FILE, 'w', encoding='utf-8') as f:
            json.dump(codes, f, ensure_ascii=False, indent=4)
    except:
        pass

def generate_code():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=15))

def create_new_code(days):
    codes = load_codes()
    while True:
        new_code = generate_code()
        if new_code not in codes:
            break
    expiry_date = datetime.now() + timedelta(days=days)
    codes[new_code] = {
        'days': days,
        'expiry': expiry_date.isoformat(),
        'created': datetime.now().isoformat(),
        'used': False,
        'used_by': None
    }
    save_codes(codes)
    return new_code, expiry_date

def validate_code(code):
    codes = load_codes()
    if code not in codes:
        return None, "❌ کد وارد شده صحیح نیست!"
    code_data = codes[code]
    expiry_date = datetime.fromisoformat(code_data['expiry'])
    if datetime.now() > expiry_date:
        return None, "⏳ کد وارد شده منقضی شده است!"
    if code_data.get('used', False):
        return None, "❌ این کد قبلاً استفاده شده است!"
    return code_data, None

def use_code(code, user_id):
    codes = load_codes()
    if code not in codes:
        return False
    codes[code]['used'] = True
    codes[code]['used_by'] = str(user_id)
    codes[code]['used_at'] = datetime.now().isoformat()
    save_codes(codes)
    return True

def get_user_expiry(user_id):
    codes = load_codes()
    user_expiry = None
    user_days = 0
    for code, data in codes.items():
        if data.get('used_by') == str(user_id) and data.get('used', False):
            expiry = datetime.fromisoformat(data['expiry'])
            if user_expiry is None or expiry > user_expiry:
                user_expiry = expiry
                user_days = data.get('days', 0)
    return user_expiry, user_days

def get_remaining_days(user_id):
    expiry, _ = get_user_expiry(user_id)
    if expiry:
        remaining = (expiry - datetime.now()).days
        return max(0, remaining)
    return 0

def get_expiry_date(user_id):
    expiry, _ = get_user_expiry(user_id)
    if expiry:
        return expiry.strftime('%Y-%m-%d')
    return "ندارد"

def has_active_subscription(user_id):
    return get_remaining_days(user_id) > 0

def is_admin(user_id):
    return user_id in ADMIN_IDS

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

# ==================== تابع تنظیم ساعت روی اسم اکانت ====================

async def set_clock_on_profile(user_id):
    """تنظیم ساعت روی اسم اکانت"""
    try:
        session_data = get_user_session(user_id)
        if not session_data:
            return False
        
        # بررسی API ID
        if session_data['api_id'] > 2147483647:
            print(f"⚠️ API ID برای کاربر {user_id} خیلی بزرگ است: {session_data['api_id']}")
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
        
        # دریافت اطلاعات کاربر
        me = await client.get_me()
        first_name = me.first_name if me.first_name else ""
        last_name = me.last_name if me.last_name else ""
        current_name = f"{first_name} {last_name}".strip()
        if not current_name:
            current_name = me.username if me.username else "کاربر"
        
        # دریافت ساعت ایران
        iran_tz = pytz.timezone('Asia/Tehran')
        iran_time = datetime.now(iran_tz)
        time_str = iran_time.strftime('%H:%M')
        
        # حذف ساعت قبلی از اسم
        clean_name = re.sub(r'\s*\d{2}:\d{2}$', '', current_name).strip()
        
        # اسم جدید با ساعت
        new_name = f"{clean_name} {time_str}".strip()
        
        # اگر اسم تغییر کرده، اعمال کن
        if new_name != current_name:
            try:
                # روش درست برای telethon - استفاده از account.updateProfile
                from telethon.tl.functions.account import UpdateProfileRequest
                await client(UpdateProfileRequest(first_name=new_name))
                print(f"✅ ساعت برای کاربر {user_id} به {new_name} تغییر کرد")
                await client.disconnect()
                return True
            except Exception as e:
                print(f"⚠️ خطا در تغییر نام: {e}")
                await client.disconnect()
                return False
        
        await client.disconnect()
        return True
        
    except Exception as e:
        print(f"⚠️ خطا در تنظیم ساعت: {e}")
        return False

async def clock_loop(user_id):
    """حلقه هر دقیقه برای بروزرسانی ساعت"""
    while True:
        try:
            await set_clock_on_profile(user_id)
        except Exception as e:
            print(f"⚠️ خطا در حلقه ساعت: {e}")
        await asyncio.sleep(60)

async def start_clock_task(user_id):
    """شروع task ساعت برای کاربر"""
    if user_id in clock_tasks:
        try:
            clock_tasks[user_id].cancel()
        except:
            pass
        del clock_tasks[user_id]
    
    task = asyncio.create_task(clock_loop(user_id))
    clock_tasks[user_id] = task
    return task

# ==================== بخش استارت ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_mention = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name
    
    if user_id in user_states:
        del user_states[user_id]
    
    if is_admin(user_id):
        text = (
            f"<b>⫸ درود {user_mention} به پنل ریپر سلف Reaper Self خوش آمدید.</b>\n\n"
            "<b>◄ توی این پنل میتوانید ربات ریپر سلف Reaper Self را کنترل و مدیریت کنید.</b>\n\n"
            "<b>◂ لطفا از منوی زیر انتخاب نمایید که چه کاری را می‌خواهید انتخاب دهید.</b>"
        )
        
        keyboard = [
            [InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings")],
            [InlineKeyboardButton("➕ ساخت کد سلف", callback_data="admin_create_code"), InlineKeyboardButton("❌ باطل کد سلف", callback_data="admin_cancel_code")],
            [InlineKeyboardButton("🚫 مسدود کردن کاربر", callback_data="admin_block_user"), InlineKeyboardButton("✅ آزاد کردن کاربر", callback_data="admin_unblock_user")],
            [InlineKeyboardButton("📤 انتقال اعتبار", callback_data="admin_transfer_credit"), InlineKeyboardButton("📉 کسر اعتبار", callback_data="admin_deduct_credit")],
            [InlineKeyboardButton("🔑 ورود سلف", callback_data="admin_salf_login"), InlineKeyboardButton("🚪 خروج سلف", callback_data="admin_salf_logout")],
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
            expiry_date = get_expiry_date(user_id)
            has_subscription = has_active_subscription(user_id)
            
            session_data = get_user_session(user_id)
            is_logged_in = session_data is not None
            
            text = (
                "<b>⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌</b>\n"
                f"<b>⫸ سلام {user_mention} به ربات ریپر سلف Reaper Self خوش آمدید !</b>\n\n"
                "<b>◄ توی این ربات میتوانید از پشتیبانی ، خرید ، نصب ربات سلف بهره ببرید !</b>\n\n"
                "<b>◂ لطفا اگر سوالی دارید از بخش پشتیبانی ، با پشتیبان ها در ارتباط باشید !</b>\n"
                f"<b>📅 انقضا شما : ( {remaining_days} روز )</b>\n"
                f"<b>🔑 وضعیت ورود : {'✅ وارد شده' if is_logged_in else '❌ وارد نشده'}</b>\n"
                "<b>⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯   ⁭⁯⁯⁭⁯‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌</b>"
            )
            
            keyboard = []
            keyboard.append([InlineKeyboardButton("👨‍💻 پشتیبانی", callback_data="support")])
            keyboard.append([InlineKeyboardButton("🤔 سلف چیست ؟", callback_data="what_is_self"), InlineKeyboardButton("📣 کانال ما", url="https://t.me/ReaperSelfChannel")])
            keyboard.append([InlineKeyboardButton(f"📅 انقضا شما : ( {remaining_days} روز )", callback_data="expiry")])
            keyboard.append([InlineKeyboardButton("✔️ احراز هویت", callback_data="verify"), InlineKeyboardButton("💳 خرید اشتراک", callback_data="buy_subscription")])
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
        "<b>⫸ برای دسترسی به خدمات ما، ابتدا باید در کانال زیر عضو شوید.</b>\n"
        "<b>◄ پس از عضویت، روی دکمه‌ی «عضو شدم» کلیک کنید.</b>"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔗 ریپر سلف Reaper Self", url="https://t.me/ReaperSelfChannel")],
        [InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_mention = f"@{query.from_user.username}" if query.from_user.username else query.from_user.first_name
    
    if is_admin(user_id):
        text = (
            f"<b>⫸ درود {user_mention} به پنل ریپر سلف Reaper Self خوش آمدید.</b>\n\n"
            "<b>◄ توی این پنل میتوانید ربات ریپر سلف Reaper Self را کنترل و مدیریت کنید.</b>\n\n"
            "<b>◂ لطفا از منوی زیر انتخاب نمایید که چه کاری را می‌خواهید انتخاب دهید.</b>"
        )
        
        keyboard = [
            [InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings")],
            [InlineKeyboardButton("➕ ساخت کد سلف", callback_data="admin_create_code"), InlineKeyboardButton("❌ باطل کد سلف", callback_data="admin_cancel_code")],
            [InlineKeyboardButton("🚫 مسدود کردن کاربر", callback_data="admin_block_user"), InlineKeyboardButton("✅ آزاد کردن کاربر", callback_data="admin_unblock_user")],
            [InlineKeyboardButton("📤 انتقال اعتبار", callback_data="admin_transfer_credit"), InlineKeyboardButton("📉 کسر اعتبار", callback_data="admin_deduct_credit")],
            [InlineKeyboardButton("🔑 ورود سلف", callback_data="admin_salf_login"), InlineKeyboardButton("🚪 خروج سلف", callback_data="admin_salf_logout")],
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
            expiry_date = get_expiry_date(user_id)
            has_subscription = has_active_subscription(user_id)
            
            session_data = get_user_session(user_id)
            is_logged_in = session_data is not None
            
            text = (
                "<b>⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌</b>\n"
                f"<b>⫸ سلام {user_mention} به ربات ریپر سلف Reaper Self خوش آمدید !</b>\n\n"
                "<b>◄ توی این ربات میتوانید از پشتیبانی ، خرید ، نصب ربات سلف بهره ببرید !</b>\n\n"
                "<b>◂ لطفا اگر سوالی دارید از بخش پشتیبانی ، با پشتیبان ها در ارتباط باشید !</b>\n"
                f"<b>📅 انقضا شما : ( {remaining_days} روز )</b>\n"
                f"<b>🔑 وضعیت ورود : {'✅ وارد شده' if is_logged_in else '❌ وارد نشده'}</b>\n"
                "<b>⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯   ⁭⁯⁯⁭⁯‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌</b>"
            )
            
            keyboard = []
            keyboard.append([InlineKeyboardButton("👨‍💻 پشتیبانی", callback_data="support")])
            keyboard.append([InlineKeyboardButton("🤔 سلف چیست ؟", callback_data="what_is_self"), InlineKeyboardButton("📣 کانال ما", url="https://t.me/ReaperSelfChannel")])
            keyboard.append([InlineKeyboardButton(f"📅 انقضا شما : ( {remaining_days} روز )", callback_data="expiry")])
            keyboard.append([InlineKeyboardButton("✔️ احراز هویت", callback_data="verify"), InlineKeyboardButton("💳 خرید اشتراک", callback_data="buy_subscription")])
            keyboard.append([InlineKeyboardButton("💶 خرید با کد", callback_data="buy_with_code")])
            
            if has_subscription:
                keyboard.append([InlineKeyboardButton("🔑 ورود سلف", callback_data="salf_login")])
            
            keyboard.append([InlineKeyboardButton("💎 نرخ", callback_data="rate")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        else:
            text = (
                "<b>⫸ شما هنوز عضو کانال زیر نشده اید !</b>\n"
                "<b>◄ ابتدا برای استفاده از ربات در کانال زیر عضو شوید !</b>"
            )
            
            keyboard = [
                [InlineKeyboardButton("🔗 ریپر سلف Reaper Self", url="https://t.me/ReaperSelfChannel")],
                [InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
    except Exception as e:
        await query.answer("❌ خطا در بررسی عضویت!", show_alert=True)

# ==================== بخش ادمین ====================

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    codes = load_codes()
    total_codes = len(codes)
    used_codes = sum(1 for c in codes.values() if c.get('used', False))
    sessions = load_sessions()
    
    text = (
        "<b>📊 آمار کل</b>\n\n"
        f"<b>🔢 تعداد کل کدها : {total_codes}</b>\n"
        f"<b>✅ کدهای استفاده شده : {used_codes}</b>\n"
        f"<b>❌ کدهای استفاده نشده : {total_codes - used_codes}</b>\n"
        f"<b>👥 تعداد سشن‌های ذخیره شده : {len(sessions)}</b>\n"
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
            "<b>⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌</b>\n"
            "<b>⫸ به بخشه بررسی پینگ ربات ریپر سلف Reaper Self خوش آمدید.</b>\n\n"
            "<b>◄ توی این بخش میتوانید پینگ واقعی رباتتان را بررسی نمایید.</b>\n\n"
            "<b>◂ لطفا از منوی زیر انتخاب نمایید.</b>\n\n"
            "<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
            f"<b>📡 وضعیت هاست : {server_info['status']}</b>\n"
            f"<b>⚡ پینگ : {server_info['ping']}</b>\n"
            f"<b>💻 سی‌پی‌یو : {server_info['cpu']}</b>\n"
            f"<b>🧠 رم : {server_info['memory']}</b>\n"
            f"<b>💾 هارد : {server_info['disk']}</b>\n"
            f"<b>🖥️ سیستم‌عامل : {server_info['os']}</b>\n"
            f"<b>⏱️ آپ‌تایم : {server_info['uptime']}</b>\n"
            "<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
            "<b>⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯   ⁭⁯⁯⁭⁯‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌</b>"
        )
    else:
        text = "<b>❌ خطا در دریافت اطلاعات سرور!</b>"
    
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
        "<b>⏳ اطلاعات اعتبار هاست</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>📅 تاریخ شروع : {host_info['start_date']}</b>\n"
        f"<b>📆 تاریخ انقضا : {host_info['expiry_date']}</b>\n"
        f"<b>⏱️ روزهای باقی‌مانده : {host_info['days_left']} روز</b>\n"
        f"<b>📊 وضعیت : {bar} {percent:.1f}%</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
    )
    
    if host_info['days_left'] <= 0:
        text += "\n<b>⚠️ هاست شما منقضی شده است! لطفا تمدید کنید.</b>"
    elif host_info['days_left'] <= 5:
        text += "\n<b>⚠️ هاست شما به زودی منقضی میشود! لطفا تمدید کنید.</b>"
    else:
        text += "\n<b>✅ هاست شما فعال است.</b>"
    
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
    await query.answer("👥 منوی کاربران به زودی اضافه میشود!", show_alert=True)

async def admin_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.answer("⚙️ تنظیمات به زودی اضافه میشود!", show_alert=True)

async def admin_create_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_states[query.from_user.id] = "waiting_for_code_days"
    
    text = (
        "<b>➕ ساخت کد سلف جدید</b>\n\n"
        "<b>◄ لطفا روز انقضا را بفرستید (عدد بین 1 تا 100000):</b>"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def admin_cancel_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_states[query.from_user.id] = "waiting_for_cancel_code"
    
    text = (
        "<b>❌ باطل کردن کد سلف</b>\n\n"
        "<b>◄ لطفا کد سلف مورد نظر برای باطل شدن را وارد کنید:</b>"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]
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
            await update.message.reply_text("<b>❌ عدد باید بین 1 تا 100000 باشد!</b>", parse_mode='HTML')
            return
        
        new_code, expiry_date = create_new_code(days)
        
        text = (
            "<b>✅ کد سلف شما با موفقیت ساخته شد</b>\n\n"
            f"<b>📝 کد سلف شما : <code>{new_code}</code></b>\n\n"
            f"<b>📅 تاریخ انقضا : {expiry_date.strftime('%Y-%m-%d')}</b>\n"
            f"<b>⏱️ مدت اعتبار : {days} روز</b>\n\n"
            "<b>💡 برای کپی کردن روی کد کلیک کنید.</b>"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="admin_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
        del user_states[user_id]
        
    except ValueError:
        await update.message.reply_text("<b>❌ لطفا یک عدد معتبر وارد کنید!</b>", parse_mode='HTML')

async def handle_cancel_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_for_cancel_code":
        return
    
    code = update.message.text.strip().upper()
    codes = load_codes()
    
    if code not in codes:
        await update.message.reply_text("<b>❌ کد وارد شده صحیح نیست!</b>", parse_mode='HTML')
        return
    
    if codes[code].get('used', False):
        await update.message.reply_text("<b>❌ این کد قبلاً استفاده شده و قابل باطل کردن نیست!</b>", parse_mode='HTML')
    else:
        del codes[code]
        save_codes(codes)
        await update.message.reply_text(f"<b>✅ کد <code>{code}</code> با موفقیت باطل شد!</b>", parse_mode='HTML')
    
    del user_states[user_id]

async def admin_block_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.answer("🚫 لطفا آیدی کاربر مورد نظر را وارد کنید!", show_alert=True)

async def admin_unblock_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.answer("✅ لطفا آیدی کاربر مورد نظر را وارد کنید!", show_alert=True)

async def admin_transfer_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.answer("📤 لطفا آیدی کاربر و مقدار اعتبار را وارد کنید!", show_alert=True)

async def admin_deduct_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.answer("📉 لطفا آیدی کاربر و مقدار اعتبار را وارد کنید!", show_alert=True)

async def admin_salf_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.answer("🔑 لطفا کد سلف را وارد کنید!", show_alert=True)

async def admin_salf_logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.answer("🚪 لطفا آیدی سلف مورد نظر را وارد کنید!", show_alert=True)

async def admin_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id in user_states:
        del user_states[query.from_user.id]
    
    user_mention = f"@{query.from_user.username}" if query.from_user.username else query.from_user.first_name
    
    text = (
        f"<b>⫸ درود {user_mention} به پنل ریپر سلف Reaper Self خوش آمدید.</b>\n\n"
        "<b>◄ توی این پنل میتوانید ربات ریپر سلف Reaper Self را کنترل و مدیریت کنید.</b>\n\n"
        "<b>◂ لطفا از منوی زیر انتخاب نمایید که چه کاری را می‌خواهید انتخاب دهید.</b>"
    )
    
    keyboard = [
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings")],
        [InlineKeyboardButton("➕ ساخت کد سلف", callback_data="admin_create_code"), InlineKeyboardButton("❌ باطل کد سلف", callback_data="admin_cancel_code")],
        [InlineKeyboardButton("🚫 مسدود کردن کاربر", callback_data="admin_block_user"), InlineKeyboardButton("✅ آزاد کردن کاربر", callback_data="admin_unblock_user")],
        [InlineKeyboardButton("📤 انتقال اعتبار", callback_data="admin_transfer_credit"), InlineKeyboardButton("📉 کسر اعتبار", callback_data="admin_deduct_credit")],
        [InlineKeyboardButton("🔑 ورود سلف", callback_data="admin_salf_login"), InlineKeyboardButton("🚪 خروج سلف", callback_data="admin_salf_logout")],
        [InlineKeyboardButton("📊 آمار کل", callback_data="admin_stats")],
        [InlineKeyboardButton("📡 بررسی پینگ", callback_data="admin_ping"), InlineKeyboardButton("⏳ اعتبار هاست", callback_data="admin_host")],
        [InlineKeyboardButton("👥 منوی کاربران", callback_data="admin_users_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

# ==================== بخش ورود سلف ====================

async def salf_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
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
        "<b>🔑 ورود به سلف</b>\n\n"
        "<b>◄ لطفا شماره موبایل خود را با کد کشور وارد کنید:</b>\n"
        "<b>مثال : +989123456789</b>\n\n"
        "<b>در صورتی که منصرف شده‌اید دکمه زیر را کلیک کنید.</b>"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
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
            "<b>❌ شماره وارد شده صحیح نیست! لطفا با کد کشور وارد کنید.</b>\n"
            "<b>مثال : +989123456789</b>",
            parse_mode='HTML'
        )
        return
    
    salf_login_data[user_id]['phone'] = phone
    user_states[user_id] = "waiting_salf_api_id"
    
    await update.message.reply_text(
        "<b>🔑 مرحله 2 از 4</b>\n\n"
        "<b>◄ لطفا آیپی عددی (API ID) خود را وارد کنید:</b>\n"
        "<b>⚠️ توجه: API ID باید عددی بین 1 تا 2147483647 باشد.</b>",
        parse_mode='HTML'
    )

async def handle_salf_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_salf_api_id":
        return
    
    text = update.message.text.strip() if update.message.text else ""
    if not text:
        await update.message.reply_text("<b>❌ لطفا یک عدد وارد کنید!</b>", parse_mode='HTML')
        return
    
    try:
        api_id = int(text)
        if api_id > 2147483647:
            await update.message.reply_text(
                "<b>❌ عدد وارد شده خیلی بزرگ است!</b>\n"
                "<b>⚠️ API ID باید عددی بین 1 تا 2147483647 باشد.</b>\n"
                "<b>◄ لطفا دوباره وارد کنید:</b>",
                parse_mode='HTML'
            )
            return
    except:
        await update.message.reply_text("<b>❌ آیپی عددی باید عدد باشد! لطفا دوباره وارد کنید.</b>", parse_mode='HTML')
        return
    
    salf_login_data[user_id]['api_id'] = api_id
    user_states[user_id] = "waiting_salf_api_hash"
    
    await update.message.reply_text(
        "<b>🔑 مرحله 3 از 4</b>\n\n"
        "<b>◄ لطفا آیپی هش (API Hash) خود را وارد کنید:</b>",
        parse_mode='HTML'
    )

async def handle_salf_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_salf_api_hash":
        return
    
    api_hash = update.message.text.strip() if update.message.text else ""
    if not api_hash or len(api_hash) < 20:
        await update.message.reply_text(
            "<b>❌ آیپی هش وارد شده صحیح نیست! لطفا دوباره وارد کنید.</b>",
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
                "<b>🔑 مرحله 4 از 4</b>\n\n"
                "<b>✅ کد تایید به شماره شما ارسال شد.</b>\n"
                "<b>◄ لطفا کد را به این صورت بفرستید: <code>1.2.3.4.5</code></b>",
                parse_mode='HTML'
            )
        else:
            await client.disconnect()
            await update.message.reply_text("<b>❌ این شماره قبلاً در سلف ثبت شده است!</b>", parse_mode='HTML')
            del user_states[user_id]
            del salf_login_data[user_id]
            
    except PhoneNumberInvalidError:
        await update.message.reply_text("<b>❌ شماره وارد شده معتبر نیست!</b>", parse_mode='HTML')
        del user_states[user_id]
        del salf_login_data[user_id]
    except FloodWaitError as e:
        await update.message.reply_text(
            f"<b>⏳ لطفا {e.seconds} ثانیه صبر کنید و دوباره تلاش کنید.</b>",
            parse_mode='HTML'
        )
        del user_states[user_id]
        del salf_login_data[user_id]
    except Exception as e:
        await update.message.reply_text(
            f"<b>❌ خطا در ارسال کد تایید: {str(e)}</b>",
            parse_mode='HTML'
        )
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
            "<b>❌ لطفا کد را به این صورت بفرستید: <code>1.2.3.4.5</code></b>",
            parse_mode='HTML'
        )
        return
    
    try:
        data = salf_login_data[user_id]
        client = data.get('client')
        
        if not client:
            await update.message.reply_text("<b>❌ خطا در اتصال! لطفا دوباره تلاش کنید.</b>", parse_mode='HTML')
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
            
            # ذخیره سشن
            session_string = client.session.save()
            save_user_session(user_id, session_string, data['phone'], data['api_hash'], data['api_id'])
            
            # ====== تنظیم ساعت روی اسم اکانت ======
            try:
                from telethon.tl.functions.account import UpdateProfileRequest
                
                # پاک کردن ساعت قبلی از اسم
                clean_name = re.sub(r'\s*\d{2}:\d{2}$', '', full_name).strip()
                new_name = f"{clean_name} {time_str}".strip()
                
                if new_name != full_name:
                    try:
                        await client(UpdateProfileRequest(first_name=new_name))
                        print(f"✅ ساعت روی اسم اکانت کاربر {user_id} تنظیم شد: {new_name}")
                    except Exception as e:
                        print(f"⚠️ خطا در تنظیم ساعت: {e}")
            except Exception as e:
                print(f"⚠️ خطا در تنظیم ساعت روی اسم: {e}")
            
            await client.disconnect()
            
            # شروع task ساعت برای کاربر (هر دقیقه بروزرسانی)
            await start_clock_task(user_id)
            
            text = (
                "<b>✅ ورود سلف به اکانت شما با موفقیت انجام شد!</b>\n\n"
                f"<b>👤 نام اکانت : {new_name if 'new_name' in locals() else full_name}</b>\n"
                f"<b>📱 شماره : {data['phone']}</b>\n"
                f"<b>🕐 ساعت ورود : {time_str}</b>\n"
                f"<b>📅 تاریخ ورود : {iran_time.strftime('%Y-%m-%d')}</b>\n\n"
                "<b>⏰ ساعت روی اسم اکانت شما فعال شد!</b>"
            )
            
            keyboard = [
                [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
            del user_states[user_id]
            del salf_login_data[user_id]
            return
            
        except PhoneCodeExpiredError:
            await update.message.reply_text(
                "<b>⏳ کد منقضی شده بود، در حال ارسال کد جدید...</b>",
                parse_mode='HTML'
            )
            
            await client.send_code_request(data['phone'])
            
            await update.message.reply_text(
                "<b>✅ کد جدید به شماره شما ارسال شد.</b>\n"
                "<b>◄ لطفا کد را به این صورت بفرستید: <code>1.2.3.4.5</code></b>",
                parse_mode='HTML'
            )
            
            user_states[user_id] = "waiting_salf_code"
            return
            
        except PhoneCodeInvalidError:
            await update.message.reply_text(
                "<b>❌ کد وارد شده صحیح نیست! لطفا دوباره تلاش کنید.</b>\n"
                "<b>◄ لطفا کد را به این صورت بفرستید: <code>1.2.3.4.5</code></b>",
                parse_mode='HTML'
            )
            return
        
    except SessionPasswordNeededError:
        user_states[user_id] = "waiting_salf_password"
        await update.message.reply_text(
            "<b>🔑 این اکانت دو مرحله‌ای فعال است.</b>\n"
            "<b>◄ لطفا پسورد خود را وارد کنید:</b>",
            parse_mode='HTML'
        )
    except Exception as e:
        await update.message.reply_text(
            f"<b>❌ خطا در ورود: {str(e)}</b>",
            parse_mode='HTML'
        )
        del user_states[user_id]
        del salf_login_data[user_id]

async def handle_salf_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_salf_password":
        return
    
    password = update.message.text.strip() if update.message.text else ""
    if not password:
        await update.message.reply_text("<b>❌ لطفا پسورد را وارد کنید!</b>", parse_mode='HTML')
        return
    
    try:
        data = salf_login_data[user_id]
        client = data.get('client')
        
        if not client:
            await update.message.reply_text("<b>❌ خطا در اتصال! لطفا دوباره تلاش کنید.</b>", parse_mode='HTML')
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
        
        # ====== تنظیم ساعت روی اسم اکانت ======
        try:
            from telethon.tl.functions.account import UpdateProfileRequest
            
            clean_name = re.sub(r'\s*\d{2}:\d{2}$', '', full_name).strip()
            new_name = f"{clean_name} {time_str}".strip()
            
            if new_name != full_name:
                try:
                    await client(UpdateProfileRequest(first_name=new_name))
                except Exception as e:
                    print(f"⚠️ خطا در تنظیم ساعت: {e}")
        except:
            pass
        
        await client.disconnect()
        
        await start_clock_task(user_id)
        
        text = (
            "<b>✅ ورود سلف به اکانت شما با موفقیت انجام شد!</b>\n\n"
            f"<b>👤 نام اکانت : {new_name if 'new_name' in locals() else full_name}</b>\n"
            f"<b>📱 شماره : {data['phone']}</b>\n"
            f"<b>🕐 ساعت ورود : {time_str}</b>\n"
            f"<b>📅 تاریخ ورود : {iran_time.strftime('%Y-%m-%d')}</b>\n\n"
            "<b>⏰ ساعت روی اسم اکانت شما فعال شد!</b>"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
        
        del user_states[user_id]
        del salf_login_data[user_id]
        
    except Exception as e:
        await update.message.reply_text(
            f"<b>❌ خطا در ورود با پسورد: {str(e)}</b>",
            parse_mode='HTML'
        )
        del user_states[user_id]
        del salf_login_data[user_id]

# ==================== بخش کاربران ====================

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = (
        "<b>⫸ شما با موفقیت به پشتیبانی متصل شدید !</b>\n"
        "<b>◄ لطفا دقت کنید که توی پشتیبانی اسپم ندهید و از دستورات سلف توی بخش پشتیبانی استفاده نکنید ، اکنون میتوانید پیام خود را ارسال کنید !</b>"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def what_is_self(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = (
        "<b>سلف به رباتی گفته میشه که روی اکانت شما نصب میشه و امکانات خاصی رو در اختیارتون میزاره ، لازم به ذکر هست که نصب شدن بر روی اکانت شما به معنی وارد شدن ربات به اکانت شما هست ( به دلیل دستور گرفتن و انجام فعالیت ها )\n\nاز جمله امکاناتی که در اختیار شما قرار میدهد شامل موارد زیر است :\n\n⫸ گذاشتن ساعت با فونت های مختلف بر روی بیو ، اسم\n⫸ قابلیت تنظیم حالت خوانده شدن خودکار پیام ها\n⫸ تنظیم حالت پاسخ خودکار\n⫸ جواب دادن به شخصی که به شما توهین میکنه\n⫸ پیام انیمیشنی\n⫸ منشی هوشمند\n⫸ دریافت پنل و تنظیمات اکانت هوشمند\n⫸ دو زبانه بودن دستورات و جواب ها\n⫸ تغییر نام و کاور فایل ها\n⫸ اعلان پیام ادیت و حذف شده در پیوی\n⫸ ذخیره پروفایل های جدید و اعلان حذف پروفایل مخاطبین\n\nو امکاناتی دیگر که میتوانید با مراجعه به بخش راهنما آن ها را ببینید و مطالعه کنید !\n\n◄ لازم به ذکر است که امکاناتی که در بالا گفته شده تنها ذره ای از امکانات سلف میباشد .</b>"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def buy_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = (
        "<b>◂ برای خرید باید ابتدا احراز هویت کنید.</b>"
    )
    
    keyboard = [
        [InlineKeyboardButton("✔️ احراز هویت", callback_data="verify")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def buy_with_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_states[query.from_user.id] = "waiting_for_activation_code"
    
    text = (
        "<b>◄ لطفا کد انقضای خریداری شده خود را ارسال کنید :</b>"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def handle_activation_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id] != "waiting_for_activation_code":
        return
    
    code = update.message.text.strip().upper() if update.message.text else ""
    if not code:
        await update.message.reply_text("<b>❌ لطفا کد را وارد کنید!</b>", parse_mode='HTML')
        return
    
    code_data, error = validate_code(code)
    if code_data is None:
        await update.message.reply_text(f"<b>{error}</b>", parse_mode='HTML')
        return
    
    if use_code(code, user_id):
        days = code_data['days']
        remaining_days = get_remaining_days(user_id)
        expiry_date = get_expiry_date(user_id)
        
        text = (
            f"<b>✅ کد با موفقیت فعال شد!</b>\n\n"
            f"<b>📅 {days} روز به اشتراک شما اضافه شد.</b>\n"
            f"<b>📅 تاریخ انقضا : {expiry_date}</b>\n"
            f"<b>⏳ روزهای باقی‌مانده : {remaining_days} روز</b>"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
        del user_states[user_id]
    else:
        await update.message.reply_text("<b>❌ خطا در فعال‌سازی کد!</b>", parse_mode='HTML')

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_mention = f"@{query.from_user.username}" if query.from_user.username else query.from_user.first_name
    
    if user_id in user_states:
        del user_states[user_id]
    if user_id in salf_login_data:
        del salf_login_data[user_id]
    
    if is_admin(user_id):
        text = (
            f"<b>⫸ درود {user_mention} به پنل ریپر سلف Reaper Self خوش آمدید.</b>\n\n"
            "<b>◄ توی این پنل میتوانید ربات ریپر سلف Reaper Self را کنترل و مدیریت کنید.</b>\n\n"
            "<b>◂ لطفا از منوی زیر انتخاب نمایید که چه کاری را می‌خواهید انتخاب دهید.</b>"
        )
        
        keyboard = [
            [InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings")],
            [InlineKeyboardButton("➕ ساخت کد سلف", callback_data="admin_create_code"), InlineKeyboardButton("❌ باطل کد سلف", callback_data="admin_cancel_code")],
            [InlineKeyboardButton("🚫 مسدود کردن کاربر", callback_data="admin_block_user"), InlineKeyboardButton("✅ آزاد کردن کاربر", callback_data="admin_unblock_user")],
            [InlineKeyboardButton("📤 انتقال اعتبار", callback_data="admin_transfer_credit"), InlineKeyboardButton("📉 کسر اعتبار", callback_data="admin_deduct_credit")],
            [InlineKeyboardButton("🔑 ورود سلف", callback_data="admin_salf_login"), InlineKeyboardButton("🚪 خروج سلف", callback_data="admin_salf_logout")],
            [InlineKeyboardButton("📊 آمار کل", callback_data="admin_stats")],
            [InlineKeyboardButton("📡 بررسی پینگ", callback_data="admin_ping"), InlineKeyboardButton("⏳ اعتبار هاست", callback_data="admin_host")],
            [InlineKeyboardButton("👥 منوی کاربران", callback_data="admin_users_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        return
    
    remaining_days = get_remaining_days(user_id)
    expiry_date = get_expiry_date(user_id)
    has_subscription = has_active_subscription(user_id)
    
    session_data = get_user_session(user_id)
    is_logged_in = session_data is not None
    
    text = (
        "<b>⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌</b>\n"
        f"<b>⫸ سلام {user_mention} به ربات ریپر سلف Reaper Self خوش آمدید !</b>\n\n"
        "<b>◄ توی این ربات میتوانید از پشتیبانی ، خرید ، نصب ربات سلف بهره ببرید !</b>\n\n"
        "<b>◂ لطفا اگر سوالی دارید از بخش پشتیبانی ، با پشتیبان ها در ارتباط باشید !</b>\n"
        f"<b>📅 انقضا شما : ( {remaining_days} روز )</b>\n"
        f"<b>🔑 وضعیت ورود : {'✅ وارد شده' if is_logged_in else '❌ وارد نشده'}</b>\n"
        "<b>⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯   ⁭⁯⁯⁭⁯‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌</b>"
    )
    
    keyboard = []
    keyboard.append([InlineKeyboardButton("👨‍💻 پشتیبانی", callback_data="support")])
    keyboard.append([InlineKeyboardButton("🤔 سلف چیست ؟", callback_data="what_is_self"), InlineKeyboardButton("📣 کانال ما", url="https://t.me/ReaperSelfChannel")])
    keyboard.append([InlineKeyboardButton(f"📅 انقضا شما : ( {remaining_days} روز )", callback_data="expiry")])
    keyboard.append([InlineKeyboardButton("✔️ احراز هویت", callback_data="verify"), InlineKeyboardButton("💳 خرید اشتراک", callback_data="buy_subscription")])
    keyboard.append([InlineKeyboardButton("💶 خرید با کد", callback_data="buy_with_code")])
    
    if has_subscription:
        keyboard.append([InlineKeyboardButton("🔑 ورود سلف", callback_data="salf_login")])
    
    keyboard.append([InlineKeyboardButton("💎 نرخ", callback_data="rate")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = (
        "<b>⫸ نرخ سلف عبارت است از :</b>\n\n"
        "<b>◄ ماهانه : 100,000 هزار تومان</b>\n\n"
        "<b>◄ دو ماهه : 150,000 هزار تومان</b>\n\n"
        "<b>◄ سه ماهه : 200,000 هزار تومان</b>\n\n"
        "<b>◄ چهار ماهه : 250,000 هزار تومان</b>\n\n"
        "<b>◄ پنج ماهه : 300,000 هزار تومان</b>\n\n"
        "<b>◄ شش ماهه : 350,000 هزار تومان</b>\n\n"
        "<b>(⚠️) توجه داشته باشید سلف فقط بر روی اکانت هایی که با شماره ایران هستند نصب میشود و اما در صورت نصب روی شماره های مجازی مسئولیت دیلیت شدن اکانت به عهده خودتان خواهد بود.</b>\n\n"
        "<b>֍ @ReaperSelfChannel</b>"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def expiry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    remaining_days = get_remaining_days(user_id)
    expiry_date = get_expiry_date(user_id)
    
    if remaining_days > 0:
        await query.answer(f"📅 انقضا شما : {expiry_date} ( {remaining_days} روز باقی مانده )", show_alert=True)
    else:
        await query.answer("⏳ اشتراک شما فعال نمیباشد!", show_alert=True)

async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = (
        "<b>◄ به منوی احراز هویت خوش آمدید ، لطفا انتخاب کنید :</b>"
    )
    
    keyboard = [
        [InlineKeyboardButton("❌ حذف کارت", callback_data="delete_card"), InlineKeyboardButton("➕ کارت جدید", callback_data="new_card")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def delete_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.answer("❌ کارت شما با موفقیت حذف شد!", show_alert=True)

async def new_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_states[query.from_user.id] = "waiting_for_photo"
    
    text = (
        "<b>به بخش احراز هویت خوش آمدید.\n\nنکات :\n1) شماره کارت و نام صاحب کارت کاملا مشخص باشد.\n2) لطفا تاریخ اعتبار و Cvv2 کارت خود را بپوشانید!\n3) فقط با کارتی که احراز هویت میکنید میتوانید خرید انجام بدید و اگر با کارت دیگری اقدام کنید تراکنش ناموفق میشود و هزینه از سمت خودِ بانک به شما بازگشت داده میشود.\n4) در صورتی که توانایی ارسال عکس از کارت را ندارید تنها راه حل ارسال عکس از کارت ملی یا شناسنامه صاحب کارت است.\n\nلطفا عکس از کارتی که میخواهید با آن خرید انجام دهید ارسال کنید.</b>"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_verify")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def back_to_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id in user_states:
        del user_states[query.from_user.id]
    
    text = (
        "<b>◄ به منوی احراز هویت خوش آمدید ، لطفا انتخاب کنید :</b>"
    )
    
    keyboard = [
        [InlineKeyboardButton("❌ حذف کارت", callback_data="delete_card"), InlineKeyboardButton("➕ کارت جدید", callback_data="new_card")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

# ==================== هندلرهای پیام ====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id in user_states:
        state = user_states[user_id]
        
        if state == "waiting_for_photo":
            if update.message.photo:
                user_states[user_id] = "waiting_for_card_number"
                await update.message.reply_text(
                    "<b>◄ لطفا شماره کارت خود را به صورت اعداد انگلیسی ارسال کنید\nدر صورتی که منصرف شدید ربات را مجدد استارت کنید : [ /start ]</b>",
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text("<b>❌ لطفا فقط عکس ارسال کنید!</b>", parse_mode='HTML')
            return
        
        elif state == "waiting_for_card_number":
            text = update.message.text.strip() if update.message.text else ""
            card_number = ''.join(filter(str.isdigit, text))
            
            if len(card_number) == 16 and card_number.isdigit():
                await update.message.reply_text(
                    "<b>درخواست احراز هویت شما برای پشتیبانی ارسال شد و در اولین فرصت تایید خواهد شد ، لطفا صبور باشید.\n\nلطفا برای تایید کارت به پشتیبانی پیام ارسال نفرمایید و درخواست احرازهویتتون رو اسپم نکنید ، در صورت مشاهده این کار یک روز با تاخیر تایید میشود.</b>",
                    parse_mode='HTML'
                )
                del user_states[user_id]
            else:
                await update.message.reply_text(
                    "<b>شماره کارت 16 رقمی است.\nلطفا شماره کارت خود را بدون هیچ کاراکتر اضافه ای وارد کنید</b>",
                    parse_mode='HTML'
                )
            return
        
        elif state == "waiting_for_code_days":
            await handle_code_days(update, context)
            return
        
        elif state == "waiting_for_cancel_code":
            await handle_cancel_code(update, context)
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

# ==================== خرید ماه‌ها ====================

async def buy_1_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.answer("💳 لطفا مبلغ 3 ترون را واریز کنید!", show_alert=True)

async def buy_2_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.answer("💳 لطفا مبلغ 6 ترون را واریز کنید!", show_alert=True)

async def buy_3_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.answer("💳 لطفا مبلغ 9 ترون را واریز کنید!", show_alert=True)

async def buy_4_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.answer("💳 لطفا مبلغ 13 ترون را واریز کنید!", show_alert=True)

async def buy_5_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.answer("💳 لطفا مبلغ 16 ترون را واریز کنید!", show_alert=True)

async def buy_6_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.answer("💳 لطفا مبلغ 19 ترون را واریز کنید!", show_alert=True)

# ==================== Main ====================

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_membership, pattern="check_membership"))
    
    # ادمین
    app.add_handler(CallbackQueryHandler(admin_stats, pattern="admin_stats"))
    app.add_handler(CallbackQueryHandler(admin_ping, pattern="admin_ping"))
    app.add_handler(CallbackQueryHandler(admin_host, pattern="admin_host"))
    app.add_handler(CallbackQueryHandler(admin_users_menu, pattern="admin_users_menu"))
    app.add_handler(CallbackQueryHandler(admin_settings, pattern="admin_settings"))
    app.add_handler(CallbackQueryHandler(admin_create_code, pattern="admin_create_code"))
    app.add_handler(CallbackQueryHandler(admin_cancel_code, pattern="admin_cancel_code"))
    app.add_handler(CallbackQueryHandler(admin_block_user, pattern="admin_block_user"))
    app.add_handler(CallbackQueryHandler(admin_unblock_user, pattern="admin_unblock_user"))
    app.add_handler(CallbackQueryHandler(admin_transfer_credit, pattern="admin_transfer_credit"))
    app.add_handler(CallbackQueryHandler(admin_deduct_credit, pattern="admin_deduct_credit"))
    app.add_handler(CallbackQueryHandler(admin_salf_login, pattern="admin_salf_login"))
    app.add_handler(CallbackQueryHandler(admin_salf_logout, pattern="admin_salf_logout"))
    app.add_handler(CallbackQueryHandler(admin_back, pattern="admin_back"))
    
    # کاربران
    app.add_handler(CallbackQueryHandler(support, pattern="support"))
    app.add_handler(CallbackQueryHandler(what_is_self, pattern="what_is_self"))
    app.add_handler(CallbackQueryHandler(buy_subscription, pattern="buy_subscription"))
    app.add_handler(CallbackQueryHandler(buy_with_code, pattern="buy_with_code"))
    app.add_handler(CallbackQueryHandler(salf_login, pattern="salf_login"))
    app.add_handler(CallbackQueryHandler(main_menu, pattern="main_menu"))
    app.add_handler(CallbackQueryHandler(rate, pattern="rate"))
    app.add_handler(CallbackQueryHandler(expiry, pattern="expiry"))
    app.add_handler(CallbackQueryHandler(verify, pattern="verify"))
    app.add_handler(CallbackQueryHandler(delete_card, pattern="delete_card"))
    app.add_handler(CallbackQueryHandler(new_card, pattern="new_card"))
    app.add_handler(CallbackQueryHandler(back_to_verify, pattern="back_to_verify"))
    app.add_handler(CallbackQueryHandler(buy_1_month, pattern="buy_1_month"))
    app.add_handler(CallbackQueryHandler(buy_2_month, pattern="buy_2_month"))
    app.add_handler(CallbackQueryHandler(buy_3_month, pattern="buy_3_month"))
    app.add_handler(CallbackQueryHandler(buy_4_month, pattern="buy_4_month"))
    app.add_handler(CallbackQueryHandler(buy_5_month, pattern="buy_5_month"))
    app.add_handler(CallbackQueryHandler(buy_6_month, pattern="buy_6_month"))
    
    app.add_handler(MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 ربات در حال اجراست...")
    app.run_polling()

if __name__ == "__main__":
    main()
