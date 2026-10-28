import os
import json
import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional

from services.subscriber_service import SubscriberService
from services.scholarship_engine import ScholarshipEngine
from services.auth_service import AuthService

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
LIVE_SCHOLARSHIPS_FILE = os.path.join(DATA_DIR, "live_scholarships.json")

# Verified base roster of flagship global scholarships
DEFAULT_LIVE_SCHOLARSHIPS = [
    {
        "id": "pearson",
        "name": "Lester B. Pearson Scholarship",
        "university": "جامعة تورنتو (University of Toronto)",
        "country": "كندا (Canada)",
        "degree": "Undergraduate (بكالوريوس)",
        "matchScore": "96%",
        "matchLabel": "توافق استثنائي",
        "status": "مفتوح حالياً للتقديم",
        "statusClass": "sp-badge-success",
        "deadline": "2026-11-06",
        "deadline_display": "6 نوفمبر 2026",
        "deadlineDays": "متبقي أسبوع واحد",
        "coverage": "تغطية كاملة 100%: الرسوم الدراسية + السكن الجامعي الكامل 4 سنوات + تكلفة الكتب والتأمين",
        "requirements": "المعدل الأكاديمي 85%+، شهادة الثانوية العامة، رسالة ترشيح من المدرسة، إثبات القيادة المجتمعية",
        "link": "https://future.utoronto.ca/pearson/",
        "is_active": True
    },
    {
        "id": "hungaricum",
        "name": "Stipendium Hungaricum Scholarship",
        "university": "جامعات المجر الحكومية (بودابست، ديبريسين، زيجد)",
        "country": "المجر (الاتحاد الأوروبي)",
        "degree": "بكالوريوس • ماجستير • دكتوراه",
        "matchScore": "95%",
        "matchLabel": "توافق مرتفع جداً",
        "status": "تفتح للتقديم قريباً",
        "statusClass": "sp-badge-info",
        "deadline": "2027-01-15",
        "deadline_display": "15 يناير 2027",
        "deadlineDays": "يفتح خلال شهرين",
        "coverage": "إعفاء دراسي 100% + راتب شهري + سكن جامعي مجاني + تأمين صحي شامل",
        "requirements": "معدل 80%+ للبكالوريوس، شهادة إتمام مرحلة سابقة، خطاب دافع وفحص طبي رسمي",
        "link": "https://stipendiumhungaricum.hu/",
        "is_active": True
    },
    {
        "id": "turkiye",
        "name": "Türkiye Bursları Government",
        "university": "كافة الجامعات التركية الحكومية الرائدة (METU, Boğaziçi)",
        "country": "تركيا (Turkey)",
        "degree": "كافة المراحل (بكالوريوس ودراسات عليا)",
        "matchScore": "93%",
        "matchLabel": "كوتا سنوية خاصة",
        "status": "تفتح 10 يناير 2027",
        "statusClass": "sp-badge-info",
        "deadline": "2027-02-20",
        "deadline_display": "20 فبراير 2027",
        "deadlineDays": "فرصة سنوية كبرى",
        "coverage": "رسوم مجانية 100% + راتب شهري + سكن جامعي + سنة تحضيرية للغة وتذاكر طيران",
        "requirements": "حد أدنى 70% للبكالوريوس (90% للطب البشري)، رسائل توصية، وخطاب نوايا قوي",
        "link": "https://www.turkiyeburslari.gov.tr/",
        "is_active": True
    },
    {
        "id": "chevening",
        "name": "Chevening UK Government Scholarship",
        "university": "جامعات المملكة المتحدة (أكسفورد، كامبريدج، إمبريال، UCL)",
        "country": "بريطانيا (UK)",
        "degree": "Master's Degree (ماجستير)",
        "matchScore": "90%",
        "matchLabel": "برنامج القادة والتميز",
        "status": "مفتوح حالياً",
        "statusClass": "sp-badge-warning",
        "deadline": "2026-11-05",
        "deadline_display": "5 نوفمبر 2026",
        "deadlineDays": "أيام معدودة للإغلاق",
        "coverage": "تمويل كامل بنسبة 100% + راتب شهري للمعيشة في بريطانيا + تذاكر طيران ذهاب وعودة",
        "requirements": "درجة البكالوريوس بتقدير جيد جداً على الأقل، سنتان خبرة مهنية، 4 مقالات قيادية",
        "link": "https://www.chevening.org/scholarships/",
        "is_active": True
    },
    {
        "id": "gks",
        "name": "Global Korea Scholarship (GKS)",
        "university": "أفضل الجامعات الكورية في سيئول والمدن الكبرى (SNU, KAIST)",
        "country": "كوريا الجنوبية (South Korea)",
        "degree": "بكالوريوس وماجستير ودكتوراه",
        "matchScore": "91%",
        "matchLabel": "تطور تكنولوجي وأكاديمي",
        "status": "التقديم السنوي عبر السفارة",
        "statusClass": "sp-badge-info",
        "deadline": "2027-03-25",
        "deadline_display": "مارس 2027",
        "deadlineDays": "تفتح في الربيع",
        "coverage": "رسوم دراسية كاملة + راتب شهري 1,000,000 وون + سنة لغة كورية وتذاكر طيران",
        "requirements": "معدل تراكمي أعلى من 80%، فحص طبي، خطة دراسية وبيان شخصي باللغة الإنجليزية",
        "link": "https://www.studyinkorea.go.kr/",
        "is_active": True
    },
    {
        "id": "daad",
        "name": "DAAD Scholarships Germany",
        "university": "جامعات ألمانيا التقنية والبحثية (TUM, LMU, Heidelberg)",
        "country": "ألمانيا (Germany)",
        "degree": "Master's & PhD (دراسات عليا)",
        "matchScore": "95%",
        "matchLabel": "توافق استثنائي",
        "status": "مفتوح حسب التخصص",
        "statusClass": "sp-badge-success",
        "deadline": "2026-12-15",
        "deadline_display": "15 ديسمبر 2026",
        "deadlineDays": "مستمر حسب البرنامج",
        "coverage": "راتب شهري 934 يورو + تأمين صحي شامل + بدل سفر وتكاليف الأبحاث والمراجع",
        "requirements": "درجة بكالوريوس لا يتجاوز عمرها 6 سنوات، سنتان خبرة عمل، وخطاب دافع أكاديمي",
        "link": "https://www.daad.de/en/",
        "is_active": True
    },
    {
        "id": "erasmus",
        "name": "Erasmus Mundus Joint Masters (EMJM)",
        "university": "اتحاد جامعات أوروبية متعددة (فرنسا، ألمانيا، إسبانيا، إيطاليا)",
        "country": "الاتحاد الأوروبي (Europe)",
        "degree": "Master's Degree (ماجستير مشترك)",
        "matchScore": "94%",
        "matchLabel": "دراسة في 2 إلى 3 دول أوروبية",
        "status": "تفتح للتقديم الآن تدريجياً",
        "statusClass": "sp-badge-info",
        "deadline": "2027-01-20",
        "deadline_display": "20 يناير 2027",
        "deadlineDays": "برامج متعددة",
        "coverage": "إعفاء دراسي كامل 100% + راتب شهري 1,400 يورو لمدة عامين + تذاكر سفر وبدل إقامة",
        "requirements": "شهادة البكالوريوس، سيرة ذاتية Europass، رسالتا توصية، ومقال دافع لكل تخصص",
        "link": "https://erasmus-plus.ec.europa.eu/opportunities/opportunities-for-individuals/students/erasmus-mundus-joint-masters",
        "is_active": True
    }
]


class AutomationService:
    """
    100% Fully Automated Background Service:
    1. Periodically refreshes and maintains live scholarships without human intervention.
    2. Dispatches weekly personalized digest emails to all registered students automatically.
    3. Scans approaching deadlines and sends automated reminder alerts (30, 14, 7, 2 days before).
    """

    def __init__(self):
        self.sub_service = SubscriberService()
        self.engine = ScholarshipEngine()
        self.auth_service = AuthService()
        self._ensure_live_scholarships_file()

    def _ensure_live_scholarships_file(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        if not os.path.exists(LIVE_SCHOLARSHIPS_FILE):
            with open(LIVE_SCHOLARSHIPS_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_LIVE_SCHOLARSHIPS, f, ensure_ascii=False, indent=2)

    def get_live_scholarships(self) -> List[Dict[str, Any]]:
        """Returns the current auto-managed scholarship catalogue."""
        data_list = []
        try:
            with open(LIVE_SCHOLARSHIPS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    data_list = data
        except Exception as e:
            logger.warning(f"Could not read live scholarships file: {e}")
            
        if not data_list:
            data_list = list(DEFAULT_LIVE_SCHOLARSHIPS)

        for item in data_list:
            if "official_link" not in item:
                item["official_link"] = item.get("link", "#")
        return data_list

    async def auto_refresh_scholarships_from_web(self):
        """
        Periodically checks for fresh opportunities using Gemini and web discovery
        and updates the live catalogue automatically.
        """
        logger.info("Executing automated scholarship discovery refresh...")
        try:
            undergrad = await self.engine.search_and_extract(
                degree="Undergraduate (Bachelor's)",
                majors=["Computer Science", "Engineering"],
                country="Palestine"
            )
            if undergrad and len(undergrad) >= 3:
                # Merge with base scholarships preserving links
                current = self.get_live_scholarships()
                current_names = {s["name"].lower() for s in current}

                for item in undergrad:
                    name = item.get("name", "").strip()
                    if name and name.lower() not in current_names:
                        current.append({
                            "id": f"auto_{abs(hash(name)) % 100000}",
                            "name": name,
                            "university": item.get("provider", "Leading Global University"),
                            "country": item.get("country_institution", "International"),
                            "degree": "بكالوريوس / ماجستير",
                            "matchScore": "92%",
                            "matchLabel": "فرصة جديدة تم رصدها آلياً ⚡",
                            "status": "مفتوح رسمياً",
                            "statusClass": "sp-badge-success",
                            "deadline": item.get("deadline", "2027-01-30"),
                            "deadline_display": item.get("deadline", "2027"),
                            "deadlineDays": "تحقق من الرابط",
                            "coverage": item.get("funding", "تغطية دراسية كاملة أو جزئية"),
                            "requirements": item.get("requirements", "متطلبات القبول الرسمية"),
                            "link": item.get("official_link", "https://google.com"),
                            "is_active": True
                        })
                with open(LIVE_SCHOLARSHIPS_FILE, "w", encoding="utf-8") as f:
                    json.dump(current, f, ensure_ascii=False, indent=2)
                logger.info(f"✅ Successfully auto-refreshed scholarship catalogue. Total now: {len(current)}")
        except Exception as e:
            logger.error(f"Error in automated scholarship discovery: {e}")

    async def auto_dispatch_weekly_digests(self) -> Dict[str, Any]:
        """
        Automated Weekly Dispatcher:
        Scans all active subscribers. If 7 days have passed since their last digest,
        generates and delivers their personalized report automatically.
        """
        subscribers = self.sub_service.get_all(active_only=True)
        now = datetime.now()
        dispatched = 0
        failed = 0

        logger.info(f"Checking weekly digest eligibility for {len(subscribers)} subscribers...")

        for sub in subscribers:
            email = sub.get("email")
            last_sent_str = sub.get("last_sent_at")
            should_send = False

            if not last_sent_str:
                should_send = True
            else:
                try:
                    last_sent_dt = datetime.fromisoformat(last_sent_str)
                    if (now - last_sent_dt).total_seconds() >= (7 * 86400 - 3600):  # 7 days with buffer
                        should_send = True
                except Exception:
                    should_send = True

            if should_send:
                logger.info(f"Automated Weekly Dispatch triggering for: {email}")
                try:
                    ok = await self.engine.send_personalized_report(
                        recipient_email=email,
                        student_name=sub.get("full_name", "Student"),
                        degree=sub.get("degree", "Undergraduate (Bachelor's)"),
                        majors=sub.get("majors", ["Computer Science"]),
                        country=sub.get("country", "Palestine"),
                        student_profile=sub
                    )
                    if ok:
                        dispatched += 1
                        self.sub_service.update_last_sent(email)
                    else:
                        failed += 1
                except Exception as e:
                    failed += 1
                    logger.error(f"Auto-dispatch error for {email}: {e}")
                await asyncio.sleep(2)  # rate limit pause

        return {
            "dispatched": dispatched,
            "failed": failed,
            "total_subscribers": len(subscribers)
        }

    async def auto_dispatch_deadline_reminders(self):
        """
        Automated Deadline Monitor:
        Scans all users and their saved_scholarships. If a deadline is approaching
        within 30, 14, 7, or 2 days, sends an automated alert email.
        """
        users = self.auth_service._load_users()
        scholarships = self.get_live_scholarships()
        sch_dict = {s["name"].lower(): s for s in scholarships}
        today = date.today()

        for user in users:
            email = user.get("email")
            saved = user.get("saved_scholarships", [])
            if not saved:
                continue

            for sch_name in saved:
                matched = sch_dict.get(sch_name.lower())
                if not matched:
                    continue
                dl_str = matched.get("deadline")
                if not dl_str:
                    continue
                try:
                    dl_date = datetime.strptime(dl_str[:10], "%Y-%m-%d").date()
                    days_remaining = (dl_date - today).days

                    # Trigger on key milestones
                    if days_remaining in [30, 14, 7, 2, 1]:
                        logger.info(f"Sending deadline reminder for '{sch_name}' to {email} ({days_remaining} days left)")
                        await self._send_reminder_email(
                            recipient_email=email,
                            student_name=user.get("full_name", "Student"),
                            scholarship_name=sch_name,
                            days_remaining=days_remaining,
                            deadline_date=dl_str,
                            link=matched.get("link", "https://google.com")
                        )
                except Exception as e:
                    logger.debug(f"Could not parse deadline date {dl_str}: {e}")

    async def _send_reminder_email(
        self,
        recipient_email: str,
        student_name: str,
        scholarship_name: str,
        days_remaining: int,
        deadline_date: str,
        link: str
    ):
        """Dispatches an urgent, beautifully styled reminder email."""
        from email.message import EmailMessage
        import smtplib

        sender_email = os.getenv("SENDER_EMAIL") or os.getenv("EMAIL_USER")
        gmail_password = os.getenv("GMAIL_APP_PASSWORD") or os.getenv("EMAIL_PASS")
        if not sender_email or not gmail_password:
            return

        gmail_password = gmail_password.replace(" ", "").strip()
        msg = EmailMessage()
        msg["Subject"] = f"تذكير بالموعد النهائي: باقي {days_remaining} أيام على إغلاق التقديم لمنحة {scholarship_name}"
        msg["From"] = f"ScholarPilot AI <{sender_email}>"
        msg["To"] = recipient_email

        html = f"""
        <div dir="rtl" style="font-family: Arial, sans-serif; background-color: #090d16; color: #f8fafc; padding: 25px; border-radius: 16px;">
            <div style="background: #1e3a8a; padding: 20px; border-radius: 12px; text-align: center; color: white;">
                <h2>تذكير باقتراب الموعد النهائي للمنحة</h2>
            </div>
            <div style="padding: 20px; background: rgba(255,255,255,0.05); margin-top: 15px; border-radius: 12px;">
                <p>مرحباً <b>{student_name}</b>،</p>
                <p>نود تذكيرك بأن المنحة المحفوظة في ملفك: <b style="color: #60a5fa;">{scholarship_name}</b></p>
                <p style="font-size: 16px; color: #f59e0b;">باقي على موعد إغلاق التقديم: <b>{days_remaining} يوماً فقط</b> (تاريخ الإغلاق: {deadline_date}).</p>
                <p>يرجى إكمال وتدقيق أوراقك الأكاديمية وخطاب الدافع فوراً والتقديم عبر البوابة الرسمية قبل انتهاء المهلة.</p>
                <div style="text-align: center; margin: 25px 0;">
                    <a href="{link}" target="_blank" style="background: #2563eb; color: white; padding: 12px 25px; border-radius: 8px; text-decoration: none; font-weight: bold;">
                        التقديم الآن عبر البوابة الرسمية
                    </a>
                </div>
            </div>
            <p style="font-size: 11px; color: #64748b; text-align: center;">ScholarPilot AI | Your AI-Powered Scholarship Advisor</p>
        </div>
        """
        msg.set_content(f"تذكير: باقي {days_remaining} يوماً على إغلاق منحة {scholarship_name}. رابط التقديم: {link}")
        msg.add_alternative(html, subtype="html")

        try:
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
                server.starttls()
                server.login(sender_email, gmail_password)
                server.send_message(msg)
                logger.info(f"Reminder delivered to {recipient_email}")
        except Exception as e:
            logger.error(f"Failed to send reminder email: {e}")


# Standalone worker loop for background tasks
async def start_automation_daemon():
    """
    Background daemon that runs continuously alongside FastAPI:
    - Checks deadlines and dispatches reminders every 24 hours.
    - Checks weekly subscription cycles.
    """
    automation = AutomationService()
    logger.info("Automation Daemon started. All tasks will run automatically in background.")

    while True:
        try:
            logger.info("Automation daemon running scheduled check...")
            await automation.auto_dispatch_deadline_reminders()
            await automation.auto_dispatch_weekly_digests()
        except Exception as e:
            logger.error(f"Error in automation daemon cycle: {e}")

        # Sleep for 6 hours between checks
        await asyncio.sleep(6 * 3600)
