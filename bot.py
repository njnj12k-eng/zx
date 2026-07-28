import os
import logging
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from pyrogram import Client
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
import asyncio

# تنظیم لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# گرفتن توکن از محیط
TOKEN = os.getenv('TOKEN')

# اگر توکن در محیط نیست
if not TOKEN:
    TOKEN = "8860863617:AAFizT8wFBJFt4uq7U9NpGfK_jwahrA35_o"

# شناسه عددی سازنده ربات
OWNER_ID = 8831703400

# 🔑 اطلاعات API
API_ID = 37160656
API_HASH = "c75ef3eadae1ffb6cad9d6736d0e2323"

# 🔑 سشن استرینگ ساخته شده - این رو با سشن خودت جایگزین کن
SESSION_STRING = "BAI3BtAAq_xN1hnEFi-XlIAys4IQ8lmBNLBIPu2Y-O302Zp4eO6QLTs6fN9CT-Ho9zwgOp5AvNWFBcdcKG8EcQbvH3pA07kP9AYTwOdAgIOKxtiyZYugt4UZxjXBRR-XhS25FNiSBS3kD4VoL2xcCvNcXUIiBjXAIJqaiWfT5sHpeNnUOW_cr-I_RI6voZHuH7v1x9ZW3jG4HYlMcPhz3w-O4dxgGC6KC4a5WNsjIjPKwSQZVT3AhG3DlyA5-HffOerxi2A6gy1y8aGPpTXobCPxpy-UGWamNqjs0RRUacYbn5iV6xkDCuwnhvRvOjN3XDnfls3_gB_1kdV0DKpJzL28jiEtbQAAAAHvR2q6AA"

# متغیرهای ذخیره موقت
user_sessions = {}
playlist = {}

# پاک کردن Webhook قبلی
try:
    response = httpx.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook")
    if response.json().get('ok'):
        print("✅ Webhook قبلی پاک شد")
except Exception as e:
    print(f"⚠️ خطا در پاک کردن Webhook: {e}")

# راه‌اندازی کلاینت pyrogram با سشن
app = Client(
    "music_bot",
    session_string=SESSION_STRING,
    api_id=API_ID,
    api_hash=API_HASH
)

# راه‌اندازی PyTgCalls برای ویس چت
call = PyTgCalls(app)

# متن استارت (همون متنی که قبلا داشتی)
START_TEXT = """
🌟 سلام <b>[ نام کاربر منشن شده ]</b> عزیز 🌹

💬 من یه ربات موزیک پلیر گروه کاملاً حرفه‌ای و پرسرعت هستم...

🆑 کانال موزیک پلیر ZX : <b>@ReaperMusicTM</b>

【 <b>Licenced By 🆉︎🆇︎</b> 】
"""

# متن اختصاصی برای سازنده
OWNER_START_TEXT = """
🌟 <b>سلام برنامه‌نویس عزیز!</b> 🌹

⫸ به پنل مدیریتی ربات ZX Music Player خوش آمدید! 🚀

⚡ <b>وضعیت ربات:</b> فعال ✅
🔄 <b>نسخه:</b> 2.0.0

【 <b>Licenced By 🆉︎🆇︎</b> 】
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر /start"""
    user = update.effective_user
    user_id = user.id
    
    if user_id == OWNER_ID:
        keyboard = [[InlineKeyboardButton("⚙️ افزودن CLI", callback_data='add_cli')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(OWNER_START_TEXT, parse_mode='HTML', reply_markup=reply_markup)
    else:
        user_mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
        final_text = START_TEXT.replace("[ نام کاربر منشن شده ]", user_mention)
        keyboard = [
            [InlineKeyboardButton("📞 پشتیبانی", url="https://t.me/XMrHadi"),
             InlineKeyboardButton("📢 کانال ربات", url="https://t.me/ReaperMusicTM")],
            [InlineKeyboardButton("👥 گروه پشتیبانی", url="https://t.me/ReaperVoidGP"),
             InlineKeyboardButton("➕ اضافه کردن به گروه", url="https://t.me/Reaper_Musicbot?startgroup=new")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(final_text, parse_mode='HTML', disable_web_page_preview=True, reply_markup=reply_markup)

# ================ دستورات پخش موزیک ================

async def play_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /play برای پخش موزیک"""
    chat_id = update.effective_chat.id
    message = update.message
    user = update.effective_user
    
    if update.effective_chat.type not in ['group', 'supergroup']:
        await message.reply_text("❌ این دستور فقط در گروه قابل استفاده است!")
        return
    
    if not context.args:
        await message.reply_text(
            "🎵 <b>نحوه استفاده:</b>\n\n"
            "◄ <code>/play [نام آهنگ یا لینک]</code>\n"
            "◂ مثال: <code>/play Shadmehr</code>",
            parse_mode='HTML'
        )
        return
    
    query = " ".join(context.args)
    processing_msg = await message.reply_text(
        f"🔍 <b>در حال جستجو و پخش:</b>\n◄ <code>{query}</code>",
        parse_mode='HTML'
    )
    
    try:
        await play_music(chat_id, query, processing_msg)
    except Exception as e:
        await processing_msg.edit_text(f"❌ <b>خطا:</b>\n<code>{str(e)}</code>", parse_mode='HTML')

async def play_music(chat_id: int, query: str, processing_msg):
    """پخش موزیک در ویس چت"""
    try:
        # بررسی اینکه آیا ربات در ویس چت است
        try:
            await call.get_call(chat_id)
            is_playing = True
        except:
            is_playing = False
        
        # لینک نمونه برای تست (بعداً میتونی از یوتیوب استفاده کنی)
        audio_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
        
        if not is_playing:
            await call.join_group_call(chat_id, MediaStream(audio_url))
            await processing_msg.edit_text(
                f"✅ <b>در حال پخش:</b>\n◄ <code>{query}</code>\n\n"
                f"🎵 <b>دستورات:</b>\n  ◄ /pause - مکث\n  ◄ /resume - ادامه\n  ◄ /stop - توقف",
                parse_mode='HTML'
            )
        else:
            if chat_id not in playlist:
                playlist[chat_id] = []
            playlist[chat_id].append(query)
            await processing_msg.edit_text(
                f"⏳ <b>آهنگ به صف اضافه شد!</b>\n◄ <code>{query}</code>\n🎵 <b>شماره در صف:</b> {len(playlist[chat_id])}",
                parse_mode='HTML'
            )
    except Exception as e:
        raise e

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /stop"""
    chat_id = update.effective_chat.id
    try:
        await call.leave_group_call(chat_id)
        if chat_id in playlist:
            del playlist[chat_id]
        await update.message.reply_text("⏹️ <b>پخش متوقف شد!</b>", parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ <b>خطا:</b>\n<code>{str(e)}</code>", parse_mode='HTML')

async def pause_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /pause"""
    chat_id = update.effective_chat.id
    try:
        await call.pause_stream(chat_id)
        await update.message.reply_text("⏸️ <b>پخش متوقف شد!</b>\n◄ برای ادامه از /resume استفاده کنید.", parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ <b>خطا:</b>\n<code>{str(e)}</code>", parse_mode='HTML')

async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /resume"""
    chat_id = update.effective_chat.id
    try:
        await call.resume_stream(chat_id)
        await update.message.reply_text("▶️ <b>پخش ادامه یافت!</b>", parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ <b>خطا:</b>\n<code>{str(e)}</code>", parse_mode='HTML')

async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /skip"""
    chat_id = update.effective_chat.id
    try:
        if chat_id in playlist and playlist[chat_id]:
            next_song = playlist[chat_id].pop(0)
            await call.change_stream(chat_id, MediaStream("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3"))
            await update.message.reply_text(f"⏭️ <b>آهنگ بعدی:</b>\n◄ <code>{next_song}</code>", parse_mode='HTML')
        else:
            await update.message.reply_text("⚠️ <b>صف پخش خالی است!</b>", parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ <b>خطا:</b>\n<code>{str(e)}</code>", parse_mode='HTML')

# ================ بقیه کدها (دکمه‌ها، ساخت سشن و ...) ================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if user_id != OWNER_ID:
        await query.answer("⛔ شما دسترسی ندارید!", show_alert=True)
        return
    await query.answer()
    if query.data == 'add_cli':
        user_sessions[user_id] = {'step': 'phone'}
        await query.edit_message_text(
            "📱 <b>افزودن CLI جدید</b>\n\n◄ لطفاً شماره تلفن خود را ارسال کنید.\n◂ مثال: <code>+989123456789</code>",
            parse_mode='HTML'
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != OWNER_ID or user_id not in user_sessions:
        return
    text = update.message.text
    step = user_sessions[user_id]['step']
    
    if step == 'phone':
        phone = text.strip()
        if not phone.startswith('+') or not phone[1:].isdigit():
            await update.message.reply_text("❌ فرمت شماره نامعتبر!", parse_mode='HTML')
            return
        user_sessions[user_id]['phone'] = phone
        user_sessions[user_id]['step'] = 'code'
        await send_verification_code(update, user_id, phone)
    elif step == 'code':
        code = text.strip()
        if not code.isdigit() or len(code) != 5:
            await update.message.reply_text("❌ کد نامعتبر!", parse_mode='HTML')
            return
        await verify_code(update, user_id, code)
    elif step == 'password':
        password = text.strip()
        if len(password) < 4:
            await update.message.reply_text("❌ رمز عبور کوتاه است!", parse_mode='HTML')
            return
        await create_session_with_password(update, user_id, password)

async def send_verification_code(update: Update, user_id: int, phone: str):
    try:
        from pyrogram import Client
        app = Client(f"session_{user_id}", api_id=API_ID, api_hash=API_HASH, phone_number=phone)
        await app.connect()
        sent_code = await app.send_code(phone)
        user_sessions[user_id]['client'] = app
        user_sessions[user_id]['phone_code_hash'] = sent_code.phone_code_hash
        await update.message.reply_text(f"📨 کد تایید به {phone} ارسال شد!", parse_mode='HTML')
        user_sessions[user_id]['step'] = 'code'
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}", parse_mode='HTML')
        if user_id in user_sessions:
            del user_sessions[user_id]

async def verify_code(update: Update, user_id: int, code: str):
    try:
        from pyrogram.errors import SessionPasswordNeeded
        phone = user_sessions[user_id]['phone']
        phone_code_hash = user_sessions[user_id]['phone_code_hash']
        app = user_sessions[user_id]['client']
        try:
            await app.sign_in(phone_number=phone, phone_code_hash=phone_code_hash, phone_code=code)
            await create_session_final(update, user_id, app, phone)
        except SessionPasswordNeeded:
            user_sessions[user_id]['step'] = 'password'
            user_sessions[user_id]['app'] = app
            await update.message.reply_text("🔐 رمز عبور دو مرحله‌ای را وارد کنید:", parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}", parse_mode='HTML')
        if user_id in user_sessions:
            del user_sessions[user_id]

async def create_session_with_password(update: Update, user_id: int, password: str):
    try:
        phone = user_sessions[user_id]['phone']
        app = user_sessions[user_id]['app']
        await app.check_password(password)
        await create_session_final(update, user_id, app, phone)
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}", parse_mode='HTML')
        if user_id in user_sessions:
            del user_sessions[user_id]

async def create_session_final(update: Update, user_id: int, app, phone: str):
    try:
        session_string = await app.export_session_string()
        with open(f"session_{phone}.txt", "w") as f:
            f.write(session_string)
        await update.message.reply_text(
            f"✅ سشن ساخته شد!\n\n"
            f"🔑 سشن:\n<code>{session_string}</code>\n\n"
            f"📌 دستورات:\n"
            f"◄ /play [نام] - پخش\n"
            f"◄ /stop - توقف\n"
            f"◄ /pause - مکث\n"
            f"◄ /resume - ادامه\n"
            f"◄ /skip - رد کردن",
            parse_mode='HTML'
        )
        await app.disconnect()
        if user_id in user_sessions:
            del user_sessions[user_id]
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}", parse_mode='HTML')
        if user_id in user_sessions:
            del user_sessions[user_id]

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_sessions:
        if 'client' in user_sessions[user_id]:
            try:
                await user_sessions[user_id]['client'].disconnect()
            except:
                pass
        if 'app' in user_sessions[user_id]:
            try:
                await user_sessions[user_id]['app'].disconnect()
            except:
                pass
        del user_sessions[user_id]
        await update.message.reply_text("❌ عملیات لغو شد!", parse_mode='HTML')
    else:
        await update.message.reply_text("ℹ️ هیچ عملیات فعالی وجود ندارد!", parse_mode='HTML')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🤖 <b>راهنمای ربات</b>

📌 <b>دستورات:</b>
• /start - شروع
• /help - راهنما
• /ping - وضعیت
• /cancel - لغو عملیات

🎵 <b>دستورات موزیک:</b>
• /play [نام] - پخش
• /stop - توقف
• /pause - مکث
• /resume - ادامه
• /skip - رد کردن
    """
    await update.message.reply_text(help_text, parse_mode='HTML')

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 پنگ! ربات فعال است ✅", parse_mode='HTML')

async def run_bot():
    try:
        await app.start()
        print("✅ کلاینت pyrogram متصل شد")
        await call.start()
        print("✅ PyTgCalls راه‌اندازی شد")
        
        application = ApplicationBuilder().token(TOKEN).build()
        application.add_handler(CommandHandler('start', start))
        application.add_handler(CommandHandler('help', help_command))
        application.add_handler(CommandHandler('ping', ping))
        application.add_handler(CommandHandler('cancel', cancel_command))
        application.add_handler(CommandHandler('play', play_command))
        application.add_handler(CommandHandler('stop', stop_command))
        application.add_handler(CommandHandler('pause', pause_command))
        application.add_handler(CommandHandler('resume', resume_command))
        application.add_handler(CommandHandler('skip', skip_command))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        print("🚀 ربات در حال روشن شدن...")
        await application.run_polling(drop_pending_updates=True, allowed_updates=['message', 'callback_query'])
    except Exception as e:
        print(f"❌ خطا: {e}")

if __name__ == '__main__':
    asyncio.run(run_bot())
