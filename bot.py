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

# اطلاعات سشن
API_ID = 37160656
API_HASH = "c75ef3eadae1ffb6cad9d6736d0e2323"
SESSION_NAME = os.getenv('SESSION_NAME', 'my_session')

# آیدی عددی سازنده ربات (فقط این شخص میتونه سشن بسازه)
OWNER_ID = 8831703400  # آیدی عددی شما

# لینک‌ها
SUPPORT_LINK = "https://t.me/XMrHadi"
CHANNEL_LINK = "https://t.me/ReaperMusicTM"
GROUP_LINK = "https://t.me/ReaperVoidGP"
BOT_LINK = "https://t.me/Reaper_Musicbot?startgroup=new"

# مراحل ساخت CLI
PHONE, IP, IP_HASH, CODE = range(4)

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

# متن استارت عمومی (برای کاربران عادی)
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
    
    # بررسی اینکه آیا کاربر سازنده است یا خیر
    is_owner = (user.id == OWNER_ID)
    
    if is_owner:
        # متن مخصوص سازنده
        final_text = OWNER_START_TEXT.replace("[ نام کاربر منشن شده ]", user_mention)
        
        # دکمه‌های مخصوص سازنده
        keyboard = [
            [
                InlineKeyboardButton("🔧 افزودن CLI", callback_data='add_cli')
            ],
            [
                InlineKeyboardButton("📞 پشتیبانی", callback_data='support'),
                InlineKeyboardButton("📢 کانال ربات", callback_data='channel')
            ],
            [
                InlineKeyboardButton("👥 گروه پشتیبانی", callback_data='group'),
                InlineKeyboardButton("➕ اضافه کردن به گروه", callback_data='add_to_group')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
    else:
        # متن عمومی برای دیگر کاربران
        final_text = PUBLIC_START_TEXT.replace("[ نام کاربر منشن شده ]", user_mention)
        
        # دکمه‌های عمومی
        keyboard = [
            [
                InlineKeyboardButton("📞 پشتیبانی", callback_data='support'),
                InlineKeyboardButton("📢 کانال ربات", callback_data='channel')
            ],
            [
                InlineKeyboardButton("👥 گروه پشتیبانی", callback_data='group'),
                InlineKeyboardButton("➕ اضافه کردن به گروه", callback_data='add_to_group')
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
    
    if query.data == 'support':
        await query.edit_message_text(
            f"📞 <b>پشتیبانی</b>\n\nبرای ارتباط با پشتیبانی روی لینک زیر کلیک کن:\n\n🔗 <a href='{SUPPORT_LINK}'>ارتباط با پشتیبانی</a>",
            parse_mode='HTML',
            disable_web_page_preview=True
        )
    elif query.data == 'channel':
        await query.edit_message_text(
            f"📢 <b>کانال ربات</b>\n\nبرای عضویت در کانال ربات روی لینک زیر کلیک کن:\n\n🔗 <a href='{CHANNEL_LINK}'>عضویت در کانال</a>",
            parse_mode='HTML',
            disable_web_page_preview=True
        )
    elif query.data == 'group':
        await query.edit_message_text(
            f"👥 <b>گروه پشتیبانی</b>\n\nبرای عضویت در گروه پشتیبانی روی لینک زیر کلیک کن:\n\n🔗 <a href='{GROUP_LINK}'>عضویت در گروه</a>",
            parse_mode='HTML',
            disable_web_page_preview=True
        )
    elif query.data == 'add_to_group':
        await query.edit_message_text(
            f"➕ <b>اضافه کردن ربات به گروه</b>\n\nبرای اضافه کردن ربات به گروهت، روی لینک زیر کلیک کن:\n\n🔗 <a href='{BOT_LINK}'>اضافه کردن ربات</a>",
            parse_mode='HTML',
            disable_web_page_preview=True
        )
    elif query.data == 'add_cli':
        # فقط سازنده میتونه CLI بسازه
        if user.id != OWNER_ID:
            await query.edit_message_text(
                "⛔ <b>دسترسی غیرمجاز!</b>\n\nشما اجازه ساخت CLI را ندارید.",
                parse_mode='HTML'
            )
            return
        
        # شروع فرآیند ساخت CLI
        context.user_data['cli_step'] = PHONE
        await query.edit_message_text(
            "📱 <b>لطفاً شماره تلفن CLI را ارسال کنید</b>\n\n"
            "⚠️ شماره را با کد کشور وارد کنید (مثال: +989123456789)",
            parse_mode='HTML'
        )
        return PHONE

async def cli_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت شماره تلفن برای CLI"""
    phone = update.message.text.strip()
    
    # بررسی فرمت شماره
    if not re.match(r'^\+?\d{10,15}$', phone):
        await update.message.reply_text(
            "❌ <b>فرمت شماره نامعتبر!</b>\n\n"
            "لطفاً شماره را با کد کشور وارد کنید.\n"
            "مثال: +989123456789",
            parse_mode='HTML'
        )
        return PHONE
    
    context.user_data['cli_phone'] = phone
    context.user_data['cli_step'] = IP
    
    await update.message.reply_text(
        "🌐 <b>لطفاً آیپی عددی را وارد کنید</b>\n\n"
        "مثال: 192.168.1.1",
        parse_mode='HTML'
    )
    return IP

async def cli_ip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت آیپی برای CLI"""
    ip = update.message.text.strip()
    
    # بررسی فرمت آیپی
    if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
        await update.message.reply_text(
            "❌ <b>فرمت آیپی نامعتبر!</b>\n\n"
            "لطفاً یک آیپی معتبر وارد کنید.\n"
            "مثال: 192.168.1.1",
            parse_mode='HTML'
        )
        return IP
    
    context.user_data['cli_ip'] = ip
    context.user_data['cli_step'] = IP_HASH
    
    await update.message.reply_text(
        "🔑 <b>لطفاً آیپی هش را وارد کنید</b>\n\n"
        "این کد از سمت سرور به شما داده می‌شود.",
        parse_mode='HTML'
    )
    return IP_HASH

async def cli_ip_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت آیپی هش برای CLI"""
    ip_hash = update.message.text.strip()
    
    context.user_data['cli_ip_hash'] = ip_hash
    
    # ارسال کد تایید به شماره
    try:
        # اینجا باید کد ارسال بشه - در حال حاضر شبیه‌سازی
        await update.message.reply_text(
            "📨 <b>کد تایید به شماره شما ارسال شد!</b>\n\n"
            "لطفاً کد ۵ رقمی را وارد کنید:",
            parse_mode='HTML'
        )
        context.user_data['cli_step'] = CODE
        return CODE
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ <b>خطا در ارسال کد!</b>\n\n{str(e)}",
            parse_mode='HTML'
        )
        return ConversationHandler.END

async def cli_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت کد تایید و ساخت سشن"""
    code = update.message.text.strip()
    
    # ساخت سشن با اطلاعات دریافت شده
    try:
        # ساخت کلاینت Pyrogram
        app = Client(
            SESSION_NAME,
            api_id=API_ID,
            api_hash=API_HASH
        )
        
        await app.start()
        me = await app.get_me()
        
        await update.message.reply_text(
            f"✅ <b>سشن با موفقیت ساخته شد!</b>\n\n"
            f"👤 نام: {me.first_name}\n"
            f"🆔 ID: <code>{me.id}</code>\n"
            f"📱 یوزرنیم: @{me.username}\n"
            f"📞 شماره: {context.user_data.get('cli_phone')}\n"
            f"🌐 آیپی: {context.user_data.get('cli_ip')}\n\n"
            f"🔑 فایل سشن: <code>{SESSION_NAME}.session</code>\n\n"
            f"⚠️ این فایل رو در جای امن نگه دار!",
            parse_mode='HTML'
        )
        
        # پاک کردن اطلاعات جلسه
        context.user_data.clear()
        return ConversationHandler.END
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ <b>خطا در ساخت سشن!</b>\n\n{str(e)}",
            parse_mode='HTML'
        )
        context.user_data.clear()
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو فرآیند ساخت CLI"""
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
        
        # اضافه کردن هندلرها
        application.add_handler(CommandHandler('start', start))
        application.add_handler(CommandHandler('help', help_command))
        application.add_handler(CommandHandler('ping', ping))
        application.add_handler(CallbackQueryHandler(button_callback))
        
        # هندلر مکالمه برای ساخت CLI
        conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(button_callback, pattern='^add_cli$')],
            states={
                PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, cli_phone)],
                IP: [MessageHandler(filters.TEXT & ~filters.COMMAND, cli_ip)],
                IP_HASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, cli_ip_hash)],
                CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, cli_code)],
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
