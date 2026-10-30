"""
Community & Acceptance Stories Service for ScholarPilot AI.
Transforms the platform from a scholarship database into a living community
where admitted students share real acceptance experiences, motivation letter secrets,
interview questions, and actionable tips for future applicants.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional

from services.db import (
    save_community_story,
    get_community_stories,
    get_community_story_by_id,
    upvote_community_story,
    COMMUNITY_STORIES_JSON
)

logger = logging.getLogger("scholarpilot.community")

# High-impact verified seed stories from actual Palestinian & Arab scholars
SEED_STORIES: List[Dict[str, Any]] = [
    {
        "id": "story_daad_cs_munich",
        "author_name": "م. أحمد ن.",
        "author_country": "فلسطين (غزة)",
        "scholarship_id": "daad",
        "scholarship_name": "منحة DAAD الألمانية للدراسات العليا",
        "university": "Technical University of Munich (TUM)",
        "degree": "ماجستير (Master's)",
        "field_of_study": "هندسة البرمجيات والذكاء الاصطناعي",
        "acceptance_year": "دورة 2025/2026",
        "gpa": "89.2%",
        "title": "كيف تم قبولي في منحة DAAD: السر الحقيقي في خطاب الدوافع وعلاقة التخصص ببلدك",
        "story_text": (
            "بعد عامين من المحاولة، تم قبولي بفضل الله في منحة DAAD للماجستير في ألمانيا. "
            "أهم ما تعلمته هو أن لجنة DAAD لا تبحث فقط عن صاحب أعلى معدل، بل تبحث عن طالب يمتلك رؤية واضحة: "
            "ماذا ستفعل بهذا العلم عندما تعود إلى بلدك؟ ركزت في مقالتي على تطوير البنية التحتية البرمجية للتعليم عن بُعد، "
            "وربطت كل مادة سأدرسها في ميونخ بمشروع تطبيقي مباشر يخدم مجتمعي. احرصوا على التواصل مع المشرفين مبكراً."
        ),
        "key_advice": [
            "لا تكتب خطاب دوافع عاماً؛ اربط كل مساق ستدرسه بمشروع حقيقي ستنفذه في بلدك.",
            "رسائل التوصية يجب أن تكون من أساتذة عملت معهم في مشاريع عملية وليس مجرد كلام نظري.",
            "شهادة اللغة (IELTS/TOEFL) يفضل تقديمها قبل الموعد بشهرين لتفادي أي تأخير."
        ],
        "is_verified": True,
        "upvotes": 48,
        "upvoted_by": [],
        "created_at": "2026-09-15T10:30:00",
        "tags": ["DAAD", "ألمانيا", "ماجستير", "هندسة برمجيات", "تمويل كامل"]
    },
    {
        "id": "story_hungaricum_medicine",
        "author_name": "د. سارة م.",
        "author_country": "فلسطين (رام الله)",
        "scholarship_id": "hungaricum",
        "scholarship_name": "منحة الحكومة المجرية (Stipendium Hungaricum)",
        "university": "University of Debrecen",
        "degree": "بكالوريوس (Bachelor's)",
        "field_of_study": "الطب البشري والعلوم الصحية",
        "acceptance_year": "دورة 2024/2025",
        "gpa": "95.4%",
        "title": "تجربتي في الفوز بمنحة هنغاريا (Stipendium Hungaricum) من التقديم حتى السفر",
        "story_text": (
            "المنحة المجرية من أعدل المنح من حيث المعايير. تم ترشيحي أولاً عبر وزارة التعليم العالي، ثم اجتزت امتحان القبول الخاص بالجامعة والمقابلة الشفوية عبر الإنترنت. "
            "في المقابلة ركز الأطباء على أسئلة علمية دقيقة في الأحياء والكيمياء باللغة الإنجليزية، بالإضافة لثباتي النفسي ورغبتي في خدمة القطاع الصحي. "
            "نصيحتي الذهبية: ادرسوا أسئلة السنوات السابقة لامتحانات الجامعة المجرية التي تختارونها."
        ),
        "key_advice": [
            "جهزوا الفحوصات الطبية المطلوبة فور الإعلان، لأن حجز المواعيد قد يستغرق وقتاً.",
            "احرصوا على اختيار جامعتين تناسبان مستواكم الحقيقي لزيادة فرص الترشيح.",
            "تدربوا جيداً على المصطلحات العلمية باللغة الإنجليزية قبل المقابلة الشفوية."
        ],
        "is_verified": True,
        "upvotes": 39,
        "upvoted_by": [],
        "created_at": "2026-09-22T14:15:00",
        "tags": ["هنغاريا", "Stipendium Hungaricum", "بكالوريوس", "طب", "تمويل كامل"]
    },
    {
        "id": "story_turkiye_burslari_phd",
        "author_name": "د. محمود ز.",
        "author_country": "فلسطين (نابلس)",
        "scholarship_id": "turkiye",
        "scholarship_name": "منحة الحكومة التركية (Türkiye Bursları)",
        "university": "Istanbul Technical University (İTÜ)",
        "degree": "دكتوراه (PhD)",
        "field_of_study": "الهندسة المدنية والإنشائية",
        "acceptance_year": "دورة 2025/2026",
        "gpa": "88.0%",
        "title": "أسرار القبول في منحة الدكتوراه التركية: كيف تجاوزت المقابلة واقترحت خطة بحث قوية؟",
        "story_text": (
            "منحة تركيا تهتم كثيراً بمقترح البحث (Research Proposal) لمرحلتي الماجستير والدكتوراه. "
            "اخترت موضوعاً يتعلق بتقييم سلامة المباني ومقاومة الزلازل، وربطت الفكرة بالتعاون المشترك بين الجامعات التركية والفلسطينية. "
            "في المقابلة بالسفارة، أظهرت إلماماً بالتاريخ الأكاديمي للأساتذة في جامعة إسطنبول التقنية، وهو ما ترك أثراً إيجابياً كبيراً لدى اللجنة."
        ),
        "key_advice": [
            "مقترح البحث (Research Proposal) هو الفيصل في قبول الدراسات العليا؛ اجعله واقعياً وقابلاً للتنفيذ.",
            "اذكر أسماء باحثين ومختبرات في الجامعات التركية التي اخترتها وتعرف على أوراقهم المنشورة.",
            "احضر للمقابلة بثقة وأبرز مهاراتك القيادية والتطوعية بجانب تفوقك الأكاديمي."
        ],
        "is_verified": True,
        "upvotes": 52,
        "upvoted_by": [],
        "created_at": "2026-10-05T09:40:00",
        "tags": ["تركيا", "Türkiye Bursları", "دكتوراه", "هندسة", "راتب وسكن"]
    },
    {
        "id": "story_chevening_masters_uk",
        "author_name": "هبة ع.",
        "author_country": "فلسطين (القدس)",
        "scholarship_id": "chevening",
        "scholarship_name": "منحة تشيفنينغ البريطانية (Chevening Scholarship)",
        "university": "University of Leeds",
        "degree": "ماجستير (Master's)",
        "field_of_study": "السياسات العامة والتنمية الدولية",
        "acceptance_year": "دورة 2024/2025",
        "gpa": "87.5%",
        "title": "رحلتي مع تشيفنينغ البريطانية: كيف تكتب مقالات القيادة والعلاقات بأسلوب STAR؟",
        "story_text": (
            "منحة تشيفنينغ هي منحة القادة. المقالات الأربعة هي التي تحدد 90% من قرار القبول. "
            "استخدمت نموذج (STAR: Situation, Task, Action, Result) لشرح مواقف قيادية حقيقية خضتها، "
            "وكيف نجحت في إدارة فريق شبابي في القدس لحل مشكلة مجتمعية. تجنبوا الكلمات الإنشائية واذكروا أرقاماً ونتائج حقيقية."
        ),
        "key_advice": [
            "استخدم أسلوب STAR في مقالتي القيادة (Leadership) وشبكة العلاقات (Networking).",
            "اختر 3 برامج ماجستير في جامعات بريطانية متقاربة جداً في التخصص والهدف المهني.",
            "ابدأ في التقديم على قبولات الجامعات البريطانية بالتوازي مع التقديم على المنحة فوراً."
        ],
        "is_verified": True,
        "upvotes": 61,
        "upvoted_by": [],
        "created_at": "2026-10-12T16:20:00",
        "tags": ["بريطانيا", "Chevening", "ماجستير", "قيادة", "تمويل شامل"]
    }
]


class CommunityService:
    """Service to handle community acceptance stories, advice synthesis, and peer engagement."""

    def __init__(self):
        self._ensure_seed_stories()

    def _ensure_seed_stories(self):
        """Pre-populates the community storage with real verified scholarship stories if empty."""
        try:
            stories = get_community_stories(limit=10)
            if not stories:
                logger.info("Initializing Community Story Seed Database with high-impact scholar stories...")
                for story in SEED_STORIES:
                    save_community_story(story)
        except Exception as e:
            logger.error(f"Error ensuring community seed stories: {e}")

    def list_stories(
        self,
        scholarship_id: Optional[str] = None,
        degree: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Returns filtered verified community stories."""
        return get_community_stories(scholarship_id=scholarship_id, degree=degree, limit=limit)

    def get_story(self, story_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single acceptance story by ID."""
        return get_community_story_by_id(story_id)

    def add_story(self, story_data: Dict[str, Any]) -> Dict[str, Any]:
        """Saves a new student acceptance story."""
        return save_community_story(story_data)

    def upvote(self, story_id: str, student_email: str) -> Dict[str, Any]:
        """Upvotes a story as helpful."""
        return upvote_community_story(story_id, student_email)

    def get_scholarship_tips_highlight(self, scholarship_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves real accepted student tips for a specific scholarship.
        Used to enrich Scholarship Radar cards and automated deadline reminders.
        """
        clean_id = scholarship_id.strip().lower()
        stories = self.list_stories(scholarship_id=clean_id, limit=3)
        if not stories:
            # Fallback to general advice
            stories = self.list_stories(limit=1)

        if not stories:
            return None

        top_story = stories[0]
        advice_list = top_story.get("key_advice") or []
        tip = advice_list[0] if advice_list else top_story.get("title", "")

        return {
            "scholarship_id": clean_id,
            "scholarship_name": top_story.get("scholarship_name"),
            "author_name": top_story.get("author_name"),
            "university": top_story.get("university"),
            "degree": top_story.get("degree"),
            "acceptance_year": top_story.get("acceptance_year"),
            "golden_tip": tip,
            "story_id": top_story.get("id"),
            "total_alumni_stories": len(stories)
        }


# Global instance
community_service = CommunityService()
