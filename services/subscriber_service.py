import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
SUBSCRIBERS_FILE = os.path.join(DATA_DIR, "subscribers.json")


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(SUBSCRIBERS_FILE):
        default_subscribers = [
            {
                "email": "medo.msz.2006@gmail.com",
                "full_name": "Mustafa AbuZaiter",
                "degree": "Undergraduate (Bachelor's)",
                "majors": [
                    "Cybersecurity",
                    "Software Engineering",
                    "Artificial Intelligence",
                    "Computer Science & IT"
                ],
                "country": "Palestine",
                "created_at": datetime.now().isoformat(),
                "last_sent_at": None,
                "status": "active"
            }
        ]
        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_subscribers, f, ensure_ascii=False, indent=2)


class SubscriberService:
    """Manages student email subscriptions for automated weekly scholarship reports."""

    def __init__(self):
        _ensure_data_dir()

    def get_all(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Returns list of subscribers."""
        _ensure_data_dir()
        try:
            with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
                subs = json.load(f)
                if active_only:
                    return [s for s in subs if s.get("status") == "active"]
                return subs
        except Exception as e:
            logger.error(f"Error reading subscribers: {e}")
            return []

    def add_or_update(
        self,
        email: str,
        full_name: str = "",
        degree: str = "Undergraduate (Bachelor's)",
        majors: Optional[List[str]] = None,
        country: str = "Palestine"
    ) -> Dict[str, Any]:
        """Adds a new student or updates existing preferences."""
        _ensure_data_dir()
        email_clean = email.strip().lower()
        if not email_clean or "@" not in email_clean:
            raise ValueError("Invalid email address")

        if majors is None:
            majors = ["Computer Science", "Software Engineering"]

        subs = self.get_all(active_only=False)
        existing = next((s for s in subs if s.get("email", "").lower() == email_clean), None)

        now_str = datetime.now().isoformat()
        if existing:
            existing["full_name"] = full_name or existing.get("full_name", "")
            existing["degree"] = degree
            existing["majors"] = majors
            existing["country"] = country
            existing["status"] = "active"
            existing["updated_at"] = now_str
            subscriber_record = existing
            logger.info(f"Updated subscriber profile: {email_clean}")
        else:
            subscriber_record = {
                "email": email_clean,
                "full_name": full_name or "Student",
                "degree": degree,
                "majors": majors,
                "country": country,
                "created_at": now_str,
                "last_sent_at": None,
                "status": "active"
            }
            subs.append(subscriber_record)
            logger.info(f"Added new subscriber: {email_clean}")

        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
            json.dump(subs, f, ensure_ascii=False, indent=2)

        return subscriber_record

    def update_last_sent(self, email: str):
        """Updates timestamp of last delivered email."""
        subs = self.get_all(active_only=False)
        for s in subs:
            if s.get("email", "").lower() == email.strip().lower():
                s["last_sent_at"] = datetime.now().isoformat()
                break
        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
            json.dump(subs, f, ensure_ascii=False, indent=2)

    def unsubscribe(self, email: str) -> bool:
        """Sets status to unsubscribed."""
        subs = self.get_all(active_only=False)
        found = False
        for s in subs:
            if s.get("email", "").lower() == email.strip().lower():
                s["status"] = "unsubscribed"
                found = True
                break
        if found:
            with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
                json.dump(subs, f, ensure_ascii=False, indent=2)
        return found
