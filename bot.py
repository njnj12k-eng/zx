import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from pyrogram import Client
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream

# تنظیم لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# تنظیمات
TOKEN = os.getenv('TOKEN')
if not TOKEN:
    TOKEN = "8860863617:AAFizT8wFBJFt4uq7U9NpGfK_jwahrA35_o"

OWNER_ID = 8831703400
API_ID = 37160656
API_HASH = "c75ef3eadae1ffb6cad9d6736d0e2323"

# سشن شما
SESSION_STRING = "BAI3BtAAq_xN1hnEFi-XlIAys4IQ8lmBNLBIPu2Y-O302Zp4eO6QLTs6fN9CT-Ho9zwgOp5AvNWFBcdcKG8EcQbvH3pA07kP9AYTwOdAgIOKxtiyZYugt4UZxjXBRR-XhS25FNiSBS3kD4VoL2xcCvNcXUIiBjXAIJqaiWfT5sHpeNnUOW_cr-I_RI6voZHuH7v1x9ZW3jG4HYlMcPhz3w-O4dxgGC6KC4a5WNsjIjPKwSQZVT3AhG3DlyA5-HffOerxi2A6gy1y8aGPpTXobCPxpy-UGWamNqjs0RRUacYbn5iV6xkDCuwnhvRvOjN3XDnfls3_gB_1kdV0DKpJzL28jiEtbQAAAAHvR2q6AA"

# متغیرها
user_sessions = {}
playlist = {}

# راه‌اندازی کلاینت
app = Client("music_bot", session_string=SESSION_STRING, api_id=API_ID, api_hash=API_HASH)
call = PyTgCalls(app)

# متن استارت
START_TEXT = """
🌟 سلام <b>[ نام کاربر منشن شده ]</b> عزیز 🌹

💬 من یه ربات موزیک پلیر گروه کاملاً حرفه‌ای و پرسرعت هستم...

🆑 کانال موزیک پلیر ZX : <b>@ReaperMusicTM</b>
【 <b>Licenced By 🆉︎🆇︎</b> 】
"""

OWNER_TEXT = """
🌟 <b>سلام برنامه‌نویس عزیز!</b> 🌹

⫸ به پنل مدیریتی خوش آمدید! 🚀
⚡ <b>وضعیت:</b> فعال ✅
【 <b>Licenced By 🆉︎🆇︎</b> 】
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id == OWNER_ID:
        keyboard = [[InlineKeyboardButton("⚙️ افزودن CLI", callback_data='add_cli')]]
        await update.message.reply_text(OWNER_TEXT, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
        text = START_TEXT.replace("[ نام کاربر منشن شده ]", mention)
        keyboard = [
            [InlineKeyboardButton("📞 پشتیبانی", url="https://t.me/XMrHadi")],
            [InlineKeyboardButton("📢 کانال ربات", url="https://t.me/ReaperMusicTM")],
            [InlineKeyboardButton("👥 گروه پشتیبانی", url="https://t.me/ReaperVoidGP")],
            [InlineKeyboardButton("➕ اضافه کردن به گروه", url="https://t.me/Reaper_Musicbot?startgroup=new")]
        ]
        await update.message.reply_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if update.effective_chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ فقط در گروه!")
        return
    if not context.args:
        await update.message.reply_text("🎵 /play [نام آهنگ]")
        return
    
    query = " ".join(context.args)
    msg = await update.message.reply_text(f"🔍 در حال پخش: {query}")
    
    try:
        # چک کردن وضعیت
        try:
            await call.get_call(chat_id)
            is_playing = True
        except:
            is_playing = False
        
        # لینک نمونه
        audio = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
        
        if not is_playing:
            await call.join_group_call(chat_id, MediaStream(audio))
            await msg.edit_text(f"✅ در حال پخش: {query}")
        else:
            if chat_id not in playlist:
                playlist[chat_id] = []
            playlist[chat_id].append(query)
            await msg.edit_text(f"⏳ به صف اضافه شد: {query}")
    except Exception as e:
        await msg.edit_text(f"❌ خطا: {str(e)}")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        await call.leave_group_call(chat_id)
        if chat_id in playlist:
            del playlist[chat_id]
        await update.message.reply_text("⏹️ پخش متوقف شد!")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")

async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await call.pause_stream(update.effective_chat.id)
        await update.message.reply_text("⏸️ مکث شد!")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")

async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await call.resume_stream(update.effective_chat.id)
        await update.message.reply_text("▶️ ادامه پخش!")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")

async def skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        if chat_id in playlist and playlist[chat_id]:
            next_song = playlist[chat_id].pop(0)
            await call.change_stream(chat_id, MediaStream("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3"))
            await update.message.reply_text(f"⏭️ آهنگ بعدی: {next_song}")
        else:
            await update.message.reply_text("⚠️ صف خالی است!")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
        await update.message.reply_text("❌ لغو شد!")
    else:
        await update.message.reply_text("ℹ️ عملیاتی وجود ندارد!")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 راهنما:\n"
        "/play [نام] - پخش\n"
        "/stop - توقف\n"
        "/pause - مکث\n"
        "/resume - ادامه\n"
        "/skip - رد کردن\n"
        "/cancel - لغو"
    )

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 پنگ! ربات فعال است ✅")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != OWNER_ID:
        await query.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    await query.answer()
    user_sessions[query.from_user.id] = {'step': 'phone'}
    await query.edit_message_text("📱 شماره خود را ارسال کنید:")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_sessions:
        return
    
    step = user_sessions[user_id]['step']
    if step == 'phone':
        phone = update.message.text.strip()
        if not phone.startswith('+'):
            await update.message.reply_text("❌ با + شروع کنید!")
            return
        user_sessions[user_id]['phone'] = phone
        user_sessions[user_id]['step'] = 'code'
        await update.message.reply_text("📨 کد تایید را وارد کنید:")
    elif step == 'code':
        code = update.message.text.strip()
        if len(code) != 5:
            await update.message.reply_text("❌ کد ۵ رقمی!")
            return
        await update.message.reply_text("✅ کد تایید شد!")
        del user_sessions[user_id]

async def run_bot():
    await app.start()
    print("✅ Pyrogram متصل شد")
    await call.start()
    print("✅ PyTgCalls راه‌اندازی شد")
    
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help))
    application.add_handler(CommandHandler('ping', ping))
    application.add_handler(CommandHandler('cancel', cancel))
    application.add_handler(CommandHandler('play', play))
    application.add_handler(CommandHandler('stop', stop))
    application.add_handler(CommandHandler('pause', pause))
    application.add_handler(CommandHandler('resume', resume))
    application.add_handler(CommandHandler('skip', skip))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🚀 ربات روشن شد!")
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(run_bot())
