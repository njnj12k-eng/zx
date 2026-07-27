import os
import logging
import httpx
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from pyrogram import Client
from pyrogram.errors import ApiIdInvalid, PhoneNumberInvalid, PasswordHashInvalid

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

# متغیرهای ذخیره موقت برای فرآیند ساخت سشن
user_sessions = {}

# پاک کردن Webhook قبلی
try:
    response = httpx.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook")
    if response.json().get('ok'):
        print("✅ Webhook قبلی پاک شد")
except Exception as e:
    print(f"⚠️ خطا در پاک کردن Webhook: {e}")

# متن استارت اصلی (همان متن قبلی)
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

# متن اختصاصی برای سازنده ربات
OWNER_START_TEXT = """
🌟 <b>سلام برنامه‌نویس عزیز!</b> 🌹

⫸ به پنل مدیریتی ربات ZX Music Player خوش آمدید! 🚀

◂ شما به عنوان <b>سازنده اصلی</b> این ربات، دسترسی ویژه به امکانات مدیریتی دارید.

◄ <b>از طریق این پنل می‌توانید:</b>
  ◂ سشن تلگرام برای پخش موزیک در ویس چت بسازید
  ◂ ربات را مدیریت کنید
  ◂ تنظیمات پیشرفته را اعمال کنید

⚡ <b>وضعیت ربات:</b> فعال ✅
📊 <b>تعداد کاربران:</b> در حال دریافت...
🔄 <b>نسخه:</b> 2.0.0

【 <b>Licenced By 🆉︎🆇︎</b> 】
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر /start با تشخیص سازنده"""
    user = update.effective_user
    user_id = user.id
    
    # بررسی اینکه آیا کاربر سازنده ربات است
    if user_id == OWNER_ID:
        # نمایش متن اختصاصی برای سازنده
        owner_text = f"{OWNER_START_TEXT}"
        
        # دکمه افزودن CLI برای سازنده
        keyboard = [
            [InlineKeyboardButton("⚙️ افزودن CLI", callback_data='add_cli')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            owner_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    else:
        # نمایش متن معمولی برای کاربران عادی
        user_mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
        final_text = START_TEXT.replace("[ نام کاربر منشن شده ]", user_mention)
        
        keyboard = [
            [
                InlineKeyboardButton("📞 پشتیبانی", url="https://t.me/XMrHadi"),
                InlineKeyboardButton("📢 کانال ربات", url="https://t.me/ReaperMusicTM")
            ],
            [
                InlineKeyboardButton("👥 گروه پشتیبانی", url="https://t.me/ReaperVoidGP"),
                InlineKeyboardButton("➕ اضافه کردن به گروه", url="https://t.me/Reaper_Musicbot?startgroup=new")
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
    user_id = query.from_user.id
    
    # فقط سازنده می‌تواند از دکمه افزودن CLI استفاده کند
    if user_id != OWNER_ID:
        await query.answer("⛔ شما دسترسی به این بخش را ندارید!", show_alert=True)
        return
    
    await query.answer()
    
    if query.data == 'add_cli':
        # شروع فرآیند ساخت سشن
        user_sessions[user_id] = {'step': 'phone'}
        
        await query.edit_message_text(
            "📱 <b>افزودن CLI جدید</b>\n\n"
            "◄ لطفاً <b>شماره تلفن</b> اکانت تلگرام خود را به همراه کد کشور ارسال کنید.\n\n"
            "◂ مثال: <code>+989123456789</code>\n\n"
            "⫸ برای لغو عملیات، دستور /cancel را ارسال کنید.",
            parse_mode='HTML'
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت پیام‌های دریافتی برای فرآیند ساخت سشن"""
    user_id = update.effective_user.id
    
    # فقط سازنده می‌تواند از این فرآیند استفاده کند
    if user_id != OWNER_ID:
        return
    
    # بررسی اینکه کاربر در فرآیند ساخت سشن است
    if user_id not in user_sessions:
        return
    
    text = update.message.text
    step = user_sessions[user_id]['step']
    
    if step == 'phone':
        # دریافت شماره تلفن
        phone = text.strip()
        
        # اعتبارسنجی ساده شماره
        if not phone.startswith('+') or not phone[1:].isdigit():
            await update.message.reply_text(
                "❌ <b>فرمت شماره تلفن نامعتبر!</b>\n\n"
                "◄ لطفاً شماره را به همراه کد کشور و با فرمت صحیح ارسال کنید.\n"
                "◂ مثال: <code>+989123456789</code>",
                parse_mode='HTML'
            )
            return
        
        user_sessions[user_id]['phone'] = phone
        user_sessions[user_id]['step'] = 'ip'
        
        await update.message.reply_text(
            "🌐 <b>مرحله بعد: وارد کردن آیپی عددی</b>\n\n"
            "◄ لطفاً <b>آیپی عددی</b> سرور یا دستگاه خود را وارد کنید.\n"
            "◂ مثال: <code>192.168.1.100</code>\n\n"
            "⫸ می‌توانید از آیپی محلی یا عمومی استفاده کنید.",
            parse_mode='HTML'
        )
    
    elif step == 'ip':
        # دریافت آیپی
        ip = text.strip()
        
        # اعتبارسنجی ساده آیپی
        import re
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(ip_pattern, ip):
            await update.message.reply_text(
                "❌ <b>فرمت آیپی نامعتبر!</b>\n\n"
                "◄ لطفاً یک آیپی معتبر وارد کنید.\n"
                "◂ مثال: <code>192.168.1.100</code>",
                parse_mode='HTML'
            )
            return
        
        user_sessions[user_id]['ip'] = ip
        user_sessions[user_id]['step'] = 'hash'
        
        await update.message.reply_text(
            "🔑 <b>مرحله آخر: وارد کردن آیپی هش</b>\n\n"
            "◄ لطفاً <b>آیپی هش</b> (HASH) مربوط به دستگاه خود را وارد کنید.\n"
            "◂ این کد را می‌توانید از تنظیمات دستگاه خود دریافت کنید.\n\n"
            "⫸ مثال: <code>a1b2c3d4e5f6g7h8i9j0</code>",
            parse_mode='HTML'
        )
    
    elif step == 'hash':
        # دریافت هش
        hash_value = text.strip()
        
        if len(hash_value) < 10:
            await update.message.reply_text(
                "❌ <b>هش وارد شده کوتاه است!</b>\n\n"
                "◄ لطفاً یک هش معتبر با حداقل ۱۰ کاراکتر وارد کنید.",
                parse_mode='HTML'
            )
            return
        
        user_sessions[user_id]['hash'] = hash_value
        user_sessions[user_id]['step'] = 'code'
        
        # ارسال کد تایید به شماره کاربر
        await send_verification_code(user_id)
    
    elif step == 'code':
        # دریافت کد تایید
        code = text.strip()
        
        if not code.isdigit():
            await update.message.reply_text(
                "❌ <b>کد وارد شده نامعتبر!</b>\n\n"
                "◄ لطفاً کد عددی ۵ رقمی ارسال شده را وارد کنید.",
                parse_mode='HTML'
            )
            return
        
        # ساخت سشن
        await create_session(user_id, code)

async def send_verification_code(user_id):
    """ارسال کد تایید به شماره کاربر"""
    phone = user_sessions[user_id]['phone']
    ip = user_sessions[user_id]['ip']
    hash_value = user_sessions[user_id]['hash']
    
    try:
        # ایجاد کلاینت موقت برای ارسال کد
        app = Client(
            f"session_{user_id}",
            api_id=hash_value,  # توجه: اینجا باید API ID واقعی باشه
            api_hash=ip,        # توجه: اینجا باید API HASH واقعی باشه
            phone_number=phone
        )
        
        await app.connect()
        sent_code = await app.send_code(phone)
        
        # ذخیره اطلاعات برای مرحله بعد
        user_sessions[user_id]['client'] = app
        user_sessions[user_id]['phone_code_hash'] = sent_code.phone_code_hash
        
        await app.disconnect()
        
        await update.message.reply_text(
            "📨 <b>کد تایید ارسال شد!</b>\n\n"
            "◄ لطفاً کد ۵ رقمی دریافت شده را وارد کنید.\n"
            "◂ کد به شماره <code>{}</code> ارسال شده است.\n\n"
            "⫸ برای لغو عملیات، دستور /cancel را ارسال کنید.".format(phone),
            parse_mode='HTML'
        )
        
        user_sessions[user_id]['step'] = 'code'
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ <b>خطا در ارسال کد!</b>\n\n"
            f"◄ خطا: <code>{str(e)}</code>\n\n"
            "◂ لطفاً اطلاعات وارد شده را بررسی کنید و دوباره تلاش کنید.\n"
            "⫸ برای شروع مجدد، روی دکمه افزودن CLI کلیک کنید.",
            parse_mode='HTML'
        )
        # پاک کردن جلسه در صورت خطا
        if user_id in user_sessions:
            del user_sessions[user_id]

async def create_session(user_id, code):
    """ساخت سشن نهایی با کد تایید"""
    try:
        phone = user_sessions[user_id]['phone']
        ip = user_sessions[user_id]['ip']
        hash_value = user_sessions[user_id]['hash']
        phone_code_hash = user_sessions[user_id].get('phone_code_hash')
        
        # ایجاد کلاینت برای ساخت سشن
        app = Client(
            f"session_{user_id}",
            api_id=hash_value,
            api_hash=ip,
            phone_number=phone
        )
        
        await app.connect()
        
        # تایید کد
        await app.sign_in(
            phone_number=phone,
            phone_code_hash=phone_code_hash,
            phone_code=code
        )
        
        # ذخیره سشن
        session_string = await app.export_session_string()
        
        # ذخیره در دیتابیس یا فایل (در اینجا فقط نمایش داده میشه)
        await update.message.reply_text(
            "✅ <b>سشن با موفقیت ساخته شد!</b>\n\n"
            "🔑 <b>سشن استرینگ:</b>\n"
            f"<code>{session_string}</code>\n\n"
            "◄ این سشن برای پخش موزیک در ویس چت استفاده خواهد شد.\n"
            "◂ لطفاً این اطلاعات را در جای امن نگهداری کنید.\n\n"
            "⫸ ربات آماده پخش موزیک در ویس چت است! 🎵",
            parse_mode='HTML'
        )
        
        await app.disconnect()
        
        # پاک کردن جلسه کاربر
        if user_id in user_sessions:
            del user_sessions[user_id]
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ <b>خطا در ساخت سشن!</b>\n\n"
            f"◄ خطا: <code>{str(e)}</code>\n\n"
            "◂ لطفاً کد وارد شده را بررسی کنید و دوباره تلاش کنید.\n"
            "⫸ برای شروع مجدد، روی دکمه افزودن CLI کلیک کنید.",
            parse_mode='HTML'
        )
        
        # پاک کردن جلسه در صورت خطا
        if user_id in user_sessions:
            del user_sessions[user_id]

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر /cancel برای لغو عملیات"""
    user_id = update.effective_user.id
    
    if user_id in user_sessions:
        # پاک کردن کلاینت در صورت وجود
        if 'client' in user_sessions[user_id]:
            try:
                await user_sessions[user_id]['client'].disconnect()
            except:
                pass
        
        del user_sessions[user_id]
        
        await update.message.reply_text(
            "❌ <b>عملیات لغو شد!</b>\n\n"
            "◄ فرآیند ساخت سشن با موفقیت لغو شد.\n"
            "◂ برای شروع مجدد، دستور /start را ارسال کنید.",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            "ℹ️ <b>هیچ عملیات فعالی برای لغو وجود ندارد!</b>",
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
• /cancel - لغو عملیات جاری

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
        # ساخت اپلیکیشن
        application = ApplicationBuilder().token(TOKEN).build()
        
        # اضافه کردن هندلرها
        application.add_handler(CommandHandler('start', start))
        application.add_handler(CommandHandler('help', help_command))
        application.add_handler(CommandHandler('ping', ping))
        application.add_handler(CommandHandler('cancel', cancel_command))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        print(f"🚀 ربات در حال روشن شدن با Polling...")
        print(f"✅ Webhook قبلی پاک شده")
        print(f"👤 سازنده ربات: {OWNER_ID}")
        
        # راه‌اندازی با Polling
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=['message', 'callback_query']
        )
        
    except Exception as e:
        print(f"❌ خطا: {e}")
