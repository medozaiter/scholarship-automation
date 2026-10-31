"""
Unit & Integration Tests for ScholarPilot AI Telegram Channel Automation.
Verifies:
1. Format of channel post (title, country, degree, deadline, coverage, link).
2. Duplicate prevention (idempotency check via DB and JSON).
3. Post ID persistence.
4. FastAPI endpoints for Telegram channel metadata and publishing.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import uuid
import unittest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from services.telegram_service import telegram_service
from services.db import (
    is_scholarship_published_to_telegram,
    save_scholarship_telegram_post,
    get_scholarship_telegram_post_id
)
from web.app import app

client = TestClient(app)


class TestTelegramAutomation(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.run_id = uuid.uuid4().hex[:8]
        self.sample_scholarship = {
            "id": f"test_daad_{self.run_id}",
            "name": "منحة الحكومة الألمانية DAAD",
            "university": "جامعة ميونخ التقنية TUM",
            "country": "ألمانيا",
            "degree": "ماجستير (Master's)",
            "deadline": "2027-01-15",
            "deadline_display": "15 يناير 2027",
            "coverage": "تمويل كامل 100% مع راتب شهري 934 يورو",
            "link": "https://www.daad.de/en/",
            "is_active": True
        }

    def test_01_channel_post_format(self):
        """Verifies post contains all mandatory attributes."""
        post_text = telegram_service.format_scholarship_post(self.sample_scholarship)
        self.assertIn("منحة الحكومة الألمانية DAAD", post_text)
        self.assertIn("ألمانيا", post_text)
        self.assertIn("ماجستير (Master's)", post_text)
        self.assertIn("15 يناير 2027", post_text)
        self.assertIn("تمويل كامل", post_text)
        self.assertIn("https://www.daad.de/en/", post_text)
        print("\n -> PASSED: [TEST 1] Telegram channel post format contains all required fields.")

    def test_02_duplicate_prevention_storage(self):
        """Verifies that publishing records post ID and marks scholarship as published."""
        test_id = f"test_gks_{self.run_id}"
        self.assertFalse(is_scholarship_published_to_telegram(test_id))

        # Save post
        save_scholarship_telegram_post(test_id, telegram_message_id=987654, channel_id="@ScholarPilot")
        self.assertTrue(is_scholarship_published_to_telegram(test_id))
        self.assertEqual(get_scholarship_telegram_post_id(test_id), "987654")
        print(" -> PASSED: [TEST 2] Duplicate prevention and Telegram post ID persistence verified.")

    async def test_03_publish_scholarship_to_channel_mock(self):
        """Verifies end-to-end publish flow with duplicate protection."""
        unique_sch = {
            "id": f"test_unique_{self.run_id}",
            "name": "Unique Test Scholarship",
            "country": "UK",
            "degree": "PhD",
            "deadline": "2027-02-01",
            "coverage": "Full Tuition",
            "link": "https://example.com/apply"
        }

        with patch.object(telegram_service, 'send_message_raw', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"message_id": 54321, "chat": {"id": -100123456}}

            # First publish -> should succeed and call Telegram API
            msg_id = await telegram_service.publish_scholarship_to_channel(unique_sch, channel_id="@TestChannel")
            self.assertEqual(msg_id, 54321)
            self.assertTrue(is_scholarship_published_to_telegram(unique_sch["id"]))
            mock_send.assert_called_once()

            # Second publish -> should detect duplicate and return existing post ID WITHOUT sending again
            mock_send.reset_mock()
            duplicate_msg_id = await telegram_service.publish_scholarship_to_channel(unique_sch, channel_id="@TestChannel")
            self.assertEqual(duplicate_msg_id, 54321)
            mock_send.assert_not_called()

        print(" -> PASSED: [TEST 3] Duplicate Telegram post prevention works 100% (skips re-posting).")

    def test_04_telegram_channel_api_endpoint(self):
        """Verifies /api/telegram/channel-info endpoint."""
        res = client.get("/api/telegram/channel-info")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("channel_id", data)
        self.assertIn("channel_url", data)
        self.assertTrue(data["channel_url"].startswith("http"))
        print(" -> PASSED: [TEST 4] /api/telegram/channel-info REST endpoint verified.")


if __name__ == "__main__":
    unittest.main()
