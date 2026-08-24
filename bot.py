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
from datetime import datetime, timedelta

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
from telethon.tl.types import KeyboardButtonCallback

TOKEN = "8961040480:AAHNKEnK7LZuCp9fSJ5td2_XdGFqPtwp_dY"
CHANNEL_USERNAME = "@rayan_self"
CHANNEL_ID = -1002637412436
ADMIN_IDS = [7795617350]

DB_FILE = "bot_database.db"

# ==================== DATABASE ====================

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
            request_date TEXT,
            admin_response TEXT,
            response_date TEXT
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
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS self_settings (
            user_id INTEGER PRIMARY KEY,
            clock_enabled INTEGER DEFAULT 0,
            auto_read INTEGER DEFAULT 0,
            auto_reply INTEGER DEFAULT 0,
            anti_insult INTEGER DEFAULT 0,
            animated_msg INTEGER DEFAULT 0,
            smart_secretary INTEGER DEFAULT 0,
            bio INTEGER DEFAULT 0,
            name_setting INTEGER DEFAULT 0,
            analytics INTEGER DEFAULT 0,
            about INTEGER DEFAULT 0,
            title INTEGER DEFAULT 0,
            anti_login INTEGER DEFAULT 0,
            auto_setting INTEGER DEFAULT 0,
            banner INTEGER DEFAULT 0,
            comment INTEGER DEFAULT 0,
            birthday INTEGER DEFAULT 0,
            alert INTEGER DEFAULT 0,
            classic INTEGER DEFAULT 1,
            modern INTEGER DEFAULT 0,
            persian INTEGER DEFAULT 1,
            english INTEGER DEFAULT 0,
            region INTEGER DEFAULT 1,
            public_self INTEGER DEFAULT 0
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

# ==================== DATABASE FUNCTIONS ====================

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

def db_update_verify_request(request_id, status, admin_response=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    if admin_response:
        cursor.execute('''
            UPDATE verify_requests 
            SET status = ?, admin_response = ?, response_date = ? 
            WHERE id = ?
        ''', (status, admin_response, datetime.now().isoformat(), request_id))
    else:
        cursor.execute('''
            UPDATE verify_requests 
            SET status = ?, response_date = ? 
            WHERE id = ?
        ''', (status, datetime.now().isoformat(), request_id))
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

def db_update_support_ticket(ticket_id, status, admin_response=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    if admin_response:
        cursor.execute('''
            UPDATE support_tickets 
            SET status = ?, admin_response = ?, response_date = ? 
            WHERE id = ?
        ''', (status, admin_response, datetime.now().isoformat(), ticket_id))
    else:
        cursor.execute('''
            UPDATE support_tickets 
            SET status = ?, response_date = ? 
            WHERE id = ?
        ''', (status, datetime.now().isoformat(), ticket_id))
    conn.commit()
    conn.close()

def db_get_self_settings(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM self_settings WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            'clock_enabled': result[1] == 1,
            'auto_read': result[2] == 1,
            'auto_reply': result[3] == 1,
            'anti_insult': result[4] == 1,
            'animated_msg': result[5] == 1,
            'smart_secretary': result[6] == 1,
            'bio': result[7] == 1,
            'name_setting': result[8] == 1,
            'analytics': result[9] == 1,
            'about': result[10] == 1,
            'title': result[11] == 1,
            'anti_login': result[12] == 1,
            'auto_setting': result[13] == 1,
            'banner': result[14] == 1,
            'comment': result[15] == 1,
            'birthday': result[16] == 1,
            'alert': result[17] == 1,
            'classic': result[18] == 1,
            'modern': result[19] == 1,
            'persian': result[20] == 1,
            'english': result[21] == 1,
            'region': result[22] == 1,
            'public_self': result[23] == 1
        }
    return {
        'clock_enabled': False,
        'auto_read': False,
        'auto_reply': False,
        'anti_insult': False,
        'animated_msg': False,
        'smart_secretary': False,
        'bio': False,
        'name_setting': False,
        'analytics': False,
        'about': False,
        'title': False,
        'anti_login': False,
        'auto_setting': False,
        'banner': False,
        'comment': False,
        'birthday': False,
        'alert': False,
        'classic': True,
        'modern': False,
        'persian': True,
        'english': False,
        'region': True,
        'public_self': False
    }

def db_update_self_settings(user_id, settings):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO self_settings 
        (user_id, clock_enabled, auto_read, auto_reply, anti_insult, animated_msg, smart_secretary,
         bio, name_setting, analytics, about, title, anti_login, auto_setting, banner, comment,
         birthday, alert, classic, modern, persian, english, region, public_self)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        1 if settings.get('clock_enabled', False) else 0,
        1 if settings.get('auto_read', False) else 0,
        1 if settings.get('auto_reply', False) else 0,
        1 if settings.get('anti_insult', False) else 0,
        1 if settings.get('animated_msg', False) else 0,
        1 if settings.get('smart_secretary', False) else 0,
        1 if settings.get('bio', False) else 0,
        1 if settings.get('name_setting', False) else 0,
        1 if settings.get('analytics', False) else 0,
        1 if settings.get('about', False) else 0,
        1 if settings.get('title', False) else 0,
        1 if settings.get('anti_login', False) else 0,
        1 if settings.get('auto_setting', False) else 0,
        1 if settings.get('banner', False) else 0,
        1 if settings.get('comment', False) else 0,
        1 if settings.get('birthday', False) else 0,
        1 if settings.get('alert', False) else 0,
        1 if settings.get('classic', True) else 0,
        1 if settings.get('modern', False) else 0,
        1 if settings.get('persian', True) else 0,
        1 if settings.get('english', False) else 0,
        1 if settings.get('region', True) else 0,
        1 if settings.get('public_self', False) else 0
    ))
    conn.commit()
    conn.close()

# ==================== HELPER FUNCTIONS ====================

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

# ==================== SELF PANEL ====================

def build_panel_text(settings):
    text = "**⚡ لطفا یکی از گزینه‌های زیر را انتخاب نمایید:**\n\n"
    
    text += "**━━━━━━━━━━━━━━━━━━━━**\n"
    text += f"**🖥️ کلاسیک:** {'✅' if settings.get('classic', True) else '❌'}\n"
    text += f"**🖥️ مدرن:** {'✅' if settings.get('modern', False) else '❌'}\n"
    text += f"**🌍 فارسی:** {'✅' if settings.get('persian', True) else '❌'}\n"
    text += f"**🌍 انگلیسی:** {'✅' if settings.get('english', False) else '❌'}\n"
    text += f"**🗺️ منطقه:** {'✅' if settings.get('region', True) else '❌'}\n"
    text += f"**🌐 سلف همگانی:** {'✅' if settings.get('public_self', False) else '❌'}\n\n"
    
    text += "**━━━━━━━━━━━━━━━━━━━━**\n"
    text += f"**📝 بیوگرافی:** {'✅' if settings.get('bio', False) else '❌'}\n"
    text += f"**📛 اسم:** {'✅' if settings.get('name_setting', False) else '❌'}\n"
    text += f"**📊 آنالیتی:** {'✅' if settings.get('analytics', False) else '❌'}\n"
    text += f"**ℹ️ درباره:** {'✅' if settings.get('about', False) else '❌'}\n"
    text += f"**📌 عنوان:** {'✅' if settings.get('title', False) else '❌'}\n"
    text += f"**🔒 آنتی لاگین:** {'✅' if settings.get('anti_login', False) else '❌'}\n\n"
    
    text += "**━━━━━━━━━━━━━━━━━━━━**\n"
    text += f"**⏰ ساعت:** {'✅' if settings.get('clock_enabled', False) else '❌'}\n"
    text += f"**👁️ خودخوان:** {'✅' if settings.get('auto_read', False) else '❌'}\n"
    text += f"**🤖 پاسخ خودکار:** {'✅' if settings.get('auto_reply', False) else '❌'}\n"
    text += f"**🛡️ ضد توهین:** {'✅' if settings.get('anti_insult', False) else '❌'}\n"
    text += f"**🎬 پیام انیمیشنی:** {'✅' if settings.get('animated_msg', False) else '❌'}\n"
    text += f"**🧠 منشی هوشمند:** {'✅' if settings.get('smart_secretary', False) else '❌'}\n"
    text += f"**🤖 خودکار:** {'✅' if settings.get('auto_setting', False) else '❌'}\n"
    text += f"**🖼️ بنر:** {'✅' if settings.get('banner', False) else '❌'}\n"
    text += f"**💬 کامنت:** {'✅' if settings.get('comment', False) else '❌'}\n"
    text += f"**🎂 تولد:** {'✅' if settings.get('birthday', False) else '❌'}\n"
    text += f"**🔔 هشدار:** {'✅' if settings.get('alert', False) else '❌'}\n"
    
    return text

def build_panel_buttons(settings, user_id):
    buttons = []
    
    row = [
        KeyboardButtonCallback(
            text=f"🖥️ کلاسیک {'✅' if settings.get('classic', True) else '❌'}",
            data=f"self_toggle_classic_{user_id}".encode()
        ),
        KeyboardButtonCallback(
            text=f"🖥️ مدرن {'✅' if settings.get('modern', False) else '❌'}",
            data=f"self_toggle_modern_{user_id}".encode()
        )
    ]
    buttons.append(row)
    
    row = [
        KeyboardButtonCallback(
            text=f"🌍 فارسی {'✅' if settings.get('persian', True) else '❌'}",
            data=f"self_toggle_persian_{user_id}".encode()
        ),
        KeyboardButtonCallback(
            text=f"🌍 انگلیسی {'✅' if settings.get('english', False) else '❌'}",
            data=f"self_toggle_english_{user_id}".encode()
        )
    ]
    buttons.append(row)
    
    row = [
        KeyboardButtonCallback(
            text=f"🗺️ منطقه {'✅' if settings.get('region', True) else '❌'}",
            data=f"self_toggle_region_{user_id}".encode()
        ),
        KeyboardButtonCallback(
            text=f"🌐 سلف همگانی {'✅' if settings.get('public_self', False) else '❌'}",
            data=f"self_toggle_public_self_{user_id}".encode()
        )
    ]
    buttons.append(row)
    
    row = [
        KeyboardButtonCallback(
            text=f"📝 بیوگرافی {'✅' if settings.get('bio', False) else '❌'}",
            data=f"self_toggle_bio_{user_id}".encode()
        ),
        KeyboardButtonCallback(
            text=f"📛 اسم {'✅' if settings.get('name_setting', False) else '❌'}",
            data=f"self_toggle_name_{user_id}".encode()
        )
    ]
    buttons.append(row)
    
    row = [
        KeyboardButtonCallback(
            text=f"📊 آنالیتی {'✅' if settings.get('analytics', False) else '❌'}",
            data=f"self_toggle_analytics_{user_id}".encode()
        ),
        KeyboardButtonCallback(
            text=f"ℹ️ درباره {'✅' if settings.get('about', False) else '❌'}",
            data=f"self_toggle_about_{user_id}".encode()
        )
    ]
    buttons.append(row)
    
    row = [
        KeyboardButtonCallback(
            text=f"📌 عنوان {'✅' if settings.get('title', False) else '❌'}",
            data=f"self_toggle_title_{user_id}".encode()
        ),
        KeyboardButtonCallback(
            text=f"🔒 آنتی لاگین {'✅' if settings.get('anti_login', False) else '❌'}",
            data=f"self_toggle_anti_login_{user_id}".encode()
        )
    ]
    buttons.append(row)
    
    row = [
        KeyboardButtonCallback(
            text=f"⏰ ساعت {'✅' if settings.get('clock_enabled', False) else '❌'}",
            data=f"self_toggle_clock_{user_id}".encode()
        ),
        KeyboardButtonCallback(
            text=f"👁️ خودخوان {'✅' if settings.get('auto_read', False) else '❌'}",
            data=f"self_toggle_auto_read_{user_id}".encode()
        )
    ]
    buttons.append(row)
    
    row = [
        KeyboardButtonCallback(
            text=f"🤖 پاسخ خودکار {'✅' if settings.get('auto_reply', False) else '❌'}",
            data=f"self_toggle_auto_reply_{user_id}".encode()
        ),
        KeyboardButtonCallback(
            text=f"🛡️ ضد توهین {'✅' if settings.get('anti_insult', False) else '❌'}",
            data=f"self_toggle_anti_insult_{user_id}".encode()
        )
    ]
    buttons.append(row)
    
    row = [
        KeyboardButtonCallback(
            text=f"🎬 پیام انیمیشنی {'✅' if settings.get('animated_msg', False) else '❌'}",
            data=f"self_toggle_animated_msg_{user_id}".encode()
        ),
        KeyboardButtonCallback(
            text=f"🧠 منشی هوشمند {'✅' if settings.get('smart_secretary', False) else '❌'}",
            data=f"self_toggle_smart_secretary_{user_id}".encode()
        )
    ]
    buttons.append(row)
    
    row = [
        KeyboardButtonCallback(
            text=f"🤖 خودکار {'✅' if settings.get('auto_setting', False) else '❌'}",
            data=f"self_toggle_auto_{user_id}".encode()
        ),
        KeyboardButtonCallback(
            text=f"🖼️ بنر {'✅' if settings.get('banner', False) else '❌'}",
            data=f"self_toggle_banner_{user_id}".encode()
        )
    ]
    buttons.append(row)
    
    row = [
        KeyboardButtonCallback(
            text=f"💬 کامنت {'✅' if settings.get('comment', False) else '❌'}",
            data=f"self_toggle_comment_{user_id}".encode()
        ),
        KeyboardButtonCallback(
            text=f"🎂 تولد {'✅' if settings.get('birthday', False) else '❌'}",
            data=f"self_toggle_birthday_{user_id}".encode()
        )
    ]
    buttons.append(row)
    
    row = [
        KeyboardButtonCallback(
            text=f"🔔 هشدار {'✅' if settings.get('alert', False) else '❌'}",
            data=f"self_toggle_alert_{user_id}".encode()
        )
    ]
    buttons.append(row)
    
    row = [
        KeyboardButtonCallback(
            text="🔄 بروزرسانی",
            data=f"self_refresh_{user_id}".encode()
        ),
        KeyboardButtonCallback(
            text="❌ بستن پنل",
            data=f"self_close_{user_id}".encode()
        )
    ]
    buttons.append(row)
    
    return buttons

async def send_self_panel(client, user_id, chat_id, message_id=None):
    try:
        settings = db_get_self_settings(user_id)
        
        panel_text = build_panel_text(settings)
        buttons = build_panel_buttons(settings, user_id)
        
        if message_id:
            try:
                await client.edit_message(
                    chat_id,
                    message_id,
                    panel_text,
                    buttons=buttons,
                    parse_mode='markdown'
                )
                return message_id
            except:
                pass
        
        sent_msg = await client.send_message(
            chat_id,
            panel_text,
            buttons=buttons,
            parse_mode='markdown'
        )
        
        return sent_msg.id
        
    except Exception as e:
        print(f"خطا در ارسال پنل: {e}")
        return None

async def show_self_panel(client, event):
    try:
        user_id = event.sender_id
        
        if not has_active_subscription(user_id):
            await client.send_message(
                event.message.peer_id,
                "**❌ شما اشتراک فعال ندارید!**\n**💳 لطفا اشتراک خریداری کنید.**",
                parse_mode='markdown'
            )
            return
        
        try:
            await client.delete_messages(event.message.peer_id, [event.message.id])
        except:
            pass
        
        await send_self_panel(client, user_id, event.message.peer_id)
        
    except Exception as e:
        print(f"خطا در نمایش پنل: {e}")

async def handle_self_callback(event, client):
    try:
        data = event.data.decode('utf-8')
        parts = data.split('_')
        
        if len(parts) < 3:
            return
        
        action = parts[1]
        user_id = int(parts[2])
        
        settings = db_get_self_settings(user_id)
        
        toggle_map = {
            'clock': 'clock_enabled',
            'auto_read': 'auto_read',
            'auto_reply': 'auto_reply',
            'anti_insult': 'anti_insult',
            'animated_msg': 'animated_msg',
            'smart_secretary': 'smart_secretary',
            'bio': 'bio',
            'name': 'name_setting',
            'analytics': 'analytics',
            'about': 'about',
            'title': 'title',
            'anti_login': 'anti_login',
            'auto': 'auto_setting',
            'banner': 'banner',
            'comment': 'comment',
            'birthday': 'birthday',
            'alert': 'alert',
            'classic': 'classic',
            'modern': 'modern',
            'persian': 'persian',
            'english': 'english',
            'region': 'region',
            'public_self': 'public_self'
        }
        
        if action in toggle_map:
            key = toggle_map[action]
            settings[key] = not settings.get(key, False)
            
            if key == 'classic' and settings['classic']:
                settings['modern'] = False
            elif key == 'modern' and settings['modern']:
                settings['classic'] = False
            
            if key == 'persian' and settings['persian']:
                settings['english'] = False
            elif key == 'english' and settings['english']:
                settings['persian'] = False
            
            db_update_self_settings(user_id, settings)
            
            if key == 'clock_enabled':
                set_clock_status(user_id, settings['clock_enabled'])
                if settings['clock_enabled']:
                    await set_clock_on_profile(user_id)
                else:
                    await remove_clock_from_profile(user_id)
            
            chat_id = event.chat_id
            message_id = event.message_id
            
            await send_self_panel(client, user_id, chat_id, message_id)
            
            await event.answer("✅ تغییرات اعمال شد!")
            return
        
        if action == 'refresh':
            chat_id = event.chat_id
            message_id = event.message_id
            await send_self_panel(client, user_id, chat_id, message_id)
            await event.answer("🔄 پنل بروزرسانی شد!")
            return
        
        if action == 'close':
            try:
                await client.delete_messages(event.chat_id, [event.message_id])
            except:
                pass
            await event.answer("❌ پنل بسته شد!")
            return
        
    except Exception as e:
        print(f"خطا در هندلر کالبک سلف: {e}")
        try:
            await event.answer("❌ خطا!")
        except:
            pass

# ==================== SELF CLIENTS ====================

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
            except SessionPasswordNeededError:
                for admin_id in ADMIN_IDS:
                    try:
                        await client.send_message(
                            admin_id,
                            "⚠️ اکانت کاربر دارای سیستم تایید دو مرحله‌ای (2FA) است.\n🗝 لطفاً رمز عبور اختصاصی را وارد کنید:"
                        )
                    except:
                        pass
                return False
            except:
                await client.disconnect()
                return False
        
        salf_clients[user_id] = client
        
        @client.on(events.MessageEdited)
        @client.on(events.NewMessage)
        async def panel_handler(event):
            if event.sender_id == user_id:
                if event.message and event.message.text:
                    if event.message.text.strip() == "پنل":
                        await show_self_panel(client, event)
        
        @client.on(events.CallbackQuery)
        async def callback_handler(event):
            await handle_self_callback(event, client)
        
        await client.run_until_disconnected()
        return True
        
    except Exception as e:
        print(f"خطا در شروع سلف کاربر {user_id}: {e}")
        return False

async def start_all_salf_clients():
    sessions = db_get_all_sessions()
    for session in sessions:
        user_id = session[0]
        asyncio.create_task(start_salf_client(user_id))

# ==================== CLOCK FUNCTIONS ====================

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

# ==================== SERVER INFO ====================

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

# ==================== BOT COMMANDS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = update.effective_user
    db_add_user(user_id, user.username, user.first_name, user.last_name)
    if is_user_banned(user_id):
        await update.message.reply_text(
            "<b>🚫 شما از طرف مدیریت مسدود شده اید!</b>\n<b>💠 در صورت نیاز با پشتیبانی تماس بگیرید.</b>",
            parse_mode='HTML'
        )
        return
    
    is_verified = is_user_verified(user_id)
    
    user_mention = f"@{user.username}" if user.username else user.first_name
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_menu_mode:
        del user_menu_mode[user_id]
    if is_admin(user_id):
        text = (
            f"<b>⚡ درود {user_mention} به پنل ریپر سلف خوش آمدید.</b>\n\n"
            "<b>🛠️ در این پنل میتوانید ربات را کنترل و مدیریت کنید.</b>\n\n"
            "<b>🔄 لطفا از منوی زیر انتخاب نمایید.</b>"
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
            session_data = get_user_session(user_id)
            is_logged_in = session_data is not None
            expiry_date = get_expiry_date(user_id)
            text = (
                f"<b>⚡ سلام {user_mention} به ربات ریپر سلف خوش آمدید!</b>\n\n"
                "<b>🎯 در این ربات میتوانید از پشتیبانی، خرید، نصب ربات سلف بهره ببرید!</b>\n\n"
                "<b>💠 اگر سوالی دارید از بخش پشتیبانی استفاده کنید.</b>"
            )
            keyboard = []
            keyboard.append([InlineKeyboardButton("👨‍💻 پشتیبانی", callback_data="support")])
            keyboard.append([InlineKeyboardButton("🤔 سلف چیست؟", callback_data="what_is_self"), InlineKeyboardButton("📣 کانال ما", url="https://t.me/rayan_self")])
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
        "<b>🔗 برای دسترسی به خدمات ما، ابتدا باید در کانال زیر عضو شوید.</b>\n"
        "<b>✅ پس از عضویت، روی دکمه «عضو شدم» کلیک کنید.</b>"
    )
    keyboard = [
        [InlineKeyboardButton("🔗 ریپر سلف", url="https://t.me/rayan_self")],
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
            "<b>🚫 شما از طرف مدیریت مسدود شده اید!</b>\n<b>💠 در صورت نیاز با پشتیبانی تماس بگیرید.</b>",
            parse_mode='HTML'
        )
        return
    
    is_verified = is_user_verified(user_id)
    
    user_mention = f"@{user.username}" if user.username else user.first_name
    if is_admin(user_id):
        text = (
            f"<b>⚡ درود {user_mention} به پنل ریپر سلف خوش آمدید.</b>\n\n"
            "<b>🛠️ در این پنل میتوانید ربات را کنترل و مدیریت کنید.</b>\n\n"
            "<b>🔄 لطفا از منوی زیر انتخاب نمایید.</b>"
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
            session_data = get_user_session(user_id)
            is_logged_in = session_data is not None
            expiry_date = get_expiry_date(user_id)
            text = (
                f"<b>⚡ سلام {user_mention} به ربات ریپر سلف خوش آمدید!</b>\n\n"
                "<b>🎯 در این ربات میتوانید از پشتیبانی، خرید، نصب ربات سلف بهره ببرید!</b>\n\n"
                "<b>💠 اگر سوالی دارید از بخش پشتیبانی استفاده کنید.</b>"
            )
            keyboard = []
            keyboard.append([InlineKeyboardButton("👨‍💻 پشتیبانی", callback_data="support")])
            keyboard.append([InlineKeyboardButton("🤔 سلف چیست؟", callback_data="what_is_self"), InlineKeyboardButton("📣 کانال ما", url="https://t.me/rayan_self")])
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
                "<b>🔗 شما هنوز عضو کانال زیر نشده اید!</b>\n"
                "<b>✅ ابتدا برای استفاده از ربات در کانال زیر عضو شوید!</b>"
            )
            keyboard = [
                [InlineKeyboardButton("🔗 ریپر سلف", url="https://t.me/rayan_self")],
                [InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    except Exception as e:
        await query.answer("❌ خطا در بررسی عضویت!", show_alert=True)

# ==================== CONTINUE WITH REST OF FUNCTIONS ====================

# (بقیه توابع مثل support, admin_reply, admin_stats, admin_ping, admin_host, show_user_menu, admin_users_menu, admin_settings, admin_settings_back, admin_back, rate, what_is_self, buy_with_code, handle_activation_code, buy_subscription, verify, verified_already, delete_card, new_card, handle_verify_photo, handle_verify_card_number, accept_verify, reject_verify, back_to_verify, back_from_user_menu, admin_block_user, admin_unblock_user, handle_block_user, handle_unblock_user, admin_create_code, admin_cancel_code, handle_code_days, handle_cancel_code, admin_transfer_credit, admin_deduct_credit, handle_transfer_credit, handle_deduct_credit, admin_salf_login, admin_salf_logout, admin_handle_salf_phone, admin_handle_salf_logout_phone, admin_handle_salf_user_id, admin_handle_salf_api_id, admin_handle_salf_api_hash, admin_handle_salf_code, admin_handle_salf_password, salf_login, handle_salf_phone, handle_salf_api_id, handle_salf_api_hash, handle_salf_code, handle_salf_password, main_menu, buy_1_month, buy_2_month, buy_3_month, buy_4_month, buy_5_month, buy_6_month, expiry, handle_message, main)
