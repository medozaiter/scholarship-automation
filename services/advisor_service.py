import os
import re
import json
import logging
from typing import Dict, List, Any, Optional
from google import genai
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

FALLBACK_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.8-flash"
]


class AdvisorService:
    """
    AI Academic Advisor & Application Document Generator:
    1. Computes Scholarship Match Scores (%) & missing requirements.
    2. Real-time AI consultation based on natural student queries.
    3. Generates tailored Motivation Letters, Academic CVs, and Recommendation Letters.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

    def calculate_match_score(
        self,
        student_profile: Dict[str, Any],
        scholarship: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculates a realistic match percentage (0-100%) and identifies missing requirements.
        """
        score = 80  # Base compatibility score
        missing_requirements = []
        strengths = []

        # 1. GPA Analysis
        gpa_str = str(student_profile.get("gpa", "")).strip()
        gpa_val = None
        match = re.search(r"(\d+(?:\.\d+)?)", gpa_str)
        if match:
            gpa_val = float(match.group(1))

        if gpa_val:
            if gpa_val >= 90 or gpa_val >= 3.7:
                score += 12
                strengths.append("معدل أكاديمي متفوق يتجاوز الحد الأدنى للمنافسة العالمية")
            elif gpa_val >= 80 or gpa_val >= 3.0:
                score += 6
                strengths.append("معدل أكاديمي جيد يفي بمتطلبات التقديم الرسمية")
            else:
                score -= 10
                missing_requirements.append("المعدل قد يكون أقل من متطلبات التنافس العالي؛ ينصح بالتركيز على رسالة دافع استثنائية")

        # 2. English Level Analysis
        english = str(student_profile.get("english_level", "")).lower()
        sch_tests = str(scholarship.get("requirements", "")).lower() + " " + str(scholarship.get("tests", "")).lower()

        if "ielts" in english or "toefl" in english or "fluent" in english or "advanced" in english or "ممتاز" in english:
            score += 8
            strengths.append("إثبات كفاءة اللغة الإنجليزية مكتمل ومؤهل للمنحة")
        elif "none" in english or "ضعيف" in english or "لا يوجد" in english:
            if "ielts" in sch_tests or "toefl" in sch_tests:
                score -= 8
                missing_requirements.append("اختبار لغة معتمد (IELTS 6.5 أو TOEFL 90) غير مسجل حالياً")
        else:
            strengths.append("مستوى لغة إنجليزية متوسط؛ معظم المنح توفر سنة تحضيرية للغة")

        # 3. Country & Nationality
        country = student_profile.get("country", "Palestine")
        if "palestine" in country.lower() or "فلسطين" in country:
            score += 5
            strengths.append("أهلية جغرافية تامة مع وجود كوتا خاصة أو أولوية تمويل لدعم الطلبة من فلسطين")

        # Cap score between 65% and 98%
        final_score = max(65, min(98, score))

        return {
            "score": final_score,
            "badge": f"{final_score}% توافق عالي" if final_score >= 85 else f"{final_score}% توافق واعد",
            "strengths": strengths[:2],
            "missing_requirements": missing_requirements if missing_requirements else ["تجهيز مسودة رسالة الدافع وجواز السفر الساري"]
        }

    async def consult_ai_advisor(
        self,
        student_query: str,
        student_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Interactive AI Advisor that responds directly to queries like:
        'معدلي 85 وهندسة برمجيات وأريد منحة في أوروبا'
        """
        if not self.client:
            return {
                "success": False,
                "advice": "يرجى ضبط مفتاح GEMINI_API_KEY لتفعيل المستشار الذكي."
            }

        profile_context = ""
        if student_profile:
            profile_context = f"""
معلومات الطالب المسجلة:
- الدرجة العلمية: {student_profile.get('degree')}
- التخصصات: {student_profile.get('majors')}
- المعدل: {student_profile.get('gpa', 'غير محدد')}
- مستوى اللغة: {student_profile.get('english_level', 'غير محدد')}
- الدولة: {student_profile.get('country', 'Palestine')}
"""

        system_instruction = (
            "أنت 'مستشار المنح الدراسية الأكاديمي الذكي' (AI Scholarship Advisor) في منصة منحة تك.\n"
            "أسلوبك: محترف، مشجع، دقيق ومباشر باللغة العربية الفصحى.\n"
            "مهمتك:\n"
            "1. تحليل سؤال الطالب ومعدله وتخصصه بدقة.\n"
            "2. ترشيح أفضل 2 إلى 3 منح دراسية حكومية أو جامعية رسمية تناسب طلبه ومفتوحة لدورة 2026/2027.\n"
            "3. تقديم خطة عمل من 3 إلى 4 خطوات تنفيذية واضحة للتقديم بنجاح.\n"
            "4. تقديم نصيحة ذهبية لرفع نسبة القبول.\n"
            "تنسيق المخرجات: استخدم عناوين واضحة ونقاطاً وتنسيق Markdown أنيق."
        )

        user_prompt = f"""
سؤال واستفسار الطالب:
"{student_query}"

{profile_context}

قدم إجابة متكاملة ومنظمة تتضمن:
1. التقييم السريع لفرص الطالب ونسبة التنافسية.
2. المنح الموصى بها بالأسماء والجهات المانحة مع المواعيد التقريبية وروابط البوابات الرسمية.
3. خطة التقديم والخطوات الفورية المطلوبة.
4. المستندات التي يجب تجهيزها الآن.
"""

        for candidate in [self.model] + FALLBACK_MODELS:
            try:
                logger.info(f"Invoking AI Advisor via {candidate}")
                response = self.client.models.generate_content(
                    model=candidate,
                    contents=user_prompt,
                    config=dict(
                        system_instruction=system_instruction,
                        temperature=0.2
                    )
                )
                if response.text:
                    return {
                        "success": True,
                        "model": candidate,
                        "advice": response.text.strip()
                    }
            except Exception as e:
                logger.warning(f"Advisor model {candidate} error: {e}")
                continue

        return {
            "success": False,
            "advice": "عذراً، الخادم منشغل حالياً. يرجى المحاولة بعد قليل أو مراجعة دليل المنح الأسبوعي."
        }

    async def generate_smart_documents(
        self,
        student_name: str,
        degree: str,
        major: str,
        gpa: str,
        scholarship_name: str,
        target_country: str = "Europe"
    ) -> Dict[str, str]:
        """
        Generates tailored application kit: Motivation Letter, Recommendation Letter Template,
        and Academic CV Outline customized for the specific scholarship and student.
        """
        if not self.client:
            return self._fallback_documents(student_name, degree, major, scholarship_name)

        system_instruction = (
            "You are an Elite Academic Admissions Consultant specializing in prestigious international scholarships.\n"
            "Generate personalized, high-impact application documents for the student in Markdown format."
        )

        prompt = f"""
Student Data:
- Name: {student_name}
- Degree: {degree}
- Major: {major}
- GPA: {gpa}
- Targeted Scholarship: {scholarship_name}
- Destination: {target_country}

Generate 3 complete, professional documents:

1. [MOTIVATION_LETTER]: A compelling, structured Statement of Purpose / Motivation Letter in English (~450 words) specifically tailored for {scholarship_name} and {major}. Address student's motivation, academic background ({gpa}), leadership aspirations, and contribution back to Palestine/community.
2. [RECOMMENDATION_LETTER]: A professional academic reference letter template that a professor or teacher can sign.
3. [ACADEMIC_CHECKLIST]: An essential step-by-step checklist for this specific scholarship.

Format with clear delimiters:
---MOTIVATION_LETTER---
(content)
---RECOMMENDATION_LETTER---
(content)
---ACADEMIC_CHECKLIST---
(content)
"""

        for candidate in [self.model] + FALLBACK_MODELS:
            try:
                response = self.client.models.generate_content(
                    model=candidate,
                    contents=prompt,
                    config=dict(
                        system_instruction=system_instruction,
                        temperature=0.3
                    )
                )
                text = response.text
                if "---MOTIVATION_LETTER---" in text:
                    parts = text.split("---MOTIVATION_LETTER---")[1]
                    mot, rest = parts.split("---RECOMMENDATION_LETTER---")
                    rec, chk = rest.split("---ACADEMIC_CHECKLIST---")
                    return {
                        "motivation_letter": mot.strip(),
                        "recommendation_letter": rec.strip(),
                        "checklist": chk.strip()
                    }
            except Exception as e:
                logger.warning(f"Doc generation error with {candidate}: {e}")
                continue

        return self._fallback_documents(student_name, degree, major, scholarship_name)

    def _fallback_documents(
        self,
        student_name: str,
        degree: str,
        major: str,
        scholarship_name: str
    ) -> Dict[str, str]:
        """Fallback document templates if AI service is temporarily offline."""
        return {
            "motivation_letter": f"""# Motivation Letter / Statement of Purpose

**To:** The Selection Committee, {scholarship_name}
**Applicant:** {student_name}
**Target Program:** {degree} in {major}

Dear Esteemed Members of the Selection Committee,

I am writing to express my enthusiastic application for the prestigious {scholarship_name}. Having pursued rigorous academic preparation in {major}, my goal is to combine academic excellence with impactful research and leadership.

Throughout my academic journey, I have maintained high dedication, striving to solve critical challenges in technology and society. Receiving this scholarship would enable me to study at an internationally recognized institution, access advanced laboratories, and collaborate with leading faculty.

Upon completion of my {degree}, I am determined to leverage my knowledge and international experience to contribute to higher education, innovation, and community development.

Thank you for considering my application.

Sincerely,
{student_name}
""",
            "recommendation_letter": f"""# Academic Recommendation Letter Template

**To:** Admissions and Scholarship Selection Board
**Subject:** Academic Recommendation for {student_name} ({scholarship_name})

Dear Committee Members,

It is my distinct pleasure to recommend {student_name} for the {scholarship_name}. As their instructor/academic advisor, I have observed their intellectual curiosity, analytical rigor, and exemplary character.

{student_name} demonstrated exceptional competence in {major}, consistently ranking among the top students. Beyond academics, they embody leadership, collaborative teamwork, and strong ethical commitment.

I give {student_name} my highest recommendation for this scholarship without reservation.

Sincerely,
[Professor / Academic Reference Name]
[Academic Title / Department]
[University / Institution Name]
""",
            "checklist": f"""# Pre-Flight Application Checklist ({scholarship_name})

- [ ] Official High School / University Transcripts (Translated & Attested)
- [ ] Statement of Purpose / Motivation Letter (Tailored to {scholarship_name})
- [ ] Academic Curriculum Vitae (Europass / Standard Academic Format)
- [ ] Two Academic Letters of Recommendation
- [ ] Valid International Passport (minimum 12 months validity)
- [ ] English Proficiency Proof (IELTS / TOEFL / Duolingo / Medium of Instruction Certificate)
- [ ] Medical Examination Certificate (if required by host country)
- [ ] Complete Online Application Portal Submission before the Official Deadline
"""
        }
