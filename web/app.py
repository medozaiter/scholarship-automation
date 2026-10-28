import os
import re
import asyncio
import logging
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from services.subscriber_service import SubscriberService
from services.scholarship_engine import ScholarshipEngine
from services.advisor_service import AdvisorService
from services.auth_service import AuthService
from services.automation_service import AutomationService, start_automation_daemon
from services.security_utils import (
    validate_email,
    validate_name,
    validate_gpa,
    validate_password,
    sanitize_text,
    sanitize_advisor_query,
    validate_talents_experience
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
INDEX_HTML_PATH = os.path.join(TEMPLATES_DIR, "index.html")
DASHBOARD_HTML_PATH = os.path.join(TEMPLATES_DIR, "dashboard.html")
CSS_PATH = os.path.join(os.path.dirname(__file__), "static", "css", "scholarpilot.css")

app = FastAPI(
    title="ScholarPilot AI - Your AI-Powered Scholarship Advisor",
    description="Automated Scholarship Discovery, Verification, AI Advisor & Document Generator",
    version="2.5.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
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
    logger.info("Initializing 100% Automated Background Scholarship & Email Daemon...")
    asyncio.create_task(start_automation_daemon())


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
    history: Optional[List[Dict[str, str]]] = None

    @field_validator("query")
    @classmethod
    def clean_query(cls, v: str) -> str:
        return sanitize_advisor_query(v)

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


class DocumentGenerationRequest(BaseModel):
    student_name: str = "Student"
    email: str
    degree: str = "Undergraduate"
    major: str = "Software Engineering"
    gpa: str = "85%"
    scholarship_name: str = "Lester B. Pearson"
    doc_type: Optional[str] = "all"
    talents_experience: Optional[str] = ""
    target_country: Optional[str] = "Europe"
    send_to_email: Optional[bool] = True

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return validate_email(v)

    @field_validator("student_name")
    @classmethod
    def check_name(cls, v: str) -> str:
        return validate_name(v)

    @field_validator("gpa")
    @classmethod
    def check_gpa(cls, v: str) -> str:
        return validate_gpa(v)

    @field_validator("talents_experience")
    @classmethod
    def check_talents(cls, v: Optional[str]) -> str:
        return validate_talents_experience(v or "")

    @field_validator("scholarship_name", "degree", "major", "target_country", "doc_type")
    @classmethod
    def clean_fields(cls, v: Optional[str]) -> str:
        return sanitize_text(v, max_length=100)


class SaveScholarshipRequest(BaseModel):
    email: str
    scholarship_name: str

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return validate_email(v)

    @field_validator("scholarship_name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        return sanitize_text(v, max_length=120)


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
        return {"success": True, "user": user, "message": "تم إنشاء حسابك وتفعيل التتبع بنجاح!"}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=400, detail="تعذر إتمام التسجيل. يرجى التأكد من صحة المدخلات.")


@app.post("/api/auth/login")
async def login_account(req: LoginRequest):
    """Authenticates student or administrator."""
    try:
        user = auth_service.login(req.email, req.password)
        if not user:
            raise HTTPException(status_code=401, detail="البريد الإلكتروني أو كلمة المرور غير صحيحة.")
        return {"success": True, "user": user}
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


@app.post("/api/advisor/chat")
@app.post("/api/advisor/consult")
async def consult_advisor(req: AdvisorChatRequest):
    """Real-time AI Scholarship Advisor answering concisely with multi-turn dialect understanding."""
    try:
        profile = None
        if req.email:
            profile = sub_service.get_by_email(req.email)

        res = await advisor_service.consult_ai_advisor(
            student_query=req.query,
            student_profile=profile,
            chat_history=req.history
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Advisor error: {e}")
        raise HTTPException(status_code=500, detail="تعذر الاتصال بالمستشار الذكي حالياً.")


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


@app.post("/api/documents/generate")
async def generate_documents(req: DocumentGenerationRequest, background_tasks: BackgroundTasks):
    """Generates tailored Motivation Letter, Recommendation Letter, Academic CV, or Checklist with official letterhead."""
    try:
        docs = await advisor_service.generate_smart_documents(
            student_name=req.student_name,
            degree=req.degree,
            major=req.major,
            gpa=req.gpa,
            scholarship_name=req.scholarship_name,
            target_country=req.target_country or "Europe",
            doc_type=req.doc_type or "all",
            talents_experience=req.talents_experience or ""
        )

        if req.send_to_email:
            background_tasks.add_task(
                engine.send_application_kit_email,
                recipient_email=req.email,
                student_name=req.student_name,
                scholarship_name=req.scholarship_name,
                degree=req.degree,
                major=req.major,
                documents=docs
            )

        return {
            "success": True,
            "scholarship_name": req.scholarship_name,
            "doc_type": req.doc_type or "all",
            "documents": docs,
            "message": f"تم توليد مستندات التقديم الرسمية لمنحة {req.scholarship_name} بنجاح!" + (" وتم إرسال نسخة إلى بريدك." if req.send_to_email else "")
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Doc generation error: {e}")
        raise HTTPException(status_code=500, detail="حدث خطأ أثناء توليد المستندات.")


@app.post("/api/documents/download")
async def download_document(req: DocumentGenerationRequest):
    """Generates and downloads a clean formatted file with official institutional letterhead."""
    try:
        docs = await advisor_service.generate_smart_documents(
            student_name=req.student_name,
            degree=req.degree,
            major=req.major,
            gpa=req.gpa,
            scholarship_name=req.scholarship_name,
            target_country=req.target_country or "Europe",
            doc_type=req.doc_type or "all",
            talents_experience=req.talents_experience or ""
        )

        ref_num = abs(hash(req.student_name + req.scholarship_name)) % 1000000
        header = (
            f"================================================================================\n"
            f"                  SCHOLARPILOT AI ACADEMIC DOSSIER & APPLICATION                     \n"
            f"              Official Institutional Application Letterhead                     \n"
            f"REF ID: REF-{ref_num:06d} | Verified Academic Dossier\n"
            f"Applicant: {req.student_name} | Program: {req.degree} in {req.major}\n"
            f"Target: {req.scholarship_name}\n"
            f"================================================================================\n\n"
        )

        doc_choice = req.doc_type or "all"
        if doc_choice == "motivation":
            content = header + docs.get("motivation_letter", "")
            filename = f"Motivation_Letter_{req.student_name.replace(' ', '_')}.txt"
        elif doc_choice == "recommendation":
            content = header + docs.get("recommendation_letter", "")
            filename = f"Recommendation_Letter_{req.student_name.replace(' ', '_')}.txt"
        elif doc_choice == "cv":
            content = header + docs.get("academic_cv", "")
            filename = f"Academic_CV_{req.student_name.replace(' ', '_')}.txt"
        elif doc_choice == "proposal":
            content = header + docs.get("research_proposal", "")
            filename = f"Research_Proposal_{req.student_name.replace(' ', '_')}.txt"
        elif doc_choice == "checklist":
            content = header + docs.get("checklist", "")
            filename = f"Application_Checklist_{req.scholarship_name.replace(' ', '_')}.txt"
        else:
            # Combine all documents with clear dividers
            content = header
            content += docs.get("academic_cv", "") + "\n\n" + ("="*52) + "\n\n"
            content += docs.get("motivation_letter", "") + "\n\n" + ("="*52) + "\n\n"
            content += docs.get("recommendation_letter", "") + "\n\n" + ("="*52) + "\n\n"
            content += docs.get("checklist", "")
            filename = f"Application_Kit_{req.scholarship_name.replace(' ', '_')}.txt"

        return Response(
            content=content,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(status_code=500, detail="تعذر تحميل المستند حالياً.")


@app.post("/api/scholarships/save")
async def save_scholarship(req: SaveScholarshipRequest):
    """Saves scholarship to student's watchlist for deadline countdown reminders."""
    try:
        result = sub_service.toggle_saved_scholarship(req.email, req.scholarship_name)
        return {"success": True, **result}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run("web.app:app", host="0.0.0.0", port=port, reload=True)
