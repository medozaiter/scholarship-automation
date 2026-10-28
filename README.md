# ScholarPilot AI | المستشار الذكي المستقل للمنح الدراسية الدولية
### Autonomous AI Scholarship Advisor & Intelligence Platform

منصة ذكية متكاملة ومستشار أكاديمي مدعوم بالذكاء الاصطناعي التوليدي (**Google Gemini**)، مصممة لمراقبة وفحص وتصفية المنح الدراسية العالمية المعتمدة بصورة آلية بنسبة 100%، وحساب نسب القبول التقديرية للطلاب، ومراجعة السير الذاتية ورسائل الدافع، وإرسال تقارير مخصصة أسبوعياً مباشرة إلى البريد الإلكتروني.

---

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%20Production%20Ready-009688?style=flat-square&logo=fastapi&logoColor=white)](web/app.py)
[![Google Gemini API](https://img.shields.io/badge/AI%20Brain-Google%20Gemini%202.5%20Flash-2563eb?style=flat-square&logo=googlegemini&logoColor=white)](https://aistudio.google.com/)
[![Render](https://img.shields.io/badge/Hosting-Render%20Cloud-46e3b7?style=flat-square&logo=render&logoColor=black)](render.yaml)
[![PostgreSQL Neon](https://img.shields.io/badge/Database-Neon%20Serverless%20Postgres-00E599?style=flat-square&logo=postgresql&logoColor=black)](https://neon.tech/)
[![Resend](https://img.shields.io/badge/Email%20API-Resend%20Engine-black?style=flat-square&logo=resend&logoColor=white)](https://resend.com/)
[![Security Hardened](https://img.shields.io/badge/Security-22%20Pass%20Audit%20Hardened-red?style=flat-square)](tests/test_security_suite.py)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

---

## 🌟 الرؤية والأهداف (Mission & Overview)

يعاني آلاف الطلاب الدوليين (وخاصة في فلسطين والعالم العربي) من تشتت فرص المنح الدراسية، وصعوبة تقييم متطلباتها المعقدة، وضياع المواعيد النهائية (**Application Deadlines**)، بالإضافة إلى التكلفة المرتفعة للاستشارات الأكاديمية الخاصة.

مشروع **ScholarPilot AI** يقدم الحل من خلال تحويل تجربة البحث عن المنح من مجرد "محرك بحث تقليدي" إلى **مستشار شخصي متكامل متاح 24/7**، يفهم الملف الأكاديمي للطالب، ويقترح الفرص المتوافقة، ويقيّم نقاط القوة والضعف، ويوجه الطالب في كل خطوة حتى إرسال ملف التقديم.

---

## 🚀 المعمارية السحابية والتقنيات (Cloud Stack Architecture)

تم بناء وهندسة النظام ليعمل بكفاءة فائقة وموثوقية سحابية كاملة بتكلفة تبدأ من الصفر:

```text
               واجهة المستخدم وخادم التطبيق
              Frontend (SPA) + FastAPI
                         │
                         ▼
             الاستضافة السحابية التلقائية
                  Render Web Service
                         │
       ┌─────────────────┼─────────────────┐
       ▼                 ▼                 ▼
قاعدة البيانات السحابية     بوابة إرسال البريد    عقل الذكاء الاصطناعي
 Neon PostgreSQL           Resend API       Google AI Studio
 (Serverless DB)        (HTTP REST API)   (Gemini 2.5 Flash)
```

1. **الواجهة الأمامية (Frontend)**:
   - واجهة عصرية وسلسة مصممة بنظام **SaaS Design System** مستوحى من (Linear و Stripe).
   - نمط إضاءة نهاري مريح للعين (**Anti-Glare Eye Comfort**) بألوان الباستيل والرمادي الناعم، ونمط ليلي جذاب (**Dark Mode**).
   - مكتبة أيقونات **Lucide SVG** نقية (خالية 100% من الإيموجي داخل عناصر التحكم والأزرار) لتوفير مظهر احترافي.

2. **الواجهة الخلفية (FastAPI Backend)**:
   - مبنية بلغة بايثون الحديثة (**Python 3.11+**) مع خادم غير متزامن (**Uvicorn ASGI**).
   - تحكم كامل بالمهام الخلفية (**Background Tasks & Daemons**) لجلب المنح وإرسال التنبيهات.

3. **قاعدة البيانات (Neon Serverless PostgreSQL + SQLAlchemy 2.0 ORM)**:
   - اتصال مشفر ببروتوكول **SSL** إجباري (`sslmode=require`) مع إدارة فعالة لمجمّع الاتصالات (**Connection Pooling**).
   - ميزة **الهجرة والتغذية التلقائية (Auto-Migration & Seeding)**: ينشئ النظام الجداول وينقل السجلات الأولية تلقائياً عند أول إقلاع دون كتابة أي كود SQL.
   - دعم التراجع الآمن (**Dual-Persistence Fallback**) للعمل محلياً عبر SQLite أو ملفات JSON في حال انقطاع الاتصال الخارجي.

4. **نظام البريد الإلكتروني (Resend HTTP REST API)**:
   - اتصال فائق السرعة عبر HTTPS يمنع تماماً مشاكل حجب منافذ SMTP (587 و 465) المعتادة في الاستضافات السحابية.
   - إرسال تقارير المنح الأسبوعية وقوالب HTML التفاعلية ورسائل تذكير المواعيد ومرفقات CSV المشفرة بـ Base64.

5. **عقل الذكاء الاصطناعي (Google AI Studio - Gemini API)**:
   - تشغيل موديلات **Gemini 2.5 Flash** أو **Gemini 3.5 Flash Lite** ذات السرعة العالية والسياق الواسع (1 Million Context Window).
   - خوارزمية **Python-First Token Optimization**: ينفذ بايثون الحسابات والفرز والتحقق الرياضي مسبقاً، بينما يتفرغ Gemini للتحليل المنطقي والاستشارة الأكاديمية لتوفير استهلاك التوكنز (**Token Conservation**).

---

## 💡 الإمكانيات والميزات الذكية (Core Capabilities)

### 1. الوعي التلقائي ببيانات الطالب (User Profile Awareness)
لا يُطلب من الطالب إعادة إدخال بياناته؛ بمجرد تسجيل الدخول أو الاشتراك، يستخدم المستشار بياناته المحفوظة فوراً:
- المعدل التراكمي (GPA)
- التخصص الدقيق (Major) والدرجة الأكاديمية (Degree Level)
- دولة الإقامة والوجهات المفضلة (Preferred Destinations)
- مستوى اللغة الإنجليزية (IELTS / TOEFL)
- المواهب والأنشطة اللامنهجية (Talents & Extracurriculars)
- المنحات المحفوظة في قائمة المراقبة (Saved Watchlist)

### 2. محرك التوافق خماسي الأبعاد (5-Dimensional Smart Matcher)
يحسب نسبة توافق رقمية (0% - 100%) لكل منحة دراسية بناءً على 5 معايير:
- **توافق المعدل (GPA Compatibility)**
- **توافق التخصص (Major Compatibility)**
- **أهلية الدولة والكوتا المخصصة (Country Quota Eligibility)**
- **توافق الدرجة العلمية (Degree Level Eligibility)**
- **متطلبات اللغة (Language Requirements)**

### 3. حاسبة احتمالية القبول ("What Are My Chances?")
تحلل مدى تنافسية الطالب على منحة معينة وتحدد:
- نسبة القبول التقديرية (Acceptance Probability Score)
- تصنيف المرشح (Strong Candidate / Competitive / Reach)
- نقاط القوة (Key Strengths) ونقاط الضعف (Weaknesses)
- توصيات دقيقة لرفع الحظوظ قبل إغلاق التقديم.

### 4. مصفوفة مقارنة المنح (Scholarship Comparison Matrix)
تتيح مقارنة فورية بين منحتين أو أكثر (مثل DAAD مقابل Stipendium Hungaricum) في جدول منظم يقارن:
- التغطية المالية وبدل المعيشة (Funding & Monthly Stipend)
- إعفاء الرسوم الدراسية (Tuition Coverage)
- درجة الصعوبة والتنافسية (Competitiveness Tier)
- متطلبات اللغة وتعقيد إجراءات التقديم (Application Complexity)
- القرار والخلاصة الاستشارية (Advisor Verdict).

### 5. المراجع الذكي للسيرة الذاتية (CV & Resume Reviewer)
- يدعم رفع ملفات السيرة الذاتية بصيغتي **PDF** و **Word (.docx)**.
- استخراج وقراءة نقية في بايثون دون الاعتماد على مكتبات خارجية ثقيلة.
- تقييم احترافي من 0 إلى 100 يشمل: التنسيق، وضوح الإنجازات، توافق أنظمة الفرز الآلي (**ATS Compatibility**)، والتوصيات التحسينية.

### 6. مراجع رسائل الدافع (Motivation Letter Reviewer)
- فحص رسائل الدافع وخطابات النوايا (**Statement of Purpose**).
- تقييم قوة المقدمة (Hook)، ووضوح الأهداف الأكاديمية، والارتباط بالمنحة، والأخطاء اللغوية، واقتراح بدائل احترافية للفقرات الضعيفة.

### 7. مولد خطط التقديم والجداول الزمنية (Application Roadmap Generator)
- تقسيم الفترة المتبقية حتى الموعد النهائي إلى أسابيع عمل محددة (Week-by-Week Milestones).
- قائمة تحقق تفاعلية (**Application Checklist**) بالوثائق المطلوبة (شهادات، توصيات، ترجمة، تصديقات).

### 8. صانع المراسلات الأكاديمية (Academic Outreach & Email Drafter)
- صياغة إيميلات جاهزة للمراسلة الأكاديمية بنقرة زر:
  - الاستفسار من مكتب المنح (Official Inquiry).
  - مراسلة المشرفين والدكاترة (Professor Outreach).
  - طلب خطابات التوصية (Recommendation Request).
  - متابعة حالة الطلب (Application Follow-up).
- مع زر نسخ فوري للحافظة (**1-Click Copy**).

### 9. الخدمة الأوتوماتيكية للنشرة الأسبوعية والعد التنازلي
- يعمل خادم خلفي (**Background Automation Daemon**) بشكل تلقائي دون تدخل بشري.
- إرسال تقرير أسبوعي محدّث بالمنح المتاحة لكل طالب وفق تخصصه ومعدله.
- إرسال تنبيهات استباقية بالعد التنازلي للمنح المحفوظة عند اقتراب الموعد النهائي (عند 30، 14، 7، ويومين).

---

## 🛡️ درع الحماية والأمان السيبراني (DevSecOps & Hardening)

اجتاز النظام مراجعة أمنية واختبار اختراق متقدماً يتضمن **22 اختبار تدقيق أمني تلقائي** ([`tests/test_security_suite.py`](file:///c:/Users/مصطفى%20زعيتر/.gemini/antigravity/scratch/Scholarship/tests/test_security_suite.py)):

- **الحماية ضد حقن موجهات الذكاء الاصطناعي (Prompt Injection Defense)**: فك وإبطال تعليمات كسر الحماية (Jailbreaks) وتسريب التوجيهات (Prompt Leakage) وتطهير مخرجات الذكاء الاصطناعي من أي أكواد خبيثة.
- **تشفير كلمات المرور وحماية التوقيت (PBKDF2-HMAC-SHA256)**: تشفير بـ 100,000 جولة، مع توقيت تحقق ثابت (**Constant-Time Execution**) عبر حسابات وهمية لمنع هجمات التوقيت الجانبية (**Timing Side-Channel Attacks**).
- **مكافحة الهجمات العنيفة وقفل الحسابات (Brute-Force Lockout)**: قفل مؤقت للحساب بعد تكرار المحاولات الخاطئة مع سجلات ذاتية التنظيف (**Sliding Window Rate Limiter**).
- **فحص الملفات المرفوعة بالبايتات السحرية (Magic Bytes Validation)**: منع رفع الملفات التنفيذية والبرمجيات الخبيثة المموّهة (مثل منع امتدادات PE/MZ التنفيذية وELF حتى لو تغير امتدادها إلى `.pdf`).
- **حماية قنابل فك الضغط (Decompression Bomb Shield)**: تحديد سقف قراءة الملفات المضغوطة وXML بحد أقصى لمنع استهلاك ذاكرة الخادم (**Memory Exhaustion DoS**).
- **منع التلاعب وتزوير الآي بي (Anti-Spoofing Defense)**: عدم الوثوق بترويسة `X-Forwarded-For` إلا من الخوادم الوسيطة المحلية المرخصة.
- **تطهير ترويسات البريد (Email Header CRLF Injection Defense)**: منع إدخال أسطر جديدة لمنع استغلال الخادم في إرسال بريد عشوائي (Spam).
- **إزالة المحارف غير المرئية (BiDi Override / Trojan Source Neutralization)**: تنظيف نصوص المدخلات من محارف تغيير اتجاه الكتابة التي تخفي نصوصاً أو أوامر ضارة.
- **ترويسات أمان HTTP الصارمة**:
  - `Content-Security-Policy (CSP)`
  - `X-Frame-Options: DENY` (لمنع Clickjacking)
  - `X-Content-Type-Options: nosniff` (لمنع MIME Spoofing)
  - `Strict-Transport-Security (HSTS)`
  - `Referrer-Policy: strict-origin-when-cross-origin`

---

## 📁 هيكلية ملفات المشروع (Repository Structure)

```text
ScholarPilotAI/
├── .env.example                     # نموذج المتغيرات البيئية الموثقة للمشروع
├── .gitignore                       # استثناء الملفات الحساسة والمؤقتة وقواعد البيانات
├── Dockerfile                       # إعدادات الحاوية للتشغيل في بيئات Docker السحابية
├── render.yaml                      # إعدادات النشر السحابي التلقائي على منصة Render
├── requirements.txt                 # مكتبات بايثون المطلوبة (FastAPI, SQLAlchemy, Resend, Gemini)
├── README.md                        # التوثيق الشامل والمعماري للمنصة
├── dispatch_weekly_subscribers.py   # مشغّل إرسال التقارير الأسبوعية للـ Cron Jobs و CI/CD
├── data/
│   ├── live_scholarships.json       # قاعدة بيانات المنح العالمية المحدثة
│   ├── subscribers.json             # سجل الطلاب المشتركين في النشرة الأسبوعية
│   └── users.json                   # الحسابات المسجلة للطلاب (نسخة احتياطية محلية)
├── services/
│   ├── db.py                        # اتصال Neon PostgreSQL ومخطط SQLAlchemy ORM والهجرة التلقائية
│   ├── email_service.py             # بوابة إرسال الإيميلات عبر Resend HTTP API وبديل SMTP
│   ├── advisor_service.py           # عقل المستشار، محرك المطابقة 5-D، ومراجعة السير الذاتية
│   ├── auth_service.py              # إدارة المصادقة، تشفير PBKDF2، وإصدار التوكنات الآمنة
│   ├── automation_service.py        # خادم الخلفية لمتابعة المواعيد والإرسال الأوتوماتيكي
│   ├── scholarship_engine.py        # محرك البحث واستخراج الفرص وتوليد تقارير HTML
│   └── security_utils.py            # أدوات الفحص، تقييد المعدل، وتطهير النصوص والملفات
├── tests/
│   ├── test_automation_suite.py     # اختبارات التكامل للخدمات الأوتوماتيكية والمستشار الذكي
│   └── test_security_suite.py       # جناح اختبارات الأمان واختبار الاختراق (22 اختباراً)
└── web/
    ├── app.py                       # تطبيق FastAPI ونقاط النهاية ونظام حماية المسارات
    ├── static/
    │   └── css/
    │       └── scholarpilot.css     # نظام التصميم البصري والألوان المريحة للعين
    └── templates/
        ├── index.html               # الصفحة الرئيسية، محرك الاستكشاف، ونافذة المستشار الذكي
        └── dashboard.html           # لوحة تحكم الطالب، قائمة المراقبة، وتعديل المعايير
```

---

## 🛠️ دليل التثبيت والتشغيل المحلي (Local Setup)

### 1. المتطلبات الأساسية (Prerequisites)
- تثبيت لغة بايثون **Python 3.10** أو أحدث.
- مفتاح **Gemini API** من Google AI Studio (اختياري للذكاء الاصطناعي الكامل، أو يعمل النظام تلقائياً بالنظام الاحتياطي).

### 2. تثبيت الحزم (Installation)
```bash
# 1. استنساخ المستودع
git clone https://github.com/medozaiter/scholarship-automation.git
cd scholarship-automation

# 2. إنشاء بيئة افتراضية وتفعيلها
python -m venv .venv
# على ويندوز:
.venv\Scripts\activate
# على لينكس أو ماك:
source .venv/bin/activate

# 3. تثبيت المتطلبات
pip install -r requirements.txt

# 4. تجهيز ملف الإعدادات
cp .env.example .env
```

### 3. تشغيل الخادم المحلي (Run Local Server)
```bash
uvicorn web.app:app --host 127.0.0.1 --port 7860 --reload
```
افتح المتصفح على الرابط: `http://127.0.0.1:7860`

### 4. تشغيل الاختبارات والتأكد من الجاهزية (Run Tests)
```bash
# تشغيل جناح اختبارات الأمان والتحصين
python tests/test_security_suite.py

# تشغيل جناح اختبارات الأتمتة والمستشار
python tests/test_automation_suite.py
```

---

## ☁️ دليل الرفع والنشر السحابي (Production Hosting Guide)

تم ضبط التطبيق ليعمل بسلاسة تامة على:
**FastAPI + Render + Neon PostgreSQL + Resend + Google AI Studio**.

### الخطوة 1: قاعدة بيانات Neon PostgreSQL
1. سجّل دخولك إلى [Neon Console](https://neon.tech/) مجاناً.
2. أنشئ مشروعاً جديداً باسم `scholarpilot`.
3. انسخ رابط الاتصال (**Connection String**) من لوحة التحكم، وسيكون بالشكل التالي:
   ```text
   postgresql://neondb_owner:xxxxxx@ep-xxxx.eu-central-1.aws.neon.tech/neondb?sslmode=require
   ```
   *(لا تقلق بشأن الجداول، سيقوم التطبيق بإنشائها ونقل البيانات إليها تلقائياً فور التشغيل)*.

### الخطوة 2: خدمة البريد Resend
1. سجّل في [Resend](https://resend.com/) مجاناً.
2. أنشئ مفتاحاً جديداً من تبويب **API Keys** يبدأ بـ `re_...`.
3. عنوان المرسل الافتراضي للتجربة: `ScholarPilot AI <onboarding@resend.dev>`.

### الخطوة 3: مفتاح Google AI Studio
1. احصل على مفتاح Gemini API من [Google AI Studio](https://aistudio.google.com/app/apikey).

### الخطوة 4: تشغيل الاستضافة على Render
1. ادخل إلى [Render Dashboard](https://dashboard.render.com/) واضغط **New +** ثم **Web Service**.
2. اربط مستودع GitHub الخاص بك.
3. ضع إعدادات البناء والتشغيل:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn web.app:app --host 0.0.0.0 --port $PORT --proxy-headers`
   - **Health Check Path**: `/healthz`
4. أضف المتغيرات البيئية (**Environment Variables**):

| المفتاح (Key) | القيمة (Value) | الغرض |
| :--- | :--- | :--- |
| `DATABASE_URL` | رابط الاتصال المنسوخ من Neon | قاعدة البيانات السحابية الدائمة |
| `RESEND_API_KEY` | مفتاح Resend الذي يبدأ بـ `re_...` | إرسال الإيميلات الأسبوعية والتقارير |
| `RESEND_FROM_EMAIL` | `ScholarPilot AI <onboarding@resend.dev>` | عنوان المرسل المعتمد |
| `GEMINI_API_KEY` | مفتاح Google AI Studio | تشغيل المستشار الذكي |
| `GEMINI_MODEL` | `gemini-2.5-flash` | اختيار الموديل فائق السرعة |
| `SECRET_KEY` | مفتاح عشوائي طويل (ينشئه Render تلقائياً) | تشفير جلسات الطلاب |
| `ALLOWED_ORIGINS` | `*` | السماح بروابط الواجهة |
| `PYTHON_VERSION` | `3.11.9` | إصدار بيئة بايثون |

5. اضغط **Deploy**؛ سيتم البناء وتشغيل المنصة فوراً وتصبح حية ومتاحة للعالم.

### الخطوة 5: التحقق من صحة النظام (Health Probe)
بمجرد اكتمال التشغيل، افتح رابط تطبيقك: `https://your-app.onrender.com/healthz`
وستتلقى رداً يؤكد عمل كافة أركان المنظومة:
```json
{
  "status": "healthy",
  "database": {
    "type": "Neon PostgreSQL",
    "connected": true,
    "pool": "active"
  },
  "email": {
    "provider": "Resend (HTTP REST API)",
    "status": "active"
  },
  "ai": {
    "provider": "Google AI Studio",
    "model": "gemini-2.5-flash",
    "configured": true
  },
  "version": "2.5.0"
}
```

---

## 📜 الترخيص (License)

هذا المشروع مرخص تحت رخصة **MIT License** المفتوحة - متاح لدعم وتمكين الطلاب والباحثين عن الفرص التعليمية حول العالم.

**تطوير وإشراف:** [Mustafa AbuZaiter](https://github.com/medozaiter)
