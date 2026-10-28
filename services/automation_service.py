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
        from services.email_service import dispatch_email
        clean_name = sanitize_text(student_name)
        clean_sch = sanitize_text(scholarship_name)
        urgency_color = "#dc2626" if days_remaining <= 7 else "#d97706"
        urgency_bg = "#fef2f2" if days_remaining <= 7 else "#fffbeb"

        html_content = f"""
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; margin: 0; padding: 20px; color: #f8fafc; }}
            .card {{ max-width: 600px; margin: 0 auto; background: #1e293b; border-radius: 16px; border: 1px solid #334155; padding: 30px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5); }}
            .badge {{ display: inline-block; padding: 6px 14px; border-radius: 20px; font-weight: bold; font-size: 13px; background: {urgency_bg}; color: {urgency_color}; border: 1px solid {urgency_color}40; margin-bottom: 16px; }}
            .title {{ font-size: 22px; font-weight: 800; color: #ffffff; margin: 0 0 12px 0; }}
            .desc {{ font-size: 14px; color: #94a3b8; line-height: 1.6; margin-bottom: 24px; }}
            .info-box {{ background: #0f172a; border-radius: 12px; padding: 16px; border: 1px solid #334155; margin-bottom: 24px; }}
            .info-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #1e293b; font-size: 13px; }}
            .btn {{ display: inline-block; background: #2563eb; color: #ffffff !important; text-decoration: none; padding: 12px 28px; border-radius: 10px; font-weight: bold; font-size: 14px; text-align: center; }}
            .footer {{ text-align: center; font-size: 11px; color: #64748b; margin-top: 24px; }}
          </style>
        </head>
        <body>
          <div class="card">
            <span class="badge">⏰ تنبيه موعد نهائي اقترب ({days_remaining} أيام متبقية)</span>
            <h1 class="title">تذكير بخصوص منحة {clean_sch}</h1>
            <p class="desc">مرحباً {clean_name}، نود تذكيرك بأن الموعد النهائي المحدد لتقديم الطلب الرسمي يقترب، لتفادي إغلاق البوابة وضياع فرصة المنافسة.</p>
            <div class="info-box">
              <div class="info-row">
                <span style="color:#94a3b8;">المنحة:</span>
                <strong style="color:#ffffff;">{clean_sch}</strong>
              </div>
              <div class="info-row">
                <span style="color:#94a3b8;">الموعد النهائي:</span>
                <strong style="color:{urgency_color};">{deadline_date}</strong>
              </div>
              <div class="info-row" style="border-bottom:none;">
                <span style="color:#94a3b8;">الوقت المتبقي:</span>
                <strong style="color:{urgency_color};">{days_remaining} يوماً</strong>
              </div>
            </div>
            <div style="text-align: center;">
              <a href="{link}" target="_blank" class="btn">الانتقال لرابط التقديم الرسمي ↗</a>
            </div>
            <div class="footer">
              تم إرسال هذا التنبيه التلقائي عبر نظام المتابعة الذكية لمنصة ScholarPilot AI.
            </div>
          </div>
        </body>
        </html>
        """
        await dispatch_email(
            to_email=recipient_email,
            subject=f"تذكير بالموعد النهائي: متبقي {days_remaining} أيام على إغلاق التقديم لمنحة {clean_sch}",
            html_content=html_content,
            text_content=f"مرحباً {clean_name}، نود تذكيرك بأن الموعد النهائي لمنحة {clean_sch} يغلق بتاريخ {deadline_date} (متبقي {days_remaining} يوماً). رابط التقديم: {link}"
        )


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
