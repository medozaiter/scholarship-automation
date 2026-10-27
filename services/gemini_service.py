import os
import json
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from google import genai

load_dotenv()

logger = logging.getLogger(__name__)

class GeminiService:
    """
    Service responsible for:
    1. Strict extraction and verification of scholarship listings from search data.
    2. Date verification & strict URL mapping (zero hallucinated links).
    3. Student eligibility evaluations.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY must be provided or set in environment variables.")

        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        self.client = genai.Client(api_key=self.api_key)

    async def analyze_and_format_scholarships(
        self,
        search_results: List[Dict[str, str]],
        degree: str,
        majors: List[str],
        funding: str,
        country: str = "Palestine"
    ) -> str:
        """
        Extracts verified scholarships strictly matching criteria, with verified source URLs
        and the mandatory deadline advisory disclaimer.
        """
        if not search_results:
            return (
                "⚠️ <b>لم يتم العثور على نتائج بحث كافية حالياً.</b>\n\n"
                "يرجى التحقق من شروط البحث أو توسيع نطاق التخصصات المطلوبة والمحاولة مرة أخرى."
            )

        # Build context mapping allowed source URLs to prevent any link hallucinations
        snippets_text = ""
        allowed_urls = []
        for i, item in enumerate(search_results, 1):
            url = item.get("url", "").strip()
            if url:
                allowed_urls.append(url)
            snippets_text += (
                f"[Source #{i}]\n"
                f"Title: {item.get('title')}\n"
                f"Snippet: {item.get('snippet')}\n"
                f"Exact URL: {url}\n\n"
            )

        majors_str = ", ".join(majors) if majors else "All relevant disciplines"

        system_instruction = (
            "You are an Elite Academic Advisor and Scholarship Verification Specialist.\n\n"
            "STRICT EXTRACTION RULES:\n"
            "1. URL INTEGRITY: You MUST take links verbatim from the provided 'Exact URL' fields. "
            "NEVER fabricate, guess, or shorten any URL. If a program does not have an exact URL in the context, do not include it.\n"
            "2. DATE & CYCLE VERIFICATION: You must check dates mentioned in titles and snippets. "
            "Include ONLY scholarships that are OPEN NOW or opening in upcoming weeks/months for the active 2026/2027 cycle. "
            "Completely exclude expired deadlines.\n"
            "3. ELIGIBILITY: Verify explicitly that the degree matches, and that applicants from the specified nationality are eligible.\n"
            "4. MANDATORY USER ADVISORY NOTICE: At the top or bottom of every single scholarship entry, or prominently in the message, "
            "include this exact Arabic notice:\n"
            "'⚠️ <i>تنبيه: يرجى التأكد من تاريخ الإغلاق والشروط النهائية عبر الرابط الرسمي دائماً.</i>'\n"
            "5. TELEGRAM HTML FORMAT ONLY: Use <b>, <i>, <code>, <a href='...'>. Never use Markdown symbols like **, ##, or [text](url)."
        )

        user_prompt = f"""
معايير البحث المطلوبة:
- الدرجة الأكاديمية: {degree}
- التخصصات المختارة: {majors_str}
- نوع التمويل المطلوب: {funding}
- دولة/جنسية المتقدم: {country}

قائمة الروابط والمصادر المعتمدة المتاحة فقط (Allowed Verified URLs):
{json.dumps(allowed_urls, indent=2)}

بيانات البحث المستخرجة (Search Context):
---
{snippets_text}
---

المطلوب بدقة:
1. استخرج أفضل 4 إلى 6 منح مطابقة تماماً للمواصفات.
2. نسق كل منحة بهذا الشكل بدقة:
   🎓 <b>[اسم المنحة والجهة المانحة]</b> - <i>[الدولة / المؤسسة]</i>
   • <b>حالة التقديم والموعد:</b> [مفتوح حالياً / يفتح قريباً] - [الموعد التقريبي/المعلن]
   • <b>التغطية المالية:</b> [ممولة بالكامل/جزئياً، الرسوم، السكن، الراتب، تسهيلات التأشيرة]
   • <b>الشروط الأساسية:</b> [المعدل الأدنى، متطلبات اللغة مثل IELTS/TOEFL، الاختبارات كـ SAT]
   • <b>الرابط الرسمي المباشر:</b> <a href="[الرابط المأخوذ حرفياً من Exact URL]">[اضغط هنا للانتقال لصفحة التقديم الرسمية]</a>
   ⚠️ <i>ملاحظة: يرجى التأكد من تاريخ الإغلاق عبر الرابط الرسمي.</i>

3. في النهاية، أضف ملخصاً بنصائح عملية تزيد من نسبة القبول.
"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=dict(
                    system_instruction=system_instruction,
                    temperature=0.1,  # Low temperature for strict factual adherence
                )
            )
            output_text = response.text or ""
            return output_text.strip()

        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}", exc_info=True)
            return (
                "❌ <b>حدث خطأ أثناء فحص وتدقيق المنح بالذكاء الاصطناعي.</b>\n"
                f"التفاصيل: <code>{str(e)}</code>\n\n"
                "يرجى المحاولة مجدداً."
            )

    async def evaluate_eligibility(
        self,
        gpa: str,
        english_level: str,
        age_or_grad_year: str,
        target_degree: str,
        target_major: str,
        country: str
    ) -> str:
        """
        Evaluates a student's profile against competitive scholarship criteria.
        Calculates compatibility score, strengths, weak spots, and action points.
        """
        system_instruction = (
            "You are a Senior University Admissions Committee Officer and Scholarship Evaluator.\n"
            "Your task is to analyze a student's academic profile and evaluate their eligibility and competitiveness "
            "for international government & university scholarships (e.g. Turkiye Burslari, Stipendium Hungaricum, "
            "UBC Scholars, MEPI Tomorrow's Leaders, Oxford Reach, GKS, etc.).\n"
            "Output must be in Telegram HTML format (using <b>, <i>, <code>, <u>)."
        )

        prompt = f"""
بيانات الطالب الأكاديمية:
- الدرجة المستهدفة: {target_degree}
- التخصص المستهدف: {target_major}
- جنسية الطالب: {country}
- المعدل التراكمي / الثانوية (GPA): {gpa}
- مستوى اللغة الإنجليزية / الشهادات: {english_level}
- العمر / سنة التخرج: {age_or_grad_year}

المطلوب:
قم بإنتاج تقرير فحص أهلية مبدئي مفصل يتضمن:
1. 📊 <b>نسبة التوافق التنافسي المبدئية:</b> (مثال: 85% - فرصة عالية جداً / 70% فرصة متوسطة تنافسية).
2. 💪 <b>نقاط القوة الأكاديمية (Strengths):</b>
3. ⚠️ <b>نقاط الضعف أو المتطلبات الناقصة (Weaknesses / Gaps):</b> (مثل الحاجة لاختبار لغة معتمد، متطلبات العمر، شروط التوثيق).
4. 🎯 <b>أبرز المنح العالمية المقترحة المتوافقة مع هذا الملف:</b>
5. 📝 <b>خطة عمل فورية لرفع نسبة القبول:</b> (3 خطوات ملموسة).

⚠️ <i>تنبيه: هذا التقييم إرشادي مبني على معايير السنوات السابقة للتنافس العالمي.</i>
"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=dict(
                    system_instruction=system_instruction,
                    temperature=0.3,
                )
            )
            return (response.text or "").strip()
        except Exception as e:
            logger.error(f"Error in eligibility evaluation: {e}")
            return f"❌ تعذر استكمال فحص الأهلية حالياً: <code>{str(e)}</code>"

    @staticmethod
    def split_telegram_message(text: str, max_length: int = 4000) -> List[str]:
        """Splits long text into Telegram-safe chunks."""
        if len(text) <= max_length:
            return [text]

        chunks = []
        current_chunk = []
        current_length = 0

        paragraphs = text.split("\n\n")

        for paragraph in paragraphs:
            para_len = len(paragraph) + 2
            if current_length + para_len > max_length:
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_length = 0

                if len(paragraph) > max_length:
                    lines = paragraph.split("\n")
                    for line in lines:
                        if current_length + len(line) + 1 > max_length:
                            chunks.append("\n".join(current_chunk))
                            current_chunk = []
                            current_length = 0
                        current_chunk.append(line)
                        current_length += len(line) + 1
                else:
                    current_chunk.append(paragraph)
                    current_length += para_len
            else:
                current_chunk.append(paragraph)
                current_length += para_len

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks
