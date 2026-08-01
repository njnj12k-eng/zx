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
ADMIN_ID = 7803165903

user_states = {}
CODES_FILE = "codes_data.json"
SESSIONS_FILE = "sessions_data.json"
salf_login_data = {}

if not os.path.exists("sessions"):
    os.makedirs("sessions")

# ... (بقیه توابع دیتابیس و ... مثل قبل)

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
        "<b>◄ لطفا آیپی عددی (API ID) خود را وارد کنید:</b>",
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
            # درخواست کد
            await client.send_code_request(data['phone'])
            salf_login_data[user_id]['client'] = client
            
            await update.message.reply_text(
                "<b>🔑 مرحله 4 از 4</b>\n\n"
                "<b>✅ کد تایید به شماره شما ارسال شد.</b>\n"
                "<b>◄ لطفا کد دریافتی را وارد کنید:</b>",
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
    
    code = update.message.text.strip() if update.message.text else ""
    if not code:
        await update.message.reply_text("<b>❌ لطفا کد را وارد کنید!</b>", parse_mode='HTML')
        return
    
    try:
        data = salf_login_data[user_id]
        client = data.get('client')
        
        if not client:
            await update.message.reply_text("<b>❌ خطا در اتصال! لطفا دوباره تلاش کنید.</b>", parse_mode='HTML')
            del user_states[user_id]
            del salf_login_data[user_id]
            return
        
        # تلاش برای ورود با کد
        try:
            await client.sign_in(data['phone'], code)
        except PhoneCodeExpiredError:
            # کد منقضی شده - دوباره درخواست کد جدید
            await update.message.reply_text(
                "<b>⏳ کد منقضی شده بود، در حال ارسال کد جدید...</b>",
                parse_mode='HTML'
            )
            
            # ارسال درخواست کد جدید
            await client.send_code_request(data['phone'])
            
            await update.message.reply_text(
                "<b>✅ کد جدید به شماره شما ارسال شد.</b>\n"
                "<b>◄ لطفا کد جدید را وارد کنید:</b>",
                parse_mode='HTML'
            )
            
            # وضعیت رو در حالت دریافت کد نگه دار
            user_states[user_id] = "waiting_salf_code"
            return
        
        # اگر ورود موفق بود
        session_string = client.session.save()
        save_user_session(user_id, session_string, data['phone'], data['api_hash'], data['api_id'])
        
        await client.disconnect()
        
        text = (
            "<b>✅ ورود سلف به اکانت شما با موفقیت انجام شد!</b>\n\n"
            f"<b>📱 شماره : {data['phone']}</b>"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
        
        del user_states[user_id]
        del salf_login_data[user_id]
        
    except SessionPasswordNeededError:
        user_states[user_id] = "waiting_salf_password"
        await update.message.reply_text(
            "<b>🔑 این اکانت دو مرحله‌ای فعال است.</b>\n"
            "<b>◄ لطفا پسورد خود را وارد کنید:</b>",
            parse_mode='HTML'
        )
    except PhoneCodeInvalidError:
        await update.message.reply_text(
            "<b>❌ کد وارد شده صحیح نیست! لطفا دوباره تلاش کنید.</b>",
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
        
        session_string = client.session.save()
        save_user_session(user_id, session_string, data['phone'], data['api_hash'], data['api_id'])
        
        await client.disconnect()
        
        text = (
            "<b>✅ ورود سلف به اکانت شما با موفقیت انجام شد!</b>\n\n"
            f"<b>📱 شماره : {data['phone']}</b>"
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

# ... (بقیه کدها مثل قبل)
