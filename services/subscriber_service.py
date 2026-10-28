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
                "gpa": "90%+",
                "english_level": "IELTS 6.5+ / Advanced",
                "target_destinations": ["Europe", "Canada", "Turkey"],
                "country": "Palestine",
                "saved_scholarships": ["Lester B. Pearson", "Stipendium Hungaricum"],
                "created_at": datetime.now().isoformat(),
                "last_sent_at": None,
                "status": "active"
            }
        ]
        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_subscribers, f, ensure_ascii=False, indent=2)


class SubscriberService:
    """Manages student profiles, criteria, and saved scholarship tracking."""

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

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Finds a subscriber by email address."""
        email_clean = email.strip().lower()
        subs = self.get_all(active_only=False)
        return next((s for s in subs if s.get("email", "").lower() == email_clean), None)

    def add_or_update(
        self,
        email: str,
        full_name: str = "",
        degree: str = "Undergraduate (Bachelor's)",
        majors: Optional[List[str]] = None,
        gpa: str = "85%",
        english_level: str = "Intermediate",
        target_destinations: Optional[List[str]] = None,
        country: str = "Palestine",
        talents_experience: str = ""
    ) -> Dict[str, Any]:
        """Adds or updates comprehensive student profile."""
        _ensure_data_dir()
        email_clean = email.strip().lower()
        if not email_clean or "@" not in email_clean:
            raise ValueError("Invalid email address")

        if majors is None:
            majors = ["Computer Science", "Software Engineering"]
        if target_destinations is None:
            target_destinations = ["Europe", "Canada", "Turkey", "Any"]

        subs = self.get_all(active_only=False)
        existing = next((s for s in subs if s.get("email", "").lower() == email_clean), None)

        now_str = datetime.now().isoformat()
        if existing:
            existing["full_name"] = full_name or existing.get("full_name", "")
            existing["degree"] = degree
            existing["majors"] = majors
            existing["gpa"] = gpa or existing.get("gpa", "85%")
            existing["english_level"] = english_level or existing.get("english_level", "Intermediate")
            existing["target_destinations"] = target_destinations or existing.get("target_destinations", ["Any"])
            existing["country"] = country or existing.get("country", "Palestine")
            if talents_experience:
                existing["talents_experience"] = talents_experience
            existing["status"] = "active"
            existing["updated_at"] = now_str
            subscriber_record = existing
            logger.info(f"Updated student profile: {email_clean}")
        else:
            subscriber_record = {
                "email": email_clean,
                "full_name": full_name or "Student",
                "degree": degree,
                "majors": majors,
                "gpa": gpa,
                "english_level": english_level,
                "target_destinations": target_destinations,
                "country": country,
                "talents_experience": talents_experience or "",
                "saved_scholarships": [],
                "created_at": now_str,
                "last_sent_at": None,
                "status": "active"
            }
            subs.append(subscriber_record)
            logger.info(f"Registered new student: {email_clean}")

        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
            json.dump(subs, f, ensure_ascii=False, indent=2)

        return subscriber_record

    def toggle_saved_scholarship(self, email: str, scholarship_name: str) -> Dict[str, Any]:
        """Saves or un-saves a scholarship for deadline alert tracking."""
        _ensure_data_dir()
        subs = self.get_all(active_only=False)
        sub = next((s for s in subs if s.get("email", "").lower() == email.strip().lower()), None)
        if not sub:
            raise ValueError("Student email not registered.")

        saved = sub.get("saved_scholarships", [])
        if scholarship_name in saved:
            saved.remove(scholarship_name)
            is_saved = False
        else:
            saved.append(scholarship_name)
            is_saved = True

        sub["saved_scholarships"] = saved
        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
            json.dump(subs, f, ensure_ascii=False, indent=2)

        return {"saved": is_saved, "all_saved": saved}

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
