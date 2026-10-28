import os
import re
import html
import time
import json
import zlib
import base64
import hmac
import hashlib
import secrets
import threading
import logging
from typing import Optional, Dict, Any, Tuple, List

logger = logging.getLogger(__name__)

# ==============================================================================
# 0. DYNAMIC CRYPTOGRAPHIC SECRET MANAGEMENT
# ==============================================================================

def _get_or_create_app_secret() -> str:
    """
    Retrieves or generates an uncompromising 256-bit cryptographically secure secret.
    Eliminates reliance on hardcoded default strings in open-source repositories.
    """
    env_secret = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET")
    if env_secret and len(env_secret.strip()) >= 32:
        return env_secret.strip()

    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    os.makedirs(data_dir, exist_ok=True)
    secret_file = os.path.join(data_dir, ".app_secret")

    if os.path.exists(secret_file):
        try:
            with open(secret_file, "r", encoding="utf-8") as f:
                saved = f.read().strip()
                if len(saved) >= 32:
                    return saved
        except Exception as e:
            logger.debug(f"Could not read existing secret file: {e}")

    new_secret = secrets.token_hex(32)
    try:
        with open(secret_file, "w", encoding="utf-8") as f:
            f.write(new_secret)
    except Exception as e:
        logger.warning(f"Could not persist dynamic secret file: {e}")

    return new_secret

APP_SECRET_KEY = _get_or_create_app_secret()

# Global File Lock for thread-safe atomic data operations
_file_io_lock = threading.Lock()

def atomic_json_write(filepath: str, data: Any):
    """
    Thread-safe, crash-resilient atomic file write pattern:
    Writes to a randomized temporary file in the same directory, flushes,
    and replaces the target file atomically to eliminate race conditions and corruption.
    """
    dir_name = os.path.dirname(filepath)
    os.makedirs(dir_name, exist_ok=True)
    tmp_path = os.path.join(dir_name, f".{os.path.basename(filepath)}.{secrets.token_hex(4)}.tmp")

    with _file_io_lock:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
        os.replace(tmp_path, filepath)


# ==============================================================================
# 1. REGEX PATTERNS & SANITIZATION FILTERS
# ==============================================================================

EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)

NAME_REGEX = re.compile(r"^[\u0600-\u06FFa-zA-Z\s\.\-']{2,70}$")

SQL_INJECTION_PATTERN = re.compile(
    r"(\b(UNION|SELECT|INSERT|DELETE|UPDATE|DROP|ALTER|EXEC|EXECUTE|SCRIPT|CREATE|TRUNCATE)\b|"
    r"(--|/\*|\*/|@@|char\s*\(|nchar\s*\(|varchar\s*\(|cast\s*\(|convert\s*\())",
    re.IGNORECASE
)

SCRIPT_TAG_PATTERN = re.compile(
    r"<[^>]*>|javascript:|data:text/html|vbscript:|onerror|onload|onclick|onmouseover|eval\(|document\.cookie",
    re.IGNORECASE
)

# Invisible Unicode control characters and BiDi override markers (Trojan Source / RTL attack defense)
BIDI_AND_INVISIBLE_CHARS = re.compile(r"[\u200B-\u200F\u202A-\u202E\u2060-\u206F\uFEFF]")

COMMON_WEAK_PASSWORDS = {
    "password", "password1", "12345678", "123456789", "qwerty123",
    "admin123", "administrator", "iloveyou", "welcome1", "pass1234",
    "abcdef12", "00000000", "11111111", "test1234", "master12"
}


def sanitize_text(val: Optional[str], max_length: int = 150) -> str:
    """Strips dangerous HTML/script tags, Bidi overrides, control chars, and limits length."""
    if val is None:
        return ""

    clean = str(val).strip()
    clean = BIDI_AND_INVISIBLE_CHARS.sub("", clean)
    clean = "".join(ch for ch in clean if ch.isprintable() or ch in "\n\r\t")
    clean = SCRIPT_TAG_PATTERN.sub("", clean)
    clean = clean.replace("\x00", "")

    if len(clean) > max_length:
        clean = clean[:max_length]

    clean = html.escape(clean, quote=True)
    return clean.strip()


def validate_email(email_str: str) -> str:
    """Strict RFC 5322 subset validation."""
    if not email_str:
        raise ValueError("البريد الإلكتروني مطلوب ولا يمكن تركه فارغاً.")

    clean = BIDI_AND_INVISIBLE_CHARS.sub("", email_str).strip().lower()

    if len(clean) > 100:
        raise ValueError("البريد الإلكتروني طويل جداً (الحد الأقصى 100 حرف).")

    if " " in clean or "\n" in clean or "\r" in clean or "\t" in clean:
        raise ValueError("البريد الإلكتروني لا يمكن أن يحتوي على مسافات أو أسطر جديدة.")

    if not EMAIL_REGEX.match(clean):
        raise ValueError("صيغة البريد الإلكتروني غير صالحة. يرجى إدخال إيميل صحيح (مثال: name@example.com).")

    return clean


def validate_name(name_str: str) -> str:
    """Validates real Arabic/English name without script injection or control chars."""
    if not name_str:
        return "Student"

    clean = BIDI_AND_INVISIBLE_CHARS.sub("", name_str).strip()

    if SCRIPT_TAG_PATTERN.search(clean) or SQL_INJECTION_PATTERN.search(clean):
        raise ValueError("الاسم يحتوي على رموز أو مدخلات غير مسموح بها أمنياً.")

    clean = re.sub(r"\s+", " ", clean)

    if len(clean) < 2:
        raise ValueError("الاسم قصير جداً (يجب أن يتكون من حرفين على الأقل).")

    if len(clean) > 60:
        clean = clean[:60]

    if not NAME_REGEX.match(clean):
        raise ValueError("يرجى إدخال اسم حقيقي يحتوي على أحرف عربية أو إنجليزية فقط دون رموز خاصة.")

    return html.escape(clean, quote=True)


def validate_gpa(gpa_str: str) -> str:
    """Validates academic GPA strictly to prevent any code or arbitrary text."""
    if not gpa_str:
        return "85%"

    clean = BIDI_AND_INVISIBLE_CHARS.sub("", gpa_str).strip()

    if SCRIPT_TAG_PATTERN.search(clean) or SQL_INJECTION_PATTERN.search(clean):
        raise ValueError("حقل المعدل يحتوي على رموز غير مسموح بها أمنياً.")

    accepted_terms = ["امتياز", "جيد جدا", "جيد جداً", "ممتاز", "جيد", "مقبول"]
    if clean in accepted_terms:
        return clean

    if re.search(r"[a-zA-Z\u0600-\u06FF]", clean):
        raise ValueError("حقل المعدل يجب أن يحتوي على أرقام فقط (مثلاً: 88% أو 3.6/4.0) ويمنع إدخال نصوص أو أحرف عشوائية.")

    if not re.match(r"^[0-9\.\s%/]+$", clean):
        raise ValueError("حقل المعدل يحتوي على رموز خاصة غير مقبولة.")

    pct_match = re.search(r"^(\d{2,3}(?:\.\d{1,2})?)\s*%?$", clean)
    if pct_match:
        val = float(pct_match.group(1))
        if 40.0 <= val <= 100.0:
            return f"{val:.1f}%".replace(".0%", "%")
        else:
            raise ValueError(f"المعدل المئوي ({val}%) غير منطقي. يجب أن يكون بين 40% و 100%.")

    scale_match = re.search(r"^([1-5](?:\.\d{1,2})?)(?:\s*/\s*([45](?:\.0)?))?$", clean)
    if scale_match:
        val = float(scale_match.group(1))
        scale = float(scale_match.group(2)) if scale_match.group(2) else 4.0
        if 1.5 <= val <= scale:
            return f"{val}/{int(scale)}"

    raise ValueError("صيغة المعدل غير صحيحة. يرجى إدخال أرقام فقط (مثال: 88% أو 3.6/4.0).")


def validate_talents_experience(val: Optional[str]) -> str:
    """Sanitizes extracurricular activities and achievements."""
    if not val:
        return ""
    return sanitize_text(val, max_length=400)


def validate_password(password_str: str) -> str:
    """Enforces 8+ characters, letters + numbers, and rejects dictionary passwords."""
    if not password_str:
        raise ValueError("كلمة المرور مطلوبة.")

    clean_pw = password_str.strip()

    if len(clean_pw) < 8:
        raise ValueError("كلمة المرور يجب أن لا تقل عن 8 أحرف لضمان الأمان الأكاديمي.")

    if len(clean_pw) > 128:
        raise ValueError("كلمة المرور طويلة جداً (الحد الأقصى 128 حرف).")

    if not re.search(r"[a-zA-Z]", clean_pw):
        raise ValueError("كلمة المرور يجب أن تحتوي على حرف واحد على الأقل.")

    if not re.search(r"[0-9]", clean_pw):
        raise ValueError("كلمة المرور يجب أن تحتوي على رقم واحد على الأقل.")

    if clean_pw.lower() in COMMON_WEAK_PASSWORDS:
        raise ValueError("كلمة المرور شائعة جداً وسهلة التخمين. يرجى اختيار كلمة مرور أقوى.")

    return clean_pw


def sanitize_email_header(val: Optional[str], max_length: int = 150) -> str:
    """Strips CRLF and null characters to prevent header injection."""
    if not val:
        return ""
    clean = str(val).replace("\r", " ").replace("\n", " ").replace("\x00", "")
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:max_length]


# ==============================================================================
# 2. CRYPTOGRAPHIC PASSWORD HASHING (PBKDF2-HMAC-SHA256 & TIMING SHIELD)
# ==============================================================================

PBKDF2_ROUNDS = 600_000
DUMMY_SALT = b"\x1b\x9e\x74\x40\x1f\x92\xa8\x72\xce\x10\x55\x8b\x3c\x84\x22\x01"

def hash_password_secure(password: str, salt_hex: Optional[str] = None) -> Tuple[str, str]:
    """Computes PBKDF2-HMAC-SHA256 hash with 600,000 rounds."""
    if not salt_hex:
        salt_bytes = secrets.token_bytes(16)
        salt_hex = salt_bytes.hex()
    else:
        salt_bytes = bytes.fromhex(salt_hex)

    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, PBKDF2_ROUNDS)
    formatted_hash = f"pbkdf2:sha256:{PBKDF2_ROUNDS}${salt_hex}${derived.hex()}"
    return formatted_hash, salt_hex


def verify_password_secure(password: str, stored_hash: str, salt: str) -> Tuple[bool, bool]:
    """Verifies password in constant-time; supports automatic migration from legacy SHA-256."""
    if not stored_hash or not password:
        return False, False

    if stored_hash.startswith("pbkdf2:sha256:"):
        try:
            parts = stored_hash.split("$")
            if len(parts) != 3:
                return False, False
            header_part, salt_hex, expected_hex = parts
            rounds = int(header_part.split(":")[-1])
            salt_bytes = bytes.fromhex(salt_hex)

            computed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, rounds).hex()
            is_valid = secrets.compare_digest(computed, expected_hex)
            needs_rehash = (rounds < PBKDF2_ROUNDS)
            return is_valid, needs_rehash
        except Exception as e:
            logger.error(f"Error verifying PBKDF2 hash: {e}")
            return False, False

    try:
        legacy_computed = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
        if secrets.compare_digest(legacy_computed, stored_hash):
            return True, True
    except Exception as e:
        logger.error(f"Error checking legacy hash: {e}")

    return False, False


def compute_dummy_pbkdf2(password: str):
    """
    Executes an identical 600,000 iteration PBKDF2 calculation on non-existent users.
    Eliminates side-channel timing discrepancies that permit user enumeration.
    """
    try:
        hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), DUMMY_SALT, PBKDF2_ROUNDS)
    except Exception:
        pass


# ==============================================================================
# 3. SECURE SESSION TOKENS
# ==============================================================================

def create_session_token(email: str, role: str = "student", expires_in_seconds: int = 7 * 86400) -> str:
    """Generates a cryptographically signed HMAC-SHA256 session token."""
    payload = {
        "email": email.strip().lower(),
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + expires_in_seconds,
        "nonce": secrets.token_hex(8)
    }
    payload_json = json.dumps(payload, separators=(',', ':'))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("utf-8").rstrip("=")

    signature = hmac.new(
        APP_SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    return f"{payload_b64}.{signature}"


def verify_session_token(token: Optional[str]) -> Optional[Dict[str, Any]]:
    """Verifies HMAC signature and expiration."""
    if not token or "." not in token:
        return None

    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, signature = parts

        expected_sig = hmac.new(
            APP_SECRET_KEY.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        if not secrets.compare_digest(signature, expected_sig):
            return None

        padding = "=" * (-len(payload_b64) % 4)
        payload_json = base64.urlsafe_b64decode((payload_b64 + padding).encode("utf-8")).decode("utf-8")
        payload = json.loads(payload_json)

        if time.time() > payload.get("exp", 0):
            return None

        return payload
    except Exception:
        return None


# ==============================================================================
# 4. MEMORY-SAFE RATE LIMITER & SPOOFING DEFENSE
# ==============================================================================

class SecurityRateLimiter:
    """
    Sliding-window rate limiter with memory self-pruning and anti-spoofing defense.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._requests: Dict[str, List[float]] = {}
        self._failed_logins: Dict[str, List[float]] = {}
        self._email_cooldowns: Dict[str, float] = {}
        self._check_counter: int = 0

        self.LIMITS = {
            "auth": (10, 60),
            "advisor": (25, 60),
            "subscribe": (6, 60),
            "upload": (8, 60),
            "general": (120, 60),
        }

    def _prune_expired_entries(self, now: float):
        """Sweeps stale buckets to prevent memory accumulation / Slowloris memory leaks."""
        expired_req_keys = []
        for k, v in self._requests.items():
            cat = k.split(":")[-1] if ":" in k else "general"
            window = self.LIMITS.get(cat, self.LIMITS["general"])[1]
            valid = [ts for ts in v if ts > (now - window)]
            if not valid:
                expired_req_keys.append(k)
            else:
                self._requests[k] = valid
        for k in expired_req_keys:
            self._requests.pop(k, None)

        expired_login_keys = [k for k, v in self._failed_logins.items() if not any(ts > (now - 900) for ts in v)]
        for k in expired_login_keys:
            self._failed_logins.pop(k, None)

        expired_email_keys = [k for k, ts in self._email_cooldowns.items() if now - ts > 3600]
        for k in expired_email_keys:
            self._email_cooldowns.pop(k, None)

    def check_rate_limit(self, client_ip: str, category: str = "general") -> Tuple[bool, int]:
        max_reqs, window = self.LIMITS.get(category, self.LIMITS["general"])
        key = f"{client_ip}:{category}"
        now = time.time()

        with self._lock:
            self._check_counter += 1
            if self._check_counter >= 80:
                self._prune_expired_entries(now)
                self._check_counter = 0

            history = self._requests.get(key, [])
            valid_from = now - window
            history = [ts for ts in history if ts > valid_from]

            if len(history) >= max_reqs:
                oldest = history[0]
                retry_after = max(1, int(window - (now - oldest)))
                self._requests[key] = history
                return False, retry_after

            history.append(now)
            self._requests[key] = history
            return True, 0

    def record_failed_login(self, identifier: str) -> int:
        now = time.time()
        window = 900
        with self._lock:
            history = self._failed_logins.get(identifier, [])
            history = [ts for ts in history if ts > (now - window)]
            history.append(now)
            self._failed_logins[identifier] = history
            return len(history)

    def is_account_locked(self, identifier: str, max_failures: int = 5) -> Tuple[bool, int]:
        now = time.time()
        window = 900
        with self._lock:
            history = self._failed_logins.get(identifier, [])
            history = [ts for ts in history if ts > (now - window)]
            self._failed_logins[identifier] = history

            if len(history) >= max_failures:
                oldest = history[0]
                remaining = max(1, int(window - (now - oldest)))
                return True, remaining
            return False, 0

    def record_successful_login(self, identifier: str):
        with self._lock:
            self._failed_logins.pop(identifier, None)

    def check_welcome_email_cooldown(self, email: str, cooldown_seconds: int = 1800) -> Tuple[bool, int]:
        clean_email = email.strip().lower()
        now = time.time()
        with self._lock:
            last_sent = self._email_cooldowns.get(clean_email, 0)
            if now - last_sent < cooldown_seconds:
                remaining = int(cooldown_seconds - (now - last_sent))
                return False, remaining
            self._email_cooldowns[clean_email] = now
            return True, 0

security_rate_limiter = SecurityRateLimiter()


# ==============================================================================
# 5. AI PROMPT INJECTION & FILE UPLOAD HARDENING
# ==============================================================================

PROMPT_INJECTION_TOKENS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior)",
    r"reveal\s+(your\s+)?(system\s+prompt|instructions|secret|api[_\s-]?key)",
    r"print\s+(the\s+)?(system\s+prompt|hidden\s+prompt)",
    r"system\s*prompt",
    r"jailbreak",
    r"developer\s+mode",
    r"DAN\s+mode",
    r"bypass\s+restrictions",
    r"roleplay\s+as\s+an\s+unfiltered",
    r"<system>",
    r"\[system\]",
    r"<\s*script\s*>",
    r"eval\s*\("
]
COMPILED_INJECTION_REGEX = re.compile("|".join(PROMPT_INJECTION_TOKENS), re.IGNORECASE)


def sanitize_advisor_query(query_str: str) -> str:
    """Sanitizes AI queries and defuses prompt injection and invisible Bidi markers."""
    if not query_str or len(query_str.strip()) < 3:
        raise ValueError("يرجى كتابة سؤال واضح لا يقل عن 3 أحرف.")

    clean = BIDI_AND_INVISIBLE_CHARS.sub("", query_str).strip()

    if len(clean) > 500:
        clean = clean[:500]

    clean = SCRIPT_TAG_PATTERN.sub("", clean)
    clean = COMPILED_INJECTION_REGEX.sub("[sanitized]", clean)
    return clean.strip()


def validate_uploaded_file(filename: str, content_bytes: bytes, max_size_mb: int = 5) -> str:
    """Validates document uploads against executable binaries, path traversal, and corrupted headers."""
    if not filename:
        raise ValueError("اسم الملف غير محدد.")

    safe_name = os.path.basename(filename).strip()
    safe_name = BIDI_AND_INVISIBLE_CHARS.sub("", safe_name)
    safe_name = re.sub(r"[^\w\.\-\s\u0600-\u06FF]", "", safe_name)
    ext = os.path.splitext(safe_name)[1].lower()

    allowed_extensions = {".pdf", ".txt", ".doc", ".docx"}
    if ext not in allowed_extensions:
        raise ValueError(f"صيغة الملف غير مدعومة ({ext}). الصيغ المسموحة هي: PDF, TXT, DOC, DOCX فقط.")

    if len(content_bytes) > max_size_mb * 1024 * 1024:
        raise ValueError(f"حجم الملف يتجاوز الحد الأقصى المسموح به ({max_size_mb} ميجابايت).")

    if len(content_bytes) < 10:
        raise ValueError("الملف فارغ أو تالف.")

    # Block executable binary headers
    if (
        content_bytes.startswith(b"MZ") or
        content_bytes.startswith(b"\x7fELF") or
        content_bytes.startswith(b"\xca\xfe\xba\xbe") or
        content_bytes.startswith(b"\xfe\xed\xfa\xce")
    ):
        raise ValueError("تم رفض الملف: صيغة تنفيذية غير مسموح برفعها أمنياً.")

    if ext == ".pdf" and not (content_bytes.startswith(b"%PDF-") or b"%PDF-" in content_bytes[:1024]):
        raise ValueError("تم رفض الملف: بنية ملف PDF غير صالحة أو تم التلاعب بها.")

    return safe_name


def sanitize_uploaded_text(text: str, max_chars: int = 15000) -> str:
    """Sanitizes extracted document text, removing Bidi overrides and injection markers."""
    if not text:
        return ""

    clean = BIDI_AND_INVISIBLE_CHARS.sub("", text)
    clean = "".join(ch for ch in clean if ch.isprintable() or ch in "\n\r\t")
    clean = SCRIPT_TAG_PATTERN.sub("", clean)
    clean = COMPILED_INJECTION_REGEX.sub("[filtered]", clean)

    if len(clean) > max_chars:
        clean = clean[:max_chars]

    return clean.strip()


def sanitize_llm_output(output_text: str) -> str:
    """Redacts accidental leaks of API keys, secrets, or internal system instruction markers."""
    if not output_text:
        return ""

    sanitized = output_text
    sanitized = re.sub(r"AIza[0-9A-Za-z-_]{35}", "[REDACTED_API_KEY]", sanitized)
    sanitized = re.sub(r"sk-[0-9A-Za-z-_]{32,}", "[REDACTED_SECRET]", sanitized)

    leak_markers = [
        "SYSTEM_INSTRUCTION", "HIDDEN_SYSTEM_PROMPT", "INTERNAL_ADVISOR_RULE",
        "YOU MUST NEVER REVEAL", "CONFIDENTIAL_ENGINE_PROMPT"
    ]
    for marker in leak_markers:
        sanitized = sanitized.replace(marker, "[REDACTED]")

    return sanitized
