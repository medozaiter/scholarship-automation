import logging
from typing import Dict, Set, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.constants import ParseMode, ChatAction
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from database import db
from services.search_service import SearchService
from services.gemini_service import GeminiService
from handlers.toolkit import toolkit_command

logger = logging.getLogger(__name__)

# Conversation States
(
    SELECT_DEGREE,
    SELECT_FUNDING,
    SELECT_MAJORS,
    SELECT_COUNTRY,
) = range(4)

# Available Majors
AVAILABLE_MAJORS: Dict[str, str] = {
    "cyber": "الأمن السيبراني (Cybersecurity)",
    "software": "هندسة البرمجيات (Software Eng)",
    "ai": "الذكاء الاصطناعي (AI & Data)",
    "cs": "علوم الحاسوب (CS & IT)",
    "eng": "الهندسة العامة (Engineering)",
    "med": "الطب والعلوم الصحية (Medicine)",
    "biz": "إدارة الأعمال والاقتصاد (Business)",
}

DEGREE_MAP = {
    "undergraduate": "بكالوريوس (Undergraduate / Bachelor's)",
    "masters": "ماجستير (Master's Degree)",
    "phd": "دكتوراه (PhD / Doctoral)",
}

FUNDING_MAP = {
    "fully_funded": "ممولة بالكامل (Fully Funded)",
    "partial": "تمويل جزئي (Partial Funding)",
    "any": "كلاهما (Fully / Partially Funded)",
}

COUNTRY_MAP = {
    "palestine": ("Palestine", "🇵🇸 فلسطين (افتراضي)"),
    "jordan": ("Jordan", "🇯🇴 الأردن"),
    "egypt": ("Egypt", "🇪🇬 مصر"),
    "saudi": ("Saudi Arabia", "🇸🇦 السعودية"),
    "uae": ("UAE", "🇦🇪 الإمارات"),
    "international": ("International / Arab Region", "🌍 باقي الدول العربية"),
}

search_service = SearchService(max_results=10)
gemini_service: GeminiService | None = None

def get_gemini_service() -> GeminiService:
    global gemini_service
    if gemini_service is None:
        gemini_service = GeminiService()
    return gemini_service


def build_majors_inline_keyboard(selected_keys: Set[str]) -> InlineKeyboardMarkup:
    """
    Builds clean, in-place multi-select inline keyboard.
    Tapping a button silently toggles checkmark without sending chat messages!
    """
    keyboard = []
    keys = list(AVAILABLE_MAJORS.keys())

    # 2 buttons per row
    for i in range(0, len(keys), 2):
        row = []
        k1 = keys[i]
        label1 = f"✅ {AVAILABLE_MAJORS[k1]}" if k1 in selected_keys else f"⬜ {AVAILABLE_MAJORS[k1]}"
        row.append(InlineKeyboardButton(label1, callback_data=f"toggle_major:{k1}"))

        if i + 1 < len(keys):
            k2 = keys[i + 1]
            label2 = f"✅ {AVAILABLE_MAJORS[k2]}" if k2 in selected_keys else f"⬜ {AVAILABLE_MAJORS[k2]}"
            row.append(InlineKeyboardButton(label2, callback_data=f"toggle_major:{k2}"))
        keyboard.append(row)

    # Big prominent submit button right under the options (no scrolling!)
    count = len(selected_keys)
    if count > 0:
        keyboard.append([
            InlineKeyboardButton(f"🚀 بدء البحث والتحليل ({count} تخصصات مختارة) ➡️", callback_data="action:confirm_majors")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("ℹ️ الرجاء اختيار تخصص واحد على الأقل", callback_data="action:none")
        ])

    keyboard.append([
        InlineKeyboardButton("⬅️ رجوع للتمويل", callback_data="action:back_to_funding"),
        InlineKeyboardButton("❌ إلغاء", callback_data="action:cancel")
    ])

    return InlineKeyboardMarkup(keyboard)


# ===================== HANDLER FUNCTIONS =====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point /start: Clean inline keyboard without chat clutter."""
    context.user_data.clear()
    context.user_data["selected_majors"] = set()

    welcome_text = (
        "👋 <b>مرحباً بك في المنصة الذكية للبحث عن المنح الدراسية!</b> 🎓\n\n"
        "يمكنك التحديد المباشر بالنقر على الخيارات أدناه دون إرسال رسائل مكررة.\n\n"
        "<b>الخطوة 1:</b> اختر الدرجة العلمية المستهدفة:"
    )

    keyboard = [
        [InlineKeyboardButton("🎓 بكالوريوس (Undergraduate)", callback_data="degree:undergraduate")],
        [InlineKeyboardButton("🎓 ماجستير (Master's Degree)", callback_data="degree:masters")],
        [InlineKeyboardButton("🎓 دكتوراه (PhD Degree)", callback_data="degree:phd")],
        [
            InlineKeyboardButton("📊 فحص الأهلية (/check)", callback_data="action:eligibility_check"),
            InlineKeyboardButton("🧰 مكتبة القوالب (/toolkit)", callback_data="toolkit:home"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    else:
        # Also clean up any lingering reply keyboard
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

    return SELECT_DEGREE


async def degree_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles degree selection and seamlessly updates the current message."""
    query = update.callback_query
    await query.answer()

    degree_key = query.data.split(":")[1]
    context.user_data["degree_key"] = degree_key
    context.user_data["degree"] = DEGREE_MAP.get(degree_key, "Undergraduate")

    text = (
        f"🎓 الدرجة العلمية: <b>{context.user_data['degree']}</b>\n\n"
        "<b>الخطوة 2:</b> اختر نوع التمويل المطلوب:"
    )

    keyboard = [
        [InlineKeyboardButton("💰 ممولة بالكامل (Fully Funded)", callback_data="funding:fully_funded")],
        [InlineKeyboardButton("💵 تمويل جزئي (Partial Funding)", callback_data="funding:partial")],
        [InlineKeyboardButton("🌐 كلاهما (All / Any)", callback_data="funding:any")],
        [InlineKeyboardButton("⬅️ رجوع للدرجة العلمية", callback_data="action:back_to_degree")],
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )
    return SELECT_FUNDING


async def funding_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles funding selection and presents the in-place multi-select keyboard."""
    query = update.callback_query
    await query.answer()

    funding_key = query.data.split(":")[1]
    context.user_data["funding_key"] = funding_key
    context.user_data["funding"] = FUNDING_MAP.get(funding_key, "Fully Funded")

    text = (
        f"🎓 الدرجة: <b>{context.user_data['degree']}</b>\n"
        f"💰 التمويل: <b>{context.user_data['funding']}</b>\n\n"
        "<b>الخطوة 3:</b> حدد التخصصات التي تهمك (انقر لتحديد أو إلغاء أي تخصص بضغطة واحدة):\n"
        "<i>ثم اضغط على الزر الأخضر بالأسفل لبدء البحث</i> ⬇️"
    )

    selected_majors: Set[str] = context.user_data.get("selected_majors", set())
    reply_markup = build_majors_inline_keyboard(selected_majors)

    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    return SELECT_MAJORS


async def major_toggled(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Toggles major selection in-place with instant feedback.
    No extra messages sent to the chat!
    """
    query = update.callback_query
    await query.answer()
    data = query.data

    selected_majors: Set[str] = context.user_data.setdefault("selected_majors", set())

    if data.startswith("toggle_major:"):
        major_key = data.split(":")[1]
        if major_key in selected_majors:
            selected_majors.remove(major_key)
        else:
            selected_majors.add(major_key)

        # Update ONLY the keyboard buttons in-place!
        reply_markup = build_majors_inline_keyboard(selected_majors)
        await query.edit_message_reply_markup(reply_markup=reply_markup)
        return SELECT_MAJORS

    elif data == "action:confirm_majors":
        if not selected_majors:
            await query.answer("يرجى اختيار تخصص واحد على الأقل!", show_alert=True)
            return SELECT_MAJORS

        chosen_labels = [AVAILABLE_MAJORS[k] for k in selected_majors if k in AVAILABLE_MAJORS]
        context.user_data["majors_display"] = chosen_labels

        text = (
            f"🎓 الدرجة: <b>{context.user_data['degree']}</b>\n"
            f"💰 التمويل: <b>{context.user_data['funding']}</b>\n"
            f"📚 التخصصات: <b>{', '.join(chosen_labels)}</b>\n\n"
            "<b>الخطوة 4 والأخيرة:</b> حدد دولة/جنسية المتقدم للتحقق من الأهلية:\n"
            "(فلسطين هي الخيار الافتراضي، أو اختر دولتك) ⬇️"
        )

        keyboard = [
            [InlineKeyboardButton("🇵🇸 فلسطين (افتراضي ومباشر)", callback_data="country:palestine")],
            [
                InlineKeyboardButton("🇯🇴 الأردن", callback_data="country:jordan"),
                InlineKeyboardButton("🇪🇬 مصر", callback_data="country:egypt"),
            ],
            [
                InlineKeyboardButton("🇸🇦 السعودية", callback_data="country:saudi"),
                InlineKeyboardButton("🇦🇪 الإمارات", callback_data="country:uae"),
            ],
            [InlineKeyboardButton("🌍 باقي الدول العربية", callback_data="country:international")],
            [InlineKeyboardButton("⬅️ تعديل التخصصات", callback_data="action:back_to_majors")],
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        return SELECT_COUNTRY

    elif data == "action:back_to_funding":
        return await degree_selected(update, context)

    elif data == "action:none":
        await query.answer("انقر على التخصصات أعلاه أولاً لتحديدها.", show_alert=False)
        return SELECT_MAJORS

    return SELECT_MAJORS


async def country_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles country selection and launches the search immediately."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("country:"):
        country_key = data.split(":")[1]
        country_info = COUNTRY_MAP.get(country_key, ("Palestine", "🇵🇸 فلسطين"))
        context.user_data["country"] = country_info[0]
        context.user_data["country_display"] = country_info[1]

        # Trigger search
        return await execute_scholarship_search(update, context)

    elif data == "action:back_to_majors":
        selected_majors = context.user_data.get("selected_majors", set())
        text = (
            f"🎓 الدرجة: <b>{context.user_data['degree']}</b>\n"
            f"💰 التمويل: <b>{context.user_data['funding']}</b>\n\n"
            "<b>الخطوة 3:</b> حدد التخصصات التي تهمك بالنقر عليها ⬇️"
        )
        await query.edit_message_text(
            text,
            reply_markup=build_majors_inline_keyboard(selected_majors),
            parse_mode=ParseMode.HTML
        )
        return SELECT_MAJORS

    return SELECT_COUNTRY


async def execute_scholarship_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Search & AI Verification Pipeline:
    1. Checks SQLite database cache (<1s response).
    2. Runs live web search and Gemini extraction.
    3. Displays verified scholarship cards with direct links.
    """
    query = update.callback_query
    chat_id = update.effective_chat.id
    bot = context.bot

    degree = context.user_data.get("degree", "Undergraduate")
    funding = context.user_data.get("funding", "Fully Funded")
    majors_display = context.user_data.get("majors_display", ["Computer Science"])
    country = context.user_data.get("country", "Palestine")

    cache_key = f"{degree}:{'|'.join(sorted(majors_display))}:{funding}:{country}"
    gemini = get_gemini_service()

    # Inform user that search is in progress
    status_text = (
        "🔍 <b>جاري البحث الذكي عن المنح المفتوحة والتحقق من التواريخ بالذكاء الاصطناعي...</b>\n\n"
        f"• <b>الدرجة:</b> {degree}\n"
        f"• <b>التخصصات:</b> {', '.join(majors_display)}\n"
        f"• <b>التمويل:</b> {funding}\n"
        f"• <b>الدولة:</b> {country}\n\n"
        "⏳ <i>يرجى الانتظار بضع ثوانٍ لجلب أدق الروابط الرسمية وتاريخ الإغلاق...</i>"
    )

    if query:
        await query.edit_message_text(status_text, parse_mode=ParseMode.HTML)
    else:
        await bot.send_message(chat_id=chat_id, text=status_text, parse_mode=ParseMode.HTML)

    await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    # 1. Check Database Cache
    cached_report = await db.get_cached_search(cache_key, ttl_hours=24)
    if cached_report:
        logger.info(f"Serving cached search report for {cache_key}")
        chunks = gemini.split_telegram_message(cached_report, max_length=3900)
        for i, chunk in enumerate(chunks):
            reply_markup = None
            if i == len(chunks) - 1:
                reply_markup = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔔 نبهني فور توفر منح جديدة في هذا التخصص", callback_data="action:subscribe_alert")],
                    [
                        InlineKeyboardButton("📊 فحص الأهلية المبدئي", callback_data="action:eligibility_check"),
                        InlineKeyboardButton("🧰 مكتبة قوالب التقديم", callback_data="toolkit:home"),
                    ],
                    [InlineKeyboardButton("🔄 بدء بحث جديد", callback_data="action:restart")]
                ])

            header = "⚡️ <i>نتائج فورية وموثقة من قاعدة البيانات:</i>\n\n" if i == 0 else ""
            await bot.send_message(
                chat_id=chat_id,
                text=header + chunk,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=reply_markup
            )
        return ConversationHandler.END

    # 2. Live Search & Gemini Verification
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

        chunks = gemini.split_telegram_message(report_text, max_length=3900)
        for i, chunk in enumerate(chunks):
            reply_markup = None
            if i == len(chunks) - 1:
                reply_markup = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔔 نبهني فور توفر منح جديدة في هذا التخصص", callback_data="action:subscribe_alert")],
                    [
                        InlineKeyboardButton("📊 فحص الأهلية المبدئي", callback_data="action:eligibility_check"),
                        InlineKeyboardButton("🧰 مكتبة قوالب التقديم", callback_data="toolkit:home"),
                    ],
                    [InlineKeyboardButton("🔄 بدء بحث جديد", callback_data="action:restart")]
                ])

            await bot.send_message(
                chat_id=chat_id,
                text=chunk,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=reply_markup
            )

    except Exception as e:
        logger.error(f"Error in search pipeline: {e}", exc_info=True)
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "❌ <b>عذراً، حدث خطأ أثناء فحص البيانات.</b>\n"
                f"التفاصيل: <code>{str(e)}</code>\n\n"
                "يرجى الضغط على الزر أدناه لإعادة المحاولة."
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 بدء بحث جديد", callback_data="action:restart")]])
        )

    return ConversationHandler.END


async def subscribe_alert_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Subscribes user to push alerts."""
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
                f"سنرسل لك إشعاراً فورياً على هذا الحساب عند اكتشاف أي منحة جديدة مطابقة لتخصصك:\n"
                f"• <b>الدرجة:</b> {degree}\n"
                f"• <b>التخصص:</b> {primary_major}\n"
                f"• <b>الدولة:</b> {country}\n\n"
                "<i>يقوم النظام بالبحث المستمر في الخلفية وتحديث قاعدة البيانات آلياً.</i>",
                parse_mode=ParseMode.HTML
            )
        else:
            await query.message.reply_text("⚠️ حدث خطأ أثناء تفعيل التنبيه.")


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels conversation and resets cleanly."""
    context.user_data.clear()
    restart_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 بدء بحث جديد", callback_data="action:restart")]])
    text = "🛑 <b>تم إلغاء العملية.</b> يمكنك البدء من جديد عبر الضغط على الزر أدناه ⬇️"

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=restart_kb, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=restart_kb, parse_mode=ParseMode.HTML)

    return ConversationHandler.END


def get_conversation_handler() -> ConversationHandler:
    """Master ConversationHandler using seamless inline keyboards."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("start", start_command),
            CallbackQueryHandler(start_command, pattern="^action:restart$"),
            CallbackQueryHandler(start_command, pattern="^action:back_to_degree$"),
            CallbackQueryHandler(start_command, pattern="^action:back_to_main_menu$"),
        ],
        states={
            SELECT_DEGREE: [
                CallbackQueryHandler(degree_selected, pattern="^degree:"),
            ],
            SELECT_FUNDING: [
                CallbackQueryHandler(funding_selected, pattern="^funding:"),
                CallbackQueryHandler(start_command, pattern="^action:back_to_degree$"),
            ],
            SELECT_MAJORS: [
                CallbackQueryHandler(major_toggled, pattern="^(toggle_major:|action:)"),
            ],
            SELECT_COUNTRY: [
                CallbackQueryHandler(country_selected, pattern="^(country:|action:)"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_command),
            CallbackQueryHandler(cancel_command, pattern="^action:cancel$"),
        ],
        allow_reentry=True,
    )
