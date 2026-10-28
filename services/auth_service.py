import os
import json
import hashlib
import secrets
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from services.security_utils import (
    validate_email,
    validate_name,
    validate_gpa,
    validate_password,
    sanitize_text
)

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")


def _ensure_users_file():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(USERS_FILE):
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
    """Authentication and Account Management Service with comprehensive security filters."""

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
        """Registers a new student user with strict input validation."""
        email_clean = validate_email(email)
        name_clean = validate_name(full_name)
        gpa_clean = validate_gpa(gpa)
        password_clean = validate_password(password)

        sanitized_majors = [sanitize_text(m, max_length=50) for m in (majors or ["Software Engineering"])]
        sanitized_degree = sanitize_text(degree, max_length=50) or "Undergraduate (Bachelor's)"
        sanitized_english = sanitize_text(english_level, max_length=50) or "Intermediate"
        sanitized_country = sanitize_text(country, max_length=50) or "Palestine"

        users = self._load_users()
        if any(u.get("email", "").lower() == email_clean for u in users):
            raise ValueError("هذا البريد الإلكتروني مسجل بالفعل. يمكنك تسجيل الدخول مباشرة.")

        salt = secrets.token_hex(8)
        hashed_pw = hashlib.sha256((salt + password_clean).encode("utf-8")).hexdigest()

        role = "admin" if email_clean == "medo.msz.2006@gmail.com" else "student"

        new_user = {
            "email": email_clean,
            "full_name": name_clean,
            "role": role,
            "salt": salt,
            "password_hash": hashed_pw,
            "degree": sanitized_degree,
            "majors": sanitized_majors,
            "gpa": gpa_clean,
            "english_level": sanitized_english,
            "country": sanitized_country,
            "saved_scholarships": [],
            "created_at": datetime.now().isoformat()
        }

        users.append(new_user)
        self._save_users(users)
        logger.info(f"Registered user: {email_clean} with role {role}")

        safe_copy = dict(new_user)
        safe_copy.pop("salt", None)
        safe_copy.pop("password_hash", None)
        return safe_copy

    def login(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Verifies credentials with sanitized input."""
        try:
            email_clean = validate_email(email)
            password_clean = validate_password(password)
        except Exception:
            return None

        users = self._load_users()
        user = next((u for u in users if u.get("email", "").lower() == email_clean), None)
        if not user:
            return None

        salt = user.get("salt", "")
        test_hash = hashlib.sha256((salt + password_clean).encode("utf-8")).hexdigest()

        if test_hash == user.get("password_hash"):
            safe_copy = dict(user)
            safe_copy.pop("salt", None)
            safe_copy.pop("password_hash", None)
            return safe_copy
        return None

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Finds user by email."""
        try:
            email_clean = validate_email(email)
        except Exception:
            return None

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
