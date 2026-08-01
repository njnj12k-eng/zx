from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import time
import platform
import subprocess
import asyncio
import os

TOKEN = "8961040480:AAHNKEnK7LZuCp9fSJ5td2_XdGFqPtwp_dY"
CHANNEL_USERNAME = "@ReaperSelfChannel"

# آیدی عددی ادمین
ADMIN_ID = 7803165903

# ذخیره وضعیت کاربران برای مرحله احراز هویت
user_states = {}

async def get_server_info():
    """دریافت اطلاعات سرور بدون psutil"""
    try:
        # پینگ - زمان پاسخگویی سرور
        ping_time = None
        try:
            # پینگ به گوگل برای تست اتصال
            process = await asyncio.create_subprocess_exec(
                "ping", "-c", "1", "8.8.8.8",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                output = stdout.decode()
                import re
                ping_match = re.search(r'time=(\d+\.?\d*)\s*ms', output)
                if ping_match:
                    ping_time = float(ping_match.group(1))
        except:
            ping_time = None
        
        # دریافت اطلاعات سیستم با دستورات لینوکس
        cpu_percent = "نامشخص"
        memory_info = "نامشخص"
        disk_info = "نامشخص"
        uptime = "نامشخص"
        
        try:
            # CPU
            process = await asyncio.create_subprocess_exec(
                "top", "-bn1", "|", "grep", "Cpu",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True
            )
            stdout, stderr = await process.communicate()
            if stdout:
                output = stdout.decode()
                import re
                cpu_match = re.search(r'(\d+\.?\d*)\s*id', output)
                if cpu_match:
                    cpu_idle = float(cpu_match.group(1))
                    cpu_percent = f"{100 - cpu_idle:.1f}%"
        except:
            pass
        
        try:
            # Memory
            process = await asyncio.create_subprocess_exec(
                "free", "-h",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if stdout:
                lines = stdout.decode().split('\n')
                for line in lines:
                    if 'Mem:' in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            total = parts[1]
                            used = parts[2]
                            memory_info = f"{used} / {total}"
                        break
        except:
            pass
        
        try:
            # Disk
            process = await asyncio.create_subprocess_exec(
                "df", "-h", "/",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if stdout:
                lines = stdout.decode().split('\n')
                for line in lines:
                    if '/dev/' in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            disk_info = f"{parts[2]} / {parts[1]}"
                        break
        except:
            pass
        
        try:
            # Uptime
            process = await asyncio.create_subprocess_exec(
                "uptime", "-p",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if stdout:
                uptime = stdout.decode().strip().replace('up ', '')
        except:
            pass
        
        # وضعیت سرور
        status = "🟢 آنلاین"
        if ping_time is None:
            status = "🔴 قطع"
        elif ping_time > 100:
            status = "🟡 هشدار"
        
        return {
            'status': status,
            'ping': f"{ping_time:.1f} ms" if ping_time else "❌ نامشخص",
            'cpu': cpu_percent,
            'memory': memory_info,
            'disk': disk_info,
            'os': platform.system(),
            'uptime': uptime
        }
    except Exception as e:
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_mention = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name
    
    # پاک کردن وضعیت کاربر
    if user_id in user_states:
        del user_states[user_id]
    
    # بررسی اینکه کاربر ادمین هست یا نه
    if user_id == ADMIN_ID:
        # منوی ادمین
        text = (
            f"<b>⫸ درود {user_mention} به پنل ریپر سلف Reaper Self خوش آمدید.</b>\n\n"
            "<b>◄ توی این پنل میتوانید ربات ریپر سلف Reaper Self را کنترل و مدیریت کنید.</b>\n\n"
            "<b>◂ لطفا از منوی زیر انتخاب نمایید که چه کاری را می‌خواهید انتخاب دهید.</b>"
        )
        
        keyboard = [
            [InlineKeyboardButton("📊 آمار کامل", callback_data="admin_stats")],
            [InlineKeyboardButton("📡 بررسی پینگ", callback_data="admin_ping")],
            [InlineKeyboardButton("⏳ اعتبار هاست", callback_data="admin_host")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        return
    
    # کاربر عادی - بررسی عضویت
    try:
        chat_member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        
        if chat_member.status in ["member", "administrator", "creator"]:
            # منوی اصلی کاربران
            text = (
                "<b>⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌</b>\n"
                f"<b>⫸ سلام {user_mention} به ربات ریپر سلف Reaper Self خوش آمدید !</b>\n\n"
                "<b>◄ توی این ربات میتوانید از پشتیبانی ، خرید ، نصب ربات سلف بهره ببرید !</b>\n\n"
                "<b>◂ لطفا اگر سوالی دارید از بخش پشتیبانی ، با پشتیبان ها در ارتباط باشید !</b>\n"
                "<b>⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯   ⁭⁯⁯⁭⁯‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌</b>"
            )
            
            keyboard = [
                [InlineKeyboardButton("🛡️ پشتیبانی 👨‍💻", callback_data="support")],
                [InlineKeyboardButton("📢 کانال دستورات", url="https://t.me/ReaperSelfChannel"), InlineKeyboardButton("❓ سلف چیست ؟ 🤔", callback_data="what_is_self")],
                [InlineKeyboardButton("⏳ انقضا : ( 0 روز )", callback_data="expiry")],
                [InlineKeyboardButton("✔️ احراز هویت", callback_data="verify"), InlineKeyboardButton("💳 خرید اشتراک", callback_data="buy_subscription")],
                [InlineKeyboardButton("💶 خرید با کد", callback_data="buy_with_code")],
                [InlineKeyboardButton("💎 نرخ", callback_data="rate")],
                [InlineKeyboardButton("📣 کانال ما", url="https://t.me/ReaperSelfChannel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            return
    except:
        pass
    
    # کاربر عضو نیست
    text = (
        "<b>⫸ برای دسترسی به خدمات ما، ابتدا باید در کانال زیر عضو شوید.</b>\n"
        "<b>◄ پس از عضویت، روی دکمه‌ی «عضو شدم» کلیک کنید.</b>"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔗 ریپر سلف Reaper Self", url="https://t.me/ReaperSelfChannel")],
        [InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_mention = f"@{query.from_user.username}" if query.from_user.username else query.from_user.first_name
    
    # ادمین نیازی به بررسی عضویت ندارد
    if user_id == ADMIN_ID:
        text = (
            f"<b>⫸ درود {user_mention} به پنل ریپر سلف Reaper Self خوش آمدید.</b>\n\n"
            "<b>◄ توی این پنل میتوانید ربات ریپر سلف Reaper Self را کنترل و مدیریت کنید.</b>\n\n"
            "<b>◂ لطفا از منوی زیر انتخاب نمایید که چه کاری را می‌خواهید انتخاب دهید.</b>"
        )
        
        keyboard = [
            [InlineKeyboardButton("📊 آمار کامل", callback_data="admin_stats")],
            [InlineKeyboardButton("📡 بررسی پینگ", callback_data="admin_ping")],
            [InlineKeyboardButton("⏳ اعتبار هاست", callback_data="admin_host")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        return
    
    try:
        chat_member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        
        if chat_member.status in ["member", "administrator", "creator"]:
            # منوی اصلی
            text = (
                "<b>⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌</b>\n"
                f"<b>⫸ سلام {user_mention} به ربات ریپر سلف Reaper Self خوش آمدید !</b>\n\n"
                "<b>◄ توی این ربات میتوانید از پشتیبانی ، خرید ، نصب ربات سلف بهره ببرید !</b>\n\n"
                "<b>◂ لطفا اگر سوالی دارید از بخش پشتیبانی ، با پشتیبان ها در ارتباط باشید !</b>\n"
                "<b>⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯   ⁭⁯⁯⁭⁯‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌</b>"
            )
            
            keyboard = [
                [InlineKeyboardButton("🛡️ پشتیبانی 👨‍💻", callback_data="support")],
                [InlineKeyboardButton("📢 کانال دستورات", url="https://t.me/ReaperSelfChannel"), InlineKeyboardButton("❓ سلف چیست ؟ 🤔", callback_data="what_is_self")],
                [InlineKeyboardButton("⏳ انقضا : ( 0 روز )", callback_data="expiry")],
                [InlineKeyboardButton("✔️ احراز هویت", callback_data="verify"), InlineKeyboardButton("💳 خرید اشتراک", callback_data="buy_subscription")],
                [InlineKeyboardButton("💶 خرید با کد", callback_data="buy_with_code")],
                [InlineKeyboardButton("💎 نرخ", callback_data="rate")],
                [InlineKeyboardButton("📣 کانال ما", url="https://t.me/ReaperSelfChannel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
        else:
            # کاربر عضو نیست
            text = (
                "<b>⫸ شما هنوز عضو کانال زیر نشده اید !</b>\n"
                "<b>◄ ابتدا برای استفاده از ربات در کانال زیر عضو شوید !</b>"
            )
            
            keyboard = [
                [InlineKeyboardButton("🔗 ریپر سلف Reaper Self", url="https://t.me/ReaperSelfChannel")],
                [InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
    except Exception as e:
        await query.answer("❌ خطا در بررسی عضویت!", show_alert=True)

# =============== بخش ادمین ===============

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.answer("📊 آمار کامل به زودی اضافه میشود!", show_alert=True)

async def admin_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # دریافت اطلاعات سرور
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
        text = (
            "<b>❌ خطا در دریافت اطلاعات سرور!</b>"
        )
    
    keyboard = [
        [InlineKeyboardButton("🔄 بروزرسانی پینگ", callback_data="admin_ping")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def admin_host(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.answer("⏳ اعتبار هاست: 28 روز باقی مانده!", show_alert=True)

async def admin_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_mention = f"@{query.from_user.username}" if query.from_user.username else query.from_user.first_name
    
    text = (
        f"<b>⫸ درود {user_mention} به پنل ریپر سلف Reaper Self خوش آمدید.</b>\n\n"
        "<b>◄ توی این پنل میتوانید ربات ریپر سلف Reaper Self را کنترل و مدیریت کنید.</b>\n\n"
        "<b>◂ لطفا از منوی زیر انتخاب نمایید که چه کاری را می‌خواهید انتخاب دهید.</b>"
    )
    
    keyboard = [
        [InlineKeyboardButton("📊 آمار کامل", callback_data="admin_stats")],
        [InlineKeyboardButton("📡 بررسی پینگ", callback_data="admin_ping")],
        [InlineKeyboardButton("⏳ اعتبار هاست", callback_data="admin_host")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

# =============== بخش کاربران عادی ===============

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
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

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
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def buy_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = (
        "<b>◂ برای خرید باید ابتدا احراز هویت کنید.</b>"
    )
    
    keyboard = [
        [InlineKeyboardButton("✔️ احراز هویت", callback_data="verify")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_mention = f"@{query.from_user.username}" if query.from_user.username else query.from_user.first_name
    
    # ادمین
    if user_id == ADMIN_ID:
        text = (
            f"<b>⫸ درود {user_mention} به پنل ریپر سلف Reaper Self خوش آمدید.</b>\n\n"
            "<b>◄ توی این پنل میتوانید ربات ریپر سلف Reaper Self را کنترل و مدیریت کنید.</b>\n\n"
            "<b>◂ لطفا از منوی زیر انتخاب نمایید که چه کاری را می‌خواهید انتخاب دهید.</b>"
        )
        
        keyboard = [
            [InlineKeyboardButton("📊 آمار کامل", callback_data="admin_stats")],
            [InlineKeyboardButton("📡 بررسی پینگ", callback_data="admin_ping")],
            [InlineKeyboardButton("⏳ اعتبار هاست", callback_data="admin_host")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        return
    
    text = (
        "<b>⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌</b>\n"
        f"<b>⫸ سلام {user_mention} به ربات ریپر سلف Reaper Self خوش آمدید !</b>\n\n"
        "<b>◄ توی این ربات میتوانید از پشتیبانی ، خرید ، نصب ربات سلف بهره ببرید !</b>\n\n"
        "<b>◂ لطفا اگر سوالی دارید از بخش پشتیبانی ، با پشتیبان ها در ارتباط باشید !</b>\n"
        "<b>⁭⁯⁯⁭⁯               ⁭⁯⁯⁭⁯   ⁭⁯⁯⁭⁯‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌</b>"
    )
    
    keyboard = [
        [InlineKeyboardButton("🛡️ پشتیبانی 👨‍💻", callback_data="support")],
        [InlineKeyboardButton("📢 کانال دستورات", url="https://t.me/ReaperSelfChannel"), InlineKeyboardButton("❓ سلف چیست ؟ 🤔", callback_data="what_is_self")],
        [InlineKeyboardButton("⏳ انقضا : ( 0 روز )", callback_data="expiry")],
        [InlineKeyboardButton("✔️ احراز هویت", callback_data="verify"), InlineKeyboardButton("💳 خرید اشتراک", callback_data="buy_subscription")],
        [InlineKeyboardButton("💶 خرید با کد", callback_data="buy_with_code")],
        [InlineKeyboardButton("💎 نرخ", callback_data="rate")],
        [InlineKeyboardButton("📣 کانال ما", url="https://t.me/ReaperSelfChannel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def buy_with_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = (
        "<b>◄ لطفا کد انقضای خریداری شده خود را ارسال کنید :</b>"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

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
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def expiry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
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
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def delete_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.answer("❌ کارت شما با موفقیت حذف شد!", show_alert=True)

async def new_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # ذخیره وضعیت کاربر برای مرحله دریافت عکس
    user_states[query.from_user.id] = "waiting_for_photo"
    
    text = (
        "<b>به بخش احراز هویت خوش آمدید.\n\nنکات :\n1) شماره کارت و نام صاحب کارت کاملا مشخص باشد.\n2) لطفا تاریخ اعتبار و Cvv2 کارت خود را بپوشانید!\n3) فقط با کارتی که احراز هویت میکنید میتوانید خرید انجام بدید و اگر با کارت دیگری اقدام کنید تراکنش ناموفق میشود و هزینه از سمت خودِ بانک به شما بازگشت داده میشود.\n4) در صورتی که توانایی ارسال عکس از کارت را ندارید تنها راه حل ارسال عکس از کارت ملی یا شناسنامه صاحب کارت است.\n\nلطفا عکس از کارتی که میخواهید با آن خرید انجام دهید ارسال کنید.</b>"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_verify")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def back_to_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # پاک کردن وضعیت کاربر
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
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # بررسی اینکه کاربر در مرحله دریافت عکس هست یا نه
    if user_id not in user_states or user_states[user_id] != "waiting_for_photo":
        return
    
    # بررسی اینکه پیام عکس هست یا نه
    if update.message.photo:
        # عکس دریافت شد
        user_states[user_id] = "waiting_for_card_number"
        
        text = (
            "<b>◄ لطفا شماره کارت خود را به صورت اعداد انگلیسی ارسال کنید\nدر صورتی که منصرف شدید ربات را مجدد استارت کنید : [ /start ]</b>"
        )
        
        await update.message.reply_text(
            text,
            parse_mode='HTML'
        )
    else:
        # هر چیزی غیر از عکس
        await update.message.reply_text(
            "<b>❌ لطفا فقط عکس ارسال کنید!</b>",
            parse_mode='HTML'
        )

async def handle_card_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # بررسی اینکه کاربر در مرحله دریافت شماره کارت هست یا نه
    if user_id not in user_states or user_states[user_id] != "waiting_for_card_number":
        return
    
    text = update.message.text.strip()
    
    # حذف فاصله ها و کاراکترهای اضافی
    card_number = ''.join(filter(str.isdigit, text))
    
    # بررسی 16 رقمی بودن
    if len(card_number) == 16 and card_number.isdigit():
        # شماره کارت معتبر
        await update.message.reply_text(
            "<b>درخواست احراز هویت شما برای پشتیبانی ارسال شد و در اولین فرصت تایید خواهد شد ، لطفا صبور باشید.\n\nلطفا برای تایید کارت به پشتیبانی پیام ارسال نفرمایید و درخواست احرازهویتتون رو اسپم نکنید ، در صورت مشاهده این کار یک روز با تاخیر تایید میشود.</b>",
            parse_mode='HTML'
        )
        # پاک کردن وضعیت کاربر
        del user_states[user_id]
    else:
        # شماره کارت نامعتبر
        await update.message.reply_text(
            "<b>شماره کارت 16 رقمی است.\nلطفا شماره کارت خود را بدون هیچ کاراکتر اضافه ای وارد کنید</b>",
            parse_mode='HTML'
        )

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

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_membership, pattern="check_membership"))
    
    # ادمین
    app.add_handler(CallbackQueryHandler(admin_stats, pattern="admin_stats"))
    app.add_handler(CallbackQueryHandler(admin_ping, pattern="admin_ping"))
    app.add_handler(CallbackQueryHandler(admin_host, pattern="admin_host"))
    app.add_handler(CallbackQueryHandler(admin_back, pattern="admin_back"))
    
    # کاربران
    app.add_handler(CallbackQueryHandler(support, pattern="support"))
    app.add_handler(CallbackQueryHandler(what_is_self, pattern="what_is_self"))
    app.add_handler(CallbackQueryHandler(buy_subscription, pattern="buy_subscription"))
    app.add_handler(CallbackQueryHandler(main_menu, pattern="main_menu"))
    app.add_handler(CallbackQueryHandler(buy_with_code, pattern="buy_with_code"))
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
    
    # هندلرهای پیام
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_card_number))
    
    print("🤖 ربات در حال اجراست...")
    app.run_polling()

if __name__ == "__main__":
    main()
