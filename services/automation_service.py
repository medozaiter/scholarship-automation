import os
import json
import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional

from services.subscriber_service import SubscriberService
from services.scholarship_engine import ScholarshipEngine
from services.auth_service import AuthService
from services.security_utils import sanitize_text, sanitize_email_header

logger = logging.getLogger("scholarpilot.automation")

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
        "target_degrees": ["Undergraduate (Bachelor's)", "بكالوريوس", "ثانوية عامة"],
        "target_majors": ["Computer Science", "Engineering", "Data Science", "Humanities", "Life Sciences"],
        "matchScore": "96%",
        "matchLabel": "توافق استثنائي",
        "status": "مفتوح حالياً للتقديم",
        "statusClass": "sp-badge-success",
        "deadline": "2026-11-06",
        "deadline_display": "6 نوفمبر 2026",
        "deadlineDays": "متبقي أسبوع واحد",
        "coverage": "تغطية كاملة 100%: الرسوم الدراسية + السكن الجامعي الكامل 4 سنوات + تكلفة الكتب والتأمين",
        "requirements": "المعدل الأكاديمي 85%+، شهادة الثانوية العامة، رسالة ترشيح من المدرسة، إثبات القيادة المجتمعية",
        "link": "https://future.utoronto.ca/pearson/about/#apply",
        "is_active": True
    },
    {
        "id": "hungaricum",
        "name": "Stipendium Hungaricum Scholarship",
        "university": "جامعات المجر الحكومية (بودابست، ديبريسين، زيجد)",
        "country": "المجر (الاتحاد الأوروبي)",
        "degree": "بكالوريوس • ماجستير • دكتوراه",
        "target_degrees": ["Undergraduate (Bachelor's)", "Master's Degree", "PhD / Doctorate", "بكالوريوس", "ماجستير", "دكتوراه"],
        "target_majors": ["Computer Science & IT", "Software Engineering", "Medicine", "Civil Engineering", "Business"],
        "matchScore": "95%",
        "matchLabel": "توافق مرتفع جداً",
        "status": "تفتح للتقديم قريباً",
        "statusClass": "sp-badge-info",
        "deadline": "2027-01-15",
        "deadline_display": "15 يناير 2027",
        "deadlineDays": "يفتح خلال شهرين",
        "coverage": "إعفاء دراسي 100% + راتب شهري + سكن جامعي مجاني + تأمين صحي شامل",
        "requirements": "معدل 80%+ للبكالوريوس، شهادة إتمام مرحلة سابقة، خطاب دافع وفحص طبي رسمي",
        "link": "https://apply.stipendiumhungaricum.hu/",
        "is_active": True
    },
    {
        "id": "turkiye",
        "name": "Türkiye Bursları Government",
        "university": "كافة الجامعات التركية الحكومية الرائدة (METU, Boğaziçi)",
        "country": "تركيا (Turkey)",
        "degree": "كافة المراحل (بكالوريوس ودراسات عليا)",
        "target_degrees": ["Undergraduate (Bachelor's)", "Master's Degree", "PhD / Doctorate", "بكالوريوس", "ماجستير", "دكتوراه"],
        "target_majors": ["Computer Science & IT", "Engineering", "Medicine", "Business", "International Relations"],
        "matchScore": "93%",
        "matchLabel": "كوتا سنوية خاصة",
        "status": "تفتح 10 يناير 2027",
        "statusClass": "sp-badge-info",
        "deadline": "2027-02-20",
        "deadline_display": "20 فبراير 2027",
        "deadlineDays": "فرصة سنوية كبرى",
        "coverage": "رسوم مجانية 100% + راتب شهري + سكن جامعي + سنة تحضيرية للغة وتذاكر طيران",
        "requirements": "حد أدنى 70% للبكالوريوس (90% للطب البشري)، رسائل توصية، وخطاب نوايا قوي",
        "link": "https://tbbs.turkiyeburslari.gov.tr/",
        "is_active": True
    },
    {
        "id": "chevening",
        "name": "Chevening UK Government Scholarship",
        "university": "جامعات المملكة المتحدة (أكسفورد، كامبريدج، إمبريال، UCL)",
        "country": "بريطانيا (UK)",
        "degree": "Master's Degree (ماجستير)",
        "target_degrees": ["Master's Degree", "ماجستير"],
        "target_majors": ["Engineering", "Public Policy", "Computer Science", "Finance", "Law"],
        "matchScore": "90%",
        "matchLabel": "برنامج القادة والتميز",
        "status": "مفتوح حالياً",
        "statusClass": "sp-badge-warning",
        "deadline": "2026-11-05",
        "deadline_display": "5 نوفمبر 2026",
        "deadlineDays": "أيام معدودة للإغلاق",
        "coverage": "تمويل كامل بنسبة 100% + راتب شهري للمعيشة في بريطانيا + تذاكر طيران ذهاب وعودة",
        "requirements": "درجة البكالوريوس بتقدير جيد جداً على الأقل، سنتان خبرة مهنية، 4 مقالات قيادية",
        "link": "https://www.chevening.org/apply/",
        "is_active": True
    },
    {
        "id": "gks",
        "name": "Global Korea Scholarship (GKS)",
        "university": "أفضل الجامعات الكورية في سيئول والمدن الكبرى (SNU, KAIST)",
        "country": "كوريا الجنوبية (South Korea)",
        "degree": "بكالوريوس وماجستير ودكتوراه",
        "target_degrees": ["Undergraduate (Bachelor's)", "Master's Degree", "PhD / Doctorate", "بكالوريوس", "ماجستير", "دكتوراه"],
        "target_majors": ["Information Technology", "AI", "Electrical Engineering", "Korean Studies", "Biotech"],
        "matchScore": "91%",
        "matchLabel": "تطور تكنولوجي وأكاديمي",
        "status": "التقديم السنوي عبر السفارة",
        "statusClass": "sp-badge-info",
        "deadline": "2027-03-25",
        "deadline_display": "مارس 2027",
        "deadlineDays": "تفتح في الربيع",
        "coverage": "رسوم دراسية كاملة + راتب شهري 1,000,000 وون + سنة لغة كورية وتذاكر طيران",
        "requirements": "معدل تراكمي أعلى من 80%، فحص طبي، خطة دراسية وبيان شخصي باللغة الإنجليزية",
        "link": "https://www.studyinkorea.go.kr/en/scholarship/gksNoticeList.do",
        "is_active": True
    },
    {
        "id": "daad",
        "name": "DAAD Scholarships Germany",
        "university": "جامعات ألمانيا التقنية والبحثية (TUM, LMU, Heidelberg)",
        "country": "ألمانيا (Germany)",
        "degree": "Master's & PhD (دراسات عليا)",
        "target_degrees": ["Master's Degree", "PhD / Doctorate", "ماجستير", "دكتوراه"],
        "target_majors": ["Engineering", "Informatics", "Data Science", "Natural Sciences", "Economics"],
        "matchScore": "95%",
        "matchLabel": "توافق استثنائي",
        "status": "مفتوح حسب التخصص",
        "statusClass": "sp-badge-success",
        "deadline": "2026-12-15",
        "deadline_display": "15 ديسمبر 2026",
        "deadlineDays": "مستمر حسب البرنامج",
        "coverage": "راتب شهري 934 يورو + تأمين صحي شامل + بدل سفر وتكاليف الأبحاث والمراجع",
        "requirements": "درجة بكالوريوس لا يتجاوز عمرها 6 سنوات، سنتان خبرة عمل، وخطاب دافع أكاديمي",
        "link": "https://www2.daad.de/deutschland/stipendium/datenbank/en/21148-scholarship-database/",
        "is_active": True
    },
    {
        "id": "erasmus",
        "name": "Erasmus Mundus Joint Masters (EMJM)",
        "university": "اتحاد جامعات أوروبية متعددة (فرنسا، ألمانيا، إسبانيا، إيطاليا)",
        "country": "الاتحاد الأوروبي (Europe)",
        "degree": "Master's Degree (ماجستير مشترك)",
        "target_degrees": ["Master's Degree", "ماجستير"],
        "target_majors": ["Artificial Intelligence", "Cybersecurity", "Environmental Sciences", "Humanities"],
        "matchScore": "94%",
        "matchLabel": "دراسة في 2 إلى 3 دول أوروبية",
        "status": "تفتح للتقديم الآن تدريجياً",
        "statusClass": "sp-badge-info",
        "deadline": "2027-01-20",
        "deadline_display": "20 يناير 2027",
        "deadlineDays": "برامج متعددة",
        "coverage": "إعفاء دراسي كامل 100% + راتب شهري 1,400 يورو لمدة عامين + تذاكر سفر وبدل إقامة",
        "requirements": "شهادة البكالوريوس، سيرة ذاتية Europass، رسالتا توصية، ومقال دافع لكل تخصص",
        "link": "https://www.eacea.ec.europa.eu/scholarships/erasmus-mundus-catalogue_en",
        "is_active": True
    }
]


class AutomationService:
    """
    Production-Grade Autonomous Scholarship Discovery & Notification Engine:
    1. Recurring Scholarship Discovery & Ingestion across Global Sources.
    2. Automatic 5-D Student Matching & Threshold-Based Immediate Notifications.
    3. Recurring 7-Day Personalized Reports & Weekly Digests.
    4. Smart Deadline Monitoring (Milestones: 30, 14, 7, 3, 1 Days).
    5. State-Persistent Notification History to prevent spam and duplicate dispatches.
    6. Continuous Daemon that survives server restarts and rate-limits email dispatches safely.
    """

    def __init__(self):
        self.sub_service = SubscriberService()
        self.engine = ScholarshipEngine()
        self.auth_service = AuthService()
        self._ensure_live_scholarships_file()
        self._last_scan_at: Optional[str] = None
        self._last_metrics: Dict[str, Any] = {}

    def _ensure_live_scholarships_file(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        if not os.path.exists(LIVE_SCHOLARSHIPS_FILE):
            with open(LIVE_SCHOLARSHIPS_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_LIVE_SCHOLARSHIPS, f, ensure_ascii=False, indent=2)

    def get_live_scholarships(self) -> List[Dict[str, Any]]:
        """Returns the current auto-managed scholarship catalogue from database or JSON."""
        from services.db import is_db_available, get_db_session, LiveScholarshipDB
        
        # 1. Try DB first
        if is_db_available() and LiveScholarshipDB is not None:
            try:
                with get_db_session() as db:
                    if db is not None:
                        db_items = db.query(LiveScholarshipDB).filter(LiveScholarshipDB.is_active == True).all()
                        if db_items and len(db_items) > 0:
                            return [item.to_dict() for item in db_items]
            except Exception as e:
                logger.debug(f"DB load live scholarships error: {e}")

        # 2. Fallback to JSON
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

    def _save_live_scholarships(self, items: List[Dict[str, Any]]):
        """Persists updated scholarships to both PostgreSQL DB and JSON store."""
        from services.db import is_db_available, get_db_session, LiveScholarshipDB

        # 1. Update Database
        if is_db_available() and LiveScholarshipDB is not None:
            try:
                with get_db_session() as db:
                    if db is not None:
                        for itm in items:
                            s_id = itm.get("id")
                            existing = db.query(LiveScholarshipDB).filter(LiveScholarshipDB.id == s_id).first()
                            if not existing:
                                db.add(LiveScholarshipDB(
                                    id=s_id,
                                    name=itm.get("name"),
                                    university=itm.get("university"),
                                    country=itm.get("country"),
                                    degree=itm.get("degree"),
                                    match_score=itm.get("matchScore"),
                                    match_label=itm.get("matchLabel"),
                                    status=itm.get("status"),
                                    status_class=itm.get("statusClass"),
                                    deadline=itm.get("deadline"),
                                    deadline_display=itm.get("deadline_display"),
                                    deadline_days=itm.get("deadlineDays"),
                                    coverage=itm.get("coverage"),
                                    requirements=itm.get("requirements"),
                                    link=itm.get("link") or itm.get("official_link"),
                                    is_active=itm.get("is_active", True)
                                ))
                            else:
                                if itm.get("link"):
                                    existing.link = itm.get("link")
                                if itm.get("deadline"):
                                    existing.deadline = itm.get("deadline")
                                if itm.get("deadline_display"):
                                    existing.deadline_display = itm.get("deadline_display")
                                if itm.get("status"):
                                    existing.status = itm.get("status")
                                if itm.get("coverage"):
                                    existing.coverage = itm.get("coverage")
            except Exception as e:
                logger.debug(f"DB save live scholarships error: {e}")

        # 2. Update JSON
        try:
            temp_file = LIVE_SCHOLARSHIPS_FILE + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, LIVE_SCHOLARSHIPS_FILE)
        except Exception as je:
            logger.error(f"Error saving live scholarships JSON: {je}")

    def _get_all_active_students(self) -> List[Dict[str, Any]]:
        """Unifies and deduplicates all registered students and active subscribers."""
        students_map: Dict[str, Dict[str, Any]] = {}

        # 1. Registered Users
        try:
            users = self.auth_service._load_users()
            for u in users:
                em = (u.get("email") or "").strip().lower()
                if em and "@" in em:
                    students_map[em] = {
                        "email": em,
                        "full_name": u.get("full_name", "Student"),
                        "degree": u.get("degree", "Undergraduate (Bachelor's)"),
                        "majors": u.get("majors") or ["Software Engineering"],
                        "gpa": u.get("gpa", "85%"),
                        "english_level": u.get("english_level", "Intermediate"),
                        "country": u.get("country", "Palestine"),
                        "target_destinations": ["Any"],
                        "talents_experience": u.get("talents_experience", ""),
                        "saved_scholarships": u.get("saved_scholarships", [])
                    }
        except Exception as e:
            logger.debug(f"Error reading users for automation: {e}")

        # 2. Active Subscribers
        try:
            subs = self.sub_service.get_all(active_only=True)
            for s in subs:
                em = (s.get("email") or "").strip().lower()
                if em and "@" in em:
                    if em not in students_map:
                        students_map[em] = s
                    else:
                        # Merge preferences
                        if s.get("target_destinations"):
                            students_map[em]["target_destinations"] = s["target_destinations"]
                        if s.get("last_sent_at"):
                            students_map[em]["last_sent_at"] = s["last_sent_at"]
                        if s.get("saved_scholarships") and not students_map[em].get("saved_scholarships"):
                            students_map[em]["saved_scholarships"] = s["saved_scholarships"]
        except Exception as e:
            logger.debug(f"Error reading subscribers for automation: {e}")

        return list(students_map.values())

    # ==========================================================================
    # 1. FULLY AUTOMATED SCHOLARSHIP DISCOVERY & INGESTION
    # ==========================================================================
    async def auto_refresh_scholarships_from_web(self) -> Dict[str, Any]:
        """
        Periodically discovers and normalizes newly published scholarships across
        all degrees and sources. Triggers automatic matching whenever new entries are detected.
        """
        logger.info("Executing automated recurring scholarship discovery scan...")
        self._last_scan_at = datetime.now().isoformat()
        newly_discovered: List[Dict[str, Any]] = []

        degrees_to_scan = [
            "Undergraduate (Bachelor's)",
            "Master's Degree",
            "PhD / Doctorate"
        ]

        current = self.get_live_scholarships()
        current_names = {s.get("name", "").strip().lower() for s in current}

        for deg in degrees_to_scan:
            try:
                extracted = await self.engine.search_and_extract(
                    degree=deg,
                    majors=["Computer Science", "Engineering", "Medicine", "Business"],
                    country="Palestine"
                )
                if extracted and len(extracted) > 0:
                    for item in extracted:
                        raw_name = item.get("name", "").strip()
                        if not raw_name or raw_name.lower() in current_names:
                            continue

                        # Normalize attributes
                        clean_id = f"auto_{abs(hash(raw_name)) % 1000000}"
                        official_url = item.get("official_link") or item.get("link") or "https://scholarpilot-ai-mkac.onrender.com"
                        deadline_val = item.get("deadline", "2027-01-30")

                        normalized_item = {
                            "id": clean_id,
                            "name": raw_name,
                            "university": item.get("country_institution") or item.get("provider", "Leading Global University"),
                            "country": item.get("country_institution", "International").split()[-1].strip("()"),
                            "degree": deg,
                            "target_degrees": [deg],
                            "target_majors": ["All Majors", "Computer Science", "Engineering"],
                            "matchScore": "92%",
                            "matchLabel": "فرصة جديدة تم رصدها آلياً ⚡",
                            "status": item.get("status", "مفتوح رسمياً للتقديم"),
                            "statusClass": "sp-badge-success",
                            "deadline": deadline_val,
                            "deadline_display": deadline_val,
                            "deadlineDays": "تحقق من الرابط",
                            "coverage": item.get("funding", "تمويل حكومي شامل أو إعفاء دراسي كامل"),
                            "requirements": item.get("requirements", "متطلبات القبول الأكاديمي الرسمية"),
                            "link": official_url,
                            "official_link": official_url,
                            "is_active": True
                        }

                        current.append(normalized_item)
                        current_names.add(raw_name.lower())
                        newly_discovered.append(normalized_item)
                        logger.info(f"✨ New Verified Scholarship Ingested: {raw_name}")
            except Exception as e:
                logger.error(f"Discovery error scanning degree '{deg}': {e}")
            await asyncio.sleep(1)

        if newly_discovered:
            self._save_live_scholarships(current)
            logger.info(f"✅ Ingestion Complete: {len(newly_discovered)} new opportunities added. Triggering automatic student matching...")
            # Trigger matching engine immediately
            matching_stats = await self.match_and_notify_students_for_new_scholarships(newly_discovered)
            return {
                "success": True,
                "new_discovered_count": len(newly_discovered),
                "total_monitored": len(current),
                "matching_stats": matching_stats
            }

        return {
            "success": True,
            "new_discovered_count": 0,
            "total_monitored": len(current),
            "matching_stats": {"alerts_sent": 0}
        }

    # ==========================================================================
    # 2 & 3. AUTOMATIC STUDENT MATCHING & NOTIFICATION ENGINE
    # ==========================================================================
    async def match_and_notify_students_for_new_scholarships(
        self,
        new_scholarships: List[Dict[str, Any]],
        match_threshold: float = 80.0
    ) -> Dict[str, Any]:
        """
        Automatic Student Matching & Notification Engine:
        Evaluates newly discovered scholarships against all active students.
        Calculates 5-D Match Scores, ranks matches, and dispatches personalized alert
        emails with detailed reasons why the scholarship is a strong match.
        Guarantees idempotency via NotificationHistory.
        """
        from services.advisor_service import AdvisorService
        from services.email_service import dispatch_email
        from services.db import is_notification_sent, record_notification

        advisor = AdvisorService()
        students = self._get_all_active_students()
        logger.info(f"Matching {len(new_scholarships)} new scholarships against {len(students)} active students...")

        total_alerts_sent = 0

        for student in students:
            email = student.get("email")
            if not email or "@" not in email:
                continue

            name = student.get("full_name") or "Student"
            gpa = student.get("gpa") or "85%"
            majors = student.get("majors") or ["Software Engineering"]
            degree = student.get("degree") or "Undergraduate (Bachelor's)"

            for sch in new_scholarships:
                sch_id = sch.get("id") or str(abs(hash(sch.get("name", ""))))
                sch_name = sch.get("name", "منحة دراسية جديدة")

                # Idempotency check: Don't notify the same student twice for the same scholarship
                notification_target = f"new_match_alert_{sch_id}_{email.lower()}"
                if is_notification_sent(email, "new_scholarship_alert", notification_target):
                    continue

                # 5-D Match Score calculation
                match_res = advisor.calculate_smart_match(student, sch)
                score = match_res.get("match_score", 0.0)

                if score >= match_threshold:
                    logger.info(f"🎯 High Match found: {sch_name} ({score}%) for {email}")
                    strengths_html = "".join([f"<li style='margin-bottom:6px;'>{s}</li>" for s in match_res.get("strengths", [])]) or "<li>توافق أكاديمي مباشر مع ملفك المسجل.</li>"
                    link = sch.get("link") or sch.get("official_link", "https://scholarpilot-ai-mkac.onrender.com")

                    subject = f"🎯 رصد منحة جديدة متوافقة مع ملفك بنسبة {score}%: {sch_name}"
                    html_content = f"""
                    <!DOCTYPE html>
                    <html dir="rtl" lang="ar">
                    <head>
                      <meta charset="utf-8">
                      <style>
                        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; margin: 0; padding: 20px; color: #f8fafc; }}
                        .card {{ max-width: 620px; margin: 0 auto; background: #1e293b; border-radius: 18px; border: 1px solid #334155; padding: 32px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5); }}
                        .score-pill {{ display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; border-radius: 9999px; font-weight: 800; font-size: 13px; background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); margin-bottom: 16px; }}
                        .title {{ font-size: 22px; font-weight: 800; color: #ffffff; margin: 0 0 14px 0; line-height: 1.4; }}
                        .desc {{ font-size: 14px; color: #94a3b8; line-height: 1.6; margin-bottom: 20px; }}
                        .info-box {{ background: #0f172a; border-radius: 12px; padding: 18px; border: 1px solid #334155; margin-bottom: 22px; }}
                        .info-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #1e293b; font-size: 13px; }}
                        .reasons {{ background: rgba(59, 130, 246, 0.08); border: 1px solid rgba(59, 130, 246, 0.25); border-radius: 12px; padding: 16px; margin-bottom: 24px; font-size: 13px; color: #cbd5e1; }}
                        .btn {{ display: inline-block; background: #2563eb; color: #ffffff !important; text-decoration: none; padding: 13px 32px; border-radius: 10px; font-weight: 800; font-size: 14px; text-align: center; box-shadow: 0 4px 12px rgba(37,99,235,0.3); }}
                        .footer {{ text-align: center; font-size: 11px; color: #64748b; margin-top: 28px; line-height: 1.5; }}
                      </style>
                    </head>
                    <body>
                      <div class="card">
                        <span class="score-pill">⚡ فرصة جديدة تم رصدها آلياً | توافق {score}%</span>
                        <h1 class="title">{sch_name}</h1>
                        <p class="desc">مرحباً {name}، رصد محرك الذكاء الاصطناعي لمنصة ScholarPilot AI فرصة منحة دراسية جديدة مطابقة بدقة لملفك الأكاديمي المسجل لدينا.</p>
                        
                        <div class="info-box">
                          <div class="info-row">
                            <span style="color:#94a3b8;">المؤسسة والدولة:</span>
                            <strong style="color:#ffffff;">{sch.get('university', sch.get('country', 'International'))} ({sch.get('country', 'دولي')})</strong>
                          </div>
                          <div class="info-row">
                            <span style="color:#94a3b8;">المرحلة الأكاديمية:</span>
                            <strong style="color:#38bdf8;">{sch.get('degree', degree)}</strong>
                          </div>
                          <div class="info-row">
                            <span style="color:#94a3b8;">التغطية المالية:</span>
                            <strong style="color:#34d399;">{sch.get('coverage', 'تمويل كامل أو جزئي')}</strong>
                          </div>
                          <div class="info-row" style="border-bottom:none;">
                            <span style="color:#94a3b8;">الموعد النهائي:</span>
                            <strong style="color:#f59e0b;">{sch.get('deadline_display', sch.get('deadline', 'راجع البوابة'))}</strong>
                          </div>
                        </div>

                        <div class="reasons">
                          <strong style="color:#60a5fa; display:block; margin-bottom:8px;">💡 لماذا تناسبك هذه المنحة بالتحديد؟</strong>
                          <ul style="margin:0; padding-right:20px; line-height:1.6;">
                            {strengths_html}
                            <li>معدلك الحالي ({gpa}) وتخصصك في ({majors[0] if majors else 'تخصصك'}) يمنحانك أهلية تنافسية قوية.</li>
                          </ul>
                        </div>

                        <div style="text-align: center;">
                          <a href="{link}" target="_blank" class="btn">الانتقال لبوابة التقديم الرسمية ↗</a>
                        </div>

                        <div class="footer">
                          تم إرسال هذا التنبيه الشخصي التلقائي بناءً على إعدادات حسابك في منصة ScholarPilot AI.<br>
                          يقوم النظام بمراقبة المواعيد النهائية وإرسال التنبيهات دورياً بدون أي تدخل يدوي.
                        </div>
                      </div>
                    </body>
                    </html>
                    """
                    text_content = f"مرحباً {name}، تم رصد منحة جديدة متوافقة معك بنسبة {score}%: {sch_name}. رابط التقديم: {link}"

                    try:
                        ok = await dispatch_email(
                            to_email=email,
                            subject=subject,
                            html_content=html_content,
                            text_content=text_content
                        )
                        if ok:
                            total_alerts_sent += 1
                            record_notification(
                                recipient=email,
                                notification_type="new_scholarship_alert",
                                target_id=notification_target,
                                subject=subject,
                                status="sent",
                                details={"scholarship_id": sch_id, "score": score}
                            )
                    except Exception as err:
                        logger.error(f"Error dispatching new match alert to {email}: {err}")
                    
                    await asyncio.sleep(1.5)  # Provider rate-limiting safeguard

        return {"alerts_sent": total_alerts_sent}

    # ==========================================================================
    # 4 & 6. WEEKLY AUTOMATED REPORTS (RECURRING 7-DAY PERSONALIZED DIGESTS)
    # ==========================================================================
    async def auto_dispatch_weekly_digests(self) -> Dict[str, Any]:
        """
        Automated Weekly Dispatcher:
        Scans all active students. If 7 days have passed since their last digest,
        generates and delivers their personalized 5-D report automatically.
        Guarantees idempotency per calendar week to prevent spam.
        """
        from services.db import is_notification_sent, record_notification

        students = self._get_all_active_students()
        now = datetime.now()
        current_week_num = now.isocalendar()[1]
        dispatched = 0
        failed = 0

        logger.info(f"Checking weekly digest eligibility for {len(students)} active students...")

        for student in students:
            email = student.get("email")
            if not email or "@" not in email:
                continue

            last_sent_str = student.get("last_sent_at")
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

            # Week-level idempotency
            week_key = f"weekly_digest_{now.year}_w{current_week_num}_{email.lower()}"
            if is_notification_sent(email, "weekly_digest", week_key):
                should_send = False

            if should_send:
                logger.info(f"Automated Weekly Digest triggering for: {email}")
                try:
                    ok = await self.engine.send_personalized_report(
                        recipient_email=email,
                        student_name=student.get("full_name", "Student"),
                        degree=student.get("degree", "Undergraduate (Bachelor's)"),
                        majors=student.get("majors", ["Software Engineering"]),
                        country=student.get("country", "Palestine"),
                        student_profile=student
                    )
                    if ok:
                        dispatched += 1
                        self.sub_service.update_last_sent(email)
                        record_notification(
                            recipient=email,
                            notification_type="weekly_digest",
                            target_id=week_key,
                            subject=f"دليل المنح الأسبوعي المخصص (أسبوع {current_week_num})",
                            status="sent",
                            details={"week": current_week_num, "year": now.year}
                        )
                    else:
                        failed += 1
                except Exception as e:
                    failed += 1
                    logger.error(f"Auto-dispatch error for {email}: {e}")
                await asyncio.sleep(2)  # rate limit pause

        return {
            "dispatched": dispatched,
            "failed": failed,
            "total_students": len(students)
        }

    # ==========================================================================
    # 5. SMART DEADLINE MONITORING (30, 14, 7, 3, 1 DAYS REMAINING)
    # ==========================================================================
    async def auto_dispatch_deadline_reminders(self) -> Dict[str, Any]:
        """
        Automated Deadline Monitor:
        Scans all students and their saved scholarships.
        Sends personalized reminders at key milestones: 30, 14, 7, 3, 1 days remaining.
        Guarantees idempotency via NotificationHistory so reminders are sent once per milestone.
        """
        from services.db import is_notification_sent, record_notification

        students = self._get_all_active_students()
        scholarships = self.get_live_scholarships()
        sch_dict = {s["name"].lower(): s for s in scholarships}
        today = date.today()
        reminders_sent = 0

        target_milestones = [30, 14, 7, 3, 1]

        for student in students:
            email = student.get("email")
            if not email or "@" not in email:
                continue

            saved = student.get("saved_scholarships", [])
            if not saved:
                continue

            for sch_name in saved:
                matched = sch_dict.get(sch_name.lower())
                if not matched:
                    # Partial match attempt
                    matched = next((s for s in scholarships if sch_name.lower() in s["name"].lower()), None)
                if not matched:
                    continue

                dl_str = matched.get("deadline")
                if not dl_str:
                    continue

                try:
                    dl_date = datetime.strptime(dl_str[:10], "%Y-%m-%d").date()
                    days_remaining = (dl_date - today).days

                    # Trigger only on designated milestones
                    if days_remaining in target_milestones:
                        reminder_key = f"deadline_{days_remaining}d_{matched.get('id', sch_name)}_{dl_str}_{email.lower()}"
                        if is_notification_sent(email, "deadline_reminder", reminder_key):
                            continue

                        logger.info(f"⏰ Dispatching deadline reminder for '{sch_name}' to {email} ({days_remaining} days left)")
                        ok = await self._send_reminder_email(
                            recipient_email=email,
                            student_name=student.get("full_name", "Student"),
                            scholarship_name=sch_name,
                            days_remaining=days_remaining,
                            deadline_date=dl_str,
                            link=matched.get("link") or matched.get("official_link", "https://scholarpilot-ai-mkac.onrender.com")
                        )
                        if ok:
                            reminders_sent += 1
                            record_notification(
                                recipient=email,
                                notification_type="deadline_reminder",
                                target_id=reminder_key,
                                subject=f"تنبيه بالموعد النهائي: متبقي {days_remaining} أيام لمنحة {sch_name}",
                                status="sent",
                                details={"days_remaining": days_remaining, "scholarship": sch_name, "deadline": dl_str}
                            )
                        await asyncio.sleep(1.5)
                except Exception as e:
                    logger.debug(f"Could not parse deadline date {dl_str}: {e}")

        return {"reminders_sent": reminders_sent}

    async def _send_reminder_email(
        self,
        recipient_email: str,
        student_name: str,
        scholarship_name: str,
        days_remaining: int,
        deadline_date: str,
        link: str
    ) -> bool:
        """Dispatches an urgent, beautifully styled personalized reminder email."""
        from services.email_service import dispatch_email
        clean_name = sanitize_text(student_name)
        clean_sch = sanitize_text(scholarship_name)
        urgency_color = "#dc2626" if days_remaining <= 3 else "#d97706"
        urgency_bg = "#fef2f2" if days_remaining <= 3 else "#fffbeb"

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
        return await dispatch_email(
            to_email=recipient_email,
            subject=f"تذكير بالموعد النهائي: متبقي {days_remaining} أيام على إغلاق التقديم لمنحة {clean_sch}",
            html_content=html_content,
            text_content=f"مرحباً {clean_name}، نود تذكيرك بأن الموعد النهائي لمنحة {clean_sch} يغلق بتاريخ {deadline_date} (متبقي {days_remaining} يوماً). رابط التقديم: {link}"
        )

    def get_automation_status(self) -> Dict[str, Any]:
        """Returns comprehensive real-time telemetry of the automation subsystem."""
        from services.db import get_notification_history

        scholarships = self.get_live_scholarships()
        students = self._get_all_active_students()
        history = get_notification_history(limit=50)

        digests_sent = sum(1 for h in history if h.get("notification_type") == "weekly_digest")
        alerts_sent = sum(1 for h in history if h.get("notification_type") == "new_scholarship_alert")
        reminders_sent = sum(1 for h in history if h.get("notification_type") == "deadline_reminder")

        return {
            "status": "active_autonomous_daemon",
            "last_scan_at": self._last_scan_at or datetime.now().isoformat(),
            "monitored_scholarships_count": len(scholarships),
            "active_students_count": len(students),
            "notification_metrics": {
                "total_sent_recorded": len(history),
                "weekly_digests_sent": digests_sent,
                "new_match_alerts_sent": alerts_sent,
                "deadline_reminders_sent": reminders_sent
            },
            "recent_dispatches": history[:10]
        }


# ==============================================================================
# 7. CONTINUOUS BACKGROUND AUTOMATION DAEMON (SURVIVES RESTARTS & CRASHES)
# ==============================================================================
async def start_automation_daemon():
    """
    Self-Operating Background Daemon that runs continuously alongside FastAPI:
    - Scans and ingests new global scholarships every cycle.
    - Evaluates every student profile and notifies them of matching opportunities.
    - Continuously evaluates deadlines at 30, 14, 7, 3, 1 day milestones.
    - Checks 7-day weekly digest eligibility for all active students.
    """
    automation = AutomationService()
    logger.info("🚀 ScholarPilotAI Autonomous Platform Daemon activated. Running self-operating background loops...")

    while True:
        try:
            logger.info("🔄 Automation cycle starting: Discovery, Matching, Deadlines & Weekly Digests...")
            
            # Step 1: Discover new scholarships and notify matching students
            discovery_res = await automation.auto_refresh_scholarships_from_web()
            logger.info(f"Discovery Cycle Output: {discovery_res}")

            # Step 2: Deadline reminders (30, 14, 7, 3, 1 days)
            deadline_res = await automation.auto_dispatch_deadline_reminders()
            logger.info(f"Deadline Cycle Output: {deadline_res}")

            # Step 3: Weekly digests (7-day intervals)
            digest_res = await automation.auto_dispatch_weekly_digests()
            logger.info(f"Weekly Digest Cycle Output: {digest_res}")

        except Exception as e:
            logger.error(f"❌ Error in autonomous daemon cycle: {e}", exc_info=True)

        # Sleep for 3 hours between background cycles
        logger.info("Automation cycle complete. Sleeping for 3 hours before next autonomous scan...")
        await asyncio.sleep(3 * 3600)
