import os
import logging
import httpx
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler
from pyrogram import Client

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

# اطلاعات سشن
API_ID = 37160656
API_HASH = "c75ef3eadae1ffb6cad9d6736d0e2323"
SESSION_NAME = os.getenv('SESSION_NAME', 'my_session')

# پاک کردن Webhook قبلی با چند بار تلاش
for i in range(3):
    try:
        response = httpx.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook")
        if response.json().get('ok'):
            print("✅ Webhook قبلی پاک شد")
            break
    except Exception as e:
        print(f"⚠️ تلاش {i+1} برای پاک کردن Webhook ناموفق بود: {e}")
        time.sleep(1)

# پاک کردن Webhook از طریق روش جایگزین
try:
    response = httpx.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=True")
    if response.json().get('ok'):
        print("✅ Webhook با drop_pending_updates پاک شد")
except Exception as e:
    print(f"⚠️ خطا: {e}")

# متن استارت
START_TEXT = """
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

async def create_session():
    """ساخت سشن کاربر با Pyrogram"""
    try:
        app = Client(
            SESSION_NAME,
            api_id=API_ID,
            api_hash=API_HASH
        )
        
        await app.start()
        me = await app.get_me()
        
        print(f"✅ سشن ساخته شد برای: {me.first_name}")
        print(f"🆔 ID: {me.id}")
        print(f"📱 @{me.username}")
        
        return app, me
        
    except Exception as e:
        print(f"❌ خطا در ساخت سشن: {e}")
        return None, None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر /start با دکمه‌های inline"""
    user = update.effective_user
    user_mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
    final_text = START_TEXT.replace("[ نام کاربر منشن شده ]", user_mention)
    
    keyboard = [
        [
            InlineKeyboardButton("📞 پشتیبانی", callback_data='support'),
            InlineKeyboardButton("📢 کانال ربات", callback_data='channel')
        ],
        [
            InlineKeyboardButton("👥 گروه پشتیبانی", callback_data='group'),
            InlineKeyboardButton("➕ اضافه کردن به گروه", callback_data='add_to_group')
        ],
        [
            InlineKeyboardButton("🔑 ساخت سشن", callback_data='create_session')
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
    await query.answer()
    
    if query.data == 'support':
        await query.edit_message_text(
            "📞 <b>پشتیبانی</b>\n\nبرای ارتباط با پشتیبانی روی لینک زیر کلیک کن:\n\n🔗 [ارتباط با پشتیبانی](https://t.me/YourSupportUsername)",
            parse_mode='HTML',
            disable_web_page_preview=True
        )
    elif query.data == 'channel':
        await query.edit_message_text(
            "📢 <b>کانال ربات</b>\n\nبرای عضویت در کانال ربات روی لینک زیر کلیک کن:\n\n🔗 [عضویت در کانال](https://t.me/YourChannelUsername)",
            parse_mode='HTML',
            disable_web_page_preview=True
        )
    elif query.data == 'group':
        await query.edit_message_text(
            "👥 <b>گروه پشتیبانی</b>\n\nبرای عضویت در گروه پشتیبانی روی لینک زیر کلیک کن:\n\n🔗 [عضویت در گروه](https://t.me/YourGroupUsername)",
            parse_mode='HTML',
            disable_web_page_preview=True
        )
    elif query.data == 'add_to_group':
        await query.edit_message_text(
            "➕ <b>اضافه کردن ربات به گروه</b>\n\nبرای اضافه کردن ربات به گروهت، روی لینک زیر کلیک کن:\n\n🔗 [اضافه کردن ربات](https://t.me/YourBotUsername?startgroup=start)",
            parse_mode='HTML',
            disable_web_page_preview=True
        )
    elif query.data == 'create_session':
        await query.edit_message_text(
            "🔄 <b>در حال ساخت سشن...</b>\n\nلطفاً صبر کنید...",
            parse_mode='HTML'
        )
        
        app, me = await create_session()
        
        if app and me:
            await query.edit_message_text(
                f"✅ <b>سشن ساخته شد!</b>\n\n"
                f"👤 نام: {me.first_name}\n"
                f"🆔 ID: <code>{me.id}</code>\n"
                f"📱 یوزرنیم: @{me.username}\n\n"
                f"🔑 فایل سشن: <code>{SESSION_NAME}.session</code>",
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text(
                "❌ <b>خطا در ساخت سشن!</b>\n\n"
                "لطفاً API_ID و API_HASH رو بررسی کن.",
                parse_mode='HTML'
            )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر /help"""
    help_text = """
🤖 <b>راهنمای ربات ZX Music Player</b>

📌 <b>دستورات اصلی:</b>
• /start - شروع و مشاهده پیام خوش‌آمدگویی
• /help - نمایش این راهنما
• /ping - بررسی وضعیت ربات
• /session - ساخت سشن Pyrogram

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

async def session_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر /session برای ساخت سشن"""
    await update.message.reply_text(
        "🔄 <b>در حال ساخت سشن...</b>\n\nلطفاً صبر کنید...",
        parse_mode='HTML'
    )
    
    app, me = await create_session()
    
    if app and me:
        await update.message.reply_text(
            f"✅ <b>سشن ساخته شد!</b>\n\n"
            f"👤 نام: {me.first_name}\n"
            f"🆔 ID: <code>{me.id}</code>\n"
            f"📱 یوزرنیم: @{me.username}\n\n"
            f"🔑 فایل سشن: <code>{SESSION_NAME}.session</code>",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            "❌ <b>خطا در ساخت سشن!</b>\n\n"
            "لطفاً API_ID و API_HASH رو بررسی کن.",
            parse_mode='HTML'
        )

if __name__ == '__main__':
    try:
        application = ApplicationBuilder().token(TOKEN).build()
        
        application.add_handler(CommandHandler('start', start))
        application.add_handler(CommandHandler('help', help_command))
        application.add_handler(CommandHandler('ping', ping))
        application.add_handler(CommandHandler('session', session_command))
        application.add_handler(CallbackQueryHandler(button_callback))
        
        print(f"🚀 ربات در حال روشن شدن با Polling...")
        print(f"✅ Webhook قبلی پاک شده")
        print(f"📱 آماده ساخت سشن با نام: {SESSION_NAME}")
        print(f"🆔 API_ID: {API_ID}")
        
        # راه‌اندازی با Polling و تنظیمات ویژه برای جلوگیری از Conflict
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=['message', 'callback_query'],
            poll_interval=1.0,
            timeout=10
        )
        
    except Exception as e:
        print(f"❌ خطا: {e}")
