# 📧 دليل ضبط بريد المنصة وضمان وصول الرسائل لصندوق الوارد (Deliverability Setup Guide)

تم تصميم وتطوير نظام البريد الإلكتروني في **ScholarPilot AI** وفقاً لأحدث معايير الأمان وتسليم الرسائل العالمية (Email Deliverability Best Practices 2026) المتوافقة مع متطلبات **Google / Yahoo / Outlook** الإلزامية.

يعتمد النظام على **Resend HTTP REST API** كمزود أساسي سحابي فائق السرعة، مع بديل تلقائي **Gmail / SMTP**، بالإضافة إلى ترويسات الإلغاء بضغطة واحدة (`List-Unsubscribe: One-Click`).

---

## 1. سجلات نظام أسماء النطاقات (DNS Records) لضمان عدم وصول الرسائل للـ SPAM

لضمان وصول تنبيهات المنح والنشرات الأسبوعية مباشرة إلى **صندوق الوارد (Primary Inbox)**، قم بإضافة السجلات التالية في لوحة تحكم نطاقك (Cloudflare, Namecheap, GoDaddy):

### أ) سجل SPF (Sender Policy Framework)
يُخوّل خوادم Resend و Google بإرسال البريد نيابة عن نطاقك الرسمي لمنع انتحال الهوية:

| الحقل (Field) | القيمة (Value) |
| :--- | :--- |
| **Type** | `TXT` |
| **Host / Name** | `@` (أو اتركها فارغة حسب مزود النطاق) |
| **Value / Content** | `v=spf1 include:resend.com ~all` |
| **TTL** | `Auto` أو `3600` |

> *إذا كنت تستخدم Google Workspace أيضاً على نفس النطاق، ادمج السجلين معاً*:  
> `v=spf1 include:_spf.google.com include:resend.com ~all`

---

### ب) سجلات DKIM (DomainKeys Identified Mail)
توقيع تشفيري رقمي بمفتاح عام/خاص يُثبت أن محتوى الإيميل لم يتم التلاعب به أثناء النقل:

1. ادخل إلى لوحة تحكم [Resend Domains](https://resend.com/domains).
2. اضغط **Add Domain** وأدخل نطاقك الرسمي (مثلاً `scholarpilot.ai`).
3. سيقوم Resend بتوليد 3 سجلات `CNAME` أو `TXT` تلقائياً تبدأ عادةً بـ:
   - **Host**: `resend._domainkey.yourdomain.com`
   - **Value**: التوقيع الرقمي المخصص المولد من Resend.
4. أضف هذه السجلات في لوحة DNS واضغط **Verify DNS Records** في Resend.

---

### ج) سجل DMARC (الإلزامي لـ Gmail و Yahoo)
يحدد سياسة التعامل مع الرسائل التي تفشل في اختبارات SPF أو DKIM لحماية سمعة النطاق:

| الحقل (Field) | القيمة (Value) |
| :--- | :--- |
| **Type** | `TXT` |
| **Host / Name** | `_dmarc` (أو `_dmarc.yourdomain.com`) |
| **Value / Content** | `v=DMARC1; p=quarantine; pct=100; rua=mailto:reports@yourdomain.com; aspf=r; adkim=r` |
| **TTL** | `Auto` أو `3600` |

* **`p=quarantine`**: يوجه مزودي البريد لنقل أي بريد مشبوه أو غير موثق للـ Spam بدلاً من رفضه فجأة أثناء فترة الإعداد.
* **`pct=100`**: تطبيق الفحص على 100% من الرسائل الصادرة.
* **`rua`**: بريد استقبال تقارير التحليل المجمعة حول أداء التسليم.

---

## 2. متغيرات البيئة في لوحة استضافة Render (Environment Variables)

لربط النظام في الإنتاج، تأكد من ضبط المتغيرات التالية في لوحة **Render Dashboard > Environment**:

```env
# 1. مفتاح واجهة برمجة Resend السحابي (الأساسي)
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxxxxxxxx

# 2. البريد الرسمي المعتمد للمنصة (بعد توثيق النطاق في Resend)
RESEND_FROM_EMAIL=ScholarPilot AI <admissions@yourdomain.com>

# 3. مزود النسخ الاحتياطي (Gmail SMTP Fallback)
SENDER_EMAIL=your-verified-email@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx

# 4. بوت تليجرام للتنبيهات الفورية (اختياري)
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
```

---

## 3. ميزات تسليم الرسائل المدمجة برمجياً في الكود

يقوم ملف `services/email_service.py` بتضمين الترويسات القياسية تلقائياً في كل رسالة يتم إرسالها:

1. **إلغاء الاشتراك بنقرة واحدة (One-Click Unsubscribe)**:
   - `List-Unsubscribe: <https://scholarpilot-ai-mkac.onrender.com/dashboard>, <mailto:unsubscribe@scholarpilot.ai>`
   - `List-Unsubscribe-Post: List-Unsubscribe=One-Click`
   *(متوافق 100% مع معايير RFC 8058 وتحديثات Gmail لعام 2024)*.
2. **تصنيف البريد المجمع**:
   - `Precedence: bulk`
   - `X-Auto-Response-Suppress: OOF, AutoReply` لمنع الردود التلقائية ورسائل العطلة من إغراق السيرفر.
3. **معرّف رسالة فريد لتعقب التكرار**:
   - `X-Entity-Ref-ID: sp_xxxxxxxx`
4. **نسخة نصية موازية (Plain Text Fallback)**:
   - كل قالب HTML يرافقه نص عادي لتجاوز فلاتر البريد الصارمة والعمل على قارئات الشاشة وساعات Apple Watch.

---

## 4. فحص واختبار جودة التسليم (Testing & Monitoring)

يمكنك اختبار درجة تسليم بريدك مجاناً عبر:
1. إرسال بريد تجريبي من لوحة التحكم أو الرادار إلى أداة [Mail-Tester](https://www.mail-tester.com).
2. يجب أن يحصل البريد على تقييم **9/10 أو 10/10**.
3. مراجعة سجلات التتبع اللحظية عبر الرابط البرمجي:
   `GET /api/notifications/events`
   لمعرفة حالة كل إشعار: `created` -> `sent` -> `delivered` -> `opened` -> `clicked`.
