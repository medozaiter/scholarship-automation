from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

# ==================== TOOLKIT TEXTS & TEMPLATES ====================

TOOLKIT_HOME_TEXT = (
    "🧰 <b>مكتبة قوالب وأدوات التقديم للمنح الدراسية (Application Toolkit)</b> 🎓\n\n"
    "لقد قمنا بإعداد هذه المكتبة الشاملة لمساعدتك في إعداد ملف تقديم احترافي وقوي "
    "يزيد من فرص قبولك في أكبر المنح الدولية.\n\n"
    "<b>اختر القسم الذي ترغب في استعراضه:</b>"
)

TOOLKIT_HOME_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("📝 نماذج رسائل الدافع (Motivation Letters)", callback_data="toolkit:motivation")],
    [InlineKeyboardButton("📄 إرشادات السيرة الذاتية (CV Formats)", callback_data="toolkit:cv")],
    [InlineKeyboardButton("✉️ دليل وقوالب طلب رسائل التوصية (LORs)", callback_data="toolkit:lor")],
    [InlineKeyboardButton("⬅️ العودة للقائمة الرئيسية", callback_data="action:back_to_main_menu")]
])

# Motivation Letters Text
MOTIVATION_TEXT = (
    "📝 <b>نماذج رسائل الدافع وبيان الغرض (Motivation Letter / SOP)</b>\n\n"
    "الهيكل النموذجي المعتمد لرسالة دافع ناجحة:\n"
    "1. <b>المقدمة:</b> من أنت، ولماذا هذا التخصص وهذه الجامعة بالتحديد؟\n"
    "2. <b>الخلفية الأكاديمية والمشاريع:</b> أبرز إنجازاتك، مشاريعك التقنية، وتحديات تغلبت عليها.\n"
    "3. <b>لماذا هذه المنحة/الدولة؟:</b> كيف يتماشى تمويل المنحة مع وضعك وطموحك؟\n"
    "4. <b>الرؤية المستقبلية (Impact):</b> كيف ستوظف المعرفة بعد التخرج لخدمة مجتمعك؟\n\n"
    "<b>قوالب جاهزة حسب التخصص:</b>"
)

MOTIVATION_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("💻 قالب: الأمن السيبراني (Cybersecurity)", callback_data="toolkit:sop_cyber")],
    [InlineKeyboardButton("🤖 قالب: الذكاء الاصطناعي وهندسة البرمجيات", callback_data="toolkit:sop_ai")],
    [InlineKeyboardButton("⬅️ رجوع لمكتبة الأدوات", callback_data="toolkit:home")]
])

SOP_CYBER_TEXT = (
    "🔒 <b>نموذج رسالة الدافع - الأمن السيبراني (Cybersecurity):</b>\n\n"
    "<code>Subject: Motivation Letter - Bachelor's in Cybersecurity Application\n\n"
    "Dear Members of the Scholarship Selection Committee,\n\n"
    "I am writing to express my strong commitment to pursuing my Bachelor's degree in Cybersecurity under [Scholarship Name] at [University Name]. Living in a world increasingly reliant on digital infrastructure, I have witnessed how crucial information defense has become. My aspiration is to develop high-level skills in network defense, cryptography, and digital forensics.\n\n"
    "Throughout my secondary studies, I achieved a GPA of [Your GPA] while actively engaging in self-taught programming and CTF (Capture the Flag) platforms. I led [Mention a small project/club], which solidified my problem-solving acumen and analytical discipline.\n\n"
    "Given my background from Palestine, opportunities for advanced, accredited cybersecurity labs are scarce. Receiving this scholarship will not only empower me to access world-class education but also equip me to contribute significantly to safeguarding digital economies upon graduation.\n\n"
    "Thank you for considering my application.\n\n"
    "Sincerely,\n[Your Name]</code>"
)

SOP_AI_TEXT = (
    "🤖 <b>نموذج رسالة الدافع - الذكاء الاصطناعي وهندسة البرمجيات:</b>\n\n"
    "<code>Subject: Statement of Purpose - Software Engineering & Artificial Intelligence\n\n"
    "Dear Admissions & Scholarship Committee,\n\n"
    "I am writing to enthusiastically apply for [Scholarship Name] to pursue an undergraduate degree in Software Engineering and Artificial Intelligence. My journey began when I developed [Mention a Python script/App/Science Fair Project], realizing the immense leverage software has in solving real-world socioeconomic bottlenecks.\n\n"
    "I have consistently ranked in the top [X%] of my class, with particular excellence in Mathematics and Computer Studies. I am eager to study under the renowned faculty at [University Name], focusing on machine learning algorithms and robust software architectures.\n\n"
    "This scholarship will bridge the financial gap and enable me to become an active contributor to open-source technologies, bridging knowledge back to underrepresented developer communities in my home country.\n\n"
    "Thank you for your time and evaluation.\n\n"
    "Warm regards,\n[Your Name]</code>"
)

CV_TEXT = (
    "📄 <b>دليل إعداد السيرة الذاتية الأكاديمية (Academic CV):</b>\n\n"
    "<b>1. نظام Europass (المفضل في أوروبا مثل المجر ورومانيا وألمانيا):</b>\n"
    "• استخدم الموقع الرسمي: <a href=\"https://europa.eu/europass/en\">Europass Editor</a>\n"
    "• احرص على استخدام التنسيق القياسي للمستوى اللغوي (CEFR: A1 to C2).\n"
    "• اذكر المهارات الرقمية (Digital Skills) وأدوات البرمجة بشكل محدد.\n\n"
    "<b>2. النظام الكندي والأمريكي (UBC, Toronto, Fulbright):</b>\n"
    "• لا تضع صورة شخصية، وتاريخ الميلاد، أو الحالة الاجتماعية (تمنع قوانين مكافحة التمييز ذلك).\n"
    "• ركز على صياغة الإنجازات بصيغة الأفعال المؤثرة: (e.g., Developed, Spearheaded, Coordinated).\n"
    "• اجعل السيرة الذاتية في صفحة واحدة أو اثنتين بحد أقصى للبكالوريوس.\n\n"
    "<b>الأقسام الأساسية:</b>\n"
    "1. Contact Information\n"
    "2. Education (High School GPA & Honors)\n"
    "3. Projects & Technical Skills\n"
    "4. Extracurricular & Leadership Activities\n"
    "5. Awards & Certifications"
)

LOR_TEXT = (
    "✉️ <b>دليل ونموذج طلب رسالة التوصية (Letter of Recommendation - LOR):</b>\n\n"
    "<b>نصائح ذهبية:</b>\n"
    "• اطلب الرسالة قبل الموعد النهائي بـ 3 أسابيع على الأقل.\n"
    "• اختر الأستاذ الذي درسك مادة وثيقة الصلة (رياضيات، فيزياء، حاسوب، أو لغة إنجليزية).\n"
    "• زود أستاذك بمسودة سيرتك الذاتية والمعدل واسم المنحة ليدعم رسالته بأمثلة دقيقة.\n\n"
    "<b>نموذج بريد إلكتروني لطلب التوصية:</b>\n\n"
    "<code>الموضوع: طلب رسالة توصية للتقديم على منحة [اسم المنحة] - [اسم الطالب]\n\n"
    "أستاذي الفاضل [اسم الأستاذ]،\nتحية طيبة وبعد،،\n\n"
    "أتمنى أن تكون بأفضل حال. أكتب لحضرتك لطلب دعمك الأكاديمي عبر كتابة رسالة توصية لتقديمي على [اسم المنحة] لدراسة [التخصص] في [الدولة/الجامعة].\n\n"
    "لقد كان لشرف كبير التعلم منك في مادة [اسم المادة]، والتي حققت فيها درجة [درجتك]، وألهمتني كثيراً في اختياري لهذا المجال.\n\n"
    "مرفق مع هذه الرسالة سيرتي الذاتية ومسودة رسالة الدافع لتسهيل كتابة التوصية. الموعد النهائي لتقديم التوصية هو [التاريخ].\n\n"
    "شاكراً ومقدراً جداً وقتك ودعمك المستمر،\nابنك/طالبك: [اسمك]\nرقم الهاتف: [رقمك]</code>"
)


# ==================== HANDLERS ====================

async def toolkit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows the main Application Toolkit menu."""
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            TOOLKIT_HOME_TEXT,
            reply_markup=TOOLKIT_HOME_KEYBOARD,
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            TOOLKIT_HOME_TEXT,
            reply_markup=TOOLKIT_HOME_KEYBOARD,
            parse_mode=ParseMode.HTML
        )


async def toolkit_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Routes callbacks from toolkit submenu buttons."""
    query = update.callback_query
    await query.answer()
    data = query.data

    back_button = InlineKeyboardMarkup([[
        InlineKeyboardButton("⬅️ رجوع لمكتبة الأدوات", callback_data="toolkit:home")
    ]])

    if data == "toolkit:home":
        await query.edit_message_text(
            TOOLKIT_HOME_TEXT,
            reply_markup=TOOLKIT_HOME_KEYBOARD,
            parse_mode=ParseMode.HTML
        )
    elif data == "toolkit:motivation":
        await query.edit_message_text(
            MOTIVATION_TEXT,
            reply_markup=MOTIVATION_KEYBOARD,
            parse_mode=ParseMode.HTML
        )
    elif data == "toolkit:sop_cyber":
        await query.edit_message_text(
            SOP_CYBER_TEXT,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ نماذج رسائل الدافع", callback_data="toolkit:motivation")
            ]]),
            parse_mode=ParseMode.HTML
        )
    elif data == "toolkit:sop_ai":
        await query.edit_message_text(
            SOP_AI_TEXT,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ نماذج رسائل الدافع", callback_data="toolkit:motivation")
            ]]),
            parse_mode=ParseMode.HTML
        )
    elif data == "toolkit:cv":
        await query.edit_message_text(
            CV_TEXT,
            reply_markup=back_button,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
    elif data == "toolkit:lor":
        await query.edit_message_text(
            LOR_TEXT,
            reply_markup=back_button,
            parse_mode=ParseMode.HTML
        )
