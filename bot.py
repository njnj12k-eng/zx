import os
import logging
import httpx  # به جای requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

# تنظیم لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# گرفتن توکن از محیط
TOKEN = os.getenv('TOKEN')

# اگر توکن در محیط نیست (برای تست محلی)
if not TOKEN:
    TOKEN = "8860863617:AAFizT8wFBJFt4uq7U9NpGfK_jwahrA35_o"  # با توکن جدید عوض کن

# پاک کردن Webhook قبلی با httpx
try:
    response = httpx.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook")
    if response.json().get('ok'):
        print("✅ Webhook قبلی پاک شد")
except Exception as e:
    print(f"⚠️ خطا در پاک کردن Webhook: {e}")

# متن استارت
START_TEXT = """
🌟 سلام <b>[ نام کاربر منشن شده ]</b> عزیز 🌹

💬 من یه ربات موزیک پلیر گروه کاملاً حرفه‌ای و پرسرعت هستم که با من میتونی به راحتی در ویس چت گروهت موزیک یا ویدئو پخش کنی!

⫸ برتری‌های انحصاری من :

◄ مجهز به <b>سیستم هوش مصنوعی (A.I)</b> برای پردازش هوشمند
◄ <b>سیستم ANN</b> برای پردازش و ذخیره‌سازی پیشرفته
◄ <b>سیستم CUH</b> برای مدیریت حرفه‌ای ویس چت
◄ <b>دانلود و جستجوی حرفه‌ای</b> رسانه‌های صوتی و تصویری
◄ <b>جلو و عقب زدن دقیقه‌ای</b> رسانه‌ها
◄ <b>پردازش و محافظت</b> از ویس‌چت گروه

⫸ ویژگی‌های منحصربفرد :

◂ <b>⚡ سرعت فوق‌العاده</b> حتی در گروه‌های ۲۰۰ هزار نفره
◂ <b>🌟 برترین پخش‌کننده</b> موزیک و ویدیو با امکانات بی‌نظیر

◂ <b>📺 پخش زنده</b> شبکه‌های ماهواره‌ای
◂ <b>📡 پخش زنده</b> شبکه‌های صدا و سیما
◂ <b>🎙️ پخش زنده</b> رادیو جهانی و استانی
◂ <b>🎬 تلویزیون، رادیو و موسیقی</b> زنده
◂ <b>🎥 فیلم سینمایی، سریال و انیمیشن</b>
◂ <b>💰 قیمت خرید اشتراک</b> بسیار مناسب

⫸ ما شبیه هیچکس نیستیم!

◄ <b>🔥 پرقدرت</b> حتی در کانال‌های میلیونی
◄ <b>✅ بی‌همتا در سرعت</b>
◄ <b>✅ بی‌همتا در امکانات</b>
◄ <b>✅ دارای مهلت بالای تست</b>
◄ <b>✅ دارای سرور اختصاصی</b>
◄ <b>✅ دارای پشتیبانی حرفه‌ای</b>
◄ <b>✅ دارای دستورات دو زبانه</b>
◄ <b>✅ جستجوی موزیک و ویدیو</b>
◄ <b>✅ قابلیت‌های فان و سرگرمی</b>
◄ <b>✅ دارای سامانه خرید آنلاین</b>
◄ <b>✅ بدون آفلاینی ۹۹.۹ درصد</b>
◄ <b>✅ ارائه آمارهای روزانه کاربران</b>
◄ <b>✅ دارای خوش‌آمدگویی هوشمند</b>
◄ <b>✅ دارای انواع قفل‌های ویس چت</b>
◄ <b>✅ پخش موزیک و ویدئو در گروه</b>
◄ <b>✅ پخش موزیک و ویدئو در کانال</b>
◄ <b>✅ دارای مای لیست و علاقه‌مندی‌ها</b>
◄ <b>✅ قابلیت ساخت ۳ پلی‌لیست موزیک</b>
◄ <b>✅ قابلیت ساخت ۲ پلی‌لیست ویدیو</b>

⫸ چرا به ما اعتماد کنیم؟

◂ <b>🥇ارائه بهترین کیفیت، تخصص ماست</b>
◂ <b>♥️ تجربه مدیریت ویسکال به سبک نوین</b>
◂ <b>🖥️ برنامه‌نویسی شده توسط تیم ZX</b>
◂ <b>🏆 بهترینی، وقتی بهترین‌ها انتخابت کنند!</b>

⫸ تذکر حقوقی :

◄ تمامی ایده‌ها و کدهای این ربات متعلق به <b>تیم ZX</b> بوده و هر گونه کپی‌برداری یا تقلید، <b>پیگرد قانونی</b> دارد. حقوق مادی و معنوی محفوظ است.

🆑 کانال موزیک پلیر ZX : <b>@ReaperMusicTM</b>

【 <b>Licenced By 🆉︎🆇︎</b> 】
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر /start"""
    user = update.effective_user
    user_mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
    final_text = START_TEXT.replace("[ نام کاربر منشن شده ]", user_mention)
    
    await update.message.reply_text(
        final_text,
        parse_mode='HTML',
        disable_web_page_preview=True
    )

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
        # ساخت اپلیکیشن
        application = ApplicationBuilder().token(TOKEN).build()
        
        # اضافه کردن هندلرها
        application.add_handler(CommandHandler('start', start))
        application.add_handler(CommandHandler('help', help_command))
        application.add_handler(CommandHandler('ping', ping))
        
        # گرفتن پورت از محیط
        port = int(os.environ.get('PORT', 8080))
        
        # URL سرویس در رندر
        webhook_url = f"https://charismatic-rejoicing.onrender.com/{TOKEN}"
        
        print(f"🚀 ربات در حال روشن شدن...")
        print(f"📡 Webhook URL: {webhook_url}")
        print(f"🔌 پورت: {port}")
        
        # راه‌اندازی با Webhook
        application.run_webhook(
            listen='0.0.0.0',
            port=port,
            url_path=TOKEN,
            webhook_url=webhook_url,
            drop_pending_updates=True
        )
        
    except Exception as e:
        print(f"❌ خطا: {e}")
