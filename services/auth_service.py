import os
import re
import json
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple

from services.security_utils import (
    validate_email,
    validate_name,
    validate_username,
    slugify_username,
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
from services.db import (
    get_db_session,
    is_db_available,
    UserDB,
    get_user_by_email,
    get_user_by_username,
    save_or_update_user,
    delete_user_by_email
)
from services.email_service import dispatch_email

logger = logging.getLogger(__name__)


def _safe_dispatch_email(email: str, subject: str, html_msg: str, plain_msg: str):
    """Safely dispatches email asynchronously or synchronously without blocking."""
    try:
        import asyncio
        loop = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            pass

        if loop and loop.is_running():
            asyncio.create_task(dispatch_email(email, subject, html_msg, plain_msg))
        else:
            try:
                asyncio.run(dispatch_email(email, subject, html_msg, plain_msg))
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Error in _safe_dispatch_email: {e}")


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")


def _ensure_users_file():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(USERS_FILE):
        hashed_pw, salt_hex = hash_password_secure("SafeAdminPass2026!")
        default_users = [
            {
                "email": "medo.msz.2006@gmail.com",
                "username": "mustafa-zaiter",
                "full_name": "Mustafa AbuZaiter",
                "role": "student",
                "salt": salt_hex,
                "password_hash": hashed_pw,
                "avatar_url": "",
                "cover_url": "",
                "city": "Gaza / Jerusalem",
                "university": "Faculty of Information Technology",
                "degree": "Undergraduate (Bachelor's)",
                "majors": ["Cybersecurity", "Software Engineering", "AI"],
                "graduation_year": "2027",
                "bio": "طالب هندسة برمجيات وأمن سيبراني مهتم بنظم الذكاء الاصطناعي وباحث عن منح دراسية دولية ممولة بالكامل.",
                "gpa": "90%+",
                "english_level": "IELTS 6.5+ / Advanced",
                "country": "Palestine",
                "talents_experience": "Full Stack Engineering, Cloud Security, AI Systems",
                "languages": [
                    {"name": "العربية", "level": "اللغة الأم"},
                    {"name": "English", "level": "Advanced (IELTS 6.5+)"}
                ],
                "skills": ["Python", "FastAPI", "Cybersecurity", "Machine Learning", "System Architecture", "React"],
                "interests": ["الذكاء الاصطناعي", "أمن المعلومات", "الحوسبة السحابية", "المنح الدولية"],
                "target_countries": ["Germany", "Canada", "Turkey", "United Kingdom", "Hungary"],
                "scholarship_interests": ["DAAD", "Chevening", "Stipendium Hungaricum", "Türkiye Bursları", "Lester B. Pearson"],
                "social_links": {
                    "whatsapp": "+970590000000",
                    "linkedin": "https://linkedin.com",
                    "github": "https://github.com",
                    "facebook": "",
                    "instagram": "",
                    "twitter": "",
                    "telegram": "",
                    "portfolio": "",
                    "website": ""
                },
                "saved_scholarships": ["Lester B. Pearson", "Stipendium Hungaricum"],
                "email_verified": True,
                "verification_code": "",
                "reset_token": "",
                "reset_token_expires": "",
                "privacy_settings": {
                    "public_profile": True,
                    "show_gpa": True,
                    "show_contact": True
                },
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        ]
        atomic_json_write(USERS_FILE, default_users)


class AuthService:
    """Authentication, Profile & Academic Identity Management Service."""

    def __init__(self):
        _ensure_users_file()

    def _normalize_user_dict(self, u: Dict[str, Any]) -> Dict[str, Any]:
        """Ensures all academic profile fields are present with sensible defaults."""
        email = u.get("email", "").lower()
        uname = u.get("username")
        if not uname:
            uname = slugify_username(u.get("full_name", ""), email)

        socials = u.get("social_links") or {}
        default_socials = {
            "whatsapp": "",
            "linkedin": "",
            "github": "",
            "facebook": "",
            "instagram": "",
            "twitter": "",
            "telegram": "",
            "portfolio": "",
            "website": ""
        }
        default_socials.update({k: v for k, v in socials.items() if k in default_socials and v})

        privacy = u.get("privacy_settings") or {}
        default_privacy = {
            "public_profile": True,
            "show_gpa": True,
            "show_contact": True
        }
        default_privacy.update({k: bool(v) for k, v in privacy.items() if k in default_privacy})

        # Ensure languages is in structured or list format
        raw_langs = u.get("languages", [])
        norm_langs = []
        for l in raw_langs:
            if isinstance(l, dict):
                norm_langs.append(l)
            elif isinstance(l, str) and l.strip():
                norm_langs.append({"name": l.strip(), "level": "Fluent"})

        return {
            "email": email,
            "username": uname,
            "full_name": u.get("full_name") or "Student",
            "role": u.get("role") or "student",
            "salt": u.get("salt", "00"),
            "password_hash": u.get("password_hash", ""),
            "avatar_url": u.get("avatar_url") or "",
            "cover_url": u.get("cover_url") or "",
            "city": u.get("city") or "",
            "university": u.get("university") or "",
            "degree": u.get("degree") or "Undergraduate (Bachelor's)",
            "majors": u.get("majors") or [],
            "graduation_year": str(u.get("graduation_year") or ""),
            "bio": u.get("bio") or "",
            "gpa": u.get("gpa") or "85%",
            "english_level": u.get("english_level") or "Intermediate",
            "country": u.get("country") or "Palestine",
            "talents_experience": u.get("talents_experience") or "",
            "languages": norm_langs,
            "skills": [str(s).strip() for s in u.get("skills", []) if str(s).strip()],
            "interests": [str(i).strip() for i in u.get("interests", []) if str(i).strip()],
            "target_countries": [str(c).strip() for c in (u.get("target_countries") or u.get("preferred_countries") or []) if str(c).strip()],
            "scholarship_interests": [str(s).strip() for s in u.get("scholarship_interests", []) if str(s).strip()],
            "social_links": default_socials,
            "saved_scholarships": u.get("saved_scholarships") or [],
            "preferred_countries": u.get("preferred_countries") or u.get("target_countries") or [],
            "funding_type": u.get("funding_type") or "Any",
            "email_notifications": u.get("email_notifications", True),
            "telegram_notifications": u.get("telegram_notifications", False),
            "telegram_chat_id": u.get("telegram_chat_id") or "",
            "email_verified": bool(u.get("email_verified", True if email == "medo.msz.2006@gmail.com" else False)),
            "verification_code": str(u.get("verification_code") or ""),
            "reset_token": str(u.get("reset_token") or ""),
            "reset_token_expires": str(u.get("reset_token_expires") or ""),
            "privacy_settings": default_privacy,
            "created_at": u.get("created_at") or datetime.now().isoformat(),
            "updated_at": u.get("updated_at") or datetime.now().isoformat()
        }

    def _load_users(self) -> List[Dict[str, Any]]:
        _ensure_users_file()
        if is_db_available():
            try:
                with get_db_session() as db:
                    if db is not None:
                        db_users = db.query(UserDB).all()
                        if db_users:
                            return [self._normalize_user_dict(u.to_dict()) for u in db_users]
            except Exception as e:
                logger.debug(f"DB load users failed, falling back to JSON: {e}")
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
                return [self._normalize_user_dict(u) for u in raw]
        except Exception as e:
            logger.error(f"Error loading users: {e}")
            return []

    def _save_users(self, users: List[Dict[str, Any]]):
        atomic_json_write(USERS_FILE, users)

    def generate_unique_username(self, full_name: str, email: str, current_email: Optional[str] = None) -> str:
        """Generates a non-conflicting unique handle slug for public profile URLs."""
        base_slug = slugify_username(full_name, email)
        users = self._load_users()
        current_clean = current_email.strip().lower() if current_email else None

        taken = {
            u.get("username", "").lower()
            for u in users
            if u.get("username") and (not current_clean or u.get("email", "").lower() != current_clean)
        }

        candidate = base_slug
        counter = 1
        while candidate in taken:
            counter += 1
            candidate = f"{base_slug}-{counter}"
        return candidate

    def register(
        self,
        email: str,
        password: str,
        full_name: str,
        username: Optional[str] = None,
        degree: str = "Undergraduate (Bachelor's)",
        majors: Optional[List[str]] = None,
        gpa: str = "85%",
        english_level: str = "Intermediate",
        country: str = "Palestine",
        city: str = "",
        university: str = "",
        graduation_year: str = "",
        bio: str = "",
        talents_experience: str = "",
        languages: Optional[List[Any]] = None,
        skills: Optional[List[str]] = None,
        interests: Optional[List[str]] = None,
        target_countries: Optional[List[str]] = None,
        scholarship_interests: Optional[List[str]] = None,
        social_links: Optional[Dict[str, str]] = None,
        privacy_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Registers a new student with complete academic profile and session token."""
        email_clean = validate_email(email)
        name_clean = validate_name(full_name)
        gpa_clean = validate_gpa(gpa)
        password_clean = validate_password(password)

        users = self._load_users()
        if any(u.get("email", "").lower() == email_clean for u in users):
            raise ValueError("هذا البريد الإلكتروني مسجل بالفعل. يمكنك تسجيل الدخول مباشرة.")

        # Resolve unique username
        if username and username.strip():
            candidate_uname = validate_username(username.strip())
            if any(u.get("username", "").lower() == candidate_uname for u in users):
                raise ValueError("اسم المستخدم هذا محجوز مسبقاً، يرجى اختيار اسم مستخدم آخر.")
            final_username = candidate_uname
        else:
            final_username = self.generate_unique_username(name_clean, email_clean)

        hashed_pw, salt_hex = hash_password_secure(password_clean)
        now_iso = datetime.now().isoformat()

        sanitized_majors = [sanitize_text(m, max_length=50) for m in (majors or ["Software Engineering"])]
        sanitized_degree = sanitize_text(degree, max_length=50) or "Undergraduate (Bachelor's)"
        sanitized_english = sanitize_text(english_level, max_length=50) or "Intermediate"
        sanitized_country = sanitize_text(country, max_length=50) or "Palestine"
        sanitized_city = sanitize_text(city, max_length=50) if city else ""
        sanitized_uni = sanitize_text(university, max_length=120) if university else ""
        sanitized_grad = sanitize_text(graduation_year, max_length=20) if graduation_year else ""
        sanitized_bio = sanitize_text(bio, max_length=500) if bio else ""
        sanitized_talents = sanitize_text(talents_experience, max_length=300) if talents_experience else ""

        # Initial 6-digit email verification code
        v_code = str(secrets.randbelow(900000) + 100000)

        new_user = {
            "email": email_clean,
            "username": final_username,
            "full_name": name_clean,
            "role": "student",
            "salt": salt_hex,
            "password_hash": hashed_pw,
            "avatar_url": "",
            "cover_url": "",
            "city": sanitized_city,
            "university": sanitized_uni,
            "degree": sanitized_degree,
            "majors": sanitized_majors,
            "graduation_year": sanitized_grad,
            "bio": sanitized_bio,
            "gpa": gpa_clean,
            "english_level": sanitized_english,
            "country": sanitized_country,
            "talents_experience": sanitized_talents,
            "languages": languages or [{"name": "العربية", "level": "اللغة الأم"}],
            "skills": skills or [],
            "interests": interests or [],
            "target_countries": target_countries or [sanitized_country],
            "scholarship_interests": scholarship_interests or [],
            "social_links": social_links or {
                "whatsapp": "",
                "linkedin": "",
                "github": "",
                "facebook": "",
                "instagram": "",
                "twitter": "",
                "telegram": "",
                "portfolio": "",
                "website": ""
            },
            "saved_scholarships": [],
            "preferred_countries": target_countries or [sanitized_country],
            "funding_type": "Any",
            "email_notifications": True,
            "telegram_notifications": False,
            "telegram_chat_id": "",
            "email_verified": False,
            "verification_code": v_code,
            "reset_token": "",
            "reset_token_expires": "",
            "privacy_settings": privacy_settings or {
                "public_profile": True,
                "show_gpa": True,
                "show_contact": True
            },
            "created_at": now_iso,
            "updated_at": now_iso
        }

        save_or_update_user(new_user)
        logger.info(f"Registered student user: {email_clean} with handle @{final_username}")

        # Issue 24-hour default session token
        token = create_session_token(email=email_clean, role="student", expires_in_seconds=86400)
        safe_copy = self.get_by_email(email_clean) or new_user
        safe_copy["session_token"] = token
        safe_copy["completeness"] = self.calculate_profile_completeness(safe_copy)
        return safe_copy

    def login(self, email: str, password: str, remember_me: bool = False) -> Optional[Dict[str, Any]]:
        """Authenticates user with PBKDF2 hash, lockout protection, and configurable session expiration."""
        try:
            email_clean = validate_email(email)
            password_clean = validate_password(password)
        except Exception:
            return None

        # Lockout check
        locked, remaining = security_rate_limiter.is_account_locked(email_clean)
        if locked:
            mins = max(1, remaining // 60)
            raise ValueError(f"تم قفل الحساب مؤقتاً بسبب كثرة محاولات الدخول الخاطئة. يرجى المحاولة بعد {mins} دقيقة.")

        user = get_user_by_email(email_clean)
        if not user:
            compute_dummy_pbkdf2(password_clean)
            security_rate_limiter.record_failed_login(email_clean)
            return None

        salt = user.get("salt", "")
        stored_hash = user.get("password_hash", "")

        is_valid, needs_rehash = verify_password_secure(password_clean, stored_hash, salt)

        if is_valid:
            security_rate_limiter.record_successful_login(email_clean)

            if needs_rehash:
                new_hash, new_salt = hash_password_secure(password_clean)
                user["password_hash"] = new_hash
                user["salt"] = new_salt
                save_or_update_user(user)
                logger.info(f"Auto-upgraded hash for {email_clean}")

            # Session expiration: 30 days if remember_me, else 24 hours
            expires_seconds = (30 * 86400) if remember_me else 86400
            token = create_session_token(
                email=email_clean,
                role=user.get("role", "student"),
                expires_in_seconds=expires_seconds
            )

            safe_copy = dict(user)
            safe_copy.pop("salt", None)
            safe_copy.pop("password_hash", None)
            safe_copy.pop("verification_code", None)
            safe_copy.pop("reset_token", None)
            safe_copy["session_token"] = token
            safe_copy["remember_me"] = remember_me
            safe_copy["expires_in_seconds"] = expires_seconds
            safe_copy["completeness"] = self.calculate_profile_completeness(safe_copy)
            return safe_copy

        security_rate_limiter.record_failed_login(email_clean)
        return None

    def forgot_password(self, email: str) -> Dict[str, Any]:
        """Generates a cryptographically secure 1-hour reset token and dispatches reset notification."""
        try:
            email_clean = validate_email(email)
        except Exception as e:
            raise ValueError(str(e))

        user = get_user_by_email(email_clean)
        if not user:
            # Defuse user enumeration side channel
            compute_dummy_pbkdf2("dummy_timing_shield")
            return {
                "success": True,
                "message": "إذا كان هذا البريد مسجلاً لدينا، فستصلك تعليمات استعادة كلمة المرور فوراً."
            }

        # Issue 1-hour secure reset token
        reset_token = secrets.token_hex(20)
        expires_at = (datetime.now() + timedelta(hours=1)).isoformat()

        user["reset_token"] = reset_token
        user["reset_token_expires"] = expires_at
        save_or_update_user(user)

        # Dispatch reset email
        subject = "استعادة كلمة المرور - ScholarPilot AI"
        html_msg = f"""
        <div dir="rtl" style="font-family: Arial, sans-serif; padding: 20px; color: #1e293b;">
            <h2>طلب استعادة كلمة المرور</h2>
            <p>مرحباً {user.get('full_name', 'طالبنا العزيز')},</p>
            <p>تلقينا طلباً لإعادة تعيين كلمة المرور لحسابك في ScholarPilot AI.</p>
            <div style="background: #f1f5f9; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 0; font-size: 14px; font-weight: bold;">رمز استعادة كلمة المرور الخاص بك:</p>
                <p style="font-size: 24px; font-weight: bold; letter-spacing: 2px; color: #2563eb; margin: 10px 0;">{reset_token}</p>
                <p style="margin: 0; font-size: 12px; color: #64748b;">هذا الرمز صالح لمدة 60 دقيقة فقط.</p>
            </div>
            <p>إذا لم تكن أنت من طلب ذلك، يمكنك تجاهل هذه الرسالة وسيبقى حسابك آمناً.</p>
        </div>
        """
        plain_msg = f"رمز استعادة كلمة المرور لحسابك في ScholarPilot AI هو: {reset_token}\nصالح لمدة 60 دقيقة."
        try:
            _safe_dispatch_email(email_clean, subject, html_msg, plain_msg)
        except Exception as e:
            logger.warning(f"Error dispatching reset email: {e}")

        logger.info(f"Password reset token generated for: {email_clean}")
        return {
            "success": True,
            "message": "تم إرسال رمز استعادة كلمة المرور إلى بريدك الإلكتروني.",
            "reset_token": reset_token  # returned for testing/local automation
        }

    def reset_password(self, email: str, token: str, new_password: str) -> bool:
        """Verifies reset token validity & expiry, then updates password PBKDF2 hash."""
        email_clean = validate_email(email)
        clean_new_pw = validate_password(new_password)
        clean_token = (token or "").strip()

        if not clean_token:
            raise ValueError("رمز الاستعادة مطلوب.")

        user = get_user_by_email(email_clean)
        if not user:
            raise ValueError("الحساب غير مسجل.")

        stored_token = user.get("reset_token", "")
        expires_str = user.get("reset_token_expires", "")

        if not stored_token or not secrets.compare_digest(stored_token, clean_token):
            raise ValueError("رمز الاستعادة غير صحيح أو غير صالح.")

        if expires_str:
            try:
                exp_dt = datetime.fromisoformat(expires_str)
                if datetime.now() > exp_dt:
                    raise ValueError("انتهت صلاحية رمز استعادة كلمة المرور. يرجى طلب رمز جديد.")
            except Exception:
                pass

        # Hash new password
        new_hash, new_salt = hash_password_secure(clean_new_pw)
        user["password_hash"] = new_hash
        user["salt"] = new_salt
        user["reset_token"] = ""
        user["reset_token_expires"] = ""
        save_or_update_user(user)

        logger.info(f"Password reset successful for {email_clean}")
        return True

    def send_verification_email(self, email: str) -> Dict[str, Any]:
        """Issues 6-digit code for student email verification."""
        email_clean = validate_email(email)
        user = get_user_by_email(email_clean)
        if not user:
            raise ValueError("الحساب غير مسجل.")

        if user.get("email_verified"):
            return {"success": True, "message": "البريد الإلكتروني موثق بالفعل."}

        code = str(secrets.randbelow(900000) + 100000)
        user["verification_code"] = code
        save_or_update_user(user)

        subject = "تأكيد وتوثيق بريدك الأكاديمي - ScholarPilot AI"
        html_msg = f"""
        <div dir="rtl" style="font-family: Arial, sans-serif; padding: 20px; color: #1e293b;">
            <h2>رمز تأكيد البريد الإلكتروني</h2>
            <p>مرحباً {user.get('full_name', 'طالبنا العزيز')},</p>
            <p>لتأكيد بريدك الإلكتروني وتفعيل الإشعارات وتوثيق ملفك الأكاديمي، أدخل الرمز التالي:</p>
            <div style="background: #eff6ff; padding: 15px; border-radius: 8px; margin: 20px 0; text-align: center;">
                <span style="font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #2563eb;">{code}</span>
            </div>
            <p style="font-size: 12px; color: #64748b;">ينتهي الرمز خلال 24 ساعة.</p>
        </div>
        """
        plain_msg = f"رمز تأكيد بريدك في ScholarPilot AI هو: {code}"
        try:
            _safe_dispatch_email(email_clean, subject, html_msg, plain_msg)
        except Exception as e:
            logger.warning(f"Error dispatching verification email: {e}")

        return {
            "success": True,
            "message": "تم إرسال كود التحقق إلى بريدك الإلكتروني.",
            "code": code
        }

    def verify_email(self, email: str, code: str) -> bool:
        """Verifies 6-digit email code and marks account as verified."""
        email_clean = validate_email(email)
        clean_code = (code or "").strip()

        user = get_user_by_email(email_clean)
        if not user:
            raise ValueError("الحساب غير مسجل.")

        stored_code = str(user.get("verification_code") or "").strip()
        if not stored_code or stored_code != clean_code:
            raise ValueError("كود التحقق غير صحيح. يرجى التأكد من الرمز المدخل.")

        user["email_verified"] = True
        user["verification_code"] = ""
        save_or_update_user(user)
        logger.info(f"Email verified for {email_clean}")

        # Dispatch account verification notification
        try:
            from services.notification_service import notification_service
            notification_service.notify_account_verification(email_clean)
        except Exception as ne:
            logger.warning(f"Verification notification error: {ne}")

        return True

    def calculate_profile_completeness(self, user_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates profile completion percentage (0-100%)
        with concrete actionable nudges for missing attributes.
        """
        u = self._normalize_user_dict(user_dict)
        score = 0
        missing = []

        # 1. Full Name (10%)
        if u.get("full_name") and len(u["full_name"].strip()) >= 3:
            score += 10
        else:
            missing.append({"field": "full_name", "weight": 10, "text": "إدخال الاسم الكامل الثلاثي (+10%)"})

        # 2. Profile Photo / Avatar (10%)
        if u.get("avatar_url") and len(u["avatar_url"].strip()) > 5:
            score += 10
        else:
            missing.append({"field": "avatar_url", "weight": 10, "text": "إضافة صورة شخصية احترافية (+10%)"})

        # 3. University & Degree (15%)
        has_degree = bool(u.get("degree"))
        has_uni = bool(u.get("university") and len(u["university"].strip()) >= 3)
        if has_degree and has_uni:
            score += 15
        elif has_degree or has_uni:
            score += 8
            missing.append({"field": "university", "weight": 7, "text": "تحديد الجامعة والمرحلة الدراسية (+7%)"})
        else:
            missing.append({"field": "university", "weight": 15, "text": "إضافة الجامعة والدرجة العلمية المستهدفة (+15%)"})

        # 4. Major (10%)
        if u.get("majors") and len(u["majors"]) > 0:
            score += 10
        else:
            missing.append({"field": "majors", "weight": 10, "text": "تحديد التخصص الأكاديمي (+10%)"})

        # 5. Country & City (10%)
        has_country = bool(u.get("country"))
        has_city = bool(u.get("city") and len(u["city"].strip()) >= 2)
        if has_country and has_city:
            score += 10
        elif has_country:
            score += 5
            missing.append({"field": "city", "weight": 5, "text": "إضافة مدينتك الحالية (+5%)"})
        else:
            missing.append({"field": "country", "weight": 10, "text": "تحديد بلد الإقامة والمدينة (+10%)"})

        # 6. Biography / About Me (10%)
        if u.get("bio") and len(u["bio"].strip()) >= 15:
            score += 10
        else:
            missing.append({"field": "bio", "weight": 10, "text": "كتابة نبذة أكاديمية عن طموحك واهتماماتك (+10%)"})

        # 7. Skills & Languages (15%)
        skills_count = len(u.get("skills", []))
        langs_count = len(u.get("languages", []))
        if skills_count >= 2 and langs_count >= 1:
            score += 15
        elif skills_count >= 1 or langs_count >= 1:
            score += 8
            missing.append({"field": "skills", "weight": 7, "text": "إضافة مهاراتك ولغاتك التي تتقنها (+7%)"})
        else:
            missing.append({"field": "skills", "weight": 15, "text": "إضافة المهارات واللغات (+15%)"})

        # 8. Target Countries & Scholarship Interests (10%)
        target_c = len(u.get("target_countries", []))
        sch_i = len(u.get("scholarship_interests", []))
        if target_c >= 1 and sch_i >= 1:
            score += 10
        elif target_c >= 1 or sch_i >= 1:
            score += 5
            missing.append({"field": "scholarship_interests", "weight": 5, "text": "تحديد وجهات الابتعاث والمنح المفضلة (+5%)"})
        else:
            missing.append({"field": "target_countries", "weight": 10, "text": "تحديد وجهات الابتعاث والمنح المفضلة (+10%)"})

        # 9. Professional Social Link (10%)
        socials = u.get("social_links") or {}
        has_social = any(bool(str(v).strip()) for v in socials.values() if isinstance(v, str))
        if has_social:
            score += 10
        else:
            missing.append({"field": "social_links", "weight": 10, "text": "إضافة رابط حسابك المهني (LinkedIn أو GitHub) (+10%)"})

        score = min(100, max(0, score))

        if score >= 90:
            badge = "ملف أكاديمي مكتمل ومثالي"
        elif score >= 70:
            badge = "ملف متقدم وجاهز للمطابقة"
        elif score >= 40:
            badge = "ملف متوسط بحاجة لبيانات إضافية"
        else:
            badge = "ملف أولي قيد الإعداد"

        return {
            "percentage": score,
            "badge": badge,
            "missing_fields": missing,
            "is_complete": score >= 90,
            "nudge_message": "الملفات الأكثر اكتمالاً تحصل على ترشيحات منح أدق وأسرع"
        }

    def update_profile(self, email: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Updates user profile with validation, handle uniqueness check, and completeness evaluation."""
        email_clean = validate_email(email)
        user = get_user_by_email(email_clean)
        if not user:
            raise ValueError("الحساب غير موجود.")

        # If username is changing, ensure uniqueness
        if "username" in profile_data and profile_data["username"]:
            new_uname = validate_username(profile_data["username"])
            if new_uname != user.get("username", "").lower():
                existing = get_user_by_username(new_uname)
                if existing and existing.get("email", "").lower() != email_clean:
                    raise ValueError("اسم المستخدم هذا محجوز مسبقاً من قبل طالب آخر.")
                user["username"] = new_uname

        # Update basic info
        if "full_name" in profile_data and profile_data["full_name"]:
            user["full_name"] = validate_name(profile_data["full_name"])

        if "avatar_url" in profile_data:
            user["avatar_url"] = sanitize_text(profile_data["avatar_url"], max_length=500)
        if "cover_url" in profile_data:
            user["cover_url"] = sanitize_text(profile_data["cover_url"], max_length=500)
        if "city" in profile_data:
            user["city"] = sanitize_text(profile_data["city"], max_length=60)
        if "university" in profile_data:
            user["university"] = sanitize_text(profile_data["university"], max_length=120)
        if "degree" in profile_data and profile_data["degree"]:
            user["degree"] = sanitize_text(profile_data["degree"], max_length=60)
        if "graduation_year" in profile_data:
            user["graduation_year"] = sanitize_text(str(profile_data["graduation_year"]), max_length=20)
        if "bio" in profile_data:
            user["bio"] = sanitize_text(profile_data["bio"], max_length=600)
        if "country" in profile_data and profile_data["country"]:
            user["country"] = sanitize_text(profile_data["country"], max_length=60)
        if "english_level" in profile_data:
            user["english_level"] = sanitize_text(profile_data["english_level"], max_length=60)
        if "gpa" in profile_data and profile_data["gpa"]:
            user["gpa"] = validate_gpa(profile_data["gpa"])

        # Update lists
        if "majors" in profile_data and isinstance(profile_data["majors"], list):
            user["majors"] = [sanitize_text(m, max_length=50) for m in profile_data["majors"] if str(m).strip()][:8]

        if "skills" in profile_data and isinstance(profile_data["skills"], list):
            user["skills"] = [sanitize_text(s, max_length=40) for s in profile_data["skills"] if str(s).strip()][:25]

        if "interests" in profile_data and isinstance(profile_data["interests"], list):
            user["interests"] = [sanitize_text(i, max_length=50) for i in profile_data["interests"] if str(i).strip()][:20]

        if "target_countries" in profile_data and isinstance(profile_data["target_countries"], list):
            clean_targets = [sanitize_text(c, max_length=40) for c in profile_data["target_countries"] if str(c).strip()][:15]
            user["target_countries"] = clean_targets
            user["preferred_countries"] = clean_targets

        if "scholarship_interests" in profile_data and isinstance(profile_data["scholarship_interests"], list):
            user["scholarship_interests"] = [sanitize_text(s, max_length=60) for s in profile_data["scholarship_interests"] if str(s).strip()][:15]

        if "languages" in profile_data and isinstance(profile_data["languages"], list):
            norm_langs = []
            for l in profile_data["languages"][:10]:
                if isinstance(l, dict):
                    name = sanitize_text(l.get("name", ""), max_length=30)
                    level = sanitize_text(l.get("level", ""), max_length=30)
                    if name:
                        norm_langs.append({"name": name, "level": level or "Intermediate"})
                elif isinstance(l, str) and l.strip():
                    norm_langs.append({"name": sanitize_text(l, max_length=30), "level": "Fluent"})
            user["languages"] = norm_langs

        # Social links
        if "social_links" in profile_data and isinstance(profile_data["social_links"], dict):
            current_socials = user.get("social_links") or {}
            allowed = ["whatsapp", "linkedin", "github", "facebook", "instagram", "twitter", "telegram", "portfolio", "website"]
            for k in allowed:
                if k in profile_data["social_links"]:
                    val = str(profile_data["social_links"][k] or "").strip()
                    current_socials[k] = sanitize_text(val, max_length=200)
            user["social_links"] = current_socials

        # Privacy settings
        if "privacy_settings" in profile_data and isinstance(profile_data["privacy_settings"], dict):
            curr_privacy = user.get("privacy_settings") or {}
            for k in ["public_profile", "show_gpa", "show_contact"]:
                if k in profile_data["privacy_settings"]:
                    curr_privacy[k] = bool(profile_data["privacy_settings"][k])
            user["privacy_settings"] = curr_privacy

        user["updated_at"] = datetime.now().isoformat()
        save_or_update_user(user)

        normalized = self._normalize_user_dict(user)
        completeness = self.calculate_profile_completeness(normalized)
        normalized["completeness"] = completeness

        # Dispatch profile completion milestone notification
        try:
            from services.notification_service import notification_service
            notification_service.notify_profile_completion(email_clean, completeness.get("percentage", 0))
        except Exception as ne:
            logger.warning(f"Profile completion notification error: {ne}")

        normalized.pop("salt", None)
        normalized.pop("password_hash", None)
        normalized.pop("verification_code", None)
        normalized.pop("reset_token", None)
        return normalized

    def change_password(self, email: str, current_password: str, new_password: str) -> bool:
        """Changes user password after strictly validating current password."""
        email_clean = validate_email(email)
        clean_new_pw = validate_password(new_password)

        user = get_user_by_email(email_clean)
        if not user:
            raise ValueError("الحساب غير موجود.")

        salt = user.get("salt", "")
        stored_hash = user.get("password_hash", "")

        is_valid, _ = verify_password_secure(current_password, stored_hash, salt)
        if not is_valid:
            raise ValueError("كلمة المرور الحالية غير صحيحة.")

        new_hash, new_salt = hash_password_secure(clean_new_pw)
        user["password_hash"] = new_hash
        user["salt"] = new_salt
        save_or_update_user(user)
        logger.info(f"Password changed successfully for {email_clean}")
        return True

    def delete_account(self, email: str, password: str) -> bool:
        """Permanently deletes account and matching preferences upon password confirmation."""
        email_clean = validate_email(email)
        user = get_user_by_email(email_clean)
        if not user:
            raise ValueError("الحساب غير موجود.")

        salt = user.get("salt", "")
        stored_hash = user.get("password_hash", "")
        is_valid, _ = verify_password_secure(password, stored_hash, salt)
        if not is_valid:
            raise ValueError("كلمة المرور غير صحيحة لتأكيد حذف الحساب.")

        delete_user_by_email(email_clean)
        logger.info(f"Account permanently deleted: {email_clean}")
        return True

    def get_public_profile(self, username_or_email: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves public student academic identity portfolio for `/profile/{username}`,
        respecting student privacy preferences.
        """
        clean_key = (username_or_email or "").strip().lower()
        if not clean_key:
            return None

        users = self._load_users()
        user = next((
            u for u in users
            if u.get("username", "").lower() == clean_key
            or u.get("email", "").lower() == clean_key
            or (u.get("email", "").split("@")[0].lower() == clean_key)
        ), None)

        if not user:
            return None

        normalized = self._normalize_user_dict(user)
        privacy = normalized.get("privacy_settings", {})
        is_public = privacy.get("public_profile", True)

        if not is_public:
            return {
                "is_private": True,
                "username": normalized.get("username"),
                "full_name": normalized.get("full_name"),
                "university": normalized.get("university"),
                "degree": normalized.get("degree"),
                "country": normalized.get("country"),
                "badge": "ملف أكاديمي خاص"
            }

        completeness = self.calculate_profile_completeness(normalized)

        # Filter social links to only non-empty ones
        public_socials = {
            k: v for k, v in normalized.get("social_links", {}).items()
            if isinstance(v, str) and v.strip()
        }

        headline = f"{normalized.get('degree', 'Student')} • {normalized.get('university', 'ScholarPilot')}"

        return {
            "is_private": False,
            "username": normalized.get("username"),
            "full_name": normalized.get("full_name"),
            "headline": headline,
            "avatar_url": normalized.get("avatar_url"),
            "cover_url": normalized.get("cover_url"),
            "city": normalized.get("city"),
            "country": normalized.get("country"),
            "university": normalized.get("university"),
            "degree": normalized.get("degree"),
            "majors": normalized.get("majors"),
            "graduation_year": normalized.get("graduation_year"),
            "bio": normalized.get("bio"),
            "gpa": normalized.get("gpa") if privacy.get("show_gpa", True) else None,
            "english_level": normalized.get("english_level"),
            "skills": normalized.get("skills"),
            "languages": normalized.get("languages"),
            "target_countries": normalized.get("target_countries"),
            "scholarship_interests": normalized.get("scholarship_interests"),
            "social_links": public_socials if privacy.get("show_contact", True) else {},
            "email_verified": normalized.get("email_verified"),
            "completeness_score": completeness.get("percentage", 100),
            "completeness_badge": completeness.get("badge", "ملف موثق"),
            "created_at": normalized.get("created_at")
        }

    def authenticate_token(self, token: Optional[str]) -> Optional[Dict[str, Any]]:
        """Verifies session token and returns full student profile with completeness metrics."""
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
        """Finds user by email with complete normalized attributes."""
        try:
            email_clean = validate_email(email)
        except Exception:
            return None

        user = get_user_by_email(email_clean)
        if user:
            norm = self._normalize_user_dict(user)
            norm.pop("salt", None)
            norm.pop("password_hash", None)
            norm.pop("verification_code", None)
            norm.pop("reset_token", None)
            norm["completeness"] = self.calculate_profile_completeness(norm)
            return norm
        return None

    def list_all_users(self) -> List[Dict[str, Any]]:
        """Returns safe user list for Admin Dashboard."""
        users = self._load_users()
        safe_list = []
        for u in users:
            c = self._normalize_user_dict(u)
            c.pop("salt", None)
            c.pop("password_hash", None)
            c.pop("verification_code", None)
            c.pop("reset_token", None)
            c["completeness"] = self.calculate_profile_completeness(c)
            safe_list.append(c)
        return safe_list
