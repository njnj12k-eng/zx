import os
import logging
import httpx
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from pyrogram import Client
import re

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

# اطلاعات سشن (از my.telegram.org)
API_ID = 37160656
API_HASH = "c75ef3eadae1ffb6cad9d6736d0e2323"
SESSION_NAME = os.getenv('SESSION_NAME', 'my_session')

# آیدی عددی سازنده ربات
OWNER_ID = 7803165903

# لینک‌ها
SUPPORT_LINK = "https://t.me/XMrHadi"
CHANNEL_LINK = "https://t.me/ReaperMusicTM"
GROUP_LINK = "https://t.me/ReaperVoidGP"
BOT_LINK = "https://t.me/Reaper_Musicbot?startgroup=new"

# مراحل ساخت CLI
PHONE, CODE = range(2)

# متغیر برای نگهداری کلاینت در حین ساخت سشن
client_instance = None

# پاک کردن Webhook قبلی
for i in range(3):
    try:
        response = httpx.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook")
        if response.json().get('ok'):
            print("✅ Webhook قبلی پاک شد")
            break
    except Exception as e:
        print(f"⚠️ تلاش {i+1} برای پاک کردن Webhook ناموفق بود: {e}")
        time.sleep(1)

try:
    response = httpx.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=True")
    if response.json().get('ok'):
        print("✅ Webhook با drop_pending_updates پاک شد")
except Exception as e:
    print(f"⚠️ خطا: {e}")

# متن استارت عمومی
PUBLIC_START_TEXT = """
🌟 سلام <b>[ نام کاربر منشن شده ]</b> عزیز 🌹

💬 من یه ربات موزیک پلیر گروه کاملاً حرفه‌ای و پرسرعت هستم که با من میتونی به راحتی در ویس چت گروهت موزیک یا ویدئو پخش کنی!

⫸ برتری‌های انحصاری من :

<b>⚡ مجهز به سیستم هوش مصنوعی (A.I)</b> برای پردازش هوشمند
<b>🧠 سیستم ANN</b> برای پردازش و ذخیره‌سازی پیشرفته
<b>🎚️ سیستم CUH</b> برای مدیریت حرفه‌ای ویس چت
<b>📥 دانلود و جستجوی حرفه‌ای</b> رسانه‌های صوتی و تصویری
<b>⏪⏩ جلو و عقب زدن دقیقه‌ای</b> رسانه‌ها
<b>🛡️ پردازش و محافظت</b> از ویس‌چت گروه

⫸ ویژگی‌های منحصربفرد :

<b>⚡ سرعت فوق‌العاده</b> حتی در گروه‌های ۲۰۰ هزار نفره
<b>🌟 برترین پخش‌کننده</b> موزیک و ویدیو با امکانات بی‌نظیر

<b>📺 پخش زنده</b> شبکه‌های ماهواره‌ای
<b>📡 پخش زنده</b> شبکه‌های صدا و سیما
<b>🎙️ پخش زنده</b> رادیو جهانی و استانی
<b>🎬 تلویزیون، رادیو و موسیقی</b> زنده
<b>🎥 فیلم سینمایی، سریال و انیمیشن</b>
<b>💰 قیمت خرید اشتراک</b> بسیار مناسب

⫸ ما شبیه هیچکس نیستیم!

<b>🔥 پرقدرت</b> حتی در کانال‌های میلیونی
<b>✅ بی‌همتا در سرعت</b>
<b>✅ بی‌همتا در امکانات</b>
<b>✅ دارای مهلت بالای تست</b>
<b>✅ دارای سرور اختصاصی</b>
<b>✅ دارای پشتیبانی حرفه‌ای</b>
<b>✅ دارای دستورات دو زبانه</b>
<b>✅ جستجوی موزیک و ویدیو</b>
<b>✅ قابلیت‌های فان و سرگرمی</b>
<b>✅ دارای سامانه خرید آنلاین</b>
<b>✅ بدون آفلاینی ۹۹.۹ درصد</b>
<b>✅ ارائه آمارهای روزانه کاربران</b>
<b>✅ دارای خوش‌آمدگویی هوشمند</b>
<b>✅ دارای انواع قفل‌های ویس چت</b>
<b>✅ پخش موزیک و ویدئو در گروه</b>
<b>✅ پخش موزیک و ویدئو در کانال</b>
<b>✅ دارای مای لیست و علاقه‌مندی‌ها</b>
<b>✅ قابلیت ساخت ۳ پلی‌لیست موزیک</b>
<b>✅ قابلیت ساخت ۲ پلی‌لیست ویدیو</b>

⫸ چرا به ما اعتماد کنیم؟

<b>🥇ارائه بهترین کیفیت، تخصص ماست</b>
<b>♥️ تجربه مدیریت ویسکال به سبک نوین</b>
<b>🖥️ برنامه‌نویسی شده توسط تیم ZX</b>
<b>🏆 بهترینی، وقتی بهترین‌ها انتخابت کنند!</b>

⫸ تذکر حقوقی :

تمام ایده‌ها و کدهای این ربات متعلق به <b>تیم ZX</b> بوده و هر گونه کپی‌برداری یا تقلید، <b>پیگرد قانونی</b> دارد. حقوق مادی و معنوی محفوظ است.

🆑 کانال موزیک پلیر ZX : <b>@ReaperMusicTM</b>

【 <b>Licenced By 🆉︎🆇︎</b> 】
"""

# متن استارت مخصوص سازنده
OWNER_START_TEXT = """
🌟 سلام <b>[ نام کاربر منشن شده ]</b> عزیز 🌹

⫸ به پنل مدیریت خوش آمدید! 

◄ شما سازنده و برنامه‌نویس اصلی این ربات هستید.

◄ از این بخش می‌توانید سشن مورد نیاز برای پخش موزیک در ویس‌چت را بسازید.

◄ برای شروع ساخت سشن، روی دکمه زیر کلیک کنید.

【 <b>Licenced By 🆉︎🆇︎</b> 】
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر /start با تشخیص سازنده"""
    user = update.effective_user
    user_mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
    
    is_owner = (user.id == OWNER_ID)
    
    if is_owner:
        final_text = OWNER_START_TEXT.replace("[ نام کاربر منشن شده ]", user_mention)
        keyboard = [
            [
                InlineKeyboardButton("🔧 افزودن CLI", callback_data='add_cli')
            ],
            [
                InlineKeyboardButton("📞 پشتیبانی", url=SUPPORT_LINK),
                InlineKeyboardButton("📢 کانال ربات", url=CHANNEL_LINK)
            ],
            [
                InlineKeyboardButton("👥 گروه پشتیبانی", url=GROUP_LINK),
                InlineKeyboardButton("➕ اضافه کردن به گروه", url=BOT_LINK)
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    else:
        final_text = PUBLIC_START_TEXT.replace("[ نام کاربر منشن شده ]", user_mention)
        keyboard = [
            [
                InlineKeyboardButton("📞 پشتیبانی", url=SUPPORT_LINK),
                InlineKeyboardButton("📢 کانال ربات", url=CHANNEL_LINK)
            ],
            [
                InlineKeyboardButton("👥 گروه پشتیبانی", url=GROUP_LINK),
                InlineKeyboardButton("➕ اضافه کردن به گروه", url=BOT_LINK)
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        final_text,
        parse_mode='HTML',
        disable_web_page_preview=True,
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کلیک روی دکمه‌ها"""
    query = update.callback_query
    user = query.from_user
    await query.answer()
    
    if query.data == 'add_cli':
        if user.id != OWNER_ID:
            await query.edit_message_text(
                "⛔ <b>دسترسی غیرمجاز!</b>\n\nشما اجازه ساخت CLI را ندارید.",
                parse_mode='HTML'
            )
            return
        
        context.user_data['step'] = PHONE
        await query.edit_message_text(
            "📱 <b>لطفاً شماره تلفن خود را وارد کنید</b>\n\n"
            "⚠️ شماره را با کد کشور وارد کنید (مثال: +989123456789)",
            parse_mode='HTML'
        )
        return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت شماره تلفن و ارسال کد"""
    phone = update.message.text.strip()
    
    if not re.match(r'^\+?\d{10,15}$', phone):
        await update.message.reply_text(
            "❌ <b>فرمت شماره نامعتبر!</b>\n\n"
            "لطفاً شماره را با کد کشور وارد کنید.\n"
            "مثال: +989123456789",
            parse_mode='HTML'
        )
        return PHONE
    
    try:
        # ساخت کلاینت برای ارسال کد
        client = Client(
            SESSION_NAME,
            api_id=API_ID,
            api_hash=API_HASH
        )
        
        await client.connect()
        
        # ارسال درخواست کد
        sent_code = await client.send_code(phone)
        
        # ذخیره اطلاعات برای مرحله بعد
        context.user_data['phone'] = phone
        context.user_data['client'] = client
        context.user_data['phone_code_hash'] = sent_code.phone_code_hash
        context.user_data['step'] = CODE
        
        await update.message.reply_text(
            "✅ <b>کد تایید ارسال شد!</b>\n\n"
            "📨 لطفاً کد ۵ رقمی دریافت شده را وارد کنید:",
            parse_mode='HTML'
        )
        return CODE
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ <b>خطا در ارسال کد!</b>\n\n{str(e)}",
            parse_mode='HTML'
        )
        return ConversationHandler.END

async def get_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت کد و تکمیل ساخت سشن"""
    code = update.message.text.strip()
    client = context.user_data.get('client')
    phone = context.user_data.get('phone')
    phone_code_hash = context.user_data.get('phone_code_hash')
    
    if not client:
        await update.message.reply_text(
            "❌ <b>خطا!</b>\n\nلطفاً دوباره تلاش کنید.",
            parse_mode='HTML'
        )
        return ConversationHandler.END
    
    try:
        # تایید کد و ورود
        await client.sign_in(
            phone_number=phone,
            phone_code_hash=phone_code_hash,
            phone_code=code
        )
        
        # گرفتن اطلاعات کاربر
        me = await client.get_me()
        
        # ذخیره سشن
        await client.disconnect()
        
        await update.message.reply_text(
            f"✅ <b>سشن با موفقیت ساخته شد!</b>\n\n"
            f"👤 نام: {me.first_name}\n"
            f"🆔 ID: <code>{me.id}</code>\n"
            f"📱 یوزرنیم: @{me.username}\n"
            f"📞 شماره: {phone}\n\n"
            f"🔑 فایل سشن: <code>{SESSION_NAME}.session</code>\n\n"
            f"⚠️ این فایل رو در جای امن نگه دار!",
            parse_mode='HTML'
        )
        
        # پاک کردن اطلاعات جلسه
        context.user_data.clear()
        return ConversationHandler.END
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ <b>خطا در تایید کد!</b>\n\n{str(e)}\n\n"
            "لطفاً کد را مجدداً وارد کنید:",
            parse_mode='HTML'
        )
        return CODE

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو فرآیند ساخت CLI"""
    client = context.user_data.get('client')
    if client:
        try:
            await client.disconnect()
        except:
            pass
    
    context.user_data.clear()
    await update.message.reply_text(
        "❌ <b>فرآیند ساخت CLI لغو شد.</b>",
        parse_mode='HTML'
    )
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر /help"""
    help_text = """
🤖 <b>راهنمای ربات ZX Music Player</b>

📌 <b>دستورات اصلی:</b>
• /start - شروع و مشاهده پیام خوش‌آمدگویی
• /help - نمایش این راهنما
• /ping - بررسی وضعیت ربات

🎵 <b>دستورات موزیک:</b>
(به زودی اضافه می‌شوند)

📞 <b>پشتیبانی:</b>
در صورت نیاز به کمک، با ما تماس بگیرید.
    """
    await update.message.reply_text(help_text, parse_mode='HTML')

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر /ping"""
    await update.message.reply_text(
        "🏓 <b>پنگ!</b>\nربات فعال و سالم است ✅", 
        parse_mode='HTML'
    )

if __name__ == '__main__':
    try:
        application = ApplicationBuilder().token(TOKEN).build()
        
        application.add_handler(CommandHandler('start', start))
        application.add_handler(CommandHandler('help', help_command))
        application.add_handler(CommandHandler('ping', ping))
        application.add_handler(CallbackQueryHandler(button_callback))
        
        # هندلر مکالمه برای ساخت CLI
        conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(button_callback, pattern='^add_cli$')],
            states={
                PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
                CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_code)],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )
        application.add_handler(conv_handler)
        
        print(f"🚀 ربات در حال روشن شدن با Polling...")
        print(f"✅ Webhook قبلی پاک شده")
        print(f"👑 آیدی سازنده: {OWNER_ID}")
        print(f"📱 آماده ساخت سشن با نام: {SESSION_NAME}")
        print(f"🆔 API_ID: {API_ID}")
        
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=['message', 'callback_query'],
            poll_interval=1.0,
            timeout=10
        )
        
    except Exception as e:
        print(f"❌ خطا: {e}")
