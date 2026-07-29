from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8961040480:AAHNKEnK7LZuCp9fSJ5td2_XdGFqPtwp_dY"
CHANNEL_USERNAME = "@ReaperSelfChannel"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # بررسی اولیه عضویت
    try:
        chat_member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if chat_member.status in ["member", "administrator", "creator"]:
            await update.message.reply_text(
                "✅ شما قبلاً عضو کانال هستید.\nخوش آمدید!"
            )
            return
    except:
        pass
    
    # متن پیام با فرمت جدید
    text = (
        "<b>⫸ برای دسترسی به خدمات ما، ابتدا باید در کانال زیر عضو شوید.</b>\n"
        "<b>◄ پس از عضویت، روی دکمه‌ی «عضو شدم» کلیک کنید.</b>"
    )
    
    keyboard = [
        [InlineKeyboardButton("ریپر سلف Reaper Self", url="https://t.me/ReaperSelfChannel")],
        [InlineKeyboardButton("✓ عضو شدم", callback_data="check_membership")]
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
    
    try:
        chat_member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        
        if chat_member.status in ["member", "administrator", "creator"]:
            # کاربر عضو شده - پیام موفقیت
            new_text = (
                "<b>⫸ این ربات درحال کد نویسی و توسعه است لطفا صبر نمایید !</b>"
            )
            
            keyboard = [
                [InlineKeyboardButton("ریپر سلف Reaper Self", url="https://t.me/ReaperSelfChannel")],
                [InlineKeyboardButton("✓ عضو شدم", callback_data="check_membership")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                new_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        else:
            # کاربر عضو نیست - پیام خطا با دکمه‌ها
            new_text = (
                "<b>✗ شما هنوز عضو کانال زیر نشده اید !</b>\n"
                "<b>◄ ابتدا برای استفاده از ربات در کانال زیر عضو شوید !</b>"
            )
            
            keyboard = [
                [InlineKeyboardButton("ریپر سلف Reaper Self", url="https://t.me/ReaperSelfChannel")],
                [InlineKeyboardButton("✓ عضو شدم", callback_data="check_membership")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                new_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
    except Exception as e:
        # خطا در بررسی عضویت
        await query.answer("❌ خطا در بررسی عضویت!", show_alert=True)

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_membership, pattern="check_membership"))
    
    print("🤖 ربات در حال اجراست...")
    app.run_polling()

if __name__ == "__main__":
    main()
