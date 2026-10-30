"""
Comprehensive Test Suite for ScholarPilot AI Community & Acceptance Stories Engine.
Verifies:
1. Seed stories initialization (DAAD, Hungaricum, Turkiye Burslari, Chevening).
2. Story submission, retrieval, and filtering by scholarship and degree.
3. Upvoting mechanism (toggle on/off).
4. Highlights extraction for scholarship radar and notification integration.
5. Integration with enriched deadline reminder email template.
6. FastAPI endpoints for community stories, details, submissions, and upvotes.
"""

import sys
import unittest
from fastapi.testclient import TestClient

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from web.app import app
from services.community_service import community_service, SEED_STORIES
from services.email_service import render_deadline_reminder_template


class TestCommunitySystem(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_seed_stories_exist(self):
        """Verifies that seed stories are initialized and accessible."""
        stories = community_service.list_stories(limit=20)
        self.assertGreaterEqual(len(stories), 4)
        scholarship_ids = [s.get("scholarship_id") for s in stories]
        self.assertIn("daad", scholarship_ids)
        self.assertIn("hungaricum", scholarship_ids)
        self.assertIn("turkiye", scholarship_ids)
        self.assertIn("chevening", scholarship_ids)
        print(" -> PASSED: [TEST 1] Pre-seeded verified acceptance stories are loaded.")

    def test_02_filter_stories_by_scholarship(self):
        """Verifies filtering community stories by specific scholarship ID."""
        daad_stories = community_service.list_stories(scholarship_id="daad")
        self.assertGreaterEqual(len(daad_stories), 1)
        self.assertEqual(daad_stories[0]["scholarship_id"], "daad")
        self.assertIn("TUM", daad_stories[0].get("university", ""))
        print(" -> PASSED: [TEST 2] Community filtering by scholarship works cleanly.")

    def test_03_submit_new_acceptance_story(self):
        """Verifies submitting a new student acceptance story."""
        new_story = {
            "id": "story_test_unit_01",
            "author_name": "طارق خليل",
            "author_email": "tariq.student@example.com",
            "author_country": "فلسطين",
            "scholarship_id": "daad",
            "scholarship_name": "منحة DAAD الألمانية للدراسات العليا",
            "university": "Heidelberg University",
            "degree": "ماجستير (Master's)",
            "field_of_study": "الكيمياء الحيوية",
            "acceptance_year": "2025/2026",
            "title": "تجربتي في الحصول على قبول DAAD بجامعة هايدلبرغ",
            "story_text": "التجهيز المبكر والتواصل مع المشرف الأكاديمي هما سر قبولي في منحة ألمانيا.",
            "key_advice": ["تواصل مع البروفيسور الألماني قبل 6 أشهر", "قدم شهادة لغة معتمدة"],
            "gpa": "91.2%",
            "tags": ["ألمانيا", "ماجستير", "DAAD"]
        }
        saved = community_service.add_story(new_story)
        self.assertEqual(saved["id"], "story_test_unit_01")

        retrieved = community_service.get_story("story_test_unit_01")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["author_name"], "طارق خليل")
        print(" -> PASSED: [TEST 3] New student acceptance story submitted and retrieved.")

    def test_04_upvote_toggle(self):
        """Verifies that upvoting increases the count and toggles appropriately."""
        story_id = "story_daad_cs_munich"
        initial_story = community_service.get_story(story_id)
        initial_votes = initial_story.get("upvotes", 0)

        # 1. Add upvote
        res1 = community_service.upvote(story_id, "test_voter_1@example.com")
        self.assertTrue(res1["success"])
        self.assertEqual(res1["action"], "added")
        self.assertEqual(res1["upvotes"], initial_votes + 1)

        # 2. Toggle off (remove upvote)
        res2 = community_service.upvote(story_id, "test_voter_1@example.com")
        self.assertTrue(res2["success"])
        self.assertEqual(res2["action"], "removed")
        self.assertEqual(res2["upvotes"], initial_votes)
        print(" -> PASSED: [TEST 4] Story upvote toggle mechanism verified.")

    def test_05_community_highlights_and_deadline_enrichment(self):
        """Verifies that community tips are extracted and injected into deadline reminder emails."""
        highlight = community_service.get_scholarship_tips_highlight("daad")
        self.assertIsNotNone(highlight)
        self.assertIn("golden_tip", highlight)
        self.assertTrue(len(highlight["golden_tip"]) > 10)

        # Render deadline email with enriched community advice
        dummy_sch = {
            "id": "daad",
            "name": "DAAD Scholarships Germany",
            "country": "Germany",
            "deadline_display": "15 ديسمبر 2026"
        }
        html, text = render_deadline_reminder_template(
            student_name="أحمد",
            scholarship=dummy_sch,
            days_left=5,
            milestone="رفع خطاب الدوافع"
        )
        self.assertIn("نصيحة ذهبية من مجتمع المقبولين", html)
        self.assertIn(highlight["golden_tip"], html)
        self.assertIn("نصيحة من طالب تم قبوله سابقاً", text)
        print(" -> PASSED: [TEST 5] Deadline reminder enriched with real peer acceptance advice.")

    def test_06_fastapi_community_endpoints(self):
        """Verifies FastAPI REST endpoints for the Community Engine."""
        # 1. GET /api/community/stories
        resp = self.client.get("/api/community/stories?scholarship_id=turkiye")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertGreaterEqual(data["count"], 1)

        # 2. GET /api/community/highlights/turkiye
        h_resp = self.client.get("/api/community/highlights/turkiye")
        self.assertEqual(h_resp.status_code, 200)
        h_data = h_resp.json()
        self.assertTrue(h_data["success"])
        self.assertIn("golden_tip", h_data["highlight"])

        # 3. POST /api/community/stories (Validation check)
        sub_resp = self.client.post("/api/community/stories", json={
            "author_name": "مريم يوسف",
            "author_country": "فلسطين",
            "scholarship_id": "chevening",
            "scholarship_name": "منحة تشيفنينغ",
            "university": "Oxford University",
            "degree": "ماجستير",
            "title": "كيف اجتزت مقابلة تشيفنينغ بنجاح",
            "story_text": "التدريب على أسئلة القيادة وإثبات التأثير المجتمعي.",
            "key_advice": ["راجع مقالاتك بدقة قبل المقابلة"]
        })
        self.assertEqual(sub_resp.status_code, 200)
        self.assertTrue(sub_resp.json()["success"])

        # 4. POST /api/community/stories/{id}/upvote
        up_resp = self.client.post("/api/community/stories/story_chevening_masters_uk/upvote", json={
            "email": "student_reviewer@example.com"
        })
        self.assertEqual(up_resp.status_code, 200)
        self.assertTrue(up_resp.json()["success"])
        print(" -> PASSED: [TEST 6] FastAPI community REST endpoints verified 100%.")


if __name__ == "__main__":
    print("\n=======================================================")
    print(" RUNNING SCHOLARPILOT COMMUNITY & ACCEPTANCE SUITE")
    print("=======================================================\n")
    unittest.main()
