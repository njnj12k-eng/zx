import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8961040480:AAHNKEnK7LZuCp9fSJ5td2_XdGFqPtwp_dY"
CHANNEL_USERNAME = "@ReaperSelfChannel"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    try:
        chat_member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        
        if chat_member.status in ["member", "administrator", "creator"]:
            await update.message.reply_text("✅ شما قبلاً عضو کانال هستید.\nخوش آمدید!")
            return
    except:
        pass
    
    text = (
        "⫸◄◂\n"
        "➥ برای دسترسی به خدمات ما، ابتدا در کانال زیر عضو شوید.\n"
        "➥ پس از عضویت، روی دکمه‌ی «عضو شدم» کلیک کنید.\n"
        "⫸◄◂"
    )
    
    keyboard = [
        [InlineKeyboardButton("ریپر سلف Reaper Self", url="https://t.me/ReaperSelfChannel")],
        [InlineKeyboardButton("✓ عضو شدم", callback_data="check_membership")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup)

async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    try:
        chat_member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        
        if chat_member.status in ["member", "administrator", "creator"]:
            await query.edit_message_text("✅ عضویت شما تأیید شد.\nاکنون می‌توانید از ربات استفاده کنید.")
        else:
            await query.answer("❌ شما هنوز عضو کانال نشدید!", show_alert=True)
    except:
        await query.answer("❌ خطا در بررسی عضویت!", show_alert=True)

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_membership, pattern="check_membership"))
    
    print("ربات در حال اجراست...")
    app.run_polling()

if __name__ == "__main__":
    main()
