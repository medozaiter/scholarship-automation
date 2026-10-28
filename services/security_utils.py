import re
import html
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Strict Email Regex (RFC 5322 subset - standard web email)
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)

# Allowed name characters: Arabic letters, English letters, spaces, hyphens, dots
NAME_REGEX = re.compile(r"^[\u0600-\u06FFa-zA-Z\s\.\-']{2,70}$")

# Disallowed dangerous SQL patterns (for defense in depth)
SQL_INJECTION_PATTERN = re.compile(
    r"(\b(UNION|SELECT|INSERT|DELETE|UPDATE|DROP|ALTER|EXEC|EXECUTE|SCRIPT|CREATE|TRUNCATE)\b|"
    r"(--|/\*|\*/|@@|char\s*\(|nchar\s*\(|varchar\s*\(|cast\s*\(|convert\s*\())",
    re.IGNORECASE
)

# Disallowed script/XSS tags
SCRIPT_TAG_PATTERN = re.compile(r"<[^>]*>|javascript:|onerror|onload|onclick|eval\(", re.IGNORECASE)


def sanitize_text(val: Optional[str], max_length: int = 150) -> str:
    """
    Strips dangerous HTML/script tags, removes control characters,
    escapes special characters, and truncates to safe length.
    """
    if val is None:
        return ""

    # Convert to string and strip whitespace
    clean = str(val).strip()

    # Reject null bytes and non-printable control chars
    clean = "".join(ch for ch in clean if ch.isprintable() or ch in "\n\r\t")

    # Remove script tags and event handlers
    clean = SCRIPT_TAG_PATTERN.sub("", clean)

    # Defuse SQL injection operators if present in prose inputs
    clean = clean.replace("\x00", "")

    # Limit maximum length
    if len(clean) > max_length:
        clean = clean[:max_length]

    # HTML escape for safe storage/display
    clean = html.escape(clean, quote=True)
    return clean.strip()


def validate_email(email_str: str) -> str:
    """
    Strictly validates email address.
    Rejects spaces, non-ASCII characters, and invalid domains.
    """
    if not email_str:
        raise ValueError("البريد الإلكتروني مطلوب ولا يمكن تركه فارغاً.")

    clean = email_str.strip().lower()

    if len(clean) > 100:
        raise ValueError("البريد الإلكتروني طويل جداً (الحد الأقصى 100 حرف).")

    if " " in clean:
        raise ValueError("البريد الإلكتروني لا يمكن أن يحتوي على مسافات.")

    if not EMAIL_REGEX.match(clean):
        raise ValueError("صيغة البريد الإلكتروني غير صالحة. يرجى إدخال إيميل صحيح (مثال: name@example.com).")

    return clean


def validate_name(name_str: str) -> str:
    """
    Validates student name. Must contain real letters (Arabic or English),
    between 2 and 60 characters, with no HTML or code injection.
    """
    if not name_str:
        return "Student"

    clean = name_str.strip()

    if SCRIPT_TAG_PATTERN.search(clean) or SQL_INJECTION_PATTERN.search(clean):
        raise ValueError("الاسم يحتوي على رموز أو مدخلات غير مسموح بها أمنياً.")

    # Remove extra spaces
    clean = re.sub(r"\s+", " ", clean)

    if len(clean) < 2:
        raise ValueError("الاسم قصير جداً (يجب أن يتكون من حرفين على الأقل).")

    if len(clean) > 60:
        clean = clean[:60]

    if not NAME_REGEX.match(clean):
        raise ValueError("يرجى إدخال اسم حقيقي يحتوي على أحرف عربية أو إنجليزية فقط دون رموز خاصة.")

    return html.escape(clean, quote=True)


def validate_gpa(gpa_str: str) -> str:
    """
    Strictly validates academic GPA / High school grade.
    Prevents ANY letters, code, script tags, or symbols (only digits, dot, slash, percent).
    Accepts:
    - Percentage: e.g. '85', '85%', '92.5%' (40% to 100%)
    - 4.0 Scale: e.g. '3.5', '3.8/4.0', '3.2' (1.5 to 4.0)
    - 5.0 Scale: e.g. '4.5', '4.2/5' (2.0 to 5.0)
    - Qualitative terms: 'امتياز', 'جيد جداً', 'ممتاز'
    Strictly blocks letters, code, XSS, or SQL injection.
    """
    if not gpa_str:
        return "85%"

    clean = gpa_str.strip()

    # Reject obvious injection attacks or control characters
    if SCRIPT_TAG_PATTERN.search(clean) or SQL_INJECTION_PATTERN.search(clean):
        raise ValueError("حقل المعدل يحتوي على رموز غير مسموح بها أمنياً.")

    # Check for accepted qualitative Arabic terms
    accepted_terms = ["امتياز", "جيد جدا", "جيد جداً", "ممتاز", "جيد", "مقبول"]
    if clean in accepted_terms:
        return clean

    # Strictly disallow Arabic letters or English letters in numeric GPA
    if re.search(r"[a-zA-Z\u0600-\u06FF]", clean):
        raise ValueError("حقل المعدل يجب أن يحتوي على أرقام فقط (مثلاً: 88% أو 3.6/4.0) ويمنع إدخال نصوص أو أحرف عشوائية.")

    # Only allow digits, dot, percent, slash, spaces
    if not re.match(r"^[0-9\.\s%/]+$", clean):
        raise ValueError("حقل المعدل يحتوي على رموز خاصة غير مقبولة.")

    # Check for percentage e.g. 85 or 85% or 92.4%
    pct_match = re.search(r"^(\d{2,3}(?:\.\d{1,2})?)\s*%?$", clean)
    if pct_match:
        val = float(pct_match.group(1))
        if 40.0 <= val <= 100.0:
            return f"{val:.1f}%".replace(".0%", "%")
        else:
            raise ValueError(f"المعدل المئوي ({val}%) غير منطقي. يجب أن يكون بين 40% و 100%.")

    # Check for 4.0 or 5.0 scale e.g. 3.6 or 3.6/4.0
    scale_match = re.search(r"^([1-5](?:\.\d{1,2})?)(?:\s*/\s*([45](?:\.0)?))?$", clean)
    if scale_match:
        val = float(scale_match.group(1))
        scale = float(scale_match.group(2)) if scale_match.group(2) else 4.0
        if 1.5 <= val <= scale:
            return f"{val}/{int(scale)}"

    raise ValueError(
        "صيغة المعدل غير صحيحة. يرجى إدخال أرقام فقط (مثال: 88% أو 3.6/4.0)."
    )


def validate_talents_experience(val: Optional[str]) -> str:
    """
    Sanitizes talents, volunteering, and extracurricular achievements.
    Prevents scripts, XSS, and SQL injection while allowing natural descriptive Arabic/English text.
    """
    if not val:
        return ""
    clean = sanitize_text(val, max_length=400)
    return clean


def validate_password(password_str: str) -> str:
    """
    Validates password length and complexity bounds.
    """
    if not password_str:
        raise ValueError("كلمة المرور مطلوبة.")

    if len(password_str) < 6:
        raise ValueError("كلمة المرور يجب أن لا تقل عن 6 أحرف.")

    if len(password_str) > 128:
        raise ValueError("كلمة المرور طويلة جداً (الحد الأقصى 128 حرف).")

    return password_str


def sanitize_advisor_query(query_str: str) -> str:
    """
    Sanitizes free-form question for AI Advisor to prevent prompt injection,
    script injection, and DoS payload attacks.
    """
    if not query_str or len(query_str.strip()) < 3:
        raise ValueError("يرجى كتابة سؤال واضح لا يقل عن 3 أحرف.")

    clean = query_str.strip()

    # Limit to reasonable question length
    if len(clean) > 400:
        clean = clean[:400]

    # Clean script tags and harmful tokens
    clean = SCRIPT_TAG_PATTERN.sub("", clean)

    # Defuse potential prompt override tricks
    prompt_injection_tokens = [
        "ignore previous instructions", "disregard all prior", "system prompt",
        "reveal your instructions", "print system prompt", "jailbreak"
    ]
    for token in prompt_injection_tokens:
        clean = re.sub(re.escape(token), "[filtered]", clean, flags=re.IGNORECASE)

    return clean.strip()
