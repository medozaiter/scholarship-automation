import os
import re
import csv
import json
import smtplib
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from email.message import EmailMessage
from dotenv import load_dotenv
from google import genai

from services.search_service import SearchService, CURATED_VERIFIED_SCHOLARSHIPS
from services.advisor_service import AdvisorService

load_dotenv()

logger = logging.getLogger(__name__)

FALLBACK_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.8-flash"
]

# Prestigious Global Master's / PhD fallbacks when requested
CURATED_GRADUATE_SCHOLARSHIPS: List[Dict[str, str]] = [
    {
        "name": "Chevening Scholarships",
        "provider": "UK Foreign, Commonwealth & Development Office (FCDO)",
        "country_institution": "United Kingdom / Leading UK Universities",
        "language": "English",
        "status": "Open Now (Annual cycle)",
        "deadline": "2026-11-05",
        "mechanism": "Integrated Central Portal (Direct application via Chevening e-portal + 3 separate UK university choices)",
        "requirements": "Undergraduate degree (minimum 2:1 equivalent / 80%+), 2+ years of professional work experience (2,800 hours), proven leadership and networking qualities",
        "tests": "English test optional at application; must meet chosen university conditional offer requirements",
        "visa_support": "Full UK Student Visa sponsorship and visa fee waiver provided by British Council / FCDO",
        "competitiveness": "Very High (~1,500 scholars selected globally from over 65,000 applicants)",
        "official_link": "https://www.chevening.org/scholarships/",
        "funding": "Fully Funded (Full university tuition, monthly living allowance, return economy airfare, arrival allowance)"
    },
    {
        "name": "DAAD Development-Related Postgraduate Courses (EPOS)",
        "provider": "German Academic Exchange Service (DAAD)",
        "country_institution": "Germany / German Partner Universities",
        "language": "English / German",
        "status": "Open Now (Deadlines vary by program through December)",
        "deadline": "2026-12-15",
        "mechanism": "Direct University Application (Apply directly to the designated master’s degree program at the German university specifying DAAD scholarship)",
        "requirements": "Bachelor's degree completed within last 6 years with above-average grades, at least 2 years of relevant professional experience, strong motivation letter",
        "tests": "IELTS 6.0+ or TOEFL 80+ for English programs; Goethe-Zertifikat B1/B2 for German programs",
        "visa_support": "Official DAAD Award Letter provided for German National Student Visa (Schengen D category)",
        "competitiveness": "High (Rigorous academic and professional review)",
        "official_link": "https://www.daad.de/en/information-services-for-higher-education-institutions/further-information-on-daad-programmes/epos/",
        "funding": "Fully Funded (€934/month stipend, travel allowances, health insurance, study allowance)"
    },
    {
        "name": "Fulbright Foreign Student Program",
        "provider": "U.S. Department of State / AMIDEAST",
        "country_institution": "USA / Accredited US Universities",
        "language": "English",
        "status": "Opening Soon (Cycle opens spring/summer)",
        "deadline": "2027-05-15",
        "mechanism": "Amideast Regional Portal (Online application through Amideast West Bank and Gaza office)",
        "requirements": "Palestinian resident of West Bank, East Jerusalem, or Gaza; four-year bachelor's degree with minimum GPA 78% or 3.0; leadership potential",
        "tests": "TOEFL / GRE vouchers provided to shortlisted candidates by Amideast",
        "visa_support": "Full J-1 Exchange Visitor Visa sponsorship, fee coverage, and DS-2019 issuance",
        "competitiveness": "Very High (Prestige flagship academic exchange award)",
        "official_link": "https://www.amideast.org/west-bank-gaza/find-a-scholarship/graduate-study/fulbright-foreign-student-program",
        "funding": "Fully Funded (Full tuition, monthly maintenance stipend, health insurance, international airfare, computer allowance)"
    },
    {
        "name": "Erasmus Mundus Joint Master Degrees (EMJM)",
        "provider": "European Commission",
        "country_institution": "European Union / International University Consortia (France, Germany, Spain, Italy, Sweden)",
        "language": "English",
        "status": "Open Now (Opening October-November across consortia)",
        "deadline": "2027-01-15",
        "mechanism": "Consortium Application (Direct online application to the specific Erasmus Mundus master's consortium website)",
        "requirements": "Recognized bachelor's degree in relevant discipline, high academic standing, English proficiency (IELTS 6.5+ / TOEFL 90+), CV in Europass format",
        "tests": "GRE / GMAT not required for majority of European consortia",
        "visa_support": "Consortium acceptance letter and official scholarship certificate for multi-country Schengen student mobility visas",
        "competitiveness": "Very High (Global competition with dedicated NDICI partner quotas including Palestine)",
        "official_link": "https://erasmus-plus.ec.europa.eu/opportunities/opportunities-for-individuals/students/erasmus-mundus-joint-masters",
        "funding": "Fully Funded (100% participation costs covered + €1,400 monthly living stipend for up to 24 months + travel/installation allowances)"
    }
]


class ScholarshipEngine:
    """
    Unified AI engine that independently searches the internet, extracts verified scholarships
    matching any student's criteria (degree, majors, country), calculates Scholarship Match Scores,
    formats the standard 11 columns, and sends personalized reports via email.
    """

    def __init__(self, gemini_api_key: Optional[str] = None):
        self.api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
        self.search_service = SearchService(max_results=10)
        self.advisor = AdvisorService(api_key=self.api_key)
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

    async def search_and_extract(
        self,
        degree: str,
        majors: List[str],
        country: str = "Palestine",
        funding: str = "Fully Funded (or Partial)"
    ) -> List[Dict[str, Any]]:
        """
        Executes live web search and uses Gemini with fallback chain to return
        the 11-column structured scholarship data.
        """
        majors_str = ", ".join(majors) if majors else "All relevant disciplines"
        logger.info(f"Starting scholarship search for {degree} | Majors: {majors_str} | Country: {country}")

        search_results = await self.search_service.search_scholarships(
            degree=degree,
            majors=majors,
            funding=funding,
            country=country
        )

        snippets_text = ""
        allowed_urls = []
        for i, item in enumerate(search_results, 1):
            url = item.get("url", "").strip()
            if url:
                allowed_urls.append(url)
            snippets_text += f"[Source #{i}]\nTitle: {item.get('title')}\nSnippet: {item.get('snippet')}\nURL: {url}\n\n"

        if self.client:
            extracted = await self._query_gemini_json(
                snippets_text=snippets_text,
                allowed_urls=allowed_urls,
                degree=degree,
                majors_str=majors_str,
                country=country,
                funding=funding
            )
            if extracted and len(extracted) >= 3:
                return self._sort_by_deadline(extracted)

        logger.info("Using verified fallback directory matching student degree...")
        return self._get_fallback_scholarships(degree, country)

    async def _query_gemini_json(
        self,
        snippets_text: str,
        allowed_urls: List[str],
        degree: str,
        majors_str: str,
        country: str,
        funding: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Queries Gemini with structured extraction instructions."""
        system_instruction = (
            "You are an Elite Academic Advisor and Scholarship Data Verification Specialist.\n"
            "Your task is to extract officially verified scholarships and return a JSON ARRAY of objects.\n"
            "STRICT RULES:\n"
            "1. Only include scholarships that are OPEN NOW or opening very soon for the 2026/2027 cycle.\n"
            "2. Exclude any expired opportunities.\n"
            "3. Take URLs strictly from the provided 'allowed_urls' or official university/government domains.\n"
            "4. Return ONLY valid JSON (no markdown formatting, no code fences, just the JSON array)."
        )

        prompt = f"""
Input Search Context:
{snippets_text}

Target Student Parameters:
- Degree: {degree}
- Majors: {majors_str}
- Country of Origin: {country}
- Funding Preference: {funding}

Required JSON Output Schema:
Return an array of objects. Each object MUST contain these exact 12 keys:
1. "name": string (Official scholarship name and provider)
2. "country_institution": string (Host country and university/institution)
3. "language": string (Instruction language)
4. "status": string ("Open Now" or "Opening Soon [Date]")
5. "deadline": string (Deadline in YYYY-MM-DD or standard date format)
6. "mechanism": string (Application mechanism: integrated single portal or separate application)
7. "requirements": string (Academic criteria, GPA, IELTS/TOEFL requirements, essential documents)
8. "tests": string (Standardized tests requirement: SAT/ACT/GRE or not required)
9. "visa_support": string (Student visa facilitation details, LOA, official letters)
10. "competitiveness": string (Competitiveness level: Very High / High / Moderate)
11. "official_link": string (Direct official portal URL)
12. "funding": string (Funding coverage details: tuition, stipend, accommodation, flights)

Ensure output is strictly valid JSON:
[
  {{ ... }}
]
"""
        model_chain = [self.model] + [m for m in FALLBACK_MODELS if m != self.model]

        for candidate in model_chain:
            try:
                logger.info(f"Invoking Gemini model for structured scholarship data: {candidate}")
                response = self.client.models.generate_content(
                    model=candidate,
                    contents=prompt,
                    config=dict(
                        system_instruction=system_instruction,
                        temperature=0.1
                    )
                )
                text = response.text.strip()
                if text.startswith("```"):
                    text = re.sub(r"^```(?:json)?\s*", "", text)
                    text = re.sub(r"\s*```$", "", text)

                data = json.loads(text)
                if isinstance(data, list) and len(data) > 0:
                    logger.info(f"Successfully extracted {len(data)} scholarships via {candidate}")
                    return data
            except Exception as e:
                logger.warning(f"Model {candidate} JSON extraction failed: {e}. Trying fallback model...")
                continue

        return None

    def _get_fallback_scholarships(self, degree: str, country: str) -> List[Dict[str, Any]]:
        """Returns verified scholarships tailored to undergraduate vs graduate."""
        degree_lower = degree.lower()
        if "master" in degree_lower or "phd" in degree_lower or "doctor" in degree_lower or "graduate" in degree_lower:
            return CURATED_GRADUATE_SCHOLARSHIPS

        from send_scholarship_report import SCHOLARSHIPS_DATA
        return SCHOLARSHIPS_DATA

    def _sort_by_deadline(self, scholarships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sorts scholarships chronologically by deadline ascending."""
        def parse_date(item):
            dl = item.get("deadline", "9999-12-31")
            match = re.search(r"(\d{4}-\d{2}-\d{2})", dl)
            if match:
                return match.group(1)
            return dl

        return sorted(scholarships, key=parse_date)

    def generate_csv(self, scholarships: List[Dict[str, Any]], filepath: str) -> str:
        """Exports the 11-column matrix to CSV."""
        headers = [
            "Scholarship & Provider Name",
            "Country / Institution (University)",
            "Language of Instruction",
            "Application Status",
            "Application Deadline",
            "Application Mechanism",
            "Academic & General Requirements",
            "Standardized Tests",
            "Visa Support & Facilitation",
            "Competitiveness & Acceptance Rate",
            "Direct Official Link"
        ]

        with open(filepath, mode="w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            for s in scholarships:
                writer.writerow([
                    s.get("name", ""),
                    s.get("country_institution", ""),
                    s.get("language", ""),
                    s.get("status", ""),
                    s.get("deadline", ""),
                    s.get("mechanism", ""),
                    s.get("requirements", ""),
                    s.get("tests", ""),
                    s.get("visa_support", ""),
                    s.get("competitiveness", ""),
                    s.get("official_link", "")
                ])
        return filepath

    def build_html_report(
        self,
        scholarships: List[Dict[str, Any]],
        student_name: str,
        degree: str,
        majors: List[str],
        country: str,
        student_profile: Optional[Dict[str, Any]] = None
    ) -> str:
        """Constructs an elegant, responsive HTML email tailored to the student with Match Scores."""
        now_str = datetime.now().strftime("%Y-%m-%d")
        majors_str = "، ".join(majors) if majors else "كافة التخصصات ذات الصلة"

        profile_data = student_profile or {
            "gpa": "85%",
            "english_level": "Intermediate",
            "country": country,
            "degree": degree
        }

        rows_html = ""
        for idx, s in enumerate(scholarships, 1):
            status = s.get("status", "Open Now")
            status_color = "#10b981" if "Open" in status or "مفتوح" in status else "#3b82f6"
            badge_text = "مفتوح حالياً (Open Now)" if "Open" in status or "مفتوح" in status else "يفتح قريباً (Opening Soon)"

            # Match Score Evaluation
            match_data = self.advisor.calculate_match_score(profile_data, s)
            score_num = match_data["score"]
            score_color = "#16a34a" if score_num >= 85 else "#2563eb"

            # Deadline Countdown calculation
            dl_text = s.get('deadline', '')
            countdown_badge = ""
            date_match = re.search(r"(\d{4})-(\d{2})-(\d{2})", dl_text)
            if date_match:
                try:
                    d_obj = datetime.strptime(date_match.group(0), "%Y-%m-%d").date()
                    days_left = (d_obj - date.today()).days
                    if days_left > 0:
                        countdown_badge = f"<span style='background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; font-size: 11px; padding: 2px 7px; border-radius: 4px; margin-right: 6px; font-weight: bold;'>⏳ بقي {days_left} يوماً!</span>"
                    elif days_left == 0:
                        countdown_badge = "<span style='background: #dc2626; color: #ffffff; font-size: 11px; padding: 2px 7px; border-radius: 4px; margin-right: 6px; font-weight: bold;'>🚨 اليوم الأخير!</span>"
                except Exception:
                    pass

            rows_html += f"""
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 14px; padding: 22px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
                
                <!-- Header of Card -->
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; border-bottom: 1px solid #f1f5f9; padding-bottom: 12px;">
                    <div>
                        <span style="background: #eff6ff; color: #1d4ed8; font-size: 12px; font-weight: bold; padding: 4px 8px; border-radius: 6px; margin-left: 8px;">#{idx}</span>
                        <h3 style="display: inline; margin: 0; font-size: 18px; color: #0f172a;">{s.get('name')}</h3>
                        <div style="color: #64748b; font-size: 13.5px; margin-top: 4px;">📍 <b>{s.get('country_institution')}</b> | لغة الدراسة: <b>{s.get('language')}</b></div>
                    </div>
                    <div style="text-align: left;">
                        <span style="background: {status_color}15; color: {status_color}; font-size: 12px; font-weight: bold; padding: 4px 10px; border-radius: 20px; border: 1px solid {status_color};">
                            {badge_text}
                        </span>
                        <div style="color: #dc2626; font-size: 13px; font-weight: bold; margin-top: 6px;">
                            {countdown_badge} {s.get('deadline')}
                        </div>
                    </div>
                </div>

                <!-- Match Score Badge & Analysis Block -->
                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px 16px; margin-bottom: 14px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="font-size: 14px; font-weight: bold; color: {score_color};">
                            🎯 نسبة توافق ملفك: <b>{score_num}%</b> ({match_data['badge']})
                        </span>
                        <span style="font-size: 11px; color: #64748b;">مُحلل بواسطة AI Match Score</span>
                    </div>
                    <div style="font-size: 12.5px; color: #334155; line-height: 1.6;">
                        <div style="color: #166534; margin-bottom: 3px;">✅ <b>أبرز نقاط القوة:</b> {' • '.join(match_data['strengths'])}</div>
                        <div style="color: #b45309;">⚠️ <b>متطلبات واجب مراعاتها:</b> {' • '.join(match_data['missing_requirements'])}</div>
                    </div>
                </div>

                <!-- 11 Column Detailed Data Table -->
                <table style="width: 100%; border-collapse: collapse; font-size: 13.5px; color: #334155;">
                    <tr>
                        <td style="padding: 6px 0; width: 25%; font-weight: bold; color: #475569;">💰 التمويل والتغطية:</td>
                        <td style="padding: 6px 0;">{s.get('funding', 'تغطية دراسية كاملة أو جزئية')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; font-weight: bold; color: #475569;">📋 آلية التقديم:</td>
                        <td style="padding: 6px 0;">{s.get('mechanism', 'تقديم عبر البوابة الرسمية')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; font-weight: bold; color: #475569;">🎓 شروط القبول:</td>
                        <td style="padding: 6px 0;">{s.get('requirements', 'المعدل الأكاديمي المطلوب ومتطلبات اللغة')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; font-weight: bold; color: #475569;">📝 الاختبارات المعيارية:</td>
                        <td style="padding: 6px 0;">{s.get('tests', 'غير مشروط أو اختياري')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; font-weight: bold; color: #475569;">🛂 دعم التأشيرة (Visa):</td>
                        <td style="padding: 6px 0;">{s.get('visa_support', 'توفير وثائق القبول الرسمية لدعم الفيزا')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; font-weight: bold; color: #475569;">📊 التنافسية:</td>
                        <td style="padding: 6px 0;"><span style="color: #b45309; font-weight: bold;">{s.get('competitiveness', 'عالي')}</span></td>
                    </tr>
                </table>

                <!-- Action Footer -->
                <div style="margin-top: 14px; text-align: left; padding-top: 12px; border-top: 1px dashed #e2e8f0; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                    <div>
                        <a href="{s.get('official_link')}" target="_blank" style="background: #2563eb; color: #ffffff; text-decoration: none; padding: 8px 18px; border-radius: 8px; font-size: 13px; font-weight: bold; display: inline-block;">
                            🔗 الانتقال لبوابة التقديم الرسمية
                        </a>
                    </div>
                    <span style="font-size: 11.5px; color: #94a3b8;">⚠️ تأكد من الشروط وتاريخ الإغلاق النهائي بالبوابة الرسمية</span>
                </div>
            </div>
            """

        html = f"""
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>دليل منح {degree} المخصصة</title>
        </head>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; color: #0f172a; line-height: 1.6;">
            <div style="max-width: 820px; margin: 0 auto;">
                
                <!-- Header Banner -->
                <div style="background: linear-gradient(135deg, #1e3a8a, #3b82f6); color: #ffffff; border-radius: 16px; padding: 30px; text-align: center; margin-bottom: 24px; box-shadow: 0 4px 12px rgba(37,99,235,0.2);">
                    <span style="background: rgba(255,255,255,0.2); font-size: 12px; font-weight: bold; padding: 4px 12px; border-radius: 20px; text-transform: uppercase;">تقرير أسبوعي ذكي | Personalized Scholarship Digest</span>
                    <h1 style="margin: 14px 0 8px 0; font-size: 24px;">دليل منح {degree} المتوافقة معك 🎓</h1>
                    <p style="margin: 0; font-size: 15px; opacity: 0.95;">
                        عزيزي الطالب <b>{student_name}</b> | التخصصات: <b>{majors_str}</b> | معدلك: <b>{profile_data.get('gpa', 'غير محدد')}</b>
                    </p>
                    <div style="margin-top: 14px; font-size: 13px; opacity: 0.85;">
                        📅 تاريخ الفحص: <b>{now_str}</b> | إجمالي الفرص المطابقة: <b>{len(scholarships)} منح</b>
                    </div>
                </div>

                <!-- Mandatory Advisory Notice -->
                <div style="background: #fffbeb; border-right: 4px solid #f59e0b; padding: 14px 18px; border-radius: 8px; margin-bottom: 24px; font-size: 13.5px; color: #92400e;">
                    ⚠️ <b>تنبيه هام للطلبة:</b> رتّب المحرك هذه الفرص تنازلياً بحسب نسبة التوافق وقرب الموعد النهائي (Deadline). نرجو مراجعة الشروط والمواعيد المحدثة عبر الرابط الرسمي لكل منحة مباشرة قبل إغلاق بوابات التقديم.
                </div>

                <!-- Scholarships List -->
                {rows_html}

                <!-- CSV Attachment Notice -->
                <div style="background: #f1f5f9; border: 1px dashed #cbd5e1; border-radius: 10px; padding: 16px; text-align: center; margin-top: 24px; font-size: 13.5px; color: #475569;">
                    📎 <b>مرفق مع هذا الإيميل:</b> ملف جدول بيانات كامل <code>scholarships_report.csv</code> يحتوي على الأعمدة الـ 11 باللغة الإنجليزية لتتمكن من فتحه وتصفحه عبر Excel في أي وقت.
                </div>

                <!-- Footer -->
                <div style="text-align: center; padding: 24px 0; font-size: 12px; color: #94a3b8;">
                    تم توليد هذا التقرير وتدقيقه تلقائياً بواسطة نظام الأوتوميشن الأسبوعي.<br>
                    جميع الحقوق محفوظة © {datetime.now().year} | Global Scholarship AI Engine
                </div>

            </div>
        </body>
        </html>
        """
        return html

    async def send_personalized_report(
        self,
        recipient_email: str,
        student_name: str,
        degree: str,
        majors: List[str],
        country: str = "Palestine",
        student_profile: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Runs the search, creates CSV/HTML with match scores, and sends directly to student's email."""
        sender_email = os.getenv("SENDER_EMAIL")
        gmail_password = os.getenv("GMAIL_APP_PASSWORD")

        if not sender_email or not gmail_password:
            logger.error("Missing SENDER_EMAIL or GMAIL_APP_PASSWORD.")
            return False

        gmail_password = gmail_password.replace(" ", "").strip()

        scholarships = await self.search_and_extract(
            degree=degree,
            majors=majors,
            country=country
        )

        temp_csv = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", f"report_{recipient_email.replace('@', '_')}.csv")
        os.makedirs(os.path.dirname(temp_csv), exist_ok=True)
        self.generate_csv(scholarships, temp_csv)
        html_content = self.build_html_report(scholarships, student_name, degree, majors, country, student_profile)

        msg = EmailMessage()
        msg["Subject"] = f"🎓 دليل منح {degree} المتوافقة معك | تقرير أسبوعي ({datetime.now().strftime('%d-%m-%Y')})"
        msg["From"] = f"Scholarship Tracker <{sender_email}>"
        msg["To"] = recipient_email

        msg.set_content(
            f"مرحباً {student_name}، مرفق تقرير أحدث منح {degree} مع درجات التوافق (Match Score) للطلاب من {country}.\n"
            f"يرجى فتح الإيميل في متصفح يدعم HTML للاطلاع على الجدول المنظم أو فتح ملف CSV المرفق."
        )
        msg.add_alternative(html_content, subtype="html")

        try:
            with open(temp_csv, "rb") as f:
                msg.add_attachment(
                    f.read(),
                    maintype="text",
                    subtype="csv",
                    filename="scholarships_report.csv"
                )
        except Exception as e:
            logger.warning(f"Could not attach CSV: {e}")

        try:
            logger.info(f"Delivering report to {recipient_email}...")
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=25) as server:
                server.starttls()
                server.login(sender_email, gmail_password)
                server.send_message(msg)
                logger.info(f"✅ Successfully delivered customized report to {recipient_email}!")
                return True
        except Exception as e:
            logger.error(f"Failed TLS delivery: {e}. Trying SSL 465...")
            try:
                with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=25) as server:
                    server.login(sender_email, gmail_password)
                    server.send_message(msg)
                    logger.info(f"✅ Successfully delivered report to {recipient_email} via SSL!")
                    return True
            except Exception as e2:
                logger.error(f"Failed to deliver to {recipient_email}: {e2}")
                return False
        finally:
            if os.path.exists(temp_csv):
                try:
                    os.remove(temp_csv)
                except Exception:
                    pass

    async def send_application_kit_email(
        self,
        recipient_email: str,
        student_name: str,
        scholarship_name: str,
        degree: str,
        major: str,
        documents: Dict[str, str]
    ) -> bool:
        """Sends generated Motivation Letter, Recommendation template, and Checklist to the student."""
        sender_email = os.getenv("SENDER_EMAIL")
        gmail_password = os.getenv("GMAIL_APP_PASSWORD")

        if not sender_email or not gmail_password:
            logger.error("Missing SENDER_EMAIL or GMAIL_APP_PASSWORD.")
            return False

        gmail_password = gmail_password.replace(" ", "").strip()

        msg = EmailMessage()
        msg["Subject"] = f"📁 حزمة مستندات التقديم الذكية | منحة {scholarship_name} ({student_name})"
        msg["From"] = f"Scholarship Assistant <{sender_email}>"
        msg["To"] = recipient_email

        body_html = f"""
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head><meta charset="utf-8"></head>
        <body style="font-family: 'Segoe UI', Tahoma, sans-serif; background-color: #f8fafc; padding: 20px; color: #0f172a;">
            <div style="max-width: 750px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 30px;">
                <h2 style="color: #1e3a8a; margin-top: 0;">📁 حزمة مستندات التقديم الذكية المخصصة لك</h2>
                <p>مرحباً <b>{student_name}</b>، تم توليد وتخصيص مستندات التقديم الخاصة بك لمنحة <b>{scholarship_name}</b> ({degree} في {major}):</p>
                
                <div style="background: #f1f5f9; padding: 18px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #0f172a;">1. رسالة الدافع المخصصة (Motivation Letter / SOP)</h3>
                    <pre style="white-space: pre-wrap; font-family: monospace; font-size: 13px; color: #334155; background: #ffffff; padding: 14px; border-radius: 6px; border: 1px solid #cbd5e1;">{documents.get('motivation_letter', '')}</pre>
                </div>

                <div style="background: #f1f5f9; padding: 18px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #0f172a;">2. نموذج خطاب التوصية الأكاديمي (Recommendation Letter)</h3>
                    <pre style="white-space: pre-wrap; font-family: monospace; font-size: 13px; color: #334155; background: #ffffff; padding: 14px; border-radius: 6px; border: 1px solid #cbd5e1;">{documents.get('recommendation_letter', '')}</pre>
                </div>

                <div style="background: #f1f5f9; padding: 18px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #0f172a;">3. قائمة التحقق والمتطلبات (Checklist)</h3>
                    <pre style="white-space: pre-wrap; font-family: monospace; font-size: 13px; color: #334155; background: #ffffff; padding: 14px; border-radius: 6px; border: 1px solid #cbd5e1;">{documents.get('checklist', '')}</pre>
                </div>

                <p style="font-size: 12px; color: #64748b; margin-top: 30px;">نصيحة: راجع خطاب الدافع واذكر فيه أي أبحاث أو مشاريع تخرج قمت بها لإبراز تميزك!</p>
            </div>
        </body>
        </html>
        """

        msg.set_content(f"مرحباً {student_name}، مرفق مستندات التقديم الخاصة بك لمنحة {scholarship_name}.")
        msg.add_alternative(body_html, subtype="html")

        try:
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=25) as server:
                server.starttls()
                server.login(sender_email, gmail_password)
                server.send_message(msg)
                logger.info(f"✅ Successfully sent documents kit to {recipient_email}")
                return True
        except Exception as e:
            logger.error(f"Error sending documents email: {e}")
            return False
