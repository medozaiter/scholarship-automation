# EduAtlas | نظام ملاحة واستكشاف المنح والفرص الأكاديمية العالمية
### Academic Opportunity Navigation & Intelligence System

[![Platform: EduAtlas](https://img.shields.io/badge/Platform-EduAtlas%20Navigation%20System-C86446?style=flat-square)](https://scholarpilot-ai-mkac.onrender.com)
[![Visual Identity](https://img.shields.io/badge/Identity-Compass%20%2B%20Topography-16324F?style=flat-square)](docs/brand_identity.md)
[![Backend: FastAPI](https://img.shields.io/badge/Backend-FastAPI%20Production%20Ready-009688?style=flat-square&logo=fastapi&logoColor=white)](web/app.py)
[![Security Hardened](https://img.shields.io/badge/Security-Helmet%20%7C%20RateLimit%20%7C%20reCAPTCHA%20%7C%20bcrypt-red?style=flat-square)](services/security_utils.py)
[![AI Brain: Gemini](https://img.shields.io/badge/AI%20Brain-Google%20Gemini%202.5%20Flash-2563eb?style=flat-square&logo=googlegemini&logoColor=white)](https://aistudio.google.com/)
[![Database: Neon](https://img.shields.io/badge/Database-Neon%20Serverless%20Postgres-00E599?style=flat-square&logo=postgresql&logoColor=black)](https://neon.tech/)
[![Email Engine: Resend](https://img.shields.io/badge/Email%20Dispatch-Resend%20%2B%20SMTP%20TLS-black?style=flat-square&logo=resend&logoColor=white)](https://resend.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

---

## 🧭 الهوية البصرية وفلسفة التصميم (Brand Concept: Compass + Topography)

منصة **EduAtlas** ليست مجرد روبوت محادثة أو تطبيق تعليمي تقليدي؛ المنصة هي **«نظام ملاحة واستكشاف متكامل يرشد الطلاب نحو الفرص والمنح الأكاديمية العالمية»**.

```text
الطلاب مستكشفون  ◄───►  المنح الدراسية وجهات  ◄───►  الجامعات معالم عالمية
```

### رموز الهوية البصرية:
- **البوصلة (Compass)**: ترمز للتوجيه الأكاديمي الدقيق وإرشاد الطالب في كل مرحلة.
- **الخطوط الطبوغرافية (Topography)**: ترمز للاستكشاف الأكاديمي وسبر أغوار الفرص الدولية.
- **نقطة الهدف (Target Point)**: المنحة الدراسية المنشودة وفرص التمويل الكامل.
- **المسارات (Routes)**: الخطط الدراسية والمراحل التقديمية حتى الوصول للقمة.

### النظام اللوني المعتمد (Design Language Palette):
- **ورق الخرائط العاجي (Map Parchment)**: `#F4F1EA` (الخلفية المريحة للعين في الوضع النهاري).
- **الصلصال التضاريسي (Exploration Terracotta)**: `#C86446` (أزرار التحفيز الأساسية ومسار التوجيه).
- **الكحلي الأكاديمي العميق (Academic Navy)**: `#16324F` (الترويسات والنصوص الرئيسية).
- **الرمادي الحجري المظلم (Deep Slate)**: `#0B1724` (خلفية الوضع الليلي عالي التباين).
- **الأخضر الزيتوني للخرائط (Olive Contour)**: `#1F4D3A` (شارات التحقق والنجاح).
- **أيقونات Lucide SVG الصافية**: واجهة احترافية خالية 100% من الإيموجي داخل عناصر التحكم والأزرار الرسمية.

---

## 🌟 القيمة الحقيقية والوظائف الرئيسية (Core Value & Capabilities)

1. **الرصد والتحديث الآلي 24/7**: نظام خلفي مؤتمت يراقب بوابات الجامعات والوزارات والهيئات المانحة، ويزيل تلقائياً أي منحة منتهية (0% منح منتهية).
2. **محرك التوافق خماسي الأبعاد (5-D Matching Engine)**: فحص ومطابقة المعدل التراكمي، التخصص، الكوتا الوطنية المتاحة، الدرجة العلمية، ومتطلبات اللغة.
3. **حاسبة احتمالية القبول («احسب فرصتك»)**: تحليل تقديري دقيق لنسب القبول وتحديد نقاط القوة والضعف لتفادي الرفض.
4. **محرك التنبيهات البريدية الذاتي (EduAtlas Dispatch Engine)**: إرسال تنبيهات فورية مخصصة ومطابقة 100% لمؤهلات الطالب فور فتح باب التقديم قبل فوات المواعيد النهائية.
5. **المستشار الأكاديمي الذكي (AI Academic Advisor)**: استشارات موجهة وفورية مدعومة بنموذج **Google Gemini 2.5 Flash** مع خوارزمية بايثون لتحسين استهلاك التوكنز (**Token Optimization**).
6. **مجتمع الطلاب المعتمد (Student Community Hub)**: تبادل تجارب القبول الواقعية، وتوثيق قصص النجاح في جامعات العالم، ومناقشة متطلبات التقديم.
7. **مرصد الأخبار والبرقيات الميدانية (Educational Newsroom)**: متابعة حية لتمديد مواعيد التقديم وتحديثات التأشيرات الدولية مع ربط آلي مباشر بقناة التلجرام الرسمية.

---

## 🛡️ طبقات الأمان والتحصين السيبراني (DevSecOps & 7-Pillar Security Suite)

تم تدعيم المنصة بمنظومة أمنية متكاملة عبر **7 طبقات حماية سيبرانية قياسية**:

```text
                الطلبات الواردة (Incoming Requests)
                               │
                               ▼
        ┌──────────────────────────────────────────────┐
        │ 1. Helmet Security Headers (CSP, HSTS, etc.) │
        └──────────────────────┬───────────────────────┘
                               │
                               ▼
        ┌──────────────────────────────────────────────┐
        │ 2. Sliding-Window Rate Limiting (RFC-429)    │
        └──────────────────────┬───────────────────────┘
                               │
                               ▼
        ┌──────────────────────────────────────────────┐
        │ 3. Google reCAPTCHA Verification Layer       │
        └──────────────────────┬───────────────────────┘
                               │
                               ▼
        ┌──────────────────────────────────────────────┐
        │ 4. Input Validation & SQL Injection Defense  │
        └──────────────────────┬───────────────────────┘
                               │
                               ▼
        ┌──────────────────────────────────────────────┐
        │ 5. Bcrypt Password Hashing (Work Factor 12)  │
        └──────────────────────┬───────────────────────┘
                               │
                               ▼
        ┌──────────────────────────────────────────────┐
        │ 6. Dual Email Verification (Code & HMAC-256) │
        └──────────────────────┬───────────────────────┘
                               │
                               ▼
              العمليات المصرح بها (Safe Execution)
```

### 1. تقييد معدل الطلبات (Rate Limiting)
- نافذة انزلاقية زمنية (**Sliding-Window Limiter**) ذاتية التنظيف لمنع تسريب الذاكرة وهجمات Slowloris.
- ترويسات RFC قياسية على كافة الردود:
  - `X-RateLimit-Limit`
  - `X-RateLimit-Remaining`
  - `X-RateLimit-Reset`
- تصنيف الحصص بحسب الحساسية:
  - عمليات المصادقة (`/api/auth/`): 10 طلبات / دقيقة.
  - رفع الملفات (`/api/user/upload-*`): 10 طلبات / دقيقة.
  - استفسارات المستشار الذكي (`/api/assistant/`): 25 طلباً / دقيقة.
  - المجتمع والتعليقات (`/api/community/`): 20 طلباً / دقيقة.
  - الطلبات العامة: 150 طلباً / دقيقة.
- حماية ضد تزوير العناوين (**Anti-Spoofing Defense**) بحظر الاعتماد على ترويسة `X-Forwarded-For` إلا من الخوادم الوسيطة الموثوقة محلياً.

### 2. توثيق البريد الإلكتروني (Email Verification)
- نظام توثيق مزدوج ومريح للطالب:
  1. **رمز تحقق رقمي (6-Digit Code)** مدة صلاحيته 24 ساعة.
  2. **رابط تفعيل فوري بنقرة واحدة (1-Click Verification Link)** مشفر بتوقيع `HMAC-SHA256` وصلاحية 48 ساعة.
- إرسال آلي لرسالة التفعيل فور إنشاء الحساب.
- شارة توثيق رسمية للملف الأكاديمي (`Verified Student Badge`).

### 3. درع الكابتشا (reCAPTCHA Protection)
- فحص خادمي موثوق لتوكنات **Google reCAPTCHA** على بوابات التسجيل، تسجيل الدخول، استعادة كلمة المرور، ونشر محتوى المجتمع.
- فحص درجة الأمان التقديرية (Score Assessment) وحظر روبوتات السبام والهجمات الآلية.
- دعم الوضع التطويري المريح والتوكنات الاختبارية لضمان عمل بيئة التطوير والاختبارات الآلية بسلاسة.

### 4. تشفير كلمات المرور المتقدم (Bcrypt Password Hashing)
- اعتماد خوارزمية **Bcrypt** القياسية مع معامل صعوبة **Work Factor 12** وأملاح عشوائية آمنة تشفيرياً.
- **الترقية التلقائية الصامتة (Seamless Auto-Migration)**: فحص كلمات المرور القديمة المشفرة بـ PBKDF2 أو SHA-256، وترقيتها تلقائياً إلى تجزئة Bcrypt الحديثة فور أول تسجيل دخول ناجح للمستخدم دون الحاجة لتغيير كلمة المرور.
- درع توقيت وهمي (**Constant-Time Execution Timing Shield**) لمنع هجمات التوقيت الجانبية وحماية الحسابات من التعداد الآلي (User Enumeration).

### 5. ترويسات الأمان الصارمة (Helmet Security Headers)
تطبيق ترويسات الحماية المتقدمة على كافة ردود الخادم:
- `X-Content-Type-Options: nosniff` (منع التلاعب بأنواع MIME).
- `X-Frame-Options: DENY` (حظر كامل لهجمات Clickjacking والتضمين في إطارات خارجية).
- `X-XSS-Protection: 1; mode=block` (تفعيل درع الحماية ضد هجمات Cross-Site Scripting).
- `Referrer-Policy: strict-origin-when-cross-origin` (حماية خصوصية الروابط المحالة).
- `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload` (إلزام بروتوكول HTTPS المشفر).
- `Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()` (حظر الوصول غير المصرح للمستشعرات).
- `Cross-Origin-Opener-Policy: same-origin-allow-popups` و `Cross-Origin-Resource-Policy: cross-origin`.
- **حجب بصمة الخادم (Server Fingerprinting Suppression)**: حذف ترويسات `Server` و `X-Powered-By` لمنع الاستطلاع الأمني للتقنيات المستخدمة.
- **سياسة أمان المحتوى (Content-Security-Policy)**: حصر مصادر السكربتات الموثوقة والسماح بالترخيص الآمن لـ Google reCAPTCHA وخطوط Google والخطوط والأيقونات المعتمدة.

### 6. التحقق الدقيق من المدخلات (Input Validation)
- نماذج **Pydantic v2** صارمة مع تدقيق أنواع البيانات وأطوال النصوص المسموحة.
- تعقيم نصوص الحقول وإزالة وسوم HTML الخبيثة وحقن السكربتات (`XSS Sanitization`).
- تنظيف محارف التوجيه المخفية والتحكم (`BiDi Override & Trojan Source Defense`).

### 7. الحماية ضد حقن قواعد البيانات (SQL Injection Protection)
- استخدام استعلامات محددة المعالم بالكامل عبر **SQLAlchemy 2.0 Parameterized ORM**.
- فحص واستبعاد أنماط وكلمات الحقن المتقدمة (`UNION SELECT`, `OR 1=1`, `DROP TABLE`, `SLEEP()`, `BENCHMARK()`, `EXEC()`) ومنع إدراجها في أي مدخلات نصية.

---

## 🏛️ المعمارية التقنية السحابية (Cloud Architecture Stack)

```text
                        متصفحات الطلاب والمستكشفين
                 Desktop / Tablet / Mobile Browsers
                                │
                                ▼
                   منصة الاستضافة السحابية Render
                Render Cloud Web Service (Linux ASGI)
                                │
                                ▼
                     خادم بايثون غير المتزامن
                     FastAPI + Uvicorn ASGI
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
 قاعدة البيانات السحابية    محرك إرسال الإيميلات    عقل الذكاء الاصطناعي
  Neon Serverless PG      Resend API + SMTP TLS    Google Gemini 2.5
 (SQLAlchemy 2.0 ORM)    (EduAtlas Alert Engine)  (google-genai SDK)
```

- **الواجهة الأمامية (Frontend)**: HTML5 Semantic, Tailwind CSS, Lucide SVG, Topography Contours, Mobile Drawer, Light/Dark Modes.
- **الواجهة الخلفية (Backend)**: Python 3.11+, FastAPI 0.115+, Uvicorn, Pydantic v2, Bleach, Bcrypt, Httpx.
- **قواعد البيانات (Data Layer)**: Neon Serverless PostgreSQL مع دعم التراجع المحلي الذري (Atomic JSON Store Fallback).
- **البريد والإنذارات (Alerts & Dispatch)**: Resend HTTP REST API مدعوماً بـ TLS SMTP وبوت التلجرام الرسمي.

---

## 📁 هيكلية ملفات المشروع (Repository Structure)

```text
Scholarship/
├── data/                               # قواعد البيانات وملفات التخزين الاحتياطية
│   ├── live_scholarships.json          # سجل المنح الدراسية العالمية المعتمدة
│   ├── news_articles.json              # مقالات وأخبار المنح والمواعيد
│   ├── community_posts.json            # منشورات المجتمع الطلابي
│   └── users.json                      # الحسابات الطلابية المحلية
├── services/                           # الطبقة الخدمية ومنطق الأعمال
│   ├── advisor_service.py              # المستشار الأكاديمي، فحص السير الذاتية ورسائل الدافع
│   ├── auth_service.py                 # المصادقة، تشفير Bcrypt، وإدارة الجلسات الآمنة
│   ├── automation_service.py           # المجدول الآلي 24/7 لرصد المواعيد وإرسال التقارير
│   ├── db.py                           # اتصال Neon PostgreSQL ومخططات SQLAlchemy ORM
│   ├── email_service.py                # محرك الإرسال البريدي عبر Resend و SMTP
│   ├── news_service.py                 # رصد الأخبار والبرقيات ونشر التلجرام
│   ├── scholarship_engine.py           # مطابقة المنح خماسية الأبعاد وتوليد التقارير
│   └── security_utils.py               # درع الحماية، التشفير، الكابتشا، تقييد المعدل، وفحص الحقن
├── tests/                              # أجنحة الاختبارات الآمنية والوظيفية
│   ├── test_advanced_security_suite.py # اختبارات الحماية الـ 7 (Bcrypt, Helmet, reCAPTCHA, etc.)
│   ├── test_scholarship_news.py        # اختبارات المركز الإخباري وتكامل التلجرام
│   ├── test_upload_and_light_mode.py   # اختبارات رفع الصور والوضع النهاري
│   └── test_automation_suite.py        # اختبارات الجدولة والمطابقة الأكاديمية
├── web/                                # تطبيق الويب والقوالب
│   ├── app.py                          # نقاط النهاية (FastAPI Routes) وترويسات الأمان
│   ├── static/                         # الملفات الثابتة وملفات الرفع
│   │   ├── css/scholarpilot.css        # نظام التصميم البصري والألوان
│   │   └── uploads/                    # مجلد رفع الصور الشخصية وأغلفة الحسابات
│   └── templates/                      # قوالب واجهة المستخدم (Jinja2)
│       ├── index.html                  # الصفحة الرئيسية وخطوات العمل والمطابقة
│       ├── dashboard.html              # لوحة تحكم الطالب وإدارة الملف الأكاديمي
│       ├── community.html              # مجتمع الطلاب وقصص النجاح المعتمدة
│       ├── news.html                   # مرصد الأخبار وتحديثات المنح الحية
│       └── assistant.html              # المستشار الأكاديمي الذكي
├── requirements.txt                    # مكتبات بايثون المطلوبة للإنتاج
├── render.yaml                         # مواصفات النشر السحابي في Render
└── README.md                           # التوثيق الشامل لهوية المنصة
```

---

## 🛠️ دليل التثبيت والتشغيل المحلي (Local Setup)

### 1. استنساخ المستودع وإنشاء البيئة الافتراضية
```bash
# 1. استنساخ المشروع
git clone https://github.com/medozaiter/scholarship-automation.git
cd scholarship-automation

# 2. إنشاء بيئة بايثون افتراضية وتفعيلها
python -m venv .venv
# على ويندوز:
.venv\Scripts\activate
# على لينكس أو ماك:
source .venv/bin/activate

# 3. تثبيت الحزم والمكتبات المعتمدة
pip install -r requirements.txt
```

### 2. إعداد المتغيرات البيئية (.env)
انسخ النموذج وأدخل مفاتيحك الخاصة:
```bash
cp .env.example .env
```
أهم المتغيرات:
```env
# رابط قاعدة البيانات السحابية (أو اتركها فارغة للاعتماد على التخزين المحلي)
DATABASE_URL=postgresql://neondb_owner:xxxx@ep-xxxx.neon.tech/neondb?sslmode=require

# مفتاح الذكاء الاصطناعي من Google AI Studio
GEMINI_API_KEY=AIzaSy...

# مفتاح خدمة البريد Resend أو SMTP
RESEND_API_KEY=re_xxxx...
RESEND_FROM_EMAIL=EduAtlas <onboarding@resend.dev>

# مفتاح Google reCAPTCHA
RECAPTCHA_SECRET_KEY=6Le...

# مفتاح التشفير للجلسات وتوكنات البريد (32 حرفاً على الأقل)
SECRET_KEY=your-super-cryptographically-secure-secret-key-2026
```

### 3. تشغيل خادم التطوير
```bash
uvicorn web.app:app --host 127.0.0.1 --port 7860 --reload
```
افتح المتصفح على: `http://127.0.0.1:7860`

### 4. تشغيل الاختبارات الآلية
```bash
# 1. فحص جناح الحماية والأمان المتقدم (7 ركائز)
python -m unittest tests/test_advanced_security_suite.py

# 2. فحص رصد الأخبار والمواعيد النهائية
python -m unittest tests/test_scholarship_news.py

# 3. فحص رفع الصور والوضع النهاري
python -m unittest tests/test_upload_and_light_mode.py

# 4. فحص جودة الكود والأنواع
npm run lint
npm run typecheck
```

---

## ☁️ النشر السحابي على Render (Cloud Deployment)

المنصة جاهزة للنشر الفوري على **Render**:
1. اربط المستودع في **Render Dashboard** واختر **Web Service**.
2. **Build Command**: `pip install -r requirements.txt`
3. **Start Command**: `uvicorn web.app:app --host 0.0.0.0 --port $PORT --proxy-headers`
4. **Health Check Path**: `/healthz`
5. عيّن المتغيرات البيئية الموضحة أعلاه، وسيتم إطلاق المنصة ونشرها مباشرة.

---

## 📜 الترخيص والمساهمة (License & Attribution)

هذا المشروع مفتوح ومطور لدعم وتمكين الطلاب العرب والدوليين في نيل فرصهم الأكاديمية العالمية.
مرخص تحت رخصة **MIT License**.

- **المطور والمشرف العام**: [Mustafa AbuZaiter (مصطفى زعيتر)](https://github.com/medozaiter)
- **المنصة الحية**: [https://scholarpilot-ai-mkac.onrender.com](https://scholarpilot-ai-mkac.onrender.com)
