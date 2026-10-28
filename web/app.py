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

app = FastAPI(
    title="Global Scholarship AI Engine",
    description="Automated Scholarship Discovery & Email Dispatch System",
    version="2.0.0"
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
    """Serves the interactive, responsive Arabic web interface."""
    return HTMLResponse(content=LANDING_PAGE_HTML)


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


LANDING_PAGE_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>محرك المنح الدراسية الذكي | Global Scholarship AI Engine</title>
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Google Fonts: Cairo -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Cairo', sans-serif; }
        .gradient-bg {
            background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
        }
        .glass-card {
            background: rgba(255, 255, 255, 0.04);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .chip-active {
            background: #2563eb !important;
            color: #ffffff !important;
            border-color: #3b82f6 !important;
            box-shadow: 0 0 15px rgba(37, 99, 235, 0.4);
        }
    </style>
</head>
<body class="gradient-bg min-h-screen text-slate-100 selection:bg-blue-600 selection:text-white">

    <!-- Navbar -->
    <header class="border-b border-slate-800/80 sticky top-0 z-50 backdrop-blur-md bg-slate-950/40">
        <div class="max-w-6xl mx-auto px-4 py-4 flex justify-between items-center">
            <div class="flex items-center space-x-3 space-x-reverse">
                <span class="text-3xl">🎓</span>
                <div>
                    <h1 class="text-lg md:text-xl font-extrabold text-white tracking-wide">Global Scholarship AI</h1>
                    <p class="text-xs text-blue-400 font-semibold">محرك الأوتوميشن الأسبوعي للمنح الدراسية</p>
                </div>
            </div>
            <div class="flex items-center space-x-3 space-x-reverse">
                <span id="subscribersBadge" class="hidden sm:inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    🟢 النظام نشط ويعمل سحابياً
                </span>
                <a href="https://github.com/medozaiter/scholarship-automation" target="_blank" class="text-xs md:text-sm bg-slate-800 hover:bg-slate-700 text-slate-200 px-3.5 py-1.5 rounded-lg border border-slate-700 transition flex items-center gap-1.5">
                    <span>GitHub ⭐</span>
                </a>
            </div>
        </div>
    </header>

    <!-- Hero Section -->
    <main class="max-w-4xl mx-auto px-4 py-10 md:py-16">
        <div class="text-center space-y-4 mb-12">
            <div class="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-sm font-semibold">
                <span>✨ خدمة مجانية ومفتوحة المصدر لجميع الطلبة</span>
            </div>
            <h2 class="text-3xl md:text-5xl font-black text-white leading-tight">
                احصل على أحدث المنح الموثوقة<br>
                <span class="bg-gradient-to-r from-blue-400 via-indigo-300 to-purple-400 bg-clip-text text-transparent">
                    مباشرة في بريدك الإلكتروني أسبوعياً 📩
                </span>
            </h2>
            <p class="text-slate-400 text-base md:text-lg max-w-2xl mx-auto leading-relaxed">
                حدد تخصصك وبريدك فقط، وسيقوم الذكاء الاصطناعي أسبوعياً بالبحث في المواقع والجامعات الرسمية، استبعاد الروابط المنتهية، وإرسال تقرير HTML فاخر وجدول Excel معتمد يضم 11 عاموداً تفصيلياً.
            </p>
        </div>

        <!-- Subscription Form Card -->
        <div class="glass-card rounded-2xl p-6 md:p-10 shadow-2xl relative overflow-hidden">
            <div class="absolute -top-24 -right-24 w-60 h-60 bg-blue-600/10 rounded-full blur-3xl pointer-events-none"></div>
            <div class="absolute -bottom-24 -left-24 w-60 h-60 bg-purple-600/10 rounded-full blur-3xl pointer-events-none"></div>

            <form id="subscribeForm" class="space-y-8 relative z-10">
                
                <!-- 1. Email & Name -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
                    <div>
                        <label class="block text-sm font-semibold text-slate-200 mb-2">البريد الإلكتروني لاستلام النتائج <span class="text-rose-400">*</span></label>
                        <input type="email" id="email" required placeholder="example@gmail.com"
                            class="w-full bg-slate-900/80 border border-slate-700/80 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition text-sm">
                    </div>
                    <div>
                        <label class="block text-sm font-semibold text-slate-200 mb-2">اسم الطالب (اختياري)</label>
                        <input type="text" id="fullName" placeholder="مثلاً: مصطفى زعيتر"
                            class="w-full bg-slate-900/80 border border-slate-700/80 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition text-sm">
                    </div>
                </div>

                <!-- 2. Degree Selection -->
                <div>
                    <label class="block text-sm font-semibold text-slate-200 mb-3">المرحلة الدراسية المطلوبة <span class="text-rose-400">*</span></label>
                    <div class="grid grid-cols-1 sm:grid-cols-3 gap-3" id="degreeGroup">
                        <button type="button" data-val="Undergraduate (Bachelor's)" class="degree-btn chip-active flex items-center justify-center gap-2 p-3.5 rounded-xl border border-slate-700 text-sm font-bold transition">
                            <span>🎓</span>
                            <span>بكالوريوس (Undergraduate)</span>
                        </button>
                        <button type="button" data-val="Master's Degree" class="degree-btn bg-slate-900/60 hover:bg-slate-800 flex items-center justify-center gap-2 p-3.5 rounded-xl border border-slate-700 text-sm font-bold text-slate-300 transition">
                            <span>📜</span>
                            <span>ماجستير (Master's)</span>
                        </button>
                        <button type="button" data-val="PhD / Doctorate" class="degree-btn bg-slate-900/60 hover:bg-slate-800 flex items-center justify-center gap-2 p-3.5 rounded-xl border border-slate-700 text-sm font-bold text-slate-300 transition">
                            <span>🔬</span>
                            <span>دكتوراه (PhD)</span>
                        </button>
                    </div>
                </div>

                <!-- 3. Majors Selection -->
                <div>
                    <div class="flex justify-between items-center mb-2">
                        <label class="block text-sm font-semibold text-slate-200">التخصصات المستهدفة (اختر أو اكتب تخصصك) <span class="text-rose-400">*</span></label>
                        <span class="text-xs text-slate-400">يمكنك اختيار أكثر من تخصص</span>
                    </div>

                    <!-- Quick Chips -->
                    <div class="flex flex-wrap gap-2 mb-3" id="majorChips">
                        <button type="button" data-major="Cybersecurity" class="major-chip chip-active px-3 py-1.5 rounded-lg border border-slate-700 text-xs font-semibold transition">الأمن السيبراني</button>
                        <button type="button" data-major="Software Engineering" class="major-chip chip-active px-3 py-1.5 rounded-lg border border-slate-700 text-xs font-semibold transition">هندسة البرمجيات</button>
                        <button type="button" data-major="Artificial Intelligence" class="major-chip chip-active px-3 py-1.5 rounded-lg border border-slate-700 text-xs font-semibold transition">الذكاء الاصطناعي</button>
                        <button type="button" data-major="Computer Science & IT" class="major-chip px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-900/60 text-slate-300 text-xs font-semibold transition">علوم الحاسوب وتكنولوجيا المعلومات</button>
                        <button type="button" data-major="Medicine & Healthcare" class="major-chip px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-900/60 text-slate-300 text-xs font-semibold transition">الطب البشري والعلوم الصحية</button>
                        <button type="button" data-major="Pharmacy" class="major-chip px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-900/60 text-slate-300 text-xs font-semibold transition">الصيدلة</button>
                        <button type="button" data-major="Civil & Electrical Engineering" class="major-chip px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-900/60 text-slate-300 text-xs font-semibold transition">الهندسة المدنية والكهربائية</button>
                        <button type="button" data-major="Business Administration & MBA" class="major-chip px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-900/60 text-slate-300 text-xs font-semibold transition">إدارة الأعمال والتمويل</button>
                    </div>

                    <!-- Custom Major Input -->
                    <input type="text" id="customMajor" placeholder="أو اكتب تخصصات إضافية هنا (مفصولة بفواصل)..."
                        class="w-full bg-slate-900/80 border border-slate-700/80 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 text-sm">
                </div>

                <!-- 4. Country of Origin -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-5 items-center">
                    <div>
                        <label class="block text-sm font-semibold text-slate-200 mb-2">الدولة / الجنسية المؤهلة</label>
                        <select id="country" class="w-full bg-slate-900/80 border border-slate-700/80 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500 text-sm">
                            <option value="Palestine" selected>🇵🇸 فلسطين (Palestine)</option>
                            <option value="Jordan">🇯🇴 الأردن (Jordan)</option>
                            <option value="Egypt">🇪🇬 مصر (Egypt)</option>
                            <option value="Syria">🇸🇾 سوريا (Syria)</option>
                            <option value="Lebanon">🇱🇧 لبنان (Lebanon)</option>
                            <option value="Yemen">🇾🇪 اليمن (Yemen)</option>
                            <option value="Iraq">🇮🇶 العراق (Iraq)</option>
                            <option value="Sudan">🇸🇩 السودان (Sudan)</option>
                            <option value="Morocco">🇲🇦 المغرب (Morocco)</option>
                            <option value="Algeria">🇩🇿 الجزائر (Algeria)</option>
                            <option value="International">🌍 طالب دولي (Any Country)</option>
                        </select>
                    </div>
                    <div class="pt-4 md:pt-6">
                        <label class="flex items-center gap-3 cursor-pointer">
                            <input type="checkbox" id="sendWelcome" checked class="w-4 h-4 rounded bg-slate-900 border-slate-700 text-blue-600 focus:ring-0">
                            <span class="text-xs text-slate-300">أرسل لي تقريراً ترحيبياً فورياً إلى الإيميل الآن ⚡</span>
                        </label>
                    </div>
                </div>

                <!-- Action Button -->
                <div class="pt-2">
                    <button type="submit" id="submitBtn" class="w-full bg-gradient-to-r from-blue-600 via-indigo-600 to-blue-700 hover:from-blue-500 hover:to-indigo-500 text-white font-bold py-4 px-6 rounded-xl shadow-lg shadow-blue-500/25 transition transform active:scale-[0.99] flex items-center justify-center gap-2">
                        <span id="btnText" class="text-base">🚀 تفعيل الاشتراك واستلام التقرير الأسبوعي مجاناً</span>
                        <div id="btnSpinner" class="hidden w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    </button>
                    <p class="text-center text-xs text-slate-400 mt-3">🔒 إيميلك آمن تماماً ولن يُستخدم إلا لإرسال دليل المنح فقط. يمكنك إلغاء الاشتراك في أي وقت.</p>
                </div>

                <!-- Alert Result Message -->
                <div id="alertBox" class="hidden p-4 rounded-xl text-sm font-semibold transition"></div>

            </form>
        </div>

        <!-- Features Grid -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16">
            <div class="glass-card p-6 rounded-xl border border-slate-800">
                <div class="text-3xl mb-3">🔍</div>
                <h3 class="text-lg font-bold text-white mb-2">بحث مستقل وتدقيق صارم</h3>
                <p class="text-sm text-slate-400 leading-relaxed">فحص فوري للمصادر والجامعات الرسمية واستبعاد المنح المنتهية أو غير الدقيقة.</p>
            </div>
            <div class="glass-card p-6 rounded-xl border border-slate-800">
                <div class="text-3xl mb-3">📊</div>
                <h3 class="text-lg font-bold text-white mb-2">11 عاموداً تفصيلياً معتمد</h3>
                <p class="text-sm text-slate-400 leading-relaxed">تغطية الرسوم، السكن، شروط المعدل واللغة، اختبارات القبول وتسهيلات فيزا الدراسة.</p>
            </div>
            <div class="glass-card p-6 rounded-xl border border-slate-800">
                <div class="text-3xl mb-3">📅</div>
                <h3 class="text-lg font-bold text-white mb-2">أوتوميشن دوري كل جمعة</h3>
                <p class="text-sm text-slate-400 leading-relaxed">تقرير أسبوعي محدث بصيغة HTML مريحة للعين مع ملف Excel/CSV مرفق مع كل إيميل.</p>
            </div>
        </div>

    </main>

    <!-- Footer -->
    <footer class="border-t border-slate-800/80 py-8 text-center text-xs text-slate-500">
        <p>تم التطوير بإتقان لدعم وتمكين الطلاب الطموحين في فلسطين والعالم العربي 🇵🇸🎓</p>
        <p class="mt-1">Global Scholarship AI Engine &copy; 2026 | مفتوح المصدر برخصة MIT</p>
    </footer>

    <!-- Script Logic -->
    <script>
        let selectedDegree = "Undergraduate (Bachelor's)";
        let selectedMajors = ["Cybersecurity", "Software Engineering", "Artificial Intelligence"];

        // Degree Buttons
        document.querySelectorAll('.degree-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.degree-btn').forEach(b => {
                    b.classList.remove('chip-active');
                    b.classList.add('bg-slate-900/60', 'text-slate-300');
                });
                btn.classList.add('chip-active');
                btn.classList.remove('bg-slate-900/60', 'text-slate-300');
                selectedDegree = btn.getAttribute('data-val');
            });
        });

        // Major Chips
        document.querySelectorAll('.major-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                const majorVal = chip.getAttribute('data-major');
                if (chip.classList.contains('chip-active')) {
                    chip.classList.remove('chip-active');
                    chip.classList.add('bg-slate-900/60', 'text-slate-300');
                    selectedMajors = selectedMajors.filter(m => m !== majorVal);
                } else {
                    chip.classList.add('chip-active');
                    chip.classList.remove('bg-slate-900/60', 'text-slate-300');
                    if (!selectedMajors.includes(majorVal)) {
                        selectedMajors.push(majorVal);
                    }
                }
            });
        });

        // Form Submit
        const form = document.getElementById('subscribeForm');
        const submitBtn = document.getElementById('submitBtn');
        const btnText = document.getElementById('btnText');
        const btnSpinner = document.getElementById('btnSpinner');
        const alertBox = document.getElementById('alertBox');

        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            // Collect custom majors if typed
            const customVal = document.getElementById('customMajor').value.trim();
            let finalMajors = [...selectedMajors];
            if (customVal) {
                const extras = customVal.split(/[,،]/).map(s => s.trim()).filter(Boolean);
                finalMajors.push(...extras);
            }

            if (finalMajors.length === 0) {
                alertBox.className = "p-4 rounded-xl text-sm font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20";
                alertBox.innerHTML = "⚠️ يرجى اختيار أو كتابة تخصص واحد على الأقل للمتابعة.";
                alertBox.classList.remove('hidden');
                return;
            }

            // Loading state
            submitBtn.disabled = true;
            btnText.textContent = "جارٍ التحقق وتفعيل الأوتوميشن...";
            btnSpinner.classList.remove('hidden');
            alertBox.classList.add('hidden');

            const payload = {
                email: document.getElementById('email').value.trim(),
                full_name: document.getElementById('fullName').value.trim() || "Student",
                degree: selectedDegree,
                majors: finalMajors,
                country: document.getElementById('country').value,
                send_welcome_report: document.getElementById('sendWelcome').checked
            };

            try {
                const res = await fetch('/api/subscribe', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();

                if (res.ok && data.success) {
                    alertBox.className = "p-5 rounded-xl text-sm font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 text-center";
                    alertBox.innerHTML = `
                        <div class="text-2xl mb-1">🎉 تهانينا! تم تفعيل اشتراكك بنجاح</div>
                        <div>${data.message}</div>
                        <div class="text-xs font-normal text-emerald-200/80 mt-2">تفقد صندوق الوارد في إيميلك (أو البريد غير الهام Spam) لرؤية أول تقرير مخصص لك.</div>
                    `;
                    alertBox.classList.remove('hidden');
                    form.reset();
                } else {
                    throw new Error(data.detail || data.message || "حدث خطأ أثناء حفظ الاشتراك.");
                }
            } catch (err) {
                alertBox.className = "p-4 rounded-xl text-sm font-semibold bg-rose-500/15 text-rose-300 border border-rose-500/30";
                alertBox.innerHTML = `❌ عذراً: ${err.message}`;
                alertBox.classList.remove('hidden');
            } finally {
                submitBtn.disabled = false;
                btnText.textContent = "🚀 تفعيل الاشتراك واستلام التقرير الأسبوعي مجاناً";
                btnSpinner.classList.add('hidden');
            }
        });
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.app:app", host="0.0.0.0", port=8000, reload=True)
