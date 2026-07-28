import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telethon import TelegramClient
from telethon.tl.functions.phone import JoinGroupCallRequest
from telethon.tl.types import InputGroupCall, DataJSON
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = os.getenv('TOKEN')
if not TOKEN:
    TOKEN = "8860863617:AAFizT8wFBJFt4uq7U9NpGfK_jwahrA35_o"

OWNER_ID = 8831703400
API_ID = 37160656
API_HASH = "c75ef3eadae1ffb6cad9d6736d0e2323"
SESSION_STRING = "BAI3BtAAq_xN1hnEFi-XlIAys4IQ8lmBNLBIPu2Y-O302Zp4eO6QLTs6fN9CT-Ho9zwgOp5AvNWFBcdcKG8EcQbvH3pA07kP9AYTwOdAgIOKxtiyZYugt4UZxjXBRR-XhS25FNiSBS3kD4VoL2xcCvNcXUIiBjXAIJqaiWfT5sHpeNnUOW_cr-I_RI6voZHuH7v1x9ZW3jG4HYlMcPhz3w-O4dxgGC6KC4a5WNsjIjPKwSQZVT3AhG3DlyA5-HffOerxi2A6gy1y8aGPpTXobCPxpy-UGWamNqjs0RRUacYbn5iV6xkDCuwnhvRvOjN3XDnfls3_gB_1kdV0DKpJzL28jiEtbQAAAAHvR2q6AA"

client = TelegramClient("music_bot", API_ID, API_HASH)
call = PyTgCalls(client)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id == OWNER_ID:
        keyboard = [[InlineKeyboardButton("⚙️ افزودن CLI", callback_data='add_cli')]]
        await update.message.reply_text("🌟 سلام برنامه‌نویس!", parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("🎵 ربات موزیک پلیر!\n/play [نام آهنگ]")

async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text("🎵 /play [نام آهنگ]")
        return
    query = " ".join(context.args)
    msg = await update.message.reply_text(f"🔍 در حال پخش: {query}")
    try:
        await call.join_group_call(chat_id, MediaStream("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"))
        await msg.edit_text(f"✅ در حال پخش: {query}")
    except Exception as e:
        await msg.edit_text(f"❌ خطا: {str(e)}")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await call.leave_group_call(update.effective_chat.id)
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
        await update.message.reply_text("▶️ ادامه!")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 پنگ! ربات فعال است ✅")

async def run_bot():
    await client.start()
    print("✅ Telethon متصل شد")
    await call.start()
    print("✅ PyTgCalls راه‌اندازی شد")
    
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('play', play))
    application.add_handler(CommandHandler('stop', stop))
    application.add_handler(CommandHandler('pause', pause))
    application.add_handler(CommandHandler('resume', resume))
    application.add_handler(CommandHandler('ping', ping))
    
    print("🚀 ربات روشن شد!")
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(run_bot())
