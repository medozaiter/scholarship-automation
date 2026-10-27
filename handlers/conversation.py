import logging
from typing import Dict, Set, List
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.constants import ParseMode, ChatAction
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from database import db
from services.search_service import SearchService
from services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

# Conversation States
(
    STEP_DEGREE,
    STEP_FUNDING,
    STEP_MAJORS,
    STEP_COUNTRY,
) = range(4)

STRICT_WARNING_MSG = "⚠️ <b>عذراً، يرجى الاختيار حصراً من الأزرار الموجودة أسفل الشاشة ⬇️</b>"

# ==================== BUTTON MAPS & KEYBOARDS ====================

# Step 1: Degree
DEGREE_OPTIONS = {
    "🎓 بكالوريوس (Undergraduate)": "Undergraduate (Bachelor's)",
    "🎓 ماجستير (Master's)": "Master's Degree",
    "🎓 دكتوراه (PhD)": "PhD / Doctoral",
}

BTN_CANCEL = "❌ إلغاء البحث"
BTN_BACK_DEGREE = "⬅️ رجوع للدرجة العلمية"
BTN_BACK_FUNDING = "⬅️ رجوع للتمويل"
BTN_BACK_MAJORS = "⬅️ رجوع لاختيار التخصصات"
BTN_PROCEED_SEARCH = "🚀 بدء البحث والتحليل ➡️"

DEGREE_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["🎓 بكالوريوس (Undergraduate)"],
        ["🎓 ماجستير (Master's)", "🎓 دكتوراه (PhD)"],
        [BTN_CANCEL]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

# Step 2: Funding
FUNDING_OPTIONS = {
    "💰 ممولة بالكامل (Fully Funded)": "Fully Funded",
    "💵 تمويل جزئي (Partial)": "Partial Funding",
    "🌐 كلاهما (Any / All)": "All / Any",
}

FUNDING_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["💰 ممولة بالكامل (Fully Funded)"],
        ["💵 تمويل جزئي (Partial)", "🌐 كلاهما (Any / All)"],
        [BTN_BACK_DEGREE, BTN_CANCEL]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

# Step 3: Majors List
MAJORS_BASE: Dict[str, str] = {
    "cyber": "الأمن السيبراني (Cybersecurity)",
    "software": "هندسة البرمجيات (Software Eng)",
    "ai": "الذكاء الاصطناعي (AI & Data)",
    "cs": "علوم الحاسوب (CS & IT)",
    "eng": "الهندسة العامة (Engineering)",
    "med": "الطب والعلوم الصحية (Medicine)",
    "biz": "إدارة الأعمال والاقتصاد (Business)",
}

# Step 4: Countries
COUNTRY_OPTIONS = {
    "🇵🇸 فلسطين (افتراضي)": "Palestine",
    "🇯🇴 الأردن": "Jordan",
    "🇪🇬 مصر": "Egypt",
    "🇸🇦 السعودية": "Saudi Arabia",
    "🇦🇪 الإمارات": "UAE",
    "🌍 باقي الدول العربية والعالم": "International / Arab Region",
}

COUNTRY_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["🇵🇸 فلسطين (افتراضي)"],
        ["🇯🇴 الأردن", "🇪🇬 مصر"],
        ["🇸🇦 السعودية", "🇦🇪 الإمارات"],
        ["🌍 باقي الدول العربية والعالم"],
        [BTN_BACK_MAJORS, BTN_CANCEL]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

search_service = SearchService(max_results=10)
gemini_service: GeminiService | None = None

def get_gemini_service() -> GeminiService:
    global gemini_service
    if gemini_service is None:
        gemini_service = GeminiService()
    return gemini_service


def build_majors_reply_keyboard(selected_keys: Set[str]) -> ReplyKeyboardMarkup:
    """Dynamically builds ReplyKeyboardMarkup showing checkmarks on selected majors."""
    rows = []
    keys = list(MAJORS_BASE.keys())

    # Build 2-column layout
    for i in range(0, len(keys), 2):
        row = []
        k1 = keys[i]
        label1 = f"✅ {MAJORS_BASE[k1]}" if k1 in selected_keys else f"⬜ {MAJORS_BASE[k1]}"
        row.append(label1)

        if i + 1 < len(keys):
            k2 = keys[i + 1]
            label2 = f"✅ {MAJORS_BASE[k2]}" if k2 in selected_keys else f"⬜ {MAJORS_BASE[k2]}"
            row.append(label2)
        rows.append(row)

    # Action row (only visible when at least 1 major is selected)
    if selected_keys:
        rows.append([BTN_PROCEED_SEARCH])

    rows.append([BTN_BACK_FUNDING, BTN_CANCEL])

    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=False)


# ===================== STEP HANDLERS & STRICT VALIDATION =====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point /start: Initializes session and shows Step 1 Degree Reply Keyboard."""
    context.user_data.clear()
    context.user_data["selected_majors"] = set()

    welcome_text = (
        "👋 <b>مرحباً بك في المنصة الذكية للبحث عن المنح الدراسية!</b> 🎓\n\n"
        "يرجى استخدام <b>الأزرار المخصصة أسفل الشاشة</b> لاختيار تفضيلاتك خطوة بخطوة.\n\n"
        "<b>الخطوة 1:</b> اختر الدرجة العلمية المستهدفة من القائمة أدناه ⬇️"
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=DEGREE_KEYBOARD,
        parse_mode=ParseMode.HTML
    )
    return STEP_DEGREE


async def handle_degree_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 1 (Degree) Handler with strict input validation."""
    user_text = update.message.text.strip()

    # Cancel button check
    if user_text == BTN_CANCEL:
        return await cancel_command(update, context)

    # Strict Validation
    if user_text not in DEGREE_OPTIONS:
        await update.message.reply_text(
            STRICT_WARNING_MSG,
            reply_markup=DEGREE_KEYBOARD,
            parse_mode=ParseMode.HTML
        )
        return STEP_DEGREE

    # Valid degree selected
    context.user_data["degree"] = DEGREE_OPTIONS[user_text]
    context.user_data["degree_display"] = user_text

    next_text = (
        f"✅ تم اختيار: <b>{user_text}</b>\n\n"
        "<b>الخطوة 2:</b> اختر نوع التمويل المطلوب من الأزرار أدناه ⬇️"
    )
    await update.message.reply_text(
        next_text,
        reply_markup=FUNDING_KEYBOARD,
        parse_mode=ParseMode.HTML
    )
    return STEP_FUNDING


async def handle_funding_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 2 (Funding) Handler with strict input validation and back-navigation."""
    user_text = update.message.text.strip()

    if user_text == BTN_CANCEL:
        return await cancel_command(update, context)

    if user_text == BTN_BACK_DEGREE:
        await update.message.reply_text(
            "⬅️ <b>العودة للدرجة العلمية:</b> اختر الدرجة من الأزرار أدناه ⬇️",
            reply_markup=DEGREE_KEYBOARD,
            parse_mode=ParseMode.HTML
        )
        return STEP_DEGREE

    # Strict Validation
    if user_text not in FUNDING_OPTIONS:
        await update.message.reply_text(
            STRICT_WARNING_MSG,
            reply_markup=FUNDING_KEYBOARD,
            parse_mode=ParseMode.HTML
        )
        return STEP_FUNDING

    context.user_data["funding"] = FUNDING_OPTIONS[user_text]
    context.user_data["funding_display"] = user_text

    selected_majors: Set[str] = context.user_data.get("selected_majors", set())
    majors_kb = build_majors_reply_keyboard(selected_majors)

    next_text = (
        f"✅ نوع التمويل: <b>{user_text}</b>\n\n"
        "<b>الخطوة 3:</b> اختر التخصصات المستهدفة (يمكنك النقر على أكثر من تخصص لتحديده):\n"
        "<i>عند الانتهاء من التحديد، اضغط على زر [ 🚀 بدء البحث والتحليل ]</i> ⬇️"
    )
    await update.message.reply_text(
        next_text,
        reply_markup=majors_kb,
        parse_mode=ParseMode.HTML
    )
    return STEP_MAJORS


async def handle_majors_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 3 (Majors) Multi-select toggle via persistent ReplyKeyboard with strict validation."""
    user_text = update.message.text.strip()
    selected_majors: Set[str] = context.user_data.setdefault("selected_majors", set())

    if user_text == BTN_CANCEL:
        return await cancel_command(update, context)

    if user_text == BTN_BACK_FUNDING:
        await update.message.reply_text(
            "⬅️ <b>العودة للتمويل:</b> اختر نوع التمويل من الأزرار أدناه ⬇️",
            reply_markup=FUNDING_KEYBOARD,
            parse_mode=ParseMode.HTML
        )
        return STEP_FUNDING

    # Proceed button check
    if user_text == BTN_PROCEED_SEARCH:
        if not selected_majors:
            await update.message.reply_text(
                "ℹ️ <b>يرجى اختيار تخصص واحد على الأقل أولاً</b> بالنقر على أزرار التخصصات أدناه ⬇️",
                reply_markup=build_majors_reply_keyboard(selected_majors),
                parse_mode=ParseMode.HTML
            )
            return STEP_MAJORS

        # Valid transition to Country Step
        chosen_labels = [MAJORS_BASE[k] for k in selected_majors if k in MAJORS_BASE]
        context.user_data["majors_display"] = chosen_labels

        next_text = (
            f"✅ التخصصات المحددة: <b>{', '.join(chosen_labels)}</b>\n\n"
            "<b>الخطوة 4:</b> حدد جنسية أو دولة المتقدم للتحقق من الأهلية:\n"
            "(فلسطين هي الخيار الافتراضي، أو اختر من القائمة) ⬇️"
        )
        await update.message.reply_text(
            next_text,
            reply_markup=COUNTRY_KEYBOARD,
            parse_mode=ParseMode.HTML
        )
        return STEP_COUNTRY

    # Check if user_text matches any major button (with ✅ or ⬜)
    matched_key = None
    for k, base_name in MAJORS_BASE.items():
        if user_text in (f"✅ {base_name}", f"⬜ {base_name}", base_name):
            matched_key = k
            break

    # Strict Validation: If user typed arbitrary free text outside the buttons
    if not matched_key:
        await update.message.reply_text(
            STRICT_WARNING_MSG,
            reply_markup=build_majors_reply_keyboard(selected_majors),
            parse_mode=ParseMode.HTML
        )
        return STEP_MAJORS

    # Toggle selection
    if matched_key in selected_majors:
        selected_majors.remove(matched_key)
        feedback = f"❌ تم إلغاء تحديد: {MAJORS_BASE[matched_key]}"
    else:
        selected_majors.add(matched_key)
        feedback = f"✅ تم تحديد: {MAJORS_BASE[matched_key]}"

    # Update keyboard with toggled state
    await update.message.reply_text(
        feedback,
        reply_markup=build_majors_reply_keyboard(selected_majors),
        parse_mode=ParseMode.HTML
    )
    return STEP_MAJORS


async def handle_country_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 4 (Country) Handler with strict validation and search execution trigger."""
    user_text = update.message.text.strip()

    if user_text == BTN_CANCEL:
        return await cancel_command(update, context)

    if user_text == BTN_BACK_MAJORS:
        selected_majors = context.user_data.get("selected_majors", set())
        await update.message.reply_text(
            "⬅️ <b>العودة لاختيار التخصصات:</b> عدل اختياراتك ثم اضغط بدء البحث ⬇️",
            reply_markup=build_majors_reply_keyboard(selected_majors),
            parse_mode=ParseMode.HTML
        )
        return STEP_MAJORS

    # Strict Validation
    if user_text not in COUNTRY_OPTIONS:
        await update.message.reply_text(
            STRICT_WARNING_MSG,
            reply_markup=COUNTRY_KEYBOARD,
            parse_mode=ParseMode.HTML
        )
        return STEP_COUNTRY

    context.user_data["country"] = COUNTRY_OPTIONS[user_text]
    context.user_data["country_display"] = user_text

    # Execute search pipeline
    return await execute_scholarship_search(update, context)


async def execute_scholarship_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Runs search, checks DB cache, executes Gemini analysis, and displays results."""
    chat_id = update.effective_chat.id
    bot = context.bot

    degree = context.user_data.get("degree", "Undergraduate")
    funding = context.user_data.get("funding", "Fully Funded")
    majors_display = context.user_data.get("majors_display", ["Computer Science"])
    country = context.user_data.get("country", "Palestine")

    cache_key = f"{degree}:{'|'.join(sorted(majors_display))}:{funding}:{country}"
    gemini = get_gemini_service()

    # Reset keyboard with a clean finish layout
    finish_kb = ReplyKeyboardMarkup(
        [
            ["🔄 بدء بحث جديد"],
            ["📊 فحص الأهلية المبدئي (/check)"],
            ["🧰 مكتبة قوالب التقديم (/toolkit)"]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

    # 1. Check Database Cache
    cached_report = await db.get_cached_search(cache_key, ttl_hours=24)
    if cached_report:
        logger.info(f"Serving cached search report for {cache_key}")
        chunks = gemini.split_telegram_message(cached_report, max_length=3900)
        for i, chunk in enumerate(chunks):
            header = "⚡️ <i>نتائج فورية ومحدثة من قاعدة البيانات المعتمدة:</i>\n\n" if i == 0 else ""
            kb = finish_kb if i == len(chunks) - 1 else None
            await bot.send_message(
                chat_id=chat_id,
                text=header + chunk,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=kb
            )
        return ConversationHandler.END

    # 2. Live Web Search & Gemini Verification
    status_msg = await bot.send_message(
        chat_id=chat_id,
        text=(
            "🔍 <b>جاري البحث في مصادر المنح العالمية والتحقق الصارم بالذكاء الاصطناعي...</b>\n\n"
            f"• <b>الدرجة:</b> {degree}\n"
            f"• <b>التخصصات:</b> {', '.join(majors_display)}\n"
            f"• <b>التمويل:</b> {funding}\n"
            f"• <b>الدولة:</b> {country}\n\n"
            "⏳ <i>يرجى الانتظار بضع ثوانٍ لجلب أدق الروابط الرسمية وتاريخ الإغلاق...</i>"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardRemove()
    )
    await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    try:
        search_results = await search_service.search_scholarships(
            degree=degree,
            majors=majors_display,
            funding=funding,
            country=country
        )

        report_text = await gemini.analyze_and_format_scholarships(
            search_results=search_results,
            degree=degree,
            majors=majors_display,
            funding=funding,
            country=country
        )

        # Cache result
        await db.set_cached_search(cache_key, report_text)

        try:
            await bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
        except Exception:
            pass

        chunks = gemini.split_telegram_message(report_text, max_length=3900)
        for i, chunk in enumerate(chunks):
            kb = finish_kb if i == len(chunks) - 1 else None
            await bot.send_message(
                chat_id=chat_id,
                text=chunk,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=kb
            )

    except Exception as e:
        logger.error(f"Error in search pipeline: {e}", exc_info=True)
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "❌ <b>عذراً، حدث خطأ أثناء فحص البيانات.</b>\n"
                f"التفاصيل: <code>{str(e)}</code>\n\n"
                "يرجى الضغط على زر بدء بحث جديد."
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=finish_kb
        )

    return ConversationHandler.END


async def subscribe_alert_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Subscribes the user to real-time alerts for the chosen track."""
    query = update.callback_query
    if query:
        await query.answer()
        chat_id = update.effective_chat.id
        degree = context.user_data.get("degree", "Undergraduate")
        majors = context.user_data.get("majors_display", ["Computer Science"])
        country = context.user_data.get("country", "Palestine")

        primary_major = majors[0] if majors else "General IT"

        success = await db.add_subscription(
            chat_id=chat_id,
            degree=degree,
            major=primary_major,
            country=country
        )

        if success:
            await query.message.reply_text(
                "🔔 <b>تم تفعيل تنبيهات المنح بنجاح!</b> ✅\n\n"
                f"سنرسل لك إشعاراً فورياً على هذا الحساب عند اكتشاف أي منحة جديدة مطابقة لمعاييرك:\n"
                f"• <b>الدرجة:</b> {degree}\n"
                f"• <b>التخصص:</b> {primary_major}\n"
                f"• <b>الدولة:</b> {country}\n\n"
                "<i>يقوم النظام بفحص المنح بشكل آلي ومستمر يومياً.</i>",
                parse_mode=ParseMode.HTML
            )
        else:
            await query.message.reply_text("⚠️ حدث خطأ أثناء تفعيل التنبيه، يرجى المحاولة لاحقاً.")


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels conversation and restores standard menu keyboard."""
    context.user_data.clear()
    restart_kb = ReplyKeyboardMarkup([["🔄 بدء بحث جديد"]], resize_keyboard=True)
    await update.message.reply_text(
        "🛑 <b>تم إلغاء عملية البحث الحالية.</b>\n\nيمكنك البدء من جديد عبر الضغط على الزر أدناه ⬇️",
        parse_mode=ParseMode.HTML,
        reply_markup=restart_kb
    )
    return ConversationHandler.END


def get_conversation_handler() -> ConversationHandler:
    """Master ConversationHandler using strict ReplyKeyboard validations."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("start", start_command),
            MessageHandler(filters.Regex("^🔄 بدء بحث جديد$"), start_command),
        ],
        states={
            STEP_DEGREE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_degree_step),
            ],
            STEP_FUNDING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_funding_step),
            ],
            STEP_MAJORS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_majors_step),
            ],
            STEP_COUNTRY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_country_step),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_command),
            MessageHandler(filters.Regex(f"^{BTN_CANCEL}$"), cancel_command),
        ],
        allow_reentry=True,
    )
