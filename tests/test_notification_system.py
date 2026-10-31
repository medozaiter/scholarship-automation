import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from web.app import app
from services.notification_service import notification_service
from services.db import (
    get_unified_notifications,
    get_unified_unread_counts,
    get_user_notification_preferences,
    update_user_notification_preferences,
    mark_unified_notification_read,
    mark_all_unified_notifications_read,
    archive_unified_notification,
    delete_unified_notification
)


class TestNotificationSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.demo_email = "test_scholar_notif@scholarpilot.com"
        cls.actor_email = "actor_scholar@scholarpilot.com"

    def test_01_serve_notifications_page(self):
        """Test that /notifications page serves clean HTML with zero server errors."""
        res = self.client.get("/notifications")
        self.assertEqual(res.status_code, 200)
        self.assertIn("ScholarPilot", res.text)
        self.assertIn("مركز التنبيهات", res.text)

    def test_02_unread_count_api(self):
        """Test GET /api/notifications/unread-count returns total and category breakdown."""
        res = self.client.get(f"/api/notifications/unread-count?email={self.demo_email}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertIn("unread_count", data)
        self.assertIn("unread_by_category", data)
        breakdown = data["unread_by_category"]
        for cat in ["scholarship", "community", "news", "system"]:
            self.assertIn(cat, breakdown)

    def test_03_notification_preferences_get_and_update(self):
        """Test GET and POST for notification preferences."""
        # 1. GET preferences
        res_get = self.client.get(f"/api/notifications/preferences?email={self.demo_email}")
        self.assertEqual(res_get.status_code, 200)
        data_get = res_get.json()
        self.assertTrue(data_get.get("success"))
        self.assertIn("preferences", data_get)

        # 2. UPDATE preferences
        new_prefs = {
            "email": self.demo_email,
            "browser_push": True,
            "email_digest_frequency": "daily",
            "scholarship_matches": True,
            "community_likes": False,
            "subscribed_countries": ["Germany", "Japan", "Norway"],
            "subscribed_majors": ["Artificial Intelligence", "Robotics"]
        }
        res_post = self.client.post("/api/notifications/preferences", json=new_prefs)
        self.assertEqual(res_post.status_code, 200)
        data_post = res_post.json()
        self.assertTrue(data_post.get("success"))
        saved_prefs = data_post.get("preferences", {})
        self.assertEqual(saved_prefs.get("email_digest_frequency"), "daily")
        self.assertIn("Japan", saved_prefs.get("subscribed_countries", []))

    def test_04_subscribe_interests_endpoint(self):
        """Test POST /api/notifications/subscribe-interests."""
        payload = {
            "email": self.demo_email,
            "countries": ["Sweden", "Netherlands"],
            "majors": ["Data Science"],
            "degrees": ["Master's"]
        }
        res = self.client.post("/api/notifications/subscribe-interests", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("preferences", {}).get("subscribed_countries"), ["Sweden", "Netherlands"])

    def test_05_scholarship_match_trigger(self):
        """Test dispatching a scholarship match notification."""
        notif = notification_service.notify_scholarship_match(
            user_email=self.demo_email,
            scholarship_id="sch_test_daad_2026",
            scholarship_name="DAAD Master's Fellowship 2026",
            match_score=94,
            country="Germany",
            deadline="2026-11-15"
        )
        self.assertIsNotNone(notif)
        self.assertEqual(notif.get("category"), "scholarship")
        self.assertEqual(notif.get("action_type"), "scholarship_match")
        self.assertIn("DAAD", notif.get("title", ""))

    def test_06_intelligent_grouping_for_likes(self):
        """Test that multiple likes on the same post are intelligently grouped."""
        # Enable community likes for test user first
        update_user_notification_preferences(self.demo_email, {"community_likes": True})

        post_id = "post_grouping_test_99"
        actor1 = {"email": "scholar_a@test.com", "full_name": "أحمد باحث", "username": "ahmed_researcher"}
        actor2 = {"email": "scholar_b@test.com", "full_name": "سارة طالبة", "username": "sara_student"}

        # First like
        n1 = notification_service.notify_post_like(
            author_email=self.demo_email,
            actor_user=actor1,
            post_id=post_id,
            post_title="تجربتي في التقديم لمنحة إيراسموس"
        )
        self.assertIsNotNone(n1)
        self.assertEqual(n1.get("count", 1), 1)

        # Second like on same post (should group into n1 with count=2)
        n2 = notification_service.notify_post_like(
            author_email=self.demo_email,
            actor_user=actor2,
            post_id=post_id,
            post_title="تجربتي في التقديم لمنحة إيراسموس"
        )
        self.assertIsNotNone(n2)
        self.assertEqual(n2.get("id"), n1.get("id"))
        self.assertGreaterEqual(n2.get("count", 1), 2)

    def test_07_mention_parsing_and_dispatch(self):
        """Test parsing @username mentions and notifying the recipient."""
        from services.db import save_or_update_user
        # Ensure a target test user exists with username
        target_username = "test_mentioned_peer"
        target_user = {
            "email": "mentioned_peer@scholarpilot.com",
            "username": target_username,
            "full_name": "الزميل المنشن",
            "password_hash": "dummy",
            "salt": "dummy",
            "is_active": True
        }
        save_or_update_user(target_user)

        author = {
            "email": self.actor_email,
            "full_name": "محرر المنشور",
            "username": "editor_user"
        }

        content = f"أنصح الزميل @{target_username} بالاطلاع على شروط منحة تشيفنينغ البريطانية لهذا العام."
        dispatched = notification_service.parse_and_notify_mentions(
            content=content,
            author_user=author,
            entity_type="post",
            entity_id="post_test_mention_101",
            entity_title="نصائح منحة تشيفنينغ"
        )
        self.assertGreaterEqual(len(dispatched), 1)
        self.assertEqual(dispatched[0].get("recipient_email"), "mentioned_peer@scholarpilot.com")
        self.assertEqual(dispatched[0].get("category"), "community")
        self.assertEqual(dispatched[0].get("action_type"), "post_mention")

    def test_08_mark_read_and_read_all(self):
        """Test marking a single notification as read and marking all read."""
        # 1. Fetch unread notifications
        res_list = self.client.get(f"/api/notifications?email={self.demo_email}&unread_only=true")
        self.assertEqual(res_list.status_code, 200)
        items = res_list.json().get("notifications", [])
        if items:
            first_id = items[0]["id"]
            # Mark single read
            res_read = self.client.post(f"/api/notifications/{first_id}/read", json={"email": self.demo_email})
            self.assertEqual(res_read.status_code, 200)
            self.assertTrue(res_read.json().get("success"))

        # 2. Mark all read
        res_read_all = self.client.post("/api/notifications/read-all", json={"email": self.demo_email})
        self.assertEqual(res_read_all.status_code, 200)
        self.assertTrue(res_read_all.json().get("success"))

        # Verify unread count is now 0
        res_count = self.client.get(f"/api/notifications/unread-count?email={self.demo_email}")
        self.assertEqual(res_count.json().get("unread_count"), 0)

    def test_09_archive_and_delete_notifications(self):
        """Test archiving and deleting notifications."""
        # Create a fresh notification
        notif = notification_service.notify_system_event(
            recipient_email=self.demo_email,
            event_type="test_lifecycle",
            title="تنبيه اختبار دورة الحياة",
            message="اختبار أرشفة وحذف التنبيهات الأكاديمية"
        )
        self.assertIsNotNone(notif)
        nid = notif["id"]

        # 1. Archive
        res_arch = self.client.post(f"/api/notifications/{nid}/archive", json={"email": self.demo_email})
        self.assertEqual(res_arch.status_code, 200)
        self.assertTrue(res_arch.json().get("success"))

        # Verify in archived filter
        res_archived_list = self.client.get(f"/api/notifications?email={self.demo_email}&archived_only=true")
        self.assertEqual(res_archived_list.status_code, 200)
        archived_ids = [n["id"] for n in res_archived_list.json().get("notifications", [])]
        self.assertIn(nid, archived_ids)

        # 2. Delete
        res_del = self.client.delete(f"/api/notifications/{nid}?email={self.demo_email}")
        self.assertEqual(res_del.status_code, 200)
        self.assertTrue(res_del.json().get("success"))

    def test_10_user_preference_suppression(self):
        """Test that disabled preferences cleanly suppress notification generation."""
        # Disable news notifications for this user
        update_user_notification_preferences(self.demo_email, {"news_breaking": False})

        article = {
            "id": "news_suppress_test_01",
            "title": "خبر عاجل لا يجب استلامه",
            "summary": "هذا الخبر لن ينشئ تنبيهاً لأن الطالب ألغى الاشتراك",
            "is_featured": True,
            "category": "scholarships"
        }
        notif = notification_service.notify_important_news(article, recipient_emails=[self.demo_email])
        # Since news_breaking is False for self.demo_email, notif list should be empty
        self.assertEqual(len(notif), 0)


if __name__ == "__main__":
    unittest.main()
