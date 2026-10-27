import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    Application,
)

from database import db
from handlers.conversation import (
    get_conversation_handler,
    subscribe_alert_callback,
    start_command,
)
from handlers.eligibility import get_eligibility_handler
from handlers.toolkit import toolkit_command, toolkit_callback_router
from services.broadcast_service import daily_scholarship_indexing_job

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext.Application").setLevel(logging.INFO)


async def on_startup(app: Application) -> None:
    """Initializes the database and schedules 24-hour recurring background crawler."""
    logger.info("Initializing SQLite database tables...")
    await db.init_db()

    # Schedule daily background indexing job (every 24 hours)
    if app.job_queue:
        app.job_queue.run_repeating(
            daily_scholarship_indexing_job,
            interval=86400,  # 24 hours
            first=30,        # Initial run 30s after boot
            name="daily_scholarship_indexer"
        )
        logger.info("Registered 24-hour automated scholarship background crawler in JobQueue.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays user commands and instructions."""
    help_text = (
        "💡 <b>دليل استخدام المنصة الذكية للمنح الدراسية:</b>\n\n"
        "• /start - بدء استبيان البحث التفاعلي واختيار التخصصات.\n"
        "• /check - فحص أهليتك الأكاديمية ونسبة التوافق لأي منحة.\n"
        "• /toolkit - مكتبة نماذج رسائل الدافع، السيرة الذاتية، ورسائل التوصية.\n"
        "• /cancel - إلغاء الاستبيان الحالي والعودة للقائمة الرئيسية.\n"
        "• /help - عرض قائمة المساعدة الحالية.\n\n"
        "<b>الميزات الفائقة المدمجة:</b>\n"
        "⚡️ <b>استجابة فورية (Instant Caching):</b> يتم تخزين وتحديث المنح في قاعدة بيانات محلية.\n"
        "🔔 <b>تنبيهات مخصصة:</b> يمكنك تفعيل التنبيه ليصلك إشعار فوري عند صدور منحة في تخصصك.\n"
        "⚠️ <b>تحقق صارم:</b> تدقيق حقيقي للتواريخ وروابط التقديم الرسمية حصراً دون أي روابط وهمية."
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Logs unexpected exceptions gracefully."""
    logger.error("Exception while handling update:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ <b>حدث خطأ غير متوقع أثناء معالجة الطلب.</b>\n"
                "يرجى المحاولة مجدداً عبر إرسال /start.",
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass


def main() -> None:
    """Configures and runs the Telegram Bot application."""
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    gemini_api_key = os.getenv("GEMINI_API_KEY")

    if not telegram_token or telegram_token == "your_telegram_bot_token_here":
        raise ValueError("Please provide a valid TELEGRAM_BOT_TOKEN in .env")

    if not gemini_api_key or gemini_api_key == "your_gemini_api_key_here":
        raise ValueError("Please provide a valid GEMINI_API_KEY in .env")

    logger.info("Building Telegram Application with asynchronous JobQueue...")

    application = (
        ApplicationBuilder()
        .token(telegram_token)
        .post_init(on_startup)
        .build()
    )

    # 1. Register Eligibility Checker Conversation
    application.add_handler(get_eligibility_handler())

    # 2. Register Scholarship Search Conversation
    application.add_handler(get_conversation_handler())

    # 3. Register Toolkit Handlers
    application.add_handler(CommandHandler("toolkit", toolkit_command))
    application.add_handler(CallbackQueryHandler(toolkit_callback_router, pattern="^toolkit:"))

    # 4. Register Alert Subscription Handlers
    application.add_handler(CallbackQueryHandler(subscribe_alert_callback, pattern="^action:subscribe_alert$"))

    # 5. Register General Commands
    application.add_handler(CommandHandler("help", help_command))

    # 6. Global Error Handler
    application.add_error_handler(error_handler)

    logger.info("Bot is fully operational and listening for events...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
