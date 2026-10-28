import os
import re
import asyncio
import logging
from typing import List, Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from services.subscriber_service import SubscriberService
from services.scholarship_engine import ScholarshipEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
INDEX_HTML_PATH = os.path.join(TEMPLATES_DIR, "index.html")

app = FastAPI(
    title="MinhaTech AI - Global Scholarship Automation Engine",
    description="Automated Scholarship Discovery, Verification & Email Dispatch Platform",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sub_service = SubscriberService()
engine = ScholarshipEngine()


class SubscriptionRequest(BaseModel):
    email: str
    full_name: Optional[str] = "Student"
    degree: str = "Undergraduate (Bachelor's)"
    majors: List[str]
    country: Optional[str] = "Palestine"
    send_welcome_report: Optional[bool] = True

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        clean = v.strip().lower()
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", clean):
            raise ValueError("صيغة البريد الإلكتروني غير صحيحة")
        return clean


async def background_send_report(
    email: str,
    full_name: str,
    degree: str,
    majors: List[str],
    country: str
):
    """Sends an immediate welcome report in background without blocking web response."""
    try:
        logger.info(f"Background task: Generating welcome report for {email}...")
        ok = await engine.send_personalized_report(
            recipient_email=email,
            student_name=full_name,
            degree=degree,
            majors=majors,
            country=country
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
    return HTMLResponse(content="<h1>منحة تك AI - مرحباً بك</h1>")


@app.post("/api/subscribe")
async def subscribe_student(req: SubscriptionRequest, background_tasks: BackgroundTasks):
    """Registers a student for recurring weekly scholarship email reports."""
    try:
        sub = sub_service.add_or_update(
            email=req.email,
            full_name=req.full_name or "Student",
            degree=req.degree,
            majors=req.majors,
            country=req.country or "Palestine"
        )

        if req.send_welcome_report:
            background_tasks.add_task(
                background_send_report,
                email=req.email,
                full_name=req.full_name or "Student",
                degree=req.degree,
                majors=req.majors,
                country=req.country or "Palestine"
            )

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "تم تفعيل اشتراكك بنجاح! ستصلك أحدث المنح الموثقة دورياً في بريدك كل أسبوع.",
                "subscriber": {
                    "email": sub["email"],
                    "degree": sub["degree"],
                    "majors": sub["majors"],
                    "country": sub["country"]
                }
            }
        )
    except Exception as e:
        logger.error(f"Subscription error: {e}")
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
        results = await engine.search_and_extract(
            degree=degree,
            majors=[major],
            country=country
        )
        return {"success": True, "count": len(results), "scholarships": results[:5]}
    except Exception as e:
        logger.error(f"Preview error: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.app:app", host="0.0.0.0", port=8000, reload=True)
