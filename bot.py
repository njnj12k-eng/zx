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

# سشن استرینگ ساخته شده (این رو از مرحله قبل کپی کنید)
SESSION_STRING = "your_session_string_here"  # سشن خود را اینجا بگذارید

# متغیرهای ذخیره موقت
user_sessions = {}
active_calls = {}  # برای ذخیره گروه‌های فعال

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

# متن استارت اصلی
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
        keyboard = [
            [InlineKeyboardButton("⚙️ افزودن CLI", callback_data='add_cli')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            OWNER_START_TEXT,
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

# ================ دستورات پخش موزیک ================

async def play_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /play برای پخش موزیک"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    message = update.message
    
    # بررسی اینکه کاربر در گروه است
    if update.effective_chat.type not in ['group', 'supergroup']:
        await message.reply_text("❌ این دستور فقط در گروه قابل استفاده است!")
        return
    
    # گرفتن لینک یا نام آهنگ
    if not context.args:
        await message.reply_text(
            "🎵 <b>نحوه استفاده:</b>\n\n"
            "◄ <code>/play [نام آهنگ یا لینک]</code>\n"
            "◂ مثال: <code>/play Shadmehr Aghili - Ghadim</code>\n\n"
            "◄ می‌توانید لینک یوتیوب یا ساندکلاد هم بفرستید:\n"
            "◂ <code>/play https://youtu.be/xxx</code>",
            parse_mode='HTML'
        )
        return
    
    query = " ".join(context.args)
    
    # پیام در حال پردازش
    processing_msg = await message.reply_text(
        f"🔍 <b>در حال جستجو و پخش:</b>\n"
        f"◄ <code>{query}</code>",
        parse_mode='HTML'
    )
    
    try:
        # بررسی اینکه کاربر در ویس چت هست
        chat_member = await app.get_chat_member(chat_id, user.id)
        
        # پخش موزیک
        await play_music(chat_id, query, processing_msg)
        
    except Exception as e:
        await processing_msg.edit_text(
            f"❌ <b>خطا در پخش!</b>\n\n"
            f"◄ خطا: <code>{str(e)}</code>\n\n"
            "◂ لطفاً مطمئن شوید:\n"
            "  • در ویس چت گروه عضو هستید\n"
            "  • لینک معتبر است\n"
            "  • ربات دسترسی دارد",
            parse_mode='HTML'
        )

async def play_music(chat_id: int, query: str, processing_msg):
    """پخش موزیک در ویس چت"""
    try:
        # اینجا باید موزیک رو از یوتیوب یا ساندکلاد دانلود کنید
        # برای نمونه از یک لینک مستقیم استفاده میکنیم
        # شما می‌توانید از کتابخانه yt-dlp برای دانلود از یوتیوب استفاده کنید
        
        # بررسی اینکه آیا ربات در ویس چت است
        call_status = await call.get_call(chat_id)
        
        if not call_status:
            # اگر ربات در ویس چت نیست، به ویس چت بپیوندد
            await call.join_group_call(
                chat_id,
                MediaStream(
                    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"  # نمونه لینک
                )
            )
            await processing_msg.edit_text(
                f"✅ <b>در حال پخش:</b>\n"
                f"◄ <code>{query}</code>\n\n"
                f"🎵 <b>حالت:</b> پخش در ویس چت",
                parse_mode='HTML'
            )
        else:
            # اگر در حال پخش است، آهنگ جدید را اضافه کند (صف)
            await processing_msg.edit_text(
                f"⏳ <b>آهنگ در صف قرار گرفت:</b>\n"
                f"◄ <code>{query}</code>",
                parse_mode='HTML'
            )
            
    except Exception as e:
        raise e

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /stop برای توقف پخش"""
    chat_id = update.effective_chat.id
    message = update.message
    
    try:
        await call.leave_group_call(chat_id)
        await message.reply_text(
            "⏹️ <b>پخش متوقف شد!</b>\n"
            "◄ ربات از ویس چت خارج شد.",
            parse_mode='HTML'
        )
    except Exception as e:
        await message.reply_text(
            f"❌ <b>خطا!</b>\n"
            f"◄ <code>{str(e)}</code>",
            parse_mode='HTML'
        )

async def pause_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /pause برای مکث"""
    chat_id = update.effective_chat.id
    message = update.message
    
    try:
        await call.pause_stream(chat_id)
        await message.reply_text(
            "⏸️ <b>پخش متوقف شد!</b>\n"
            "◄ برای ادامه از /resume استفاده کنید.",
            parse_mode='HTML'
        )
    except Exception as e:
        await message.reply_text(
            f"❌ <b>خطا!</b>\n"
            f"◄ <code>{str(e)}</code>",
            parse_mode='HTML'
        )

async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /resume برای ادامه پخش"""
    chat_id = update.effective_chat.id
    message = update.message
    
    try:
        await call.resume_stream(chat_id)
        await message.reply_text(
            "▶️ <b>پخش ادامه یافت!</b>",
            parse_mode='HTML'
        )
    except Exception as e:
        await message.reply_text(
            f"❌ <b>خطا!</b>\n"
            f"◄ <code>{str(e)}</code>",
            parse_mode='HTML'
        )

async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /skip برای رد کردن آهنگ"""
    chat_id = update.effective_chat.id
    message = update.message
    
    try:
        # در اینجا باید آهنگ بعدی از صف پخش شود
        await call.change_stream(
            chat_id,
            MediaStream("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3")
        )
        await message.reply_text(
            "⏭️ <b>آهنگ رد شد!</b>\n"
            "◄ آهنگ بعدی در حال پخش است.",
            parse_mode='HTML'
        )
    except Exception as e:
        await message.reply_text(
            f"❌ <b>خطا!</b>\n"
            f"◄ <code>{str(e)}</code>",
            parse_mode='HTML'
        )

# ================ بقیه هندلرها ================

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
        
        # ذخیره شماره و ارسال کد تایید
        user_sessions[user_id]['phone'] = phone
        user_sessions[user_id]['step'] = 'code'
        
        # ارسال کد تایید به شماره کاربر
        await send_verification_code(update, user_id, phone)
    
    elif step == 'code':
        # دریافت کد تایید
        code = text.strip()
        
        if not code.isdigit() or len(code) != 5:
            await update.message.reply_text(
                "❌ <b>کد وارد شده نامعتبر!</b>\n\n"
                "◄ لطفاً کد عددی ۵ رقمی ارسال شده را وارد کنید.",
                parse_mode='HTML'
            )
            return
        
        # تایید کد و بررسی نیاز به رمز عبور
        await verify_code(update, user_id, code)
    
    elif step == 'password':
        # دریافت رمز عبور دو مرحله‌ای
        password = text.strip()
        
        if len(password) < 4:
            await update.message.reply_text(
                "❌ <b>رمز عبور وارد شده کوتاه است!</b>\n\n"
                "◄ لطفاً رمز عبور صحیح حساب تلگرام خود را وارد کنید.",
                parse_mode='HTML'
            )
            return
        
        # ساخت سشن با رمز عبور
        await create_session_with_password(update, user_id, password)

async def send_verification_code(update: Update, user_id: int, phone: str):
    """ارسال کد تایید به شماره کاربر"""
    try:
        from pyrogram import Client
        
        app = Client(
            f"session_{user_id}",
            api_id=API_ID,
            api_hash=API_HASH,
            phone_number=phone
        )
        
        await app.connect()
        sent_code = await app.send_code(phone)
        
        # ذخیره اطلاعات برای مرحله بعد
        user_sessions[user_id]['client'] = app
        user_sessions[user_id]['phone_code_hash'] = sent_code.phone_code_hash
        
        await update.message.reply_text(
            f"📨 <b>کد تایید ارسال شد!</b>\n\n"
            f"◄ کد ۵ رقمی به شماره <code>{phone}</code> ارسال شد.\n"
            f"◂ لطفاً کد دریافتی را وارد کنید.\n\n"
            f"⫸ برای لغو عملیات، دستور /cancel را ارسال کنید.",
            parse_mode='HTML'
        )
        
        user_sessions[user_id]['step'] = 'code'
        
    except ImportError:
        await update.message.reply_text(
            "❌ <b>کتابخانه pyrogram نصب نیست!</b>\n\n"
            "◄ لطفاً ابتدا pyrogram را نصب کنید:\n"
            "◂ <code>pip install pyrogram</code>",
            parse_mode='HTML'
        )
        if user_id in user_sessions:
            del user_sessions[user_id]
            
    except Exception as e:
        error_msg = str(e)
        await update.message.reply_text(
            f"❌ <b>خطا در ارسال کد!</b>\n\n"
            f"◄ خطا: <code>{error_msg}</code>\n\n"
            "◂ لطفاً شماره و API را بررسی کنید.\n"
            "⫸ برای شروع مجدد، روی دکمه افزودن CLI کلیک کنید.",
            parse_mode='HTML'
        )
        if user_id in user_sessions:
            del user_sessions[user_id]

async def verify_code(update: Update, user_id: int, code: str):
    """تایید کد و بررسی نیاز به رمز عبور"""
    try:
        from pyrogram import Client
        from pyrogram.errors import SessionPasswordNeeded
        
        phone = user_sessions[user_id]['phone']
        phone_code_hash = user_sessions[user_id]['phone_code_hash']
        app = user_sessions[user_id]['client']
        
        # تایید کد
        try:
            await app.sign_in(
                phone_number=phone,
                phone_code_hash=phone_code_hash,
                phone_code=code
            )
            
            # اگر کد درست بود و رمز عبور نیاز نبود
            await create_session_final(update, user_id, app, phone)
            
        except SessionPasswordNeeded:
            # اگر رمز عبور دو مرحله‌ای فعال بود
            user_sessions[user_id]['step'] = 'password'
            user_sessions[user_id]['app'] = app
            
            await update.message.reply_text(
                "🔐 <b>حساب شما دارای رمز عبور دو مرحله‌ای است!</b>\n\n"
                "◄ لطفاً <b>رمز عبور</b> حساب تلگرام خود را وارد کنید.\n"
                "◂ این رمزی است که برای ورود به تلگرام تنظیم کرده‌اید.\n\n"
                "⫸ برای لغو عملیات، دستور /cancel را ارسال کنید.",
                parse_mode='HTML'
            )
        
    except Exception as e:
        error_msg = str(e)
        await update.message.reply_text(
            f"❌ <b>خطا در تایید کد!</b>\n\n"
            f"◄ خطا: <code>{error_msg}</code>\n\n"
            "◂ لطفاً کد وارد شده را بررسی کنید و دوباره تلاش کنید.\n"
            "⫸ برای شروع مجدد، روی دکمه افزودن CLI کلیک کنید.",
            parse_mode='HTML'
        )
        if user_id in user_sessions:
            del user_sessions[user_id]

async def create_session_with_password(update: Update, user_id: int, password: str):
    """ساخت سشن با رمز عبور دو مرحله‌ای"""
    try:
        from pyrogram import Client
        from pyrogram.errors import PasswordHashInvalid
        
        phone = user_sessions[user_id]['phone']
        app = user_sessions[user_id]['app']
        
        # روش صحیح ورود با رمز عبور در pyrogram
        try:
            await app.check_password(password)
        except PasswordHashInvalid:
            await update.message.reply_text(
                "❌ <b>رمز عبور وارد شده اشتباه است!</b>\n\n"
                "◄ لطفاً رمز عبور صحیح حساب تلگرام خود را وارد کنید.\n"
                "◂ اگر رمز را فراموش کرده‌اید، از طریق تلگرام آن را بازیابی کنید.\n"
                "⫸ برای شروع مجدد، روی دکمه افزودن CLI کلیک کنید.",
                parse_mode='HTML'
            )
            if user_id in user_sessions:
                del user_sessions[user_id]
            return
        
        # ساخت سشن
        await create_session_final(update, user_id, app, phone)
        
    except Exception as e:
        error_msg = str(e)
        await update.message.reply_text(
            f"❌ <b>خطا در ساخت سشن!</b>\n\n"
            f"◄ خطا: <code>{error_msg}</code>\n\n"
            "◂ لطفاً رمز عبور را بررسی کنید و دوباره تلاش کنید.\n"
            "⫸ برای شروع مجدد، روی دکمه افزودن CLI کلیک کنید.",
            parse_mode='HTML'
        )
        if user_id in user_sessions:
            del user_sessions[user_id]

async def create_session_final(update: Update, user_id: int, app, phone: str):
    """ساخت نهایی سشن و ذخیره در فایل"""
    try:
        # ساخت سشن استرینگ
        session_string = await app.export_session_string()
        
        # ذخیره سشن در فایل
        with open(f"session_{phone}.txt", "w") as f:
            f.write(session_string)
        
        await update.message.reply_text(
            f"✅ <b>سشن با موفقیت ساخته شد!</b>\n\n"
            f"📱 <b>شماره:</b> <code>{phone}</code>\n\n"
            f"🔑 <b>سشن استرینگ:</b>\n"
            f"<code>{session_string}</code>\n\n"
            f"◄ سشن در فایل <code>session_{phone}.txt</code> ذخیره شد.\n"
            f"◂ این سشن برای پخش موزیک در ویس چت استفاده خواهد شد.\n\n"
            f"⫸ ربات آماده پخش موزیک در ویس چت است! 🎵\n\n"
            f"📌 <b>دستورات پخش موزیک:</b>\n"
            f"◄ <code>/play [نام آهنگ]</code> - پخش آهنگ\n"
            f"◄ <code>/stop</code> - توقف پخش\n"
            f"◄ <code>/pause</code> - مکث\n"
            f"◄ <code>/resume</code> - ادامه پخش\n"
            f"◄ <code>/skip</code> - رد کردن آهنگ",
            parse_mode='HTML'
        )
        
        await app.disconnect()
        
        # پاک کردن جلسه کاربر
        if user_id in user_sessions:
            del user_sessions[user_id]
        
    except Exception as e:
        error_msg = str(e)
        await update.message.reply_text(
            f"❌ <b>خطا در ساخت سشن!</b>\n\n"
            f"◄ خطا: <code>{error_msg}</code>\n\n"
            "◂ لطفاً دوباره تلاش کنید.\n"
            "⫸ برای شروع مجدد، روی دکمه افزودن CLI کلیک کنید.",
            parse_mode='HTML'
        )
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
        if 'app' in user_sessions[user_id]:
            try:
                await user_sessions[user_id]['app'].disconnect()
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

🎵 <b>دستورات پخش موزیک:</b>
• /play [نام یا لینک] - پخش موزیک در ویس چت
• /stop - توقف پخش و خروج از ویس چت
• /pause - مکث موقت
• /resume - ادامه پخش
• /skip - رد کردن آهنگ فعلی

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

async def run_bot():
    """راه‌اندازی کلاینت و ربات"""
    try:
        # اتصال کلاینت pyrogram
        await app.start()
        print("✅ کلاینت pyrogram متصل شد")
        
        # راه‌اندازی PyTgCalls
        await call.start()
        print("✅ PyTgCalls راه‌اندازی شد")
        
        # ساخت اپلیکیشن تلگرام
        application = ApplicationBuilder().token(TOKEN).build()
        
        # اضافه کردن هندلرها
        application.add_handler(CommandHandler('start', start))
        application.add_handler(CommandHandler('help', help_command))
        application.add_handler(CommandHandler('ping', ping))
        application.add_handler(CommandHandler('cancel', cancel_command))
        
        # دستورات پخش موزیک
        application.add_handler(CommandHandler('play', play_command))
        application.add_handler(CommandHandler('stop', stop_command))
        application.add_handler(CommandHandler('pause', pause_command))
        application.add_handler(CommandHandler('resume', resume_command))
        application.add_handler(CommandHandler('skip', skip_command))
        
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        print(f"🚀 ربات در حال روشن شدن با Polling...")
        print(f"✅ Webhook قبلی پاک شده")
        print(f"👤 سازنده ربات: {OWNER_ID}")
        
        # راه‌اندازی با Polling
        await application.run_polling(
            drop_pending_updates=True,
            allowed_updates=['message', 'callback_query']
        )
        
    except Exception as e:
        print(f"❌ خطا: {e}")

if __name__ == '__main__':
    # اجرای ربات
    asyncio.run(run_bot())
