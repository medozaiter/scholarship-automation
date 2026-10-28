import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

from services.security_utils import (
    validate_email,
    validate_name,
    validate_gpa,
    validate_password,
    sanitize_text,
    hash_password_secure,
    verify_password_secure,
    compute_dummy_pbkdf2,
    create_session_token,
    verify_session_token,
    security_rate_limiter,
    atomic_json_write
)
from services.db import get_db_session, is_db_available, UserDB

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")


def _ensure_users_file():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(USERS_FILE):
        hashed_pw, salt_hex = hash_password_secure("SafeAdminPass2026!")
        default_users = [
            {
                "email": "medo.msz.2006@gmail.com",
                "full_name": "Mustafa AbuZaiter",
                "role": "student",
                "salt": salt_hex,
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
        atomic_json_write(USERS_FILE, default_users)


class AuthService:
    """Authentication and Account Management Service with PBKDF2 encryption & brute-force defense."""

    def __init__(self):
        _ensure_users_file()

    def _load_users(self) -> List[Dict[str, Any]]:
        _ensure_users_file()
        if is_db_available():
            try:
                with get_db_session() as db:
                    if db is not None:
                        db_users = db.query(UserDB).all()
                        if db_users:
                            return [u.to_dict() for u in db_users]
            except Exception as e:
                logger.debug(f"DB load users failed, falling back to JSON: {e}")
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading users: {e}")
            return []

    def _save_users(self, users: List[Dict[str, Any]]):
        atomic_json_write(USERS_FILE, users)

    def register(
        self,
        email: str,
        password: str,
        full_name: str,
        degree: str = "Undergraduate (Bachelor's)",
        majors: Optional[List[str]] = None,
        gpa: str = "85%",
        english_level: str = "Intermediate",
        country: str = "Palestine",
        talents_experience: str = ""
    ) -> Dict[str, Any]:
        """Registers a new student user with PBKDF2-HMAC-SHA256 password hashing & session token."""
        email_clean = validate_email(email)
        name_clean = validate_name(full_name)
        gpa_clean = validate_gpa(gpa)
        password_clean = validate_password(password)

        sanitized_majors = [sanitize_text(m, max_length=50) for m in (majors or ["Software Engineering"])]
        sanitized_degree = sanitize_text(degree, max_length=50) or "Undergraduate (Bachelor's)"
        sanitized_english = sanitize_text(english_level, max_length=50) or "Intermediate"
        sanitized_country = sanitize_text(country, max_length=50) or "Palestine"
        sanitized_talents = sanitize_text(talents_experience, max_length=300) if talents_experience else ""

        users = self._load_users()
        if any(u.get("email", "").lower() == email_clean for u in users):
            raise ValueError("هذا البريد الإلكتروني مسجل بالفعل. يمكنك تسجيل الدخول مباشرة.")

        hashed_pw, salt_hex = hash_password_secure(password_clean)

        new_user = {
            "email": email_clean,
            "full_name": name_clean,
            "role": "student",
            "salt": salt_hex,
            "password_hash": hashed_pw,
            "degree": sanitized_degree,
            "majors": sanitized_majors,
            "gpa": gpa_clean,
            "english_level": sanitized_english,
            "country": sanitized_country,
            "talents_experience": sanitized_talents,
            "saved_scholarships": [],
            "created_at": datetime.now().isoformat()
        }

        if is_db_available():
            try:
                with get_db_session() as db:
                    if db is not None:
                        db.add(UserDB(
                            email=email_clean,
                            full_name=name_clean,
                            role="student",
                            salt=salt_hex,
                            password_hash=hashed_pw,
                            degree=sanitized_degree,
                            majors=sanitized_majors,
                            gpa=gpa_clean,
                            english_level=sanitized_english,
                            country=sanitized_country,
                            talents_experience=sanitized_talents,
                            saved_scholarships=[],
                            created_at=new_user["created_at"]
                        ))
            except Exception as dbe:
                logger.error(f"Error persisting user to PostgreSQL/Neon: {dbe}")

        users.append(new_user)
        self._save_users(users)
        logger.info(f"Registered user securely: {email_clean}")

        token = create_session_token(email=email_clean, role="student")
        safe_copy = dict(new_user)
        safe_copy.pop("salt", None)
        safe_copy.pop("password_hash", None)
        safe_copy["session_token"] = token
        return safe_copy

    def login(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticates user credentials against PBKDF2 hash (with legacy SHA256 upgrade),
        enforces account lockout on brute-force attempts, and issues signed session tokens.
        """
        try:
            email_clean = validate_email(email)
            password_clean = validate_password(password)
        except Exception:
            return None

        # Check account lockout before verifying
        locked, remaining = security_rate_limiter.is_account_locked(email_clean)
        if locked:
            mins = max(1, remaining // 60)
            raise ValueError(f"تم قفل الحساب مؤقتاً بسبب كثرة محاولات الدخول الخاطئة. يرجى المحاولة بعد {mins} دقيقة.")

        users = self._load_users()
        user = next((u for u in users if u.get("email", "").lower() == email_clean), None)
        if not user:
            # Defuse side-channel timing attack via dummy PBKDF2 calculation
            compute_dummy_pbkdf2(password_clean)
            security_rate_limiter.record_failed_login(email_clean)
            return None

        salt = user.get("salt", "")
        stored_hash = user.get("password_hash", "")

        is_valid, needs_rehash = verify_password_secure(password_clean, stored_hash, salt)

        if is_valid:
            # Clear failed login attempts upon success
            security_rate_limiter.record_successful_login(email_clean)

            # Auto-upgrade legacy hash to PBKDF2 if required
            if needs_rehash:
                new_hash, new_salt = hash_password_secure(password_clean)
                user["password_hash"] = new_hash
                user["salt"] = new_salt
                if is_db_available():
                    try:
                        with get_db_session() as db:
                            if db is not None:
                                db_user = db.query(UserDB).filter(UserDB.email == email_clean).first()
                                if db_user:
                                    db_user.password_hash = new_hash
                                    db_user.salt = new_salt
                    except Exception as dbe:
                        logger.debug(f"DB password rehash update error: {dbe}")
                self._save_users(users)
                logger.info(f"Auto-upgraded password hash to PBKDF2-HMAC-SHA256 for: {email_clean}")

            # Issue signed session token
            token = create_session_token(email=email_clean, role=user.get("role", "student"))

            safe_copy = dict(user)
            safe_copy.pop("salt", None)
            safe_copy.pop("password_hash", None)
            safe_copy["session_token"] = token
            return safe_copy

        # Invalid password
        security_rate_limiter.record_failed_login(email_clean)
        return None

    def authenticate_token(self, token: Optional[str]) -> Optional[Dict[str, Any]]:
        """Verifies session token and returns current user profile."""
        if not token:
            return None
        payload = verify_session_token(token)
        if not payload:
            return None
        email = payload.get("email")
        if not email:
            return None
        return self.get_by_email(email)

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
