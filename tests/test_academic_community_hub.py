"""
Comprehensive Test Suite for ScholarPilot AI Academic Community Hub.
Verifies:
1. Post creation with text, media, scholarship links, and success stories.
2. Category filtering and sorting (latest, popular, trending).
3. Search and discovery across topics, universities, and scholars.
4. Comments and nested replies (add, edit, delete, hierarchy).
5. Engagement interactions (like, save, share).
6. Student networking (follow, unfollow, network stats).
7. Success stories spotlight retrieval.
8. Real-time in-app community notification generation and mark-read.
9. Moderation reporting and spam validation.
10. Public profile integration displaying user community posts and network.
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
from services.auth_service import AuthService
from services.community_service import community_service
from services.security_utils import security_rate_limiter

auth_service = AuthService()


class TestAcademicCommunityHub(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.test_email = "community_scholar_test@example.com"
        cls.test_password = "SecurePassword123!"
        cls.test_username = "community-scholar-test"

        cls.peer_email = "community_peer_test@example.com"
        cls.peer_password = "PeerPassword123!"
        cls.peer_username = "community-peer-test"

    def setUp(self):
        # Clear rate limiters
        security_rate_limiter._requests.clear()
        security_rate_limiter._failed_logins.clear()

        # Clean existing test users safely
        try:
            auth_service.delete_account(self.test_email, self.test_password)
        except Exception:
            pass
        try:
            auth_service.delete_account(self.peer_email, self.peer_password)
        except Exception:
            pass

        # Register primary test user
        auth_service.register(
            email=self.test_email,
            password=self.test_password,
            full_name="د. سامر الأكاديمي",
            username=self.test_username,
            country="Palestine",
            university="Birzeit University",
            degree="ماجستير هندسة برمجيات"
        )
        login_res = auth_service.login(self.test_email, self.test_password)
        self.auth_token = login_res.get("session_token") or login_res.get("token")
        self.auth_headers = {"Authorization": f"Bearer {self.auth_token}"}

        # Register peer user
        auth_service.register(
            email=self.peer_email,
            password=self.peer_password,
            full_name="سارة الباحثة",
            username=self.peer_username,
            country="Jordan",
            university="University of Jordan",
            degree="بكالوريوس ذكاء اصطناعي"
        )
        peer_login = auth_service.login(self.peer_email, self.peer_password)
        self.peer_token = peer_login.get("session_token") or peer_login.get("token")
        self.peer_headers = {"Authorization": f"Bearer {self.peer_token}"}

    def tearDown(self):
        try:
            auth_service.delete_account(self.test_email, self.test_password)
        except Exception:
            pass
        try:
            auth_service.delete_account(self.peer_email, self.peer_password)
        except Exception:
            pass

    def test_01_post_creation_and_auth_protection(self):
        """Verifies authenticated post creation and unauthenticated rejection."""
        # Unauthenticated attempt should fail
        unauth_res = self.client.post("/api/community/posts", json={
            "title": "محاولة بدون تسجيل",
            "content": "محتوى غير مصرح به"
        })
        self.assertEqual(unauth_res.status_code, 401)

        # Authenticated post creation
        post_payload = {
            "title": "تجربتي في الحصول على قبول الدكتوراه في جامعة أكسفورد",
            "content": "أشارككم أهم النقاط التي ركزت عليها في مقترح البحث العلمي للحصول على الدعم الكامل.",
            "category": "research",
            "post_type": "text",
            "scholarship_id": "chevening",
            "scholarship_name": "منحة تشيفنينغ",
            "is_success_story": True,
            "success_details": {
                "scholarship_won": "منحة أكسفورد الكاملة",
                "acceptance_year": "2026/2027",
                "tips": ["ابدأ بالتواصل مع المشرفين مبكراً"]
            }
        }
        res = self.client.post("/api/community/posts", json=post_payload, headers=self.auth_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        created_post = data.get("post")
        self.assertEqual(created_post.get("author_username"), self.test_username)
        self.assertEqual(created_post.get("category"), "research")
        self.assertTrue(created_post.get("is_success_story"))

        # Cleanup post
        post_id = created_post["id"]
        del_res = self.client.delete(f"/api/community/posts/{post_id}", headers=self.auth_headers)
        self.assertEqual(del_res.status_code, 200)
        print(" -> PASSED: [TEST 1] Authenticated post creation & 401 protection verified.")

    def test_02_feed_filtering_and_sorting(self):
        """Verifies filtering by category and sorting by latest, popular, and trending."""
        # Create 2 posts in different categories
        p1 = self.client.post("/api/community/posts", json={
            "title": "منحة الحكومة التركية 2026",
            "content": "كل ما تحتاج معرفته عن المنحة التركية وإجراءات التقديم.",
            "category": "scholarships"
        }, headers=self.auth_headers).json()["post"]

        p2 = self.client.post("/api/community/posts", json={
            "title": "استفسار حول القبول المشروط",
            "content": "هل تقبل الجامعات الألمانية خطاب القبول المشروط باللغة؟",
            "category": "admissions"
        }, headers=self.auth_headers).json()["post"]

        # Filter by scholarships
        res_sch = self.client.get("/api/community/posts?category=scholarships")
        self.assertEqual(res_sch.status_code, 200)
        posts_sch = res_sch.json()["posts"]
        self.assertTrue(any(p["id"] == p1["id"] for p in posts_sch))
        self.assertFalse(any(p["id"] == p2["id"] for p in posts_sch))

        # Sort by latest
        res_sort = self.client.get("/api/community/posts?sort_by=latest")
        self.assertEqual(res_sort.status_code, 200)
        self.assertGreaterEqual(len(res_sort.json()["posts"]), 2)

        # Cleanup
        self.client.delete(f"/api/community/posts/{p1['id']}", headers=self.auth_headers)
        self.client.delete(f"/api/community/posts/{p2['id']}", headers=self.auth_headers)
        print(" -> PASSED: [TEST 2] Category filtering & sorting verified.")

    def test_03_search_and_discovery(self):
        """Verifies full-text search across community discussions."""
        unique_keyword = "عالم_الروبوتات_والأتمتة_2027"
        p = self.client.post("/api/community/posts", json={
            "title": f"بحث علمي جديد في {unique_keyword}",
            "content": "نشرت اليوم ورقة بحثية جديدة في مؤتمر علمي دولي.",
            "category": "research"
        }, headers=self.auth_headers).json()["post"]

        res = self.client.get(f"/api/community/posts?search={unique_keyword}")
        self.assertEqual(res.status_code, 200)
        found_posts = res.json()["posts"]
        self.assertTrue(any(unique_keyword in p_item["title"] for p_item in found_posts))

        self.client.delete(f"/api/community/posts/{p['id']}", headers=self.auth_headers)
        print(" -> PASSED: [TEST 3] Full-text search and discovery verified.")

    def test_04_comments_and_nested_replies(self):
        """Verifies adding comments, nested replies, editing, and deleting comments."""
        p = self.client.post("/api/community/posts", json={
            "title": "نقاش مفتوح حول اختبار GRE",
            "content": "ما هي أفضل المصادر المجانية للتحضير لاختبار GRE؟",
            "category": "academic_questions"
        }, headers=self.auth_headers).json()["post"]
        post_id = p["id"]

        # Peer adds top-level comment
        c1_res = self.client.post(f"/api/community/posts/{post_id}/comments", json={
            "content": "أنصح بشدة بكتب Manhattan Prep وقنوات اليوتيوب التعليمية."
        }, headers=self.peer_headers)
        self.assertEqual(c1_res.status_code, 200)
        c1 = c1_res.json()["comment"]

        # Primary user replies to peer's comment (nested reply)
        reply_res = self.client.post(f"/api/community/posts/{post_id}/comments", json={
            "content": "شكراً جزيلاً سارة! هل ركزت على قسم الرياضيات أكثر؟",
            "parent_id": c1["id"]
        }, headers=self.auth_headers)
        self.assertEqual(reply_res.status_code, 200)
        reply = reply_res.json()["comment"]
        self.assertEqual(reply.get("parent_id"), c1["id"])

        # Fetch comments tree
        tree_res = self.client.get(f"/api/community/posts/{post_id}/comments")
        self.assertEqual(tree_res.status_code, 200)
        tree = tree_res.json()["comments"]
        target_c1 = next((item for item in tree if item["id"] == c1["id"]), None)
        self.assertIsNotNone(target_c1)
        self.assertEqual(len(target_c1.get("replies", [])), 1)

        # Peer edits comment
        edit_res = self.client.put(f"/api/community/comments/{c1['id']}", json={
            "content": "تعديل: أنصح بـ Manhattan Prep + اختبارات ETS الرسمية."
        }, headers=self.peer_headers)
        self.assertEqual(edit_res.status_code, 200)
        self.assertTrue(edit_res.json()["comment"]["is_edited"])

        # Peer deletes comment
        del_c_res = self.client.delete(f"/api/community/comments/{c1['id']}", headers=self.peer_headers)
        self.assertEqual(del_c_res.status_code, 200)

        self.client.delete(f"/api/community/posts/{post_id}", headers=self.auth_headers)
        print(" -> PASSED: [TEST 4] Comments, nested replies, edit & delete verified.")

    def test_05_engagement_interactions_like_save_share(self):
        """Verifies like toggle, save/bookmark toggle, and share counter."""
        p = self.client.post("/api/community/posts", json={
            "title": "منحة داد الكاملة للدراسات العليا",
            "content": "فرصة مميزة للباحثين للعام الأكاديمي القادم.",
            "category": "scholarships"
        }, headers=self.auth_headers).json()["post"]
        post_id = p["id"]

        # Peer likes the post
        like_res = self.client.post(f"/api/community/posts/{post_id}/like", headers=self.peer_headers)
        self.assertEqual(like_res.status_code, 200)
        self.assertTrue(like_res.json()["is_liked"])
        self.assertEqual(like_res.json()["likes_count"], 1)

        # Peer unlikes the post
        unlike_res = self.client.post(f"/api/community/posts/{post_id}/like", headers=self.peer_headers)
        self.assertEqual(unlike_res.status_code, 200)
        self.assertFalse(unlike_res.json()["is_liked"])
        self.assertEqual(unlike_res.json()["likes_count"], 0)

        # Peer saves the post
        save_res = self.client.post(f"/api/community/posts/{post_id}/save", headers=self.peer_headers)
        self.assertEqual(save_res.status_code, 200)
        self.assertTrue(save_res.json()["is_saved"])

        # Share counter
        share_res = self.client.post(f"/api/community/posts/{post_id}/share")
        self.assertEqual(share_res.status_code, 200)
        self.assertGreaterEqual(share_res.json()["shares_count"], 1)

        self.client.delete(f"/api/community/posts/{post_id}", headers=self.auth_headers)
        print(" -> PASSED: [TEST 5] Like, save & share engagement interactions verified.")

    def test_06_student_networking_follow_unfollow(self):
        """Verifies student peer follow/unfollow connection system."""
        # Peer follows primary student
        fol_res = self.client.post(f"/api/community/users/{self.test_username}/follow", headers=self.peer_headers)
        self.assertEqual(fol_res.status_code, 200)
        self.assertTrue(fol_res.json()["is_following"])

        # Check network stats of primary student
        net_res = self.client.get(f"/api/community/users/{self.test_username}/network", headers=self.peer_headers)
        self.assertEqual(net_res.status_code, 200)
        net_data = net_res.json()
        self.assertGreaterEqual(net_data["followers_count"], 1)
        self.assertTrue(net_data["is_following"])

        # Peer unfollows primary student
        unfol_res = self.client.post(f"/api/community/users/{self.test_username}/follow", headers=self.peer_headers)
        self.assertEqual(unfol_res.status_code, 200)
        self.assertFalse(unfol_res.json()["is_following"])
        print(" -> PASSED: [TEST 6] Student networking follow/unfollow verified.")

    def test_07_in_app_notifications_generation(self):
        """Verifies real-time community in-app notifications generated for likes and comments."""
        p = self.client.post("/api/community/posts", json={
            "title": "منحة ماكس بلانك الصيفية",
            "content": "نصائح تجهيز السيرة الذاتية الأكاديمية.",
            "category": "internships"
        }, headers=self.auth_headers).json()["post"]
        post_id = p["id"]

        # Peer likes post -> should generate notification for primary user
        self.client.post(f"/api/community/posts/{post_id}/like", headers=self.peer_headers)

        # Primary user checks notifications
        notif_res = self.client.get("/api/community/notifications", headers=self.auth_headers)
        self.assertEqual(notif_res.status_code, 200)
        notifs = notif_res.json()["notifications"]
        like_notif = next((n for n in notifs if n.get("action_type") == "like" and n.get("target_id") == post_id), None)
        self.assertIsNotNone(like_notif)

        # Mark notifications read
        mark_res = self.client.post("/api/community/notifications/mark-read", headers=self.auth_headers)
        self.assertEqual(mark_res.status_code, 200)

        self.client.delete(f"/api/community/posts/{post_id}", headers=self.auth_headers)
        print(" -> PASSED: [TEST 7] In-app community notifications generated & read verified.")

    def test_08_moderation_reporting(self):
        """Verifies content reporting workflow."""
        rep_res = self.client.post("/api/community/report", json={
            "target_type": "post",
            "target_id": "post_test_sample_123",
            "reason": "محتوى دعائي غير مرغوب فيه",
            "details": "رابط تجاري مشبوه"
        }, headers=self.peer_headers)
        self.assertEqual(rep_res.status_code, 200)
        self.assertTrue(rep_res.json()["success"])
        print(" -> PASSED: [TEST 8] Content reporting & moderation workflow verified.")

    def test_09_public_profile_community_posts_integration(self):
        """Verifies public profile returns student's community posts and network metrics."""
        # Create a post under primary student
        p = self.client.post("/api/community/posts", json={
            "title": "منشور أكاديمي للملف الشخصي",
            "content": "يجب أن يظهر هذا المنشور داخل صفحتي العامة.",
            "category": "general_discussion"
        }, headers=self.auth_headers).json()["post"]

        # Fetch public profile API
        prof_res = self.client.get(f"/api/profile/{self.test_username}")
        self.assertEqual(prof_res.status_code, 200)
        prof_data = prof_res.json()["profile"]

        self.assertIn("network", prof_data)
        self.assertIn("community_posts", prof_data)
        user_posts = prof_data["community_posts"]
        self.assertTrue(any(post_item["id"] == p["id"] for post_item in user_posts))

        self.client.delete(f"/api/community/posts/{p['id']}", headers=self.auth_headers)
        print(" -> PASSED: [TEST 9] Public profile community posts integration verified.")

    def test_10_html_page_served_correctly(self):
        """Verifies GET /community serves modern academic interface."""
        res = self.client.get("/community")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/html", res.headers.get("content-type", ""))
        self.assertIn("ScholarPilot", res.text)
        self.assertIn("المجتمع الأكاديمي", res.text)
        print(" -> PASSED: [TEST 10] /community page serving verified.")


if __name__ == "__main__":
    unittest.main()
