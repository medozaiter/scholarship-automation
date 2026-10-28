import os
import json
import hashlib
import secrets
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")


def _ensure_users_file():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(USERS_FILE):
        # Default admin account for Mustafa
        salt = secrets.token_hex(8)
        hashed_pw = hashlib.sha256((salt + "admin123").encode("utf-8")).hexdigest()
        default_users = [
            {
                "email": "medo.msz.2006@gmail.com",
                "full_name": "Mustafa AbuZaiter (Admin)",
                "role": "admin",
                "salt": salt,
                "password_hash": hashed_pw,
                "degree": "Undergraduate (Bachelor's)",
                "majors": ["Cybersecurity", "Software Engineering", "AI"],
                "gpa": "90%+",
                "english_level": "IELTS 6.5+ / Advanced",
                "country": "Palestine",
                "saved_scholarships": ["Lester B. Pearson", "Stipendium Hungaricum"],
                "created_at": datetime.now().isoformat()
            }
        ]
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_users, f, ensure_ascii=False, indent=2)


class AuthService:
    """Authentication and Account Management Service for Students and Administrators."""

    def __init__(self):
        _ensure_users_file()

    def _load_users(self) -> List[Dict[str, Any]]:
        _ensure_users_file()
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading users: {e}")
            return []

    def _save_users(self, users: List[Dict[str, Any]]):
        _ensure_users_file()
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)

    def register(
        self,
        email: str,
        password: str,
        full_name: str,
        degree: str = "Undergraduate (Bachelor's)",
        majors: Optional[List[str]] = None,
        gpa: str = "85%",
        english_level: str = "Intermediate",
        country: str = "Palestine"
    ) -> Dict[str, Any]:
        """Registers a new student user."""
        email_clean = email.strip().lower()
        if not email_clean or "@" not in email_clean:
            raise ValueError("صيغة البريد الإلكتروني غير صحيحة")
        if len(password) < 6:
            raise ValueError("كلمة المرور يجب أن لا تقل عن 6 أحرف")

        users = self._load_users()
        if any(u.get("email", "").lower() == email_clean for u in users):
            raise ValueError("هذا البريد الإلكتروني مسجل بالفعل. يمكنك تسجيل الدخول مباشرة.")

        salt = secrets.token_hex(8)
        hashed_pw = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()

        # If it's Mustafa's email or first user, assign admin
        role = "admin" if email_clean == "medo.msz.2006@gmail.com" else "student"

        new_user = {
            "email": email_clean,
            "full_name": full_name or "Student",
            "role": role,
            "salt": salt,
            "password_hash": hashed_pw,
            "degree": degree,
            "majors": majors or ["Software Engineering"],
            "gpa": gpa,
            "english_level": english_level,
            "country": country,
            "saved_scholarships": [],
            "created_at": datetime.now().isoformat()
        }

        users.append(new_user)
        self._save_users(users)
        logger.info(f"Registered user: {email_clean} with role {role}")

        # Return user info without salt/hash
        safe_copy = dict(new_user)
        safe_copy.pop("salt", None)
        safe_copy.pop("password_hash", None)
        return safe_copy

    def login(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Verifies credentials and returns user profile if correct."""
        email_clean = email.strip().lower()
        users = self._load_users()
        user = next((u for u in users if u.get("email", "").lower() == email_clean), None)
        if not user:
            return None

        salt = user.get("salt", "")
        test_hash = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()

        if test_hash == user.get("password_hash"):
            safe_copy = dict(user)
            safe_copy.pop("salt", None)
            safe_copy.pop("password_hash", None)
            return safe_copy
        return None

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Finds user by email."""
        email_clean = email.strip().lower()
        users = self._load_users()
        user = next((u for u in users if u.get("email", "").lower() == email_clean), None)
        if user:
            safe_copy = dict(user)
            safe_copy.pop("salt", None)
            safe_copy.pop("password_hash", None)
            return safe_copy
        return None

    def list_all_users(self) -> List[Dict[str, Any]]:
        """Returns safe user list for Admin Dashboard."""
        users = self._load_users()
        safe_list = []
        for u in users:
            c = dict(u)
            c.pop("salt", None)
            c.pop("password_hash", None)
            safe_list.append(c)
        return safe_list
