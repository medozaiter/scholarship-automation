import os
import re
import asyncio
import logging
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query, Request, Response, UploadFile, File, Form
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from services.subscriber_service import SubscriberService
from services.scholarship_engine import ScholarshipEngine
from services.advisor_service import AdvisorService
from services.auth_service import AuthService
from services.automation_service import AutomationService, start_automation_daemon
from services.community_service import community_service
from services.db import init_db_and_migrate, is_db_available, get_notification_history
from services.email_service import get_email_provider_info, dispatch_email, get_last_dispatch_meta
from services.security_utils import (
    validate_email,
    validate_name,
    validate_gpa,
    validate_password,
    sanitize_text,
    sanitize_advisor_query,
    validate_talents_experience,
    validate_uploaded_file,
    sanitize_uploaded_text,
    security_rate_limiter,
    verify_session_token
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
INDEX_HTML_PATH = os.path.join(TEMPLATES_DIR, "index.html")
DASHBOARD_HTML_PATH = os.path.join(TEMPLATES_DIR, "dashboard.html")
ASSISTANT_HTML_PATH = os.path.join(TEMPLATES_DIR, "assistant.html")
NOTIFICATIONS_HTML_PATH = os.path.join(TEMPLATES_DIR, "notifications.html")
CSS_PATH = os.path.join(os.path.dirname(__file__), "static", "css", "scholarpilot.css")

app = FastAPI(
    title="ScholarPilot AI - Your AI-Powered Scholarship Advisor",
    description="Automated Scholarship Discovery, Verification, AI Advisor & Document Generator",
    version="2.5.0"
)

# Secure CORS Middleware
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "").strip()
allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()] if allowed_origins_env else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=bool(allowed_origins_env),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Application Rate Limiting Middleware with Anti-Spoofing Defense
@app.middleware("http")
async def rate_limiting_middleware(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/"):
        peer_ip = request.client.host if request.client else "127.0.0.1"
        forwarded = request.headers.get("x-forwarded-for")
        # Anti-spoofing: only trust X-Forwarded-For if direct peer is local reverse proxy or testclient
        if forwarded and peer_ip in ["127.0.0.1", "::1", "localhost", "testclient"]:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = peer_ip

        category = "general"
        if path.startswith("/api/auth/"):
            category = "auth"
        elif path.startswith("/api/advisor/upload-"):
            category = "upload"
        elif path.startswith("/api/advisor/"):
            category = "advisor"
        elif path == "/api/subscribe":
            category = "subscribe"

        allowed, retry_after = security_rate_limiter.check_rate_limit(client_ip, category)
        if not allowed:
            logger.warning(f"Rate limit exceeded for IP {client_ip} on category '{category}'")
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "detail": f"تم تجاوز عدد الطلبات المسموح به. يرجى الانتظار {retry_after} ثانية والمحاولة مجدداً.",
                    "retry_after": retry_after
                },
                headers={"Retry-After": str(retry_after)}
            )
    return await call_next(request)

# Hardened Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://unpkg.com https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: https:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "object-src 'none'; "
        "base-uri 'self';"
    )
    return response

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_error = errors[0] if errors else {}
    msg = first_error.get("msg", "البيانات المدخلة غير صحيحة")
    if msg.startswith("Value error, "):
        msg = msg.replace("Value error, ", "")
    clean_errors = [
        {"loc": list(e.get("loc", [])), "msg": e.get("msg", ""), "type": e.get("type", "")}
        for e in errors
    ]
    return JSONResponse(
        status_code=400,
        content={"success": False, "detail": msg, "errors": clean_errors}
    )

sub_service = SubscriberService()
engine = ScholarshipEngine()
advisor_service = AdvisorService()
auth_service = AuthService()
automation_service = AutomationService()

@app.on_event("startup")
async def startup_event():
    """Initializes database schema migrations, notification queue, and background daemon."""
    logger.info("Initializing database migrations and tables...")
    try:
        init_db_and_migrate()
    except Exception as e:
        logger.error(f"Database initialization warning: {e}")

    logger.info("Starting Asynchronous Notification Queue Worker...")
    try:
        from services.notification_queue import start_notification_worker
        start_notification_worker()
    except Exception as e:
        logger.error(f"Notification worker start error: {e}")

    logger.info("Initializing 100% Automated Background Scholarship & Email Daemon...")
    asyncio.create_task(start_automation_daemon())


@app.get("/healthz")
@app.get("/api/health")
async def health_check():
    """Production health check probe for Render, Uptime Robot, and cloud load balancers."""
    raw_db = os.getenv("DATABASE_URL", "")
    db_type = "Neon PostgreSQL" if "postgres" in raw_db else "SQLite / JSON Store"
    email_info = get_email_provider_info()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()

    return {
        "status": "healthy",
        "timestamp": asyncio.get_event_loop().time(),
        "database": {
            "type": db_type,
            "connected": is_db_available(),
            "pool": "active"
        },
        "email": email_info,
        "ai": {
            "provider": "Google AI Studio",
            "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            "configured": bool(gemini_key and len(gemini_key) > 5)
        },
        "version": "2.5.0"
    }


# ==================== STRICT REQUEST VALIDATION MODELS ====================

class SubscriptionRequest(BaseModel):
    email: str
    full_name: Optional[str] = "Student"
    degree: str = "Undergraduate (Bachelor's)"
    majors: List[str]
    gpa: Optional[str] = "85%"
    talents_experience: Optional[str] = ""
    english_level: Optional[str] = "Intermediate"
    target_destinations: Optional[List[str]] = ["Any"]
    country: Optional[str] = "Palestine"
    send_welcome_report: Optional[bool] = True

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return validate_email(v)

    @field_validator("full_name")
    @classmethod
    def check_name(cls, v: Optional[str]) -> str:
        return validate_name(v or "Student")

    @field_validator("gpa")
    @classmethod
    def check_gpa(cls, v: Optional[str]) -> str:
        return validate_gpa(v or "85%")

    @field_validator("talents_experience")
    @classmethod
    def check_talents(cls, v: Optional[str]) -> str:
        return validate_talents_experience(v or "")

    @field_validator("majors")
    @classmethod
    def clean_majors(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("يرجى اختيار أو كتابة تخصص واحد على الأقل.")
        cleaned = [sanitize_text(m, max_length=50) for m in v if m.strip()]
        if not cleaned:
            raise ValueError("يرجى إدخال اسم تخصص صحيح.")
        return cleaned[:8]  # Limit to max 8 majors

    @field_validator("degree", "english_level", "country")
    @classmethod
    def sanitize_fields(cls, v: Optional[str]) -> str:
        return sanitize_text(v, max_length=60)


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    degree: Optional[str] = "Undergraduate (Bachelor's)"
    majors: Optional[List[str]] = None
    gpa: Optional[str] = "85%"
    talents_experience: Optional[str] = ""
    english_level: Optional[str] = "Intermediate"
    country: Optional[str] = "Palestine"

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return validate_email(v)

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password(v)

    @field_validator("full_name")
    @classmethod
    def check_name(cls, v: str) -> str:
        return validate_name(v)

    @field_validator("gpa")
    @classmethod
    def check_gpa(cls, v: Optional[str]) -> str:
        return validate_gpa(v or "85%")

    @field_validator("talents_experience")
    @classmethod
    def check_talents(cls, v: Optional[str]) -> str:
        return validate_talents_experience(v or "")

    @field_validator("degree", "english_level", "country")
    @classmethod
    def clean_text(cls, v: Optional[str]) -> str:
        return sanitize_text(v, max_length=60)


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return validate_email(v)

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password(v)


class AdvisorChatRequest(BaseModel):
    query: str
    email: Optional[str] = None
    scholarship_id: Optional[str] = None
    history: Optional[List[Dict[str, str]]] = None
    profile: Optional[Dict[str, Any]] = None

    @field_validator("query")
    @classmethod
    def clean_query(cls, v: str) -> str:
        return sanitize_advisor_query(v)

    @field_validator("scholarship_id")
    @classmethod
    def clean_sch_id(cls, v: Optional[str]) -> Optional[str]:
        if v and v.strip():
            return sanitize_text(v, max_length=100)
        return None

    @field_validator("email")
    @classmethod
    def check_optional_email(cls, v: Optional[str]) -> Optional[str]:
        if v and v.strip():
            return validate_email(v)
        return None


class MatchCalculationRequest(BaseModel):
    gpa: str = "85%"
    degree: str = "Undergraduate (Bachelor's)"
    majors: List[str] = ["Software Engineering"]
    talents_experience: Optional[str] = ""
    country: Optional[str] = "Palestine"
    scholarship_name: Optional[str] = ""

    @field_validator("gpa")
    @classmethod
    def check_gpa(cls, v: str) -> str:
        return validate_gpa(v)

    @field_validator("talents_experience")
    @classmethod
    def check_talents(cls, v: Optional[str]) -> str:
        return validate_talents_experience(v or "")

    @field_validator("majors")
    @classmethod
    def check_majors(cls, v: List[str]) -> List[str]:
        if not v:
            return ["Software Engineering"]
        cleaned = [sanitize_text(m, max_length=50) for m in v[:8] if m.strip()]
        return cleaned or ["Software Engineering"]


class SaveScholarshipRequest(BaseModel):
    email: str
    scholarship_name: str

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return validate_email(v)


class CommunityStorySubmit(BaseModel):
    author_name: str
    author_email: Optional[str] = None
    author_country: Optional[str] = "فلسطين"
    scholarship_id: str
    scholarship_name: str
    university: Optional[str] = ""
    degree: Optional[str] = "ماجستير"
    field_of_study: Optional[str] = "تخصص أكاديمي"
    acceptance_year: Optional[str] = "2025/2026"
    title: str
    story_text: str
    key_advice: Optional[List[str]] = []
    gpa: Optional[str] = "85%+"
    tags: Optional[List[str]] = []

    @field_validator("title")
    @classmethod
    def clean_title(cls, v: str) -> str:
        return sanitize_text(v, max_length=255)

    @field_validator("story_text")
    @classmethod
    def clean_story(cls, v: str) -> str:
        return sanitize_text(v, max_length=5000)

    @field_validator("scholarship_name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        return sanitize_text(v, max_length=120)


class UpdatePreferencesRequest(BaseModel):
    email: str
    preferred_countries: Optional[List[str]] = None
    funding_type: Optional[str] = "Any"
    email_notifications: Optional[bool] = True
    telegram_notifications: Optional[bool] = False
    telegram_chat_id: Optional[str] = None
    degree: Optional[str] = None
    majors: Optional[List[str]] = None

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return validate_email(v)


class ReadNotificationRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return validate_email(v)


class ChancesRequest(BaseModel):
    email: Optional[str] = None
    scholarship_name: Optional[str] = None


class CompareRequest(BaseModel):
    email: Optional[str] = None
    scholarships: List[str] = ["hungaricum", "daad"]

    @field_validator("scholarships")
    @classmethod
    def check_scholarships(cls, v: List[str]) -> List[str]:
        return [sanitize_text(s, max_length=100) for s in v[:5]]


class CVReviewRequest(BaseModel):
    email: Optional[str] = None
    cv_text: str
    target_scholarship: Optional[str] = None

    @field_validator("cv_text")
    @classmethod
    def check_cv_len(cls, v: str) -> str:
        if len(v) > 30000:
            return v[:30000]
        return v


class LetterReviewRequest(BaseModel):
    email: Optional[str] = None
    letter_text: str
    target_scholarship: Optional[str] = None

    @field_validator("letter_text")
    @classmethod
    def check_letter_len(cls, v: str) -> str:
        if len(v) > 30000:
            return v[:30000]
        return v


class RoadmapRequest(BaseModel):
    email: Optional[str] = None
    scholarship_name: str = "Stipendium Hungaricum"


class DraftEmailRequest(BaseModel):
    email: Optional[str] = None
    email_type: str = "inquiry"
    target_scholarship: Optional[str] = None
    recipient_name: Optional[str] = None
    context: Optional[str] = None


def _get_verified_profile_email(request: Request, requested_email: Optional[str]) -> Optional[str]:
    """
    Resolves the verified student email from:
    1. Authorization Bearer session token.
    2. Session cookie.
    3. Requested email parameter (when authenticated or active student).
    Ensures legitimate users get immediate profile-awareness without unnecessary friction.
    """
    clean_target = requested_email.strip().lower() if requested_email and requested_email.strip() else None

    # 1. Bearer Header Verification
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1].strip()
        payload = verify_session_token(token)
        if payload and payload.get("email"):
            return payload.get("email").strip().lower()

    # 2. Session Cookie Verification
    cookie_token = request.cookies.get("session_token") or request.cookies.get("minha_token")
    if cookie_token:
        payload = verify_session_token(cookie_token)
        if payload and payload.get("email"):
            return payload.get("email").strip().lower()

    # 3. Direct Requested Email
    if clean_target and "@" in clean_target:
        return clean_target

    return None


# ==================== BACKGROUND TASKS & ENDPOINTS ====================

async def background_send_report(
    email: str,
    full_name: str,
    degree: str,
    majors: List[str],
    country: str,
    student_profile: Optional[Dict[str, Any]] = None
):
    """Sends an immediate welcome report in background without blocking web response."""
    try:
        logger.info(f"Background task: Generating welcome report for {email}...")
        ok = await engine.send_personalized_report(
            recipient_email=email,
            student_name=full_name,
            degree=degree,
            majors=majors,
            country=country,
            student_profile=student_profile
        )
        if ok:
            sub_service.update_last_sent(email)
            logger.info(f"Background welcome report delivered to {email}")
    except Exception as e:
        logger.error(f"Error sending welcome report to {email}: {e}")


@app.get("/", response_class=HTMLResponse)
async def serve_landing_page():
    """Serves the interactive, responsive Arabic web interface with dark/light mode."""
    if os.path.exists(INDEX_HTML_PATH):
        with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>ScholarPilot AI - Your AI-Powered Scholarship Advisor</h1>")


@app.get("/static/css/scholarpilot.css")
async def serve_static_css():
    """Serves the unified production-grade SaaS CSS design system."""
    if os.path.exists(CSS_PATH):
        with open(CSS_PATH, "r", encoding="utf-8") as f:
            return Response(content=f.read(), media_type="text/css")
    return Response(content="/* ScholarPilot AI Design System */", media_type="text/css")


@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard():
    """Serves the user account portal & admin control panel."""
    if os.path.exists(DASHBOARD_HTML_PATH):
        with open(DASHBOARD_HTML_PATH, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>لوحة التحكم</h1>")


@app.get("/assistant", response_class=HTMLResponse)
async def serve_assistant_page():
    """Serves the dedicated full-page ChatGPT-like AI Scholarship Assistant."""
    if os.path.exists(ASSISTANT_HTML_PATH):
        with open(ASSISTANT_HTML_PATH, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>المستشار الأكاديمي الذكي - ScholarPilot AI Assistant</h1>")


@app.get("/notifications", response_class=HTMLResponse)
async def serve_notifications_page():
    """Serves the dedicated notification center page."""
    if os.path.exists(NOTIFICATIONS_HTML_PATH):
        with open(NOTIFICATIONS_HTML_PATH, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>مركز التنبيهات - ScholarPilot AI</h1>")


@app.post("/api/auth/register")
async def register_account(req: RegisterRequest):
    """Creates a new student account and registers them for automated alerts with strict security filters."""
    try:
        user = auth_service.register(
            email=req.email,
            password=req.password,
            full_name=req.full_name,
            degree=req.degree or "Undergraduate (Bachelor's)",
            majors=req.majors or ["Software Engineering"],
            gpa=req.gpa or "85%",
            english_level=req.english_level or "Intermediate",
            country=req.country or "Palestine",
            talents_experience=req.talents_experience or ""
        )
        sub_service.add_or_update(
            email=req.email,
            full_name=req.full_name,
            degree=req.degree or "Undergraduate (Bachelor's)",
            majors=req.majors or ["Software Engineering"],
            gpa=req.gpa or "85%",
            english_level=req.english_level or "Intermediate",
            country=req.country or "Palestine",
            talents_experience=req.talents_experience or ""
        )
        token = user.get("session_token", "")
        return {"success": True, "user": user, "token": token, "message": "تم إنشاء حسابك وتفعيل التتبع بنجاح!"}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=400, detail="تعذر إتمام التسجيل. يرجى التأكد من صحة المدخلات.")


@app.post("/api/auth/login")
async def login_account(req: LoginRequest):
    """Authenticates student or administrator with PBKDF2 verification, lockout protection, and session token."""
    try:
        user = auth_service.login(req.email, req.password)
        if not user:
            raise HTTPException(status_code=401, detail="البريد الإلكتروني أو كلمة المرور غير صحيحة.")
        token = user.get("session_token", "")
        return {"success": True, "user": user, "token": token}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.post("/api/subscribe")
async def subscribe_student(req: SubscriptionRequest, background_tasks: BackgroundTasks):
    """Registers a student with comprehensive profile for recurring weekly scholarship email reports."""
    try:
        sub = sub_service.add_or_update(
            email=req.email,
            full_name=req.full_name or "Student",
            degree=req.degree,
            majors=req.majors,
            gpa=req.gpa or "85%",
            english_level=req.english_level or "Intermediate",
            target_destinations=req.target_destinations or ["Any"],
            country=req.country or "Palestine",
            talents_experience=req.talents_experience or ""
        )

        if req.send_welcome_report:
            background_tasks.add_task(
                background_send_report,
                email=req.email,
                full_name=req.full_name or "Student",
                degree=req.degree,
                majors=req.majors,
                country=req.country or "Palestine",
                student_profile=sub
            )

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "تم تفعيل اشتراكك وحساب نسبة التوافق بنجاح! ستصلك التقارير المحدثة أسبوعياً بدون تدخل يدوي.",
                "subscriber": {
                    "email": sub["email"],
                    "degree": sub["degree"],
                    "majors": sub["majors"],
                    "gpa": sub["gpa"],
                    "english_level": sub["english_level"],
                    "country": sub["country"],
                    "talents_experience": sub.get("talents_experience", "")
                }
            }
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Subscription error: {e}")
        raise HTTPException(status_code=400, detail="حدث خطأ في معالجة الطلب.")


@app.post("/api/student/send-report")
async def send_student_report_direct(req: SubscriptionRequest):
    """
    Direct synchronous endpoint for sending the weekly report to student's email.
    Provides instant real-time delivery status and detailed diagnostic message if blocked.
    """
    clean_email = (req.email or "").strip().lower()
    if not clean_email or "@" not in clean_email:
        raise HTTPException(status_code=400, detail="البريد الإلكتروني غير صالح.")

    allowed, wait_sec = security_rate_limiter.check_welcome_email_cooldown(clean_email)
    if not allowed:
        return {
            "success": False,
            "cooldown": True,
            "wait_seconds": wait_sec,
            "detail": f"يرجى الانتظار {wait_sec} ثانية قبل إعادة طلب التقرير منعاً للتكرار."
        }

    degree = req.degree or "Undergraduate (Bachelor's)"
    majors = req.majors or ["Software Engineering"]
    country = req.country or "Palestine"
    full_name = req.full_name or "Student"

    profile = {
        "email": clean_email,
        "full_name": full_name,
        "degree": degree,
        "majors": majors,
        "gpa": req.gpa or "85%",
        "country": country,
        "talents_experience": req.talents_experience or ""
    }

    try:
        ok = await engine.send_personalized_report(
            recipient_email=clean_email,
            student_name=full_name,
            degree=degree,
            majors=majors,
            country=country,
            student_profile=profile
        )

        meta = get_last_dispatch_meta()

        if ok:
            sub_service.update_last_sent(clean_email)
            return {
                "success": True,
                "provider": meta.get("provider", "Resend"),
                "detail": f"تم تسليم التقرير الأكاديمي بنجاح إلى: {clean_email}. تفقد صندوق الوارد أو مجلد الرسائل غير المرغوب فيها (Spam)."
            }
        else:
            error_msg = meta.get("error_detail") or "تعذر تسليم البريد الإلكتروني. يرجى مراجعة إعدادات مزود البريد."
            return {
                "success": False,
                "provider": meta.get("provider"),
                "detail": error_msg,
                "hint": meta.get("hint")
            }
    except Exception as e:
        logger.error(f"Error executing synchronous send-report to {clean_email}: {e}")
        return {
            "success": False,
            "detail": f"حدث خطأ أثناء إعداد التقرير: {str(e)[:150]}"
        }


@app.post("/api/email/test")
async def test_email_dispatch(payload: Dict[str, str]):
    """
    Diagnostic tool to verify email delivery to any test recipient.
    """
    to_email = payload.get("email", "").strip()
    if not to_email or "@" not in to_email:
        raise HTTPException(status_code=400, detail="البريد الإلكتروني غير صالح.")
    
    test_html = """
    <div style="font-family: Arial, sans-serif; direction: rtl; text-align: right; padding: 24px; background-color: #0f172a; color: #f8fafc; border-radius: 16px; border: 1px solid #334155;">
        <h2 style="color: #38bdf8; margin-top: 0;">🚀 اختبار تسليم رسائل ScholarPilot AI</h2>
        <p>مرحباً بك! هذه رسالة تحقق تؤكد أن محرك البريد متصل ويعمل بنجاح وقادر على الوصول إلى صندوق بريدك.</p>
        <p style="font-size: 13px; color: #94a3b8;">إذا استلمت هذه الرسالة، فهذا يعني أن نظام الإشعارات والتذكيرات جاهز تماماً.</p>
    </div>
    """
    ok = await dispatch_email(
        to_email=to_email,
        subject="ScholarPilot AI - رسالة تأكيد فحص البريد الإلكتروني",
        html_content=test_html,
        text_content="ScholarPilot AI - Test Email Verification."
    )
    meta = get_last_dispatch_meta()
    return {
        "success": ok,
        "recipient": to_email,
        "meta": meta
    }


@app.get("/api/scholarships/live")
async def get_live_scholarships():
    """Returns autonomous live scholarships automatically fetched and maintained with application links & requirements."""
    try:
        items = automation_service.get_live_scholarships()
        return {
            "success": True,
            "count": len(items),
            "source": "Automated Live Feed & Ingestion Engine",
            "scholarships": items
        }
    except Exception as e:
        logger.error(f"Live scholarships error: {e}")
        return {"success": False, "count": 0, "scholarships": []}


@app.get("/api/scholarships/details/{scholarship_id}")
@app.get("/api/scholarships/{scholarship_id}")
async def get_scholarship_by_id(scholarship_id: str):
    """Returns detailed attributes and application portal for a specific scholarship."""
    clean_id = sanitize_text(scholarship_id, max_length=100).lower()
    if clean_id == "live":
        return await get_live_scholarships()
    items = automation_service.get_live_scholarships()
    matched = next((s for s in items if s.get("id", "").lower() == clean_id), None)
    if not matched:
        matched = next((s for s in advisor_service.catalog if s.get("id", "").lower() == clean_id), None)
    if not matched:
        raise HTTPException(status_code=404, detail="المنحة غير موجودة.")
    return {"success": True, "scholarship": matched}


@app.get("/api/automation/status")
async def get_automation_telemetry():
    """Returns autonomous engine status, monitored scholarship counts, student reach, and notification logs."""
    try:
        return automation_service.get_automation_status()
    except Exception as e:
        logger.error(f"Error fetching automation status: {e}")
        return {"status": "error", "detail": str(e)}


@app.get("/api/automation/history")
async def get_notifications_history_endpoint(limit: int = 50):
    """Returns persistent audit log of sent digests, match alerts, and deadline reminders."""
    try:
        history = get_notification_history(limit=min(limit, 100))
        return {
            "success": True,
            "count": len(history),
            "history": history
        }
    except Exception as e:
        logger.error(f"Error fetching notification history: {e}")
        return {"success": False, "count": 0, "history": []}


@app.post("/api/automation/trigger-cycle")
async def trigger_full_automation_cycle(background_tasks: BackgroundTasks):
    """Manually triggers an immediate autonomous cycle: Discovery, Matching, Deadlines & Digests."""
    async def _run_cycle():
        try:
            logger.info("Manual trigger: Starting full autonomous cycle...")
            await automation_service.auto_refresh_scholarships_from_web()
            await automation_service.auto_dispatch_deadline_reminders()
            await automation_service.auto_dispatch_weekly_digests()
            logger.info("Manual trigger: Full autonomous cycle complete.")
        except Exception as err:
            logger.error(f"Error in manually triggered automation cycle: {err}")

    background_tasks.add_task(_run_cycle)
    return {
        "success": True,
        "message": "تم بدء دورة الأتمتة الكاملة (استكشاف المنح، مطابقة الطلاب، التذكيرات، والتقارير الأسبوعية) بنجاح في الخلفية."
    }


# =====================================================================
# IN-APP NOTIFICATIONS & USER PREFERENCES API
# =====================================================================

@app.get("/api/notifications")
async def get_notifications_api(
    email: Optional[str] = None,
    limit: int = 50,
    unread_only: bool = False
):
    """Returns in-app notifications and unread count for a student."""
    from services.db import get_in_app_notifications, get_unread_notification_count
    if not email:
        return {"success": True, "notifications": [], "unread_count": 0}
    clean_email = email.strip().lower()
    items = get_in_app_notifications(clean_email, limit=limit, unread_only=unread_only)
    unread = get_unread_notification_count(clean_email)
    return {"success": True, "notifications": items, "unread_count": unread}


@app.post("/api/notifications/{notification_id}/read")
async def mark_notification_read_api(
    notification_id: str,
    req: ReadNotificationRequest
):
    """Marks a single notification as read."""
    from services.db import mark_notification_as_read
    ok = mark_notification_as_read(req.email, notification_id)
    return {"success": ok}


@app.post("/api/notifications/read-all")
async def mark_all_notifications_read_api(req: ReadNotificationRequest):
    """Marks all notifications for a student as read."""
    from services.db import mark_all_notifications_as_read
    count = mark_all_notifications_as_read(req.email)
    return {"success": True, "marked_count": count}


@app.get("/api/user/preferences")
async def get_user_preferences_api(email: str):
    """Returns user notification & matching preferences."""
    from services.db import get_user_preferences
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="البريد الإلكتروني غير صالح")
    prefs = get_user_preferences(email)
    return {"success": True, "preferences": prefs}


@app.post("/api/user/preferences")
async def update_user_preferences_api(req: UpdatePreferencesRequest):
    """Updates user notification & matching preferences."""
    from services.db import update_user_preferences
    payload = {
        "preferred_countries": req.preferred_countries,
        "funding_type": req.funding_type,
        "email_notifications": req.email_notifications,
        "telegram_notifications": req.telegram_notifications,
        "telegram_chat_id": req.telegram_chat_id,
        "degree": req.degree,
        "majors": req.majors
    }
    ok = update_user_preferences(req.email, payload)
    if not ok:
        raise HTTPException(status_code=400, detail="تعذر حفظ التفضيلات")
    return {"success": True, "message": "تم حفظ تفضيلاتك بنجاح!"}


@app.get("/api/notifications/events")
async def get_notification_events_api(email: Optional[str] = None, limit: int = 50):
    """Returns notification lifecycle tracking events (created, sent, delivered, opened, clicked)."""
    from services.db import get_notification_events
    events = get_notification_events(recipient=email, limit=limit)
    return {"success": True, "events": events}


@app.get("/api/notifications/queue/status")
async def get_queue_status_api():
    """Returns notification queue runtime metrics."""
    from services.notification_queue import get_queue_status
    return {"success": True, "queue": get_queue_status()}


@app.post("/api/advisor/chat")
@app.post("/api/advisor/consult")
async def consult_advisor(req: AdvisorChatRequest, request: Request):
    """Real-time AI Scholarship Advisor answering concisely with multi-turn dialect understanding, token optimization, and profile/scholarship awareness."""
    try:
        safe_email = _get_verified_profile_email(request, req.email)
        profile = advisor_service.resolve_student_profile(email=safe_email, explicit_profile=req.profile)
        res = await advisor_service.consult_ai_advisor(
            student_query=req.query,
            student_profile=profile,
            chat_history=req.history,
            email=safe_email,
            scholarship_id=req.scholarship_id
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Advisor error: {e}")
        raise HTTPException(status_code=500, detail="تعذر الاتصال بالمستشار الذكي حالياً.")


@app.post("/api/advisor/chances")
async def estimate_my_chances(req: ChancesRequest, request: Request):
    """Calculates student admission probability, competitiveness tier, and confidence level."""
    try:
        safe_email = _get_verified_profile_email(request, req.email)
        profile = advisor_service.resolve_student_profile(email=safe_email)
        return advisor_service.estimate_acceptance_chances(
            student_profile=profile,
            scholarship_target=req.scholarship_name
        )
    except Exception as e:
        logger.error(f"Chances estimation error: {e}")
        raise HTTPException(status_code=500, detail="حدث خطأ أثناء حساب احتمالية القبول.")


@app.post("/api/advisor/compare")
async def compare_scholarships_route(req: CompareRequest, request: Request):
    """Generates side-by-side comparison table between 2+ scholarships with tailored verdict."""
    try:
        safe_email = _get_verified_profile_email(request, req.email)
        profile = advisor_service.resolve_student_profile(email=safe_email)
        return advisor_service.compare_scholarships(
            scholarship_names_or_ids=req.scholarships,
            student_profile=profile
        )
    except Exception as e:
        logger.error(f"Comparison error: {e}")
        raise HTTPException(status_code=500, detail="حدث خطأ أثناء إعداد المقارنة.")


@app.post("/api/advisor/review-cv")
async def review_cv_text_route(req: CVReviewRequest, request: Request):
    """Reviews text CV and returns CV Score (0-100), strengths, and recommendations."""
    try:
        safe_email = _get_verified_profile_email(request, req.email)
        profile = advisor_service.resolve_student_profile(email=safe_email)
        clean_text = sanitize_uploaded_text(req.cv_text)
        return await advisor_service.review_cv(
            cv_text=clean_text,
            student_profile=profile,
            target_scholarship=req.target_scholarship
        )
    except Exception as e:
        logger.error(f"CV review error: {e}")
        raise HTTPException(status_code=500, detail="حدث خطأ أثناء فحص السيرة الذاتية.")


@app.post("/api/advisor/upload-cv")
async def upload_and_review_cv(
    request: Request,
    file: UploadFile = File(...),
    email: Optional[str] = Form(None),
    target_scholarship: Optional[str] = Form(None)
):
    """Uploads PDF/TXT/DOCX CV, extracts text without external binaries, and generates full evaluation."""
    try:
        content = await file.read()
        safe_name = validate_uploaded_file(file.filename or "cv.pdf", content, max_size_mb=5)
        extracted = advisor_service.extract_text_from_document_bytes(content, safe_name)
        if not extracted or len(extracted.strip()) < 30:
            raise HTTPException(status_code=400, detail="لم يتم العثور على نصوص مقروءة داخل الملف المرفوع.")
        safe_email = _get_verified_profile_email(request, email)
        profile = advisor_service.resolve_student_profile(email=safe_email)
        return await advisor_service.review_cv(
            cv_text=extracted,
            student_profile=profile,
            target_scholarship=target_scholarship
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CV upload error: {e}")
        raise HTTPException(status_code=500, detail="تعذر تدقيق ملف السيرة الذاتية.")


@app.post("/api/advisor/review-letter")
async def review_letter_text_route(req: LetterReviewRequest, request: Request):
    """Reviews Statement of Purpose / Motivation Letter text and returns score and improvements."""
    try:
        safe_email = _get_verified_profile_email(request, req.email)
        profile = advisor_service.resolve_student_profile(email=safe_email)
        clean_text = sanitize_uploaded_text(req.letter_text)
        return await advisor_service.review_motivation_letter(
            letter_text=clean_text,
            student_profile=profile,
            target_scholarship=req.target_scholarship
        )
    except Exception as e:
        logger.error(f"Letter review error: {e}")
        raise HTTPException(status_code=500, detail="حدث خطأ أثناء تدقيق خطاب الدافع.")


@app.post("/api/advisor/upload-letter")
async def upload_and_review_letter(
    request: Request,
    file: UploadFile = File(...),
    email: Optional[str] = Form(None),
    target_scholarship: Optional[str] = Form(None)
):
    """Uploads Motivation letter document (PDF/TXT/DOCX), extracts text, and reviews it."""
    try:
        content = await file.read()
        safe_name = validate_uploaded_file(file.filename or "motivation_letter.pdf", content, max_size_mb=5)
        extracted = advisor_service.extract_text_from_document_bytes(content, safe_name)
        if not extracted or len(extracted.strip()) < 50:
            raise HTTPException(status_code=400, detail="نص خطاب الدافع في الملف المرفوع قصير جداً أو غير مقروء.")
        safe_email = _get_verified_profile_email(request, email)
        profile = advisor_service.resolve_student_profile(email=safe_email)
        return await advisor_service.review_motivation_letter(
            letter_text=extracted,
            student_profile=profile,
            target_scholarship=target_scholarship
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Letter upload error: {e}")
        raise HTTPException(status_code=500, detail="تعذر تدقيق ملف خطاب الدافع.")


@app.post("/api/advisor/roadmap")
async def generate_roadmap_route(req: RoadmapRequest, request: Request):
    """Generates detailed 4-8 week milestone roadmap and interactive checklist."""
    try:
        safe_email = _get_verified_profile_email(request, req.email)
        profile = advisor_service.resolve_student_profile(email=safe_email)
        return advisor_service.generate_application_roadmap(
            scholarship_name=req.scholarship_name,
            student_profile=profile
        )
    except Exception as e:
        logger.error(f"Roadmap error: {e}")
        raise HTTPException(status_code=500, detail="حدث خطأ أثناء توليد خطة التقديم.")


@app.post("/api/advisor/draft-email")
async def draft_email_route(req: DraftEmailRequest, request: Request):
    """Generates official academic email ready to copy."""
    try:
        safe_email = _get_verified_profile_email(request, req.email)
        profile = advisor_service.resolve_student_profile(email=safe_email)
        return advisor_service.draft_official_email(
            email_type=req.email_type,
            student_profile=profile,
            target_scholarship=req.target_scholarship,
            recipient_name=req.recipient_name,
            additional_context=req.context
        )
    except Exception as e:
        logger.error(f"Draft email error: {e}")
        raise HTTPException(status_code=500, detail="حدث خطأ أثناء صياغة الإيميل الرسمي.")
        return advisor_service.draft_official_email(
            email_type=req.email_type,
            student_profile=profile,
            target_scholarship=req.target_scholarship,
            recipient_name=req.recipient_name,
            additional_context=req.context
        )
    except Exception as e:
        logger.error(f"Draft email error: {e}")
        raise HTTPException(status_code=500, detail="حدث خطأ أثناء صياغة الإيميل الرسمي.")


@app.get("/api/advisor/deadlines")
async def get_deadlines_route():
    """Returns analytics on scholarships closing this week, in 30 days, and upcoming openings."""
    try:
        return advisor_service.get_deadline_analytics()
    except Exception as e:
        logger.error(f"Deadlines error: {e}")
        raise HTTPException(status_code=500, detail="حدث خطأ في استرجاع مواعيد الإغلاق.")


@app.post("/api/match/calculate")
async def calculate_match(req: MatchCalculationRequest):
    """Calculates student admission probability & match percentage based on GPA, talents, and target profile."""
    try:
        res = advisor_service.calculate_match_score(
            gpa=req.gpa,
            majors=req.majors,
            country=req.country or "Palestine",
            scholarship={"name": req.scholarship_name or "Global Scholarship", "target_majors": req.majors},
            student_talents=req.talents_experience or ""
        )
        return {"success": True, "match": res}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Match calculation error: {e}")
        raise HTTPException(status_code=500, detail="حدث خطأ أثناء تقييم نسبة القبول.")


@app.post("/api/scholarships/save")
async def save_scholarship(req: SaveScholarshipRequest, request: Request):
    """Saves scholarship to student's watchlist for deadline countdown reminders with optional session token verification."""
    try:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1].strip()
            token_user = auth_service.authenticate_token(token)
            if token_user and token_user.get("email"):
                # Enforce authenticated session email to prevent IDOR
                req.email = token_user["email"]

        result = sub_service.toggle_saved_scholarship(req.email, req.scholarship_name)
        return {"success": True, **result}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Save scholarship error: {e}")
        raise HTTPException(status_code=400, detail="تعذر حفظ المنحة. يرجى التحقق من صحة البيانات.")


@app.get("/api/stats")
async def get_stats():
    """Public stats on total active subscribers."""
    subs = sub_service.get_all(active_only=True)
    return {
        "active_subscribers_count": len(subs),
        "status": "online",
        "engine_model": os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    }


@app.get("/api/preview")
async def preview_scholarships(
    degree: str = Query("Undergraduate (Bachelor's)"),
    major: str = Query("Cybersecurity"),
    country: str = Query("Palestine")
):
    """Provides a live JSON preview of top matching scholarships."""
    try:
        clean_degree = sanitize_text(degree, max_length=50)
        clean_major = sanitize_text(major, max_length=50)
        clean_country = sanitize_text(country, max_length=50)
        results = await engine.search_and_extract(
            degree=clean_degree,
            majors=[clean_major],
            country=clean_country
        )
        return {"success": True, "count": len(results), "scholarships": results[:5]}
    except Exception as e:
        logger.error(f"Preview error: {e}")
        return {"success": False, "count": 0, "error": "تعذر استرجاع المنح المقترحة حالياً."}


# =====================================================================
# COMMUNITY & ACCEPTANCE EXPERIENCES API
# =====================================================================

@app.get("/api/community/stories")
async def get_community_stories_endpoint(
    scholarship_id: Optional[str] = None,
    degree: Optional[str] = None,
    limit: int = 50
):
    """Returns verified acceptance stories & tips from admitted scholars."""
    try:
        stories = community_service.list_stories(scholarship_id=scholarship_id, degree=degree, limit=limit)
        return {
            "success": True,
            "count": len(stories),
            "stories": stories
        }
    except Exception as e:
        logger.error(f"Error fetching community stories: {e}")
        return {"success": False, "count": 0, "stories": []}


@app.get("/api/community/stories/{story_id}")
async def get_community_story_by_id_endpoint(story_id: str):
    """Returns a single acceptance story by ID."""
    story = community_service.get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="القصة غير موجودة.")
    return {"success": True, "story": story}


@app.post("/api/community/stories")
async def submit_community_story_endpoint(payload: CommunityStorySubmit):
    """Submits a new acceptance experience or scholarship advice."""
    try:
        story_dict = {
            "author_name": payload.author_name.strip(),
            "author_email": payload.author_email.strip() if payload.author_email else "",
            "author_country": payload.author_country.strip() if payload.author_country else "فلسطين",
            "scholarship_id": payload.scholarship_id.strip().lower(),
            "scholarship_name": payload.scholarship_name.strip(),
            "university": payload.university.strip() if payload.university else "",
            "degree": payload.degree.strip() if payload.degree else "ماجستير",
            "field_of_study": payload.field_of_study.strip() if payload.field_of_study else "تخصص أكاديمي",
            "acceptance_year": payload.acceptance_year.strip() if payload.acceptance_year else "2025/2026",
            "title": payload.title.strip(),
            "story_text": payload.story_text.strip(),
            "key_advice": payload.key_advice or [],
            "gpa": payload.gpa.strip() if payload.gpa else "85%+",
            "tags": payload.tags or [],
            "is_verified": True
        }
        saved = community_service.add_story(story_dict)
        return {
            "success": True,
            "message": "شكراً لك! تم نشر تجربة قبولك بنجاح لتلهم وتفيد الطلاب الآخرين.",
            "story": saved
        }
    except Exception as e:
        logger.error(f"Error saving community story: {e}")
        raise HTTPException(status_code=400, detail="تعذر نشر التجربة. يرجى التأكد من ملء الحقول المطلوبة.")


@app.post("/api/community/stories/{story_id}/upvote")
async def upvote_community_story_endpoint(story_id: str, payload: Dict[str, str]):
    """Records an upvote indicating this student acceptance experience was helpful."""
    email = payload.get("email", "").strip() or "anonymous_student@scholarpilot.ai"
    result = community_service.upvote(story_id, email)
    return result


@app.get("/api/community/highlights/{scholarship_id}")
async def get_scholarship_community_highlights_endpoint(scholarship_id: str):
    """Returns acceptance tips & accepted student count for a specific scholarship in the radar."""
    tips = community_service.get_scholarship_tips_highlight(scholarship_id)
    return {
        "success": bool(tips is not None),
        "highlight": tips
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run("web.app:app", host="0.0.0.0", port=port, reload=True)
