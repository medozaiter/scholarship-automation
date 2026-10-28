# 🎓 منحة تك AI | MinhaTech AI Copilot
### المنظومة الذكية لتتبع المنح، حساب نسبة التوافق، وتوليد مستندات التقديم 🚀

[![GitHub Workflow](https://img.shields.io/badge/GitHub%20Actions-Automated%20Weekly-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)](.github/workflows/weekly_scholarship.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-Web%20App-009688?style=for-the-badge&logo=fastapi&logoColor=white)](web/app.py)
[![Google Gemini AI](https://img.shields.io/badge/Google%20Gemini-3.5%20Flash%20Lite-orange?style=for-the-badge&logo=googlegemini&logoColor=white)](https://aistudio.google.com/)
[![Dark / Light Mode](https://img.shields.io/badge/Theme-Dark%20%26%20Light-purple?style=for-the-badge)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

---

## 🌟 نظرة عامة (Overview)

**منحة تك AI (MinhaTech AI Copilot)** هي منصة ذكاء اصطناعي شاملة ومفتوحة المصدر، صُممت لمساعدة الطلاب في **فلسطين والعالم العربي** على تحقيق أحلامهم الأكاديمية في الخارج.

يدخل الطالب بياناته **مرة واحدة فقط** (التخصص، المعدل، الدولة، مرحلة الدراسة، ومستوى اللغة)، ثم تتولى المنظومة كل شيء بالخلفية:
1. **جلب المنح الرسمية المفتوحة دورياً** واستبعاد الروابط المنتهية.
2. **حساب نسبة توافق ملفك الأكاديمي (Match Score %)** لكل منحة، وتنبيهك بالمتطلبات الناقصة.
3. **إرسال تقرير أسبوعي مخصص (Personalized Digest)** بأفضل 5 فرص مناسبة لك في إيميل HTML فاخر مع ملف Excel.
4. **تذكيرك التلقائي بالمواعيد النهائية (Deadline Reminders)** قبل إغلاق بوابات التقديم بشهر وأسبوعين وأسبوع ويومين.
5. **مستشار أكاديمي مباشر بالذكاء الاصطناعي (AI Advisor)** للإجابة على استفساراتك ووضع خطة التقديم.
6. **مُولّد مستندات التقديم الذكية (Smart Documents Generator)** لكتابة خطاب الدافع (Motivation Letter)، نموذج التوصية الأكاديمية، وقائمة التحقق المخصصة لكل منحة.

---

## 🚀 المميزات والوظائف الـ 6 الرئيسية (Core Modules)

### 1️⃣ التنبيه الذكي للمنح (Smart Scholarship Alert)
يسجل الطالب ملفه الأكاديمي (التخصص، المعدل التراكمي، مستوى اللغة، الدرجة العلمية، والوجهات المفضلة). يبحث النظام دورياً بالإنترنت ويرسل تنبيهاً فور توفر منحة جديدة مطابقة أو اقتراب موعد إغلاقها.

### 2️⃣ التقرير الأسبوعي المخصص (Personalized Scholarship Digest)
بدلاً من استقبال عشرات الرسائل العشوائية، يتلقى الطالب رسالة أسبوعية واحدة كل جمعة صباحاً تحتوي:
* أفضل 5 منح مناسبة تماماً لتخصصه ومعدله.
* بطاقة **نسبة التوافق (Match Score %)**.
* قائمة **المتطلبات الواجب مراعاتها والنواقص**.
* شارة عد تنازلي للموعد النهائي (مثلاً: بقي 12 يوماً!).

### 3️⃣ محرك حساب نسبة التوافق (Scholarship Match Score Engine)
تحليل دقيق يقارن معدل الطالب الأكاديمي، كفاءة اللغة الإنجليزية، الأهلية الجغرافية، والتخصص المطلوب مع شروط المنحة لحساب نسبة مئوية واقعية (مثلاً: 94% توافق عالي) مع تحديد نقاط القوة.

### 4️⃣ رادار وتذكير المواعيد النهائية (Deadline Reminder System)
عند حفظ أي منحة في قائمة المتابعة، يرسل النظام تنبيهات متدرجة:
* قبل شهر
* قبل أسبوعين
* قبل أسبوع
* قبل يومين (تنبيه نهائي)

### 5️⃣ المستشار الأكاديمي بالذكاء الاصطناعي (AI Scholarship Advisor)
مربع استشارة مباشر على الموقع؛ يكتب الطالب استفساره بحرية (مثلاً: *"معدلي 85 وهندسة برمجيات وأريد منحة في أوروبا"*). يقوم Gemini AI بتحليل الاستفسار وترشيح أفضل المنح الحكومية وخطة التقديم والخطوات الفورية.

### 6️⃣ مُولّد مستندات التقديم الذكية (Smart Application Documents Generator)
بمجرد اختيار المنحة المستهدفة، يولد النظام تلقائياً:
* **خطاب دافع احترافي مخصص (Motivation Letter / SOP)** يعكس تخصص ومعدل الطالب.
* **نموذج خطاب توصية أكاديمي (Academic Recommendation Letter)** جاهز لتوقيع الأساتذة.
* **قائمة التحقق المسبقة (Pre-Flight Application Checklist)** بجميع الأوراق المطلوبة.
* إمكانية إرسال الحزمة كاملة فوراً إلى إيميل الطالب بنقرة واحدة!

---

## 📋 الأعمدة الـ 11 في جدول التقرير (11-Column Matrix)

يتضمن كل تقرير تفاصيل دقيقة باللغة الإنجليزية:
1. **Scholarship & Provider Name** (اسم المنحة والجهة المانحة).
2. **Country / Institution** (الدولة والجامعة المستضيفة).
3. **Language of Instruction** (لغة الدراسة والبرامج التحضيرية).
4. **Application Status** (الحالة: مفتوح حالياً Open Now أو يفتح قريباً).
5. **Application Deadline** (تاريخ الموعد النهائي الدقيق).
6. **Application Mechanism** (آلية التقديم: مدمج أو منفصل).
7. **Academic & General Requirements** (المعدل المطلوب وشروط اللغة).
8. **Standardized Tests** (شروط SAT / ACT / GRE أو اختبارات القبول).
9. **Visa Support & Facilitation** (تسهيلات التأشيرة وخطابات الدعم الرسمية).
10. **Competitiveness & Acceptance Rate** (مستوى التنافسية ونسبة القبول).
11. **Direct Official Link** (الرابط المباشر للبوابة الرسمية).

---

## 🖥️ تشغيل المنصة محلياً (Run Locally)

```bash
# 1. تفعيل البيئة وتثبيت الحزم
pip install -r requirements.txt

# 2. تشغيل خادم FastAPI
uvicorn web.app:app --host 0.0.0.0 --port 8000 --reload
```
افتح المتصفح على: **`http://localhost:8000`** 🌟

---

## 📂 هيكلية المشروع (Project Architecture)

```text
scholarship-automation/
├── .github/
│   └── workflows/
│       └── weekly_scholarship.yml    # الأوتوميشن السحابي الأسبوعي عبر GitHub Actions
├── data/
│   ├── subscribers.json              # قاعدة بيانات الطلاب وسجلات التوافق
│   └── subscribers.example.json      # نموذج توضيحي لملف المشتركين
├── web/
│   ├── templates/
│   │   └── index.html                # واجهة الويب الفاخرة (Dark/Light + AI Advisor + Doc Generator)
│   ├── __init__.py
│   └── app.py                        # خادم واجهات برمجة التطبيقات (FastAPI)
├── services/
│   ├── advisor_service.py            # محرك حساب نسبة التوافق + المستشار الذكي + توليد المستندات
│   ├── scholarship_engine.py         # محرك البحث والاستخراج المباشر للأعمدة الـ 11 والتقارير
│   ├── subscriber_service.py         # إدارة ملفات وتفضيلات الطلبة وتذكيرات المواعيد
│   ├── gemini_service.py             # تكامل Google Gemini مع سلاسل التحويل التلقائي
│   ├── search_service.py             # محرك البحث المخصص (DuckDuckGo Scraper)
│   ├── broadcast_service.py          # خدمة البث في القنوات
│   └── cache_service.py              # تخزين مؤقت لتوفير استهلاك الـ API
├── dispatch_weekly_subscribers.py    # مشغل الإرسال الدوري لكافة الطلاب المسجلين
├── send_scholarship_report.py        # المحرك الفردي لإرسال تقرير مخصص
├── config.json                       # ملف إعدادات الطالب الشخصي
├── requirements.txt                  # مكتبات بايثون المطلوبة
├── Procfile                          # ملف تشغيل السحابة
├── render.yaml                       # تكوين النشر بنقرة واحدة على Render
├── .env.example                      # نموذج لمتغيرات البيئة
└── README.md                         # التوثيق الشامل ودليل الاستخدام
```

---

## 🔒 الأمان والخصوصية (Security & Privacy)

* جميع البيانات الحساسة (كلمات مرور التطبيقات ومفاتيح الـ API) مشفرة ومحمية عبر ملف `.gitignore`.
* تُحفظ الأسرار في GitHub Secrets المشفرة أثناء التشغيل السحابي.
* لا يتم مشاركة بيانات أو إيميلات الطلبة إطلاقاً.

---

## 📄 الترخيص (License)

هذا المشروع مرخص تحت رخصة **MIT** - متاح مجاناً للجميع لدعم الطلاب والتعليم.

---

<div align="center">
  <b>صُمم بحب لدعم الطلاب الطموحين في فلسطين وحول العالم 🇵🇸🎓</b><br>
  تم تطويره وإدارته بواسطة <a href="https://github.com/medozaiter"><b>Mustafa AbuZaiter</b></a>
</div>
