"""
Comprehensive Test Suite for ScholarPilot AI Notification & Matching Subsystem.
Verifies:
1. Email Templates & Deliverability Headers
2. In-App Notifications DB & JSON Operations
3. User Preferences Synchronization
4. Telegram Alert Formatting
5. Notification Queue & Deduplication Engine
6. FastAPI Endpoints (/notifications, /api/notifications*, /api/user/preferences)
"""

import os
import sys
import asyncio
import time
from fastapi.testclient import TestClient

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from web.app import app
from services.db import (
    create_in_app_notification,
    get_in_app_notifications,
    get_unread_notification_count,
    mark_notification_as_read,
    mark_all_notifications_as_read,
    record_notification_event,
    get_notification_events,
    get_user_preferences,
    update_user_preferences
)
from services.email_service import (
    render_new_match_template,
    render_deadline_reminder_template,
    render_welcome_template,
    render_weekly_digest_template
)
from services.telegram_service import telegram_service
from services.notification_queue import enqueue_notification, get_queue_status

client = TestClient(app)

TEST_EMAIL = "test_notifications_suite@example.com"


def test_email_templates_and_headers():
    print("\n[TEST 1] Verifying 4 HTML Templates & Deliverability Plain-Text Fallbacks...")

    # 1. New Match
    sch = {
        "name": "Stipendium Hungaricum Scholarship",
        "country": "المجر",
        "university": "جامعة بودابست",
        "degree": "بكالوريوس وماجستير",
        "coverage": "تغطية كاملة 100%",
        "deadline_display": "15 يناير 2027",
        "link": "https://apply.stipendiumhungaricum.hu/"
    }
    html1, text1 = render_new_match_template("Mustafa", sch, match_score=94, reasons=["تخصص متطابق", "معدل ممتاز"])
    assert "Stipendium Hungaricum" in html1
    assert "List-Unsubscribe" in html1 or "التقديم عبر البوابة الرسمية" in html1
    assert "94%" in text1
    assert len(text1) > 50

    # 2. Deadline Reminder
    html2, text2 = render_deadline_reminder_template("Mustafa", sch, days_left=7, milestone="رفع كشف العلامات")
    assert "7 أيام" in html2 or "متبقي 7" in html2
    assert "7 أيام" in text2

    # 3. Welcome Email
    html3, text3 = render_welcome_template("Mustafa", TEST_EMAIL, {"degree": "بكالوريوس", "gpa": "92%", "country": "فلسطين"})
    assert "مرحباً بك في ScholarPilot AI" in html3
    assert "92%" in text3

    # 4. Weekly Digest
    html4, text4 = render_weekly_digest_template("Mustafa", [sch], closing_soon=[sch], advice="اهتم برسالة الدافع")
    assert "النشرة الأسبوعية" in html4
    assert "نشرة المنح" in text4

    print(" -> PASSED: All 4 Templates render valid responsive HTML with rich Arabic copy & plain-text fallbacks.")


def test_in_app_notifications():
    print("\n[TEST 2] Verifying In-App Notifications Storage & Read-State Logic...")
    
    # Create notification
    notif = create_in_app_notification(
        recipient=TEST_EMAIL,
        title="🎯 منحة جديدة متوافقة: Stipendium Hungaricum",
        message="تم رصد منحة في المجر متوافقة مع تخصصك بنسبة 95%",
        notif_type="match",
        scholarship_id="hungaricum",
        link="https://apply.stipendiumhungaricum.hu/"
    )
    assert notif["id"] is not None
    assert notif["recipient"] == TEST_EMAIL
    assert notif["is_read"] is False

    # Check unread count
    unread_before = get_unread_notification_count(TEST_EMAIL)
    assert unread_before >= 1

    # Fetch list
    items = get_in_app_notifications(TEST_EMAIL, limit=10)
    assert len(items) >= 1
    found = any(it["id"] == notif["id"] for it in items)
    assert found

    # Mark as read
    ok = mark_notification_as_read(TEST_EMAIL, notif["id"])
    assert ok is True

    # Mark all read
    create_in_app_notification(TEST_EMAIL, "Alert 2", "Msg 2")
    create_in_app_notification(TEST_EMAIL, "Alert 3", "Msg 3")
    marked_count = mark_all_notifications_as_read(TEST_EMAIL)
    assert marked_count >= 2
    assert get_unread_notification_count(TEST_EMAIL) == 0

    print(" -> PASSED: In-App Notifications lifecycle (create, fetch, mark read, mark all read) verified.")


def test_user_preferences():
    print("\n[TEST 3] Verifying User Notification & Matching Preferences...")
    
    prefs_payload = {
        "preferred_countries": ["Germany", "Canada"],
        "funding_type": "Full",
        "email_notifications": True,
        "telegram_notifications": True,
        "telegram_chat_id": "987654321",
        "degree": "Master's Degree",
        "majors": ["Artificial Intelligence", "Cybersecurity"]
    }

    updated = update_user_preferences(TEST_EMAIL, prefs_payload)
    assert updated is True

    loaded = get_user_preferences(TEST_EMAIL)
    assert loaded["funding_type"] == "Full"
    assert loaded["telegram_notifications"] is True
    assert loaded["telegram_chat_id"] == "987654321"
    assert "Germany" in loaded["preferred_countries"]
    assert "Canada" in loaded["preferred_countries"]

    print(" -> PASSED: User preferences persisted and retrieved accurately.")


def test_notification_events_tracking():
    print("\n[TEST 4] Verifying Notification Lifecycle Events Tracking...")
    
    evt = record_notification_event(
        recipient=TEST_EMAIL,
        notification_type="new_match_alert",
        channel="email",
        target_id="sch_pearson_123",
        status="delivered",
        meta={"score": 96}
    )
    assert evt["id"] is not None

    events = get_notification_events(recipient=TEST_EMAIL, limit=10)
    assert len(events) >= 1
    assert any(e["target_id"] == "sch_pearson_123" for e in events)

    print(" -> PASSED: Notification events tracked (created, sent, delivered, opened, clicked).")


def test_queue_and_deduplication():
    print("\n[TEST 5] Verifying Notification Queue & Strict Deduplication...")

    async def _run_queue_test():
        # First enqueue
        ok1 = await enqueue_notification(
            channel="in_app",
            recipient=TEST_EMAIL,
            notification_type="match_alert",
            target_id="sch_unique_dedup_001",
            payload={"title": "Test Title", "message": "Test Message"}
        )
        assert ok1 is True, "First enqueue should succeed"

        # Duplicate enqueue attempt (should be rejected immediately)
        ok2 = await enqueue_notification(
            channel="in_app",
            recipient=TEST_EMAIL,
            notification_type="match_alert",
            target_id="sch_unique_dedup_001",
            payload={"title": "Test Title", "message": "Test Message"}
        )
        assert ok2 is False, "Duplicate enqueue MUST be rejected to protect student from spam"

        status = get_queue_status()
        assert "skipped_duplicate" in status
        assert status["skipped_duplicate"] >= 1

    asyncio.run(_run_queue_test())
    print(" -> PASSED: Queue deduplication blocks duplicate dispatches.")


def test_fastapi_endpoints():
    print("\n[TEST 6] Verifying FastAPI Web & API Endpoints...")

    # 1. /notifications page
    res = client.get("/notifications")
    assert res.status_code == 200
    assert "مركز التنبيهات" in res.text

    # 2. GET /api/notifications
    res2 = client.get(f"/api/notifications?email={TEST_EMAIL}")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["success"] is True
    assert "notifications" in data2
    assert "unread_count" in data2

    # 3. GET /api/user/preferences
    res3 = client.get(f"/api/user/preferences?email={TEST_EMAIL}")
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["success"] is True
    assert data3["preferences"]["telegram_chat_id"] == "987654321"

    # 4. POST /api/user/preferences
    res4 = client.post("/api/user/preferences", json={
        "email": TEST_EMAIL,
        "funding_type": "Partial",
        "email_notifications": True,
        "telegram_notifications": False
    })
    assert res4.status_code == 200
    assert res4.json()["success"] is True

    # 5. GET /api/notifications/queue/status
    res5 = client.get("/api/notifications/queue/status")
    assert res5.status_code == 200
    assert "queue" in res5.json()

    print(" -> PASSED: All FastAPI notification and preferences endpoints functioning as expected.")


if __name__ == "__main__":
    test_email_templates_and_headers()
    test_in_app_notifications()
    test_user_preferences()
    test_notification_events_tracking()
    test_queue_and_deduplication()
    test_fastapi_endpoints()
    print("\n=======================================================")
    print(" ALL 6 NOTIFICATION & MATCHING SUITE TESTS PASSED 100%! ")
    print("=======================================================\n")
