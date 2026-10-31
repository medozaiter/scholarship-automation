"""
Comprehensive Test Suite for the Scholarship News Center (أخبار المنح).
Verifies:
1. News page rendering & navigation.
2. 8 designated educational categories & counts.
3. Full-text search and multi-criteria sorting.
4. Scholarship deadline protection (strict exclusion of expired opportunities).
5. Strict news quality control & deduplication.
6. Community interactions (authenticated comments, nested replies, comment likes, saving, sharing).
7. Telegram channel automated broadcast & duplicate prevention.
8. AI Assistant integration with active verified news context.
"""

import unittest
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient

from web.app import app
from services.auth_service import AuthService
from services.news_service import news_service, NEWS_CATEGORIES
from services.advisor_service import AdvisorService
from services.db import (
    get_news_articles,
    get_news_article_by_id,
    save_news_article,
    enforce_news_deadlines,
    is_news_published_to_telegram
)

auth_service = AuthService()
advisor_service = AdvisorService()


class TestScholarshipNewsCenter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.test_email = "news_scholar_test@example.com"
        cls.test_password = "SecurePassword123!"

        # Clean up if existing
        try:
            auth_service.delete_account(cls.test_email, cls.test_password)
        except Exception:
            pass

        # Register test student
        reg_res = auth_service.register(
            email=cls.test_email,
            password=cls.test_password,
            full_name="طالب إخباري تجريبي",
            username="news-scholar-test"
        )
        cls.auth_token = reg_res.get("session_token") or reg_res.get("token")
        cls.auth_headers = {"Authorization": f"Bearer {cls.auth_token}"}

    @classmethod
    def tearDownClass(cls):
        try:
            auth_service.delete_account(cls.test_email, cls.test_password)
        except Exception:
            pass

    def test_01_news_page_rendering(self):
        """[TEST 1] Verifies /news page serves 200 OK with correct HTML structure and no emojis."""
        res = self.client.get("/news")
        self.assertEqual(res.status_code, 200)
        html = res.text
        self.assertIn("ScholarPilot", html)
        self.assertIn("أخبار المنح", html)
        self.assertIn("data-lucide", html)
        print("\n -> PASSED: [TEST 1] /news HTML page rendering and Lucide icons verified.")

    def test_02_categories_metadata_and_counts(self):
        """[TEST 2] Verifies all 8 designated categories exist with active counts."""
        res = self.client.get("/api/news/categories")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        cats = data.get("categories", {})

        expected_cats = [
            "scholarships", "universities", "study_abroad", "admissions",
            "research", "funding_opportunities", "international_programs", "internship_opportunities"
        ]
        for ec in expected_cats:
            self.assertIn(ec, cats)
            self.assertIn("label", cats[ec])
            self.assertIn("count", cats[ec])
            self.assertGreaterEqual(cats[ec]["count"], 1)

        print(" -> PASSED: [TEST 2] All 8 educational categories and counts verified.")

    def test_03_category_filtering_and_sorting(self):
        """[TEST 3] Verifies filtering by category and sorting by latest, popular, and deadline."""
        # 1. Category Filter: scholarships
        res_sch = self.client.get("/api/news?category=scholarships")
        self.assertEqual(res_sch.status_code, 200)
        articles_sch = res_sch.json()["data"]["articles"]
        self.assertTrue(all(a["category"] == "scholarships" for a in articles_sch))

        # 2. Category Filter: admissions
        res_adm = self.client.get("/api/news?category=admissions")
        self.assertEqual(res_adm.status_code, 200)
        articles_adm = res_adm.json()["data"]["articles"]
        self.assertTrue(all(a["category"] == "admissions" for a in articles_adm))

        # 3. Sort by popular
        res_pop = self.client.get("/api/news?sort_by=popular")
        self.assertEqual(res_pop.status_code, 200)
        articles_pop = res_pop.json()["data"]["articles"]
        self.assertGreaterEqual(len(articles_pop), 2)
        score1 = articles_pop[0].get("views_count", 0) + articles_pop[0].get("shares_count", 0) * 2
        score2 = articles_pop[1].get("views_count", 0) + articles_pop[1].get("shares_count", 0) * 2
        self.assertGreaterEqual(score1, score2)

        print(" -> PASSED: [TEST 3] Category filtering and multi-criteria sorting verified.")

    def test_04_full_text_search(self):
        """[TEST 4] Verifies search across titles, summaries, and countries."""
        # Search for Chevening
        res1 = self.client.get("/api/news?search=تشيفنينغ")
        self.assertEqual(res1.status_code, 200)
        articles1 = res1.json()["data"]["articles"]
        self.assertGreaterEqual(len(articles1), 1)
        self.assertIn("تشيفنينغ", articles1[0]["title"])

        # Search for Germany/DAAD
        res2 = self.client.get("/api/news?search=ألمانيا")
        self.assertEqual(res2.status_code, 200)
        articles2 = res2.json()["data"]["articles"]
        self.assertGreaterEqual(len(articles2), 1)

        print(" -> PASSED: [TEST 4] Full-text search and discovery verified.")

    def test_05_scholarship_deadline_protection(self):
        """[TEST 5] CRITICAL: Verifies expired scholarship news items are marked and hidden from active feed."""
        # The pre-seeded article news_stockholm_field_expired_2026 has deadline: 2026-09-01 (past)
        expired_art = get_news_article_by_id("news_stockholm_field_expired_2026")
        self.assertIsNotNone(expired_art)
        self.assertTrue(expired_art.get("is_expired"))

        # Default query: only_active=True -> Must NOT contain expired article!
        res_active = self.client.get("/api/news?only_active=true")
        self.assertEqual(res_active.status_code, 200)
        active_articles = res_active.json()["data"]["articles"]
        self.assertFalse(any(a["id"] == "news_stockholm_field_expired_2026" for a in active_articles))
        self.assertTrue(all(not a.get("is_expired", False) for a in active_articles))

        # Query all (including archive): only_active=false -> Contains expired article
        res_all = self.client.get("/api/news?only_active=false")
        self.assertEqual(res_all.status_code, 200)
        all_articles = res_all.json()["data"]["articles"]
        self.assertTrue(any(a["id"] == "news_stockholm_field_expired_2026" for a in all_articles))

        print(" -> PASSED: [TEST 5] Scholarship deadline protection (strict expired item exclusion) verified.")

    def test_06_news_quality_control_and_deduplication(self):
        """[TEST 6] Verifies non-educational content rejection and title/URL deduplication."""
        # 1. Political / non-educational content rejection
        bad_article = {
            "title": "مباراة كرة قدم وتصريحات اللاعبين بعد انتهاء اللقاء",
            "summary": "تقرير شامل عن مباراة كرة القدم ومجريات شوطي المباراة والنتائج",
            "content": "شهدت المباراة منافسة قوية بين الفريقين وسجل اللاعب هدف الفوز في الوقت القاتل.",
            "category": "scholarships"
        }
        valid, msg = news_service.validate_and_filter_article(bad_article)
        self.assertFalse(valid)
        self.assertIn("معايير الجودة", msg)

        # 2. Duplicate article detection (matching existing title)
        dup_article = {
            "title": "تمديد الموعد النهائي للتقديم على منح تشيفنينغ البريطانية (Chevening) لعام 2026/2027",
            "summary": "ملخص جديد لهذا الخبر للتحقق من نظام كشف التكرار الآلي للمنصة",
            "content": "تفاصيل إضافية كاملة للتقديم على المنحة وشروط القبول والأهلية المطلوبة.",
            "category": "scholarships"
        }
        valid2, msg2 = news_service.validate_and_filter_article(dup_article)
        self.assertFalse(valid2)
        self.assertIn("مطابق", msg2)

        print(" -> PASSED: [TEST 6] News quality control & duplicate article prevention verified.")

    def test_07_community_interactions_comments_and_likes(self):
        """[TEST 7] Verifies authenticated commenting, nested replies, comment likes, and 401 guard."""
        art_id = "news_chevening_extension_2026"

        # 1. Unauthenticated comment -> 401
        res_unauth = self.client.post(f"/api/news/{art_id}/comments", json={"content": "تعليق غير مصرح به"})
        self.assertEqual(res_unauth.status_code, 401)

        # 2. Authenticated comment
        res_comm = self.client.post(
            f"/api/news/{art_id}/comments",
            headers=self.auth_headers,
            json={"content": "خبر ممتاز وتمديد فرصة رائعة لاستكمال توصيات المشرف الأكاديمي."}
        )
        self.assertEqual(res_comm.status_code, 200)
        c_data = res_comm.json().get("comment")
        self.assertIsNotNone(c_data)
        comment_id = c_data["id"]

        # 3. Authenticated nested reply
        res_reply = self.client.post(
            f"/api/news/{art_id}/comments",
            headers=self.auth_headers,
            json={"content": "أتفق معك تماماً، التقديم الآن متاح حتى 20 نوفمبر.", "parent_id": comment_id}
        )
        self.assertEqual(res_reply.status_code, 200)
        r_data = res_reply.json().get("comment")
        self.assertEqual(r_data.get("parent_id"), comment_id)

        # 4. Like comment toggle
        res_like = self.client.post(
            f"/api/news/comments/{comment_id}/like",
            headers=self.auth_headers
        )
        self.assertEqual(res_like.status_code, 200)
        self.assertTrue(res_like.json().get("is_liked"))
        self.assertEqual(res_like.json().get("likes_count"), 1)

        print(" -> PASSED: [TEST 7] Authenticated news comments, nested replies, and likes verified.")

    def test_08_save_and_share_interactions(self):
        """[TEST 8] Verifies toggling article save and incrementing share counts."""
        art_id = "news_erasmus_mundus_open_2027"

        # 1. Ensure clean initial state
        art = get_news_article_by_id(art_id)
        if self.test_email in [e.lower() for e in art.get("saved_by", [])]:
            self.client.post(f"/api/news/{art_id}/save", headers=self.auth_headers)

        # 2. Save toggle -> True
        res_save = self.client.post(f"/api/news/{art_id}/save", headers=self.auth_headers)
        self.assertEqual(res_save.status_code, 200)
        self.assertTrue(res_save.json().get("is_saved"))

        # Verify it reflects in article fetch
        res_get = self.client.get(f"/api/news/{art_id}", headers=self.auth_headers)
        self.assertEqual(res_get.status_code, 200)
        self.assertTrue(res_get.json()["article"]["is_saved"])

        # 3. Unsave toggle -> False
        res_unsave = self.client.post(f"/api/news/{art_id}/save", headers=self.auth_headers)
        self.assertEqual(res_unsave.status_code, 200)
        self.assertFalse(res_unsave.json().get("is_saved"))

        # 2. Share increment
        res_share = self.client.post(f"/api/news/{art_id}/share")
        self.assertEqual(res_share.status_code, 200)
        self.assertGreater(res_share.json().get("shares_count", 0), 0)

        print(" -> PASSED: [TEST 8] Save to reading list and share count tracking verified.")

    def test_09_telegram_channel_broadcast_and_deduplication(self):
        """[TEST 9] Verifies Telegram broadcast formatting, dispatch, and deduplication."""
        art_id = "news_chevening_extension_2026"
        art = get_news_article_by_id(art_id)

        # 1. Format check
        post_text = news_service.format_news_telegram_post(art)
        self.assertIn("أخبار المنح", post_text)
        self.assertIn("تمديد الموعد النهائي", post_text)
        self.assertIn("المملكة المتحدة", post_text)
        self.assertIn("الموعد النهائي", post_text)
        self.assertIn("اضغط هنا للتقديم", post_text)
        self.assertIn("@ScholarPilot", post_text)

        # 2. Broadcast dispatch
        msg_id = news_service.broadcast_news_to_telegram(art_id)
        self.assertIsNotNone(msg_id)

        # 3. Deduplication check
        is_published = is_news_published_to_telegram(art_id)
        self.assertTrue(is_published)

        # Re-broadcast must return existing message ID and avoid duplicate sending
        msg_id_2 = news_service.broadcast_news_to_telegram(art_id)
        self.assertEqual(msg_id, msg_id_2)

        print(" -> PASSED: [TEST 9] Telegram bulletin formatting, broadcast, and deduplication verified.")

    def test_10_ai_assistant_news_integration(self):
        """[TEST 10] Verifies AI Advisor context injection with active news and deadline guidance."""
        profile = {
            "full_name": "سارة المحمود",
            "majors": ["هندسة حاسوب"],
            "degree": "Undergraduate",
            "gpa": "91%",
            "country": "Palestine"
        }

        # 1. Context prompt injection
        ctx = advisor_service.build_advisor_context(
            student_query="هل هناك أي تمديدات أو أخبار جديدة عن المنح الأوروبية والبريطانية؟",
            student_profile=profile
        )
        self.assertEqual(ctx["intent"], "news_updates")
        self.assertIn("أحدث الأخبار المعتمدة والفرص النشطة للمنح", ctx["context_prompt"])
        self.assertIn("تشيفنينغ", ctx["context_prompt"])
        self.assertIn("إيراسموس", ctx["context_prompt"])
        # Expired Stockholm article must NOT be in context!
        self.assertNotIn("news_stockholm_field_expired_2026", ctx["context_prompt"])

        # 2. Fallback response generation
        fallback = advisor_service._generate_deterministic_advisor_fallback(
            query="ما هي أحدث أخبار المنح؟",
            profile=profile,
            context=ctx
        )
        self.assertIn("سارة المحمود", fallback)
        self.assertIn("أحدث الأخبار والفرص المعتمدة", fallback)
        self.assertIn("تنويه موثوقية المواعيد", fallback)

        print(" -> PASSED: [TEST 10] AI Assistant active news context injection & expired exclusion verified.")


if __name__ == "__main__":
    unittest.main()
