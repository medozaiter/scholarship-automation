import os
import re
import json
import logging
from datetime import datetime
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
        student_profile: Optional[Dict[str, Any]] = None,
        scholarship: Optional[Dict[str, Any]] = None,
        gpa: Optional[str] = None,
        majors: Optional[List[str]] = None,
        country: Optional[str] = None,
        student_talents: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates a realistic match percentage (0-100%) and admission probability
        based on GPA, majors, and the applicant's talents, volunteering, and experiences.
        Supports both dict profile and keyword arguments.
        """
        if student_profile is None:
            student_profile = {
                "gpa": gpa or "85%",
                "majors": majors or ["Software Engineering"],
                "country": country or "Palestine",
                "talents_experience": student_talents or ""
            }
        elif student_talents and not student_profile.get("talents_experience"):
            student_profile["talents_experience"] = student_talents

        if scholarship is None:
            scholarship = {"name": "Global Scholarship", "target_majors": majors or ["Any"]}
        score = 75  # Base compatibility score
        missing_requirements = []
        strengths = []

        # 1. GPA Analysis (Weight: 40%)
        gpa_str = str(student_profile.get("gpa", "")).strip()
        gpa_val = None
        match = re.search(r"(\d+(?:\.\d+)?)", gpa_str)
        if match:
            gpa_val = float(match.group(1))

        if gpa_val:
            if gpa_val >= 90 or (gpa_val >= 3.7 and gpa_val <= 4.0):
                score += 15
                strengths.append(f"معدل أكاديمي متفوق ({gpa_str}) يتجاوز عتبة التنافس العالمية")
            elif gpa_val >= 82 or (gpa_val >= 3.2 and gpa_val <= 4.0):
                score += 9
                strengths.append(f"معدل أكاديمي جيد جداً ({gpa_str}) مؤهل للقبول والتنافس المباشر")
            elif gpa_val >= 75 or (gpa_val >= 2.8 and gpa_val <= 4.0):
                score += 3
                strengths.append(f"معدل أكاديمي مقبول ({gpa_str}) يفي بالحد الأدنى للشروط")
            else:
                score -= 8
                missing_requirements.append("المعدل يحتاج لدعم قوي عبر رسالة دافع مبهرة وأنشطة تميز عملية")

        # 2. Talents, Volunteering & Extracurricular Activities (Weight: 35%)
        talents = str(student_profile.get("talents_experience", "")).strip()
        if talents:
            talent_score = 0
            # Research / Conferences
            if re.search(r"(بحث|علمي|أوراق|مؤتمر|دراسة|publication|research|paper)", talents, re.I):
                talent_score += 8
                strengths.append("خبرة في البحث العلمي والمؤتمرات تمنحك أفضلية كبرى لدى لجان القبول")
            # Competitions / Hackathons / Awards
            if re.search(r"(مسابقة|هاكاثون|جائزة|تكريم|أول|فوز|hackathon|competition|award)", talents, re.I):
                talent_score += 8
                strengths.append("المشاركة في المسابقات والجوائز تعكس شغفاً وتفوقاً استثنائياً")
            # Community / Volunteering / Leadership
            if re.search(r"(تطوع|مبادرة|قيادة|نادي|مجتمعي|رئيس|volunteer|community|leadership)", talents, re.I):
                talent_score += 6
                strengths.append("سجل تطوعي وقيادي يثبت التأثير المجتمعي المطلوب في المنح الدولية")
            # Projects / Practical Work
            if re.search(r"(مشروع|عمل|تدريب|خبرة|تطوير|برمجة|تصميم|internship|project|work)", talents, re.I):
                talent_score += 6
                strengths.append("خبرة عملية ومشاريع تطبيقية تثبت جاهزيتك الميدانية")

            # Default bonus for entering talents
            talent_score = max(5, min(20, talent_score))
            score += talent_score
        else:
            missing_requirements.append("إضافة أنشطة تطوعية أو مشاريع عملية سيرفع نسبة قبولك بنسبة 15%")

        # 3. Country & Special Quotas (Weight: 10%)
        country = str(student_profile.get("country", "Palestine")).lower()
        if "palestine" in country or "فلسطين" in country:
            score += 5
            strengths.append("أولوية دعم وكوتا مخصصة للطلبة الفلسطينيين في هذه المنحة")

        # Cap score realistically between 65% and 98%
        final_score = max(65, min(98, score))

        # Probability rating
        if final_score >= 90:
            prob_label = "فرصة قبول استثنائية (High Probability)"
        elif final_score >= 80:
            prob_label = "فرصة قبول قوية وتنافسية (Strong Competitor)"
        else:
            prob_label = "فرصة قبول جيدة مع حاجة لتدعيم الملف (Good Prospect)"

        return {
            "score": final_score,
            "match_score": f"{final_score}%",
            "admission_probability": f"{final_score}%",
            "probability_label": prob_label,
            "badge": f"{final_score}% توافق وتوقع قبول",
            "strengths": strengths[:3],
            "missing_requirements": missing_requirements if missing_requirements else ["تجهيز جواز سفر ساري المفعول وصياغة خطاب الدافع"]
        }

    async def consult_ai_advisor(
        self,
        student_query: str,
        student_profile: Optional[Dict[str, Any]] = None,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Interactive, witty, and concise AI Advisor trained on student inquiries:
        - Understands colloquial Arabic and regional student phrasing.
        - Answers directly to the point ("يجاوب ع قد الكلام").
        - Suggests concrete scholarships with official deadlines.
        - Ends with a smart interactive follow-up question.
        """
        if not self.client:
            return {
                "success": False,
                "advice": "يرجى ضبط مفتاح GEMINI_API_KEY لتفعيل المستشار الذكي."
            }

        profile_context = ""
        if student_profile:
            profile_context = f"""
بيانات الطالب:
- الدرجة العلمية: {student_profile.get('degree', 'بكالوريوس')}
- التخصصات: {student_profile.get('majors', 'هندسة حاسوب / برمجيات')}
- المعدل: {student_profile.get('gpa', '85%')}
- المواهب والخبرات: {student_profile.get('talents_experience', 'أنشطة عامة')}
- الدولة: {student_profile.get('country', 'فلسطين')}
"""

        system_instruction = (
            "أنت 'المستشار الأكاديمي لمنحة تك AI' - مرشد أكاديمي ذكي، ودود، وسريع البديهة.\n"
            "أسلوبك وقواعدك الإلزامية:\n"
            "1. افهم حكي الطالب وعاميته بدقة (عامية فلسطينية، شامية، مصرية، أو فصحى) وتعامل معه كمرشد مخلص.\n"
            "2. 'جاوب ع قد الكلام': كن مباشراً، مختصراً، ومركزاً. لا تكتب مقدمات طويلة مكررة ولا نصوصاً حشوية.\n"
            "3. إذا سألك عن تخصص أو معدل: اعطه فوراً أفضل 2 أو 3 منح حقيقية ومضمونة تناسبه لدورة 2026/2027 مع ميعاد التقديم وشروطها باختصار شديد.\n"
            "4. احسب له سريعاً توقع قبوله أو نصيحة ترفع حظوظه.\n"
            "5. اختم كلامك دائماً بسؤال تفاعلي ذكي واحد قصير (مثلاً: 'شو رأيك نبدأ نجهز أوراق منحة منهم، ولا حابب تركز على دولة معينة؟').\n"
            "التنسيق: نقاط واضحة ورشيقة (Bullet points)."
        )

        history_text = ""
        if chat_history:
            history_text = "سجل المحادثة السابقة بينكما:\n"
            for msg in chat_history[-6:]:
                role = "الطالب" if msg.get("role") in ["user", "student"] else "المستشار"
                history_text += f"{role}: {msg.get('text', '')}\n"

        prompt = f"""
{history_text}
{profile_context}
سؤال الطالب الجديد:
"{student_query}"

أجب باختصار واحترافية تفاعلية (جاوب ع قد السؤال وبنقاط ذكية ومباشرة).
"""

        for candidate in [self.model] + FALLBACK_MODELS:
            try:
                logger.info(f"Invoking AI Advisor via {candidate}")
                response = self.client.models.generate_content(
                    model=candidate,
                    contents=prompt,
                    config=dict(
                        system_instruction=system_instruction,
                        temperature=0.3
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
            "advice": "عذراً، الخادم منشغل حالياً. يرجى المحاولة بعد قليل أو مراجعة رادار المنح الأسبوعي."
        }

    async def generate_smart_documents(
        self,
        student_name: str,
        degree: str,
        major: str,
        gpa: str,
        scholarship_name: str,
        target_country: str = "Global",
        doc_type: str = "all",
        talents_experience: str = ""
    ) -> Dict[str, str]:
        """
        Generates tailored application kit: Motivation Letter, Recommendation Letter,
        Academic CV, Research Proposal, or Checklist customized for the specific scholarship and student.
        """
        if not self.client:
            return self._fallback_documents(student_name, degree, major, scholarship_name, doc_type)

        system_instruction = (
            "You are an Elite Academic Admissions Consultant and Scholarship Document Architect.\n"
            "Generate personalized, high-impact official application documents in clean Markdown format with institutional letterhead headers."
        )

        prompt = f"""
Student Profile:
- Applicant Name: {student_name}
- Degree Level: {degree}
- Major: {major}
- Academic GPA: {gpa}
- Targeted Scholarship: {scholarship_name}
- Destination: {target_country}
- Special Talents & Experience: {talents_experience or "Academic projects and leadership"}
- Requested Document Focus: {doc_type}

Generate full, professional, highly articulated documents tailored strictly to {scholarship_name}.
If doc_type is 'all', generate all sections. Otherwise focus deeply on the requested document:

---MOTIVATION_LETTER---
(A compelling, structured 450-word Statement of Purpose / Motivation Letter in English tailored to {scholarship_name} and {major}, highlighting academic drive, {gpa}, impact, and Palestine/global community leadership)

---RECOMMENDATION_LETTER---
(An official academic recommendation letter template from a university professor with specific praise of {student_name}'s capabilities)

---ACADEMIC_CV---
(A polished Academic CV structure including Education, Research Interests, Projects, Honors, and Skills)

---ACADEMIC_CHECKLIST---
(A clear, step-by-step checklist of requirements, attestations, translations, and deadlines for {scholarship_name})
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
                text = response.text or ""
                docs = {}

                if "---MOTIVATION_LETTER---" in text:
                    p1 = text.split("---MOTIVATION_LETTER---")[1]
                    mot, r1 = p1.split("---RECOMMENDATION_LETTER---") if "---RECOMMENDATION_LETTER---" in p1 else (p1, "")
                    docs["motivation_letter"] = mot.strip()

                    if "---ACADEMIC_CV---" in r1:
                        rec, r2 = r1.split("---ACADEMIC_CV---")
                        docs["recommendation_letter"] = rec.strip()
                        if "---ACADEMIC_CHECKLIST---" in r2:
                            cv, chk = r2.split("---ACADEMIC_CHECKLIST---")
                            docs["academic_cv"] = cv.strip()
                            docs["checklist"] = chk.strip()
                        else:
                            docs["academic_cv"] = r2.strip()
                    elif "---ACADEMIC_CHECKLIST---" in r1:
                        rec, chk = r1.split("---ACADEMIC_CHECKLIST---")
                        docs["recommendation_letter"] = rec.strip()
                        docs["checklist"] = chk.strip()
                    else:
                        docs["recommendation_letter"] = r1.strip()

                if docs:
                    return docs
            except Exception as e:
                logger.warning(f"Doc generation error with {candidate}: {e}")
                continue

        return self._fallback_documents(student_name, degree, major, scholarship_name, doc_type)

    def _fallback_documents(
        self,
        student_name: str,
        degree: str,
        major: str,
        scholarship_name: str,
        doc_type: str = "all"
    ) -> Dict[str, str]:
        """Fallback document templates with official institutional headers and printable letterhead styling."""
        now_date = datetime.now().strftime("%B %d, %Y")
        ref_id = f"REF-{hash(student_name + scholarship_name) % 1000000:06d}"

        return {
            "motivation_letter": f"""================================================================================
OFFICIAL STATEMENT OF PURPOSE & MOTIVATION LETTER
Reference: {ref_id} | Date: {now_date}
Target Institution: Selection Committee of {scholarship_name}
================================================================================

To: The Esteemed Selection Committee for {scholarship_name}
Applicant: {student_name}
Proposed Program: {degree} in {major}

Dear Esteemed Members of the Selection Committee,

I am writing to formally submit my application for the prestigious {scholarship_name}. Having pursued focused academic excellence in {major}, my ambition is to conduct research and leadership work that directly addresses technological and societal challenges.

Throughout my studies, I have consistently maintained a high standard of academic dedication. Receiving the {scholarship_name} represents a transformative opportunity to learn within a globally renowned academic ecosystem, engage with world-class faculty, and contribute meaningfully to the scholarly community.

My long-term vision is to apply the international expertise acquired through {scholarship_name} toward pioneering high-impact initiatives in {major}, fostering innovation, and empowering students and researchers in my homeland and globally.

Thank you for your consideration of my candidacy.

Sincerely,
{student_name}
Applicant Signature: _______________________
Email: [Registered Applicant Email]
Date of Application: {now_date}
================================================================================
""",
            "recommendation_letter": f"""================================================================================
CONFIDENTIAL ACADEMIC RECOMMENDATION LETTER
Reference: {ref_id}-REC | Date: {now_date}
Target: {scholarship_name} Admissions Directorate
================================================================================

To: Scholarship Evaluation & Selection Committee
Subject: Letter of Recommendation for {student_name} ({degree} - {major})

Dear Members of the Board,

It is a genuine honor to recommend {student_name} for the {scholarship_name}. Having supervised and taught {student_name} in advanced coursework within {major}, I can attest to their intellectual curiosity, analytical precision, and dedication.

{student_name} ranks among the most promising students I have mentored, exhibiting not only conceptual mastery of {major} but also exemplary integrity and teamwork. Their ability to synthesize complex concepts and execute practical projects distinguishes them as an exceptional scholarship candidate.

I extend my highest, unreserved recommendation for {student_name}'s admission to {scholarship_name}.

Respectfully submitted,

___________________________________________
Professor / Academic Advisor Signature
Department of {major}
Institution: [Accredited University / Academic Faculty]
Official Seal / Stamp: [Verified Institutional Reference]
================================================================================
""",
            "academic_cv": f"""================================================================================
ACADEMIC CURRICULUM VITAE (EUROPASS & INTERNATIONAL STANDARD)
Name: {student_name} | Major: {major} | Degree Level: {degree}
Target: {scholarship_name}
================================================================================

1. ACADEMIC EDUCATION
   * {degree} in {major}
     Status: In-progress / Completed with Distinction
     Relevant Coursework: Advanced Algorithms, Systems Architecture, Research Methodology

2. HONORS, AWARDS & ACHIEVEMENTS
   * High Academic Standing & Dean's Honor Roll
   * Competitive Hackathons, Scientific Research Projects & Technical Competitions
   * Community Volunteering & Student Leadership Initiatives

3. TECHNICAL & RESEARCH SKILLS
   * Domain Competencies: {major} Specializations
   * Languages: Arabic (Native), English (Academic Proficiency)
   * Research Tools: LaTeX, Data Analysis, Software Engineering Frameworks

4. REFERENCES
   * Available upon request from verified institutional professors.
================================================================================
""",
            "checklist": f"""================================================================================
OFFICIAL APPLICATION REQUIREMENTS & VERIFICATION CHECKLIST
Scholarship: {scholarship_name}
================================================================================

[x] 1. Certified Transcripts & Graduation Certificate (English Translation & Notarization)
[x] 2. Statement of Purpose / Motivation Letter (Customized for {scholarship_name})
[x] 3. Two Academic Letters of Recommendation (Signed on University Letterhead)
[x] 4. Academic CV in Europass / International Standard Format
[x] 5. Valid International Passport (Minimum 12 Months Validity)
[x] 6. Proof of Language Proficiency (or Enrollment in Preparatory Year)
[x] 7. Relevant Certificates, Awards, Research Papers & Portfolios
[x] 8. Submission via the Official Application Portal before Deadline
================================================================================
"""
        }
