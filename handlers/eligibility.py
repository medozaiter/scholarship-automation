import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode, ChatAction
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

# States for Eligibility Conversation
ASK_GPA, ASK_ENGLISH, ASK_AGE = range(3)

gemini_service: GeminiService | None = None

def get_gemini_service() -> GeminiService:
    global gemini_service
    if gemini_service is None:
        gemini_service = GeminiService()
    return gemini_service


async def start_eligibility_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for student profile eligibility evaluation."""
    text = (
        "📊 <b>مرحباً بك في أداة فحص الأهلية المبدئي للمنح العالمية!</b> 🎯\n\n"
        "سنقوم بمقارنة ملفك الأكاديمي مع معايير القبول التنافسية لأبرز المنح الدولية "
        "(مثل المنحة التركية، الهنغارية، MEPI، تورنتو، GKS وغيرها).\n\n"
        "<b>الخطوة 1 من 3:</b>\n"
        "يرجى كتابة <b>معدلك التراكمي</b> (نسبتك المئوية في الثانوية أو GPA في الجامعة):\n"
        "<i>(مثال: 88% أو 3.5/4.0)</i>"
    )

    cancel_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("❌ إلغاء", callback_data="eligibility:cancel")
    ]])

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=cancel_kb, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=cancel_kb, parse_mode=ParseMode.HTML)

    return ASK_GPA


async def received_gpa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores GPA and prompts for English proficiency level."""
    context.user_data["eligibility_gpa"] = update.message.text.strip()

    text = (
        f"✅ تم حفظ المعدل: <b>{context.user_data['eligibility_gpa']}</b>\n\n"
        "<b>الخطوة 2 من 3:</b>\n"
        "ما هو مستواك في <b>اللغة الإنجليزية</b>؟ هل لديك اختبار معتمد؟\n"
        "<i>(مثال: IELTS 6.5، TOEFL iBT 80، Duolingo 110، أو مستوى جيد بدون شهادة رسمية)</i>"
    )
    cancel_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("❌ إلغاء", callback_data="eligibility:cancel")
    ]])

    await update.message.reply_text(text, reply_markup=cancel_kb, parse_mode=ParseMode.HTML)
    return ASK_ENGLISH


async def received_english(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores English level and prompts for age/graduation year."""
    context.user_data["eligibility_english"] = update.message.text.strip()

    text = (
        f"✅ تم حفظ مستوى اللغة: <b>{context.user_data['eligibility_english']}</b>\n\n"
        "<b>الخطوة 3 من 3:</b>\n"
        "يرجى كتابة <b>عمرك الحالي وسنة تخرجك</b>:\n"
        "<i>(مثال: 18 سنة - خريج 2026، أو 22 سنة - خريج حديث)</i>"
    )
    cancel_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("❌ إلغاء", callback_data="eligibility:cancel")
    ]])

    await update.message.reply_text(text, reply_markup=cancel_kb, parse_mode=ParseMode.HTML)
    return ASK_AGE


async def received_age_and_evaluate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Executes AI evaluation using Gemini and returns structured assessment."""
    context.user_data["eligibility_age"] = update.message.text.strip()

    chat_id = update.effective_chat.id
    bot = context.bot

    status_msg = await update.message.reply_text(
        "🧠 <b>جاري تحليل ملفك الأكاديمي بواسطة الذكاء الاصطناعي ومطابقته مع شروط المنح الدولية...</b>\n"
        "⏳ <i>يرجى الانتظار بضع ثوانٍ...</i>",
        parse_mode=ParseMode.HTML
    )
    await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    gpa = context.user_data.get("eligibility_gpa", "85%")
    english = context.user_data.get("eligibility_english", "Good without test")
    age = context.user_data.get("eligibility_age", "19 years")
    degree = context.user_data.get("degree", "Undergraduate (Bachelor's)")
    major = ", ".join(context.user_data.get("majors_display", ["Computer Science / Engineering"]))
    country = context.user_data.get("country", "Palestine")

    gemini = get_gemini_service()
    evaluation_report = await gemini.evaluate_eligibility(
        gpa=gpa,
        english_level=english,
        age_or_grad_year=age,
        target_degree=degree,
        target_major=major,
        country=country
    )

    try:
        await bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
    except Exception:
        pass

    action_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 ابحث عن منح تناسب ملفي الآن", callback_data="action:restart")],
        [InlineKeyboardButton("🧰 الذهاب لمكتبة قوالب التقديم", callback_data="toolkit:home")]
    ])

    await update.message.reply_text(
        evaluation_report,
        reply_markup=action_kb,
        parse_mode=ParseMode.HTML
    )

    return ConversationHandler.END


async def cancel_eligibility(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the eligibility check flow."""
    text = "🛑 <b>تم إلغاء فحص الأهلية.</b> يمكنك العودة في أي وقت بإرسال /check أو /start."
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    return ConversationHandler.END


def get_eligibility_handler() -> ConversationHandler:
    """Builds and returns ConversationHandler for Eligibility Checker."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("check", start_eligibility_check),
            CallbackQueryHandler(start_eligibility_check, pattern="^action:eligibility_check$"),
        ],
        states={
            ASK_GPA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, received_gpa),
            ],
            ASK_ENGLISH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, received_english),
            ],
            ASK_AGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, received_age_and_evaluate),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_eligibility),
            CallbackQueryHandler(cancel_eligibility, pattern="^eligibility:cancel$"),
        ],
        allow_reentry=True,
    )
