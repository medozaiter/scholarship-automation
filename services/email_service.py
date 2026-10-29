"""
Universal Email Delivery Service for ScholarPilot AI.
Primary provider: Resend API (HTTP REST API, no SMTP blocked ports).
Fallback provider: Gmail / Custom SMTP.
Local test fallback: Safe mock delivery logger.

Includes:
- Email Service Abstraction Layer (EmailService class)
- Inbox Deliverability Optimization (SPF / DKIM / DMARC / List-Unsubscribe / Precedence)
- 4 High-Conversion Responsive HTML Templates with Plain Text Fallbacks:
  1. New Scholarship Match Alert
  2. Scholarship Deadline Reminder
  3. Welcome & Profile Confirmation
  4. Weekly Curated Scholarship Digest
"""

import os
import base64
import logging
import smtplib
from email.message import EmailMessage
from typing import Optional, List, Dict, Any, Tuple
import httpx

from services.security_utils import sanitize_email_header

logger = logging.getLogger("scholarpilot.email")

RESEND_API_URL = "https://api.resend.com/emails"

_last_dispatch_meta: Dict[str, Any] = {
    "success": False,
    "provider": None,
    "recipient": None,
    "error_detail": None,
    "hint": None,
    "raw_resend_error": None
}


def get_last_dispatch_meta() -> Dict[str, Any]:
    """Returns the diagnostic metadata from the last email dispatch attempt."""
    return dict(_last_dispatch_meta)


# =====================================================================
# HTML EMAIL TEMPLATES & PLAIN TEXT GENERATION
# =====================================================================

def _email_wrapper(title: str, preheader: str, body_html: str, cta_url: str = "", cta_text: str = "") -> str:
    """Wraps template body in a resilient, responsive email design compatible with Gmail & Outlook."""
    cta_block = ""
    if cta_url and cta_text:
        cta_block = f"""
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="margin: 28px 0;">
          <tr>
            <td align="center">
              <a href="{cta_url}" target="_blank" style="background: linear-gradient(135deg, #2563eb, #3b82f6); color: #ffffff; text-decoration: none; padding: 14px 28px; border-radius: 8px; font-weight: bold; font-size: 15px; display: inline-block; box-shadow: 0 4px 12px rgba(37,99,235,0.3);">
                {cta_text} &larr;
              </a>
            </td>
          </tr>
        </table>
        """

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <title>{title}</title>
  <style>
    body, table, td, p, a {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
    body {{ margin: 0; padding: 0; background-color: #0b1120; color: #e2e8f0; }}
    .container {{ max-width: 600px; margin: 0 auto; background-color: #111827; border: 1px solid #1f2937; border-radius: 12px; overflow: hidden; }}
    .header {{ background: linear-gradient(135deg, #0f172a, #1e293b); padding: 28px 24px; text-align: center; border-bottom: 1px solid #374151; }}
    .content {{ padding: 28px 24px; direction: rtl; text-align: right; line-height: 1.7; font-size: 15px; }}
    .badge {{ display: inline-block; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: bold; background: #1e3a8a; color: #93c5fd; }}
    .card {{ background-color: #1f2937; border: 1px solid #374151; border-radius: 8px; padding: 18px; margin: 18px 0; }}
    .footer {{ background-color: #0b1120; padding: 20px 24px; text-align: center; font-size: 12px; color: #64748b; border-top: 1px solid #1f2937; }}
    .footer a {{ color: #3b82f6; text-decoration: none; }}
  </style>
</head>
<body style="margin: 0; padding: 20px 0; background-color: #0b1120;">
  <span style="display:none;font-size:1px;color:#0b1120;line-height:1px;max-height:0px;max-width:0px;opacity:0;overflow:hidden;">
    {preheader}
  </span>
  <table border="0" cellpadding="0" cellspacing="0" width="100%">
    <tr>
      <td align="center">
        <div class="container" style="max-width: 600px; background-color: #111827; border: 1px solid #1f2937; border-radius: 12px;">
          <div class="header" style="background-color: #0f172a; padding: 24px; text-align: center; border-bottom: 1px solid #1f2937;">
            <div style="font-size: 22px; font-weight: bold; color: #ffffff; letter-spacing: 0.5px;">
              🎓 Scholar<span style="color: #3b82f6;">Pilot</span> AI
            </div>
            <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">المستشار الأكاديمي الذكي لاقتناص المنح الدراسية</div>
          </div>
          <div class="content" style="padding: 28px 24px; color: #e2e8f0; direction: rtl; text-align: right;">
            {body_html}
            {cta_block}
          </div>
          <div class="footer" style="padding: 20px; font-size: 12px; color: #64748b; text-align: center; border-top: 1px solid #1f2937;">
            <p style="margin: 0 0 8px 0;">تصلك هذه الرسالة بناءً على اشتراكك في تنبيهات المنح الأكاديمية عبر ScholarPilot AI.</p>
            <p style="margin: 0;">
              <a href="https://scholarpilot-ai-mkac.onrender.com/dashboard" style="color: #3b82f6;">إدارة تفضيلات التنبيهات</a> &bull;
              <a href="https://scholarpilot-ai-mkac.onrender.com/assistant" style="color: #3b82f6;">المستشار الذكي</a>
            </p>
          </div>
        </div>
      </td>
    </tr>
  </table>
</body>
</html>"""


def render_new_match_template(
    student_name: str,
    scholarship: Dict[str, Any],
    match_score: int = 90,
    reasons: Optional[List[str]] = None
) -> Tuple[str, str]:
    """1. New Scholarship Match Alert Template (HTML + Plain text)."""
    title = scholarship.get("name") or scholarship.get("title", "منحة دراسية جديدة")
    country = scholarship.get("country", "")
    university = scholarship.get("university", "")
    degree = scholarship.get("degree", "جميع المراحل")
    deadline = scholarship.get("deadline_display") or scholarship.get("deadline", "قريباً")
    coverage = scholarship.get("coverage", "تمويل كامل")
    link = scholarship.get("link", "https://scholarpilot-ai-mkac.onrender.com")

    reasons_list = reasons or [
        f"المستوى الدراسي المطلوب: {degree}",
        f"الدولة المستهدفة: {country}",
        f"نسبة القبول التقديرية بناءً على سجلك الأكاديمي: {match_score}%"
    ]
    reasons_html = "".join([f"<li style='margin-bottom:6px; color:#cbd5e1;'>{r}</li>" for r in reasons_list])

    body_html = f"""
    <div style="text-align: center; margin-bottom: 20px;">
      <span class="badge" style="background:#1e3a8a; color:#93c5fd; padding:4px 12px; border-radius:999px; font-size:12px;">
        🎯 تطابق جديد بنسبة {match_score}%
      </span>
      <h2 style="color: #ffffff; margin: 12px 0 6px 0; font-size: 20px;">مرحباً {student_name or 'عزيزي الطالب'}، وجدنا لك فرصة مميزة!</h2>
      <p style="color: #94a3b8; font-size: 14px; margin: 0;">قام رادار المنح باكتشاف منحة دراسية تطابق ملفك الأكاديمي ومعاييرك المسجلة.</p>
    </div>

    <div class="card" style="background:#1f2937; border:1px solid #374151; border-radius:8px; padding:18px; margin:18px 0;">
      <h3 style="color:#60a5fa; margin:0 0 12px 0; font-size:17px;">{title}</h3>
      <table border="0" cellpadding="4" cellspacing="0" width="100%" style="font-size:14px; color:#cbd5e1;">
        <tr>
          <td width="30%" style="color:#94a3b8;">🌍 الدولة / الجامعة:</td>
          <td><strong>{country}</strong> {f'({university})' if university else ''}</td>
        </tr>
        <tr>
          <td style="color:#94a3b8;">📜 المرحلة الدراسية:</td>
          <td>{degree}</td>
        </tr>
        <tr>
          <td style="color:#94a3b8;">💰 التغطية المالية:</td>
          <td>{coverage}</td>
        </tr>
        <tr>
          <td style="color:#94a3b8;">⏰ الموعد النهائي:</td>
          <td><span style="color:#f59e0b; font-weight:bold;">{deadline}</span></td>
        </tr>
      </table>
    </div>

    <div style="margin: 20px 0;">
      <h4 style="color:#ffffff; margin:0 0 10px 0; font-size:15px;">لماذا تم ترشيح هذه المنحة لملفك؟</h4>
      <ul style="padding-right: 20px; margin: 0;">
        {reasons_html}
      </ul>
    </div>
    """

    html = _email_wrapper(
        title=f"🎯 فرصة منحة جديدة: {title}",
        preheader=f"منحة جديدة مطابقة لملفك الأكاديمي بنسبة {match_score}%: {title}",
        body_html=body_html,
        cta_url=link,
        cta_text="التقديم عبر البوابة الرسمية للمنحة"
    )

    plain_text = f"""مرحباً {student_name or 'عزيزي الطالب'}،

🎯 وجدنا لك منحة دراسية مطابقة لملفك الأكاديمي بنسبة {match_score}%:
المنحة: {title}
الدولة: {country} ({university})
المرحلة: {degree}
التمويل: {coverage}
الموعد النهائي: {deadline}

للتقديم الرسمي عبر بوابة المنحة:
{link}

ScholarPilot AI - مستشارك الأكاديمي
"""
    return html, plain_text


def render_deadline_reminder_template(
    student_name: str,
    scholarship: Dict[str, Any],
    days_left: int = 7,
    milestone: str = "تجهيز الوثائق النهائية"
) -> Tuple[str, str]:
    """2. Scholarship Deadline Reminder Template."""
    title = scholarship.get("name") or scholarship.get("title", "المنحة المحفوظة")
    country = scholarship.get("country", "")
    deadline = scholarship.get("deadline_display") or scholarship.get("deadline", "قريباً")
    link = scholarship.get("link", "https://scholarpilot-ai-mkac.onrender.com")

    body_html = f"""
    <div style="text-align: center; margin-bottom: 20px;">
      <span class="badge" style="background:#7c2d12; color:#fdba74; padding:4px 12px; border-radius:999px; font-size:12px;">
        ⚠️ تذكير بالموعد النهائي: متبقي {days_left} {'أيام' if days_left > 2 else 'يوم'}
      </span>
      <h2 style="color: #ffffff; margin: 12px 0 6px 0; font-size: 20px;">تنبيه اقتراب إغلاق باب التقديم</h2>
      <p style="color: #94a3b8; font-size: 14px; margin: 0;">منحة {title} تقترب من الموعد النهائي المحدد ({deadline}).</p>
    </div>

    <div class="card" style="background:#1f2937; border:1px solid #374151; border-radius:8px; padding:18px; margin:18px 0;">
      <h3 style="color:#f59e0b; margin:0 0 10px 0; font-size:16px;">خطوة التجهيز الموصى بها حالياً: {milestone}</h3>
      <p style="margin:0 0 12px 0; color:#cbd5e1; font-size:14px;">
        لضمان قبول طلبك وتفادي الضغط التقني في الساعات الأخيرة، ننصحك برفع الوثائق التالية عبر بوابة التقديم:
      </p>
      <ul style="padding-right: 20px; margin: 0; color:#cbd5e1; font-size:14px;">
        <li>كشف العلامات المترجم والمصدق رسميّاً.</li>
        <li>خطاب الدوافع (Statement of Purpose) بعد مراجعته بالذكاء الاصطناعي.</li>
        <li>رسالتا التوصية الأكاديميتان وتأكيد معلومات الأساتذة.</li>
      </ul>
    </div>
    """

    html = _email_wrapper(
        title=f"⚠️ تذكير موعد نهائي: {title} (متبقي {days_left} أيام)",
        preheader=f"متبقي {days_left} أيام على إغلاق منحة {title} - أكمل تقديمك الآن",
        body_html=body_html,
        cta_url=link,
        cta_text="فتح بوابة التقديم الرسمية واستكمال الطلب"
    )

    plain_text = f"""مرحباً {student_name or 'عزيزي الطالب'}،

⚠️ تذكير اقتراب الموعد النهائي:
منحة: {title} ({country})
متبقي: {days_left} أيام فقط
الموعد النهائي: {deadline}
المرحلة الحالية: {milestone}

رابط بوابة التقديم:
{link}

ScholarPilot AI - مستشارك الأكاديمي
"""
    return html, plain_text


def render_welcome_template(
    student_name: str,
    email: str,
    profile: Optional[Dict[str, Any]] = None
) -> Tuple[str, str]:
    """3. Welcome Email Template."""
    profile = profile or {}
    degree = profile.get("degree", "بكالوريوس / ماجستير")
    gpa = profile.get("gpa", "85%")
    country = profile.get("country", "فلسطين")
    majors = ", ".join(profile.get("majors", ["تكنولوجيا المعلومات"]))

    body_html = f"""
    <div style="text-align: center; margin-bottom: 20px;">
      <span class="badge" style="background:#065f46; color:#a7f3d0; padding:4px 12px; border-radius:999px; font-size:12px;">
        🎉 مرحباً بك في ScholarPilot AI
      </span>
      <h2 style="color: #ffffff; margin: 12px 0 6px 0; font-size: 20px;">تم تفعيل نظام رادار واقتناص المنح بنجاح!</h2>
      <p style="color: #94a3b8; font-size: 14px; margin: 0;">أهلاً بك يا {student_name or 'عزيزي الطالب'}. تم حفظ معاييرك الأكاديمية بنجاح.</p>
    </div>

    <div class="card" style="background:#1f2937; border:1px solid #374151; border-radius:8px; padding:18px; margin:18px 0;">
      <h3 style="color:#38bdf8; margin:0 0 10px 0; font-size:15px;">ملفك الأكاديمي المسجل:</h3>
      <table border="0" cellpadding="4" cellspacing="0" width="100%" style="font-size:14px; color:#cbd5e1;">
        <tr><td width="35%" style="color:#94a3b8;">المرحلة:</td><td>{degree}</td></tr>
        <tr><td style="color:#94a3b8;">المعدل:</td><td>{gpa}</td></tr>
        <tr><td style="color:#94a3b8;">التخصصات المستهدفة:</td><td>{majors}</td></tr>
        <tr><td style="color:#94a3b8;">الدولة الحالية:</td><td>{country}</td></tr>
      </table>
    </div>

    <div style="margin: 20px 0; color:#cbd5e1; font-size:14px;">
      <p><strong>ما الذي سيحدث الآن؟</strong></p>
      <ul style="padding-right: 20px;">
        <li>سيقوم رادار الذكاء الاصطناعي بمطابقة كل منحة جديدة فور فتحها مع ملفك.</li>
        <li>ستصلك تقارير أسبوعية بأفضل الفرص المتاحة ومواعيد التقديم.</li>
        <li>يمكنك في أي وقت محادثة المستشار الأكاديمي الذكي لحساب فرص قبولك ومراجعة سيرتك الذاتية.</li>
      </ul>
    </div>
    """

    html = _email_wrapper(
        title="🎉 أهلاً بك في ScholarPilot AI - تم تفعيل حسابك",
        preheader="تم تفعيل حسابك الأكاديمي في ScholarPilot AI ورادار المنح جاهز لتنبيهك",
        body_html=body_html,
        cta_url="https://scholarpilot-ai-mkac.onrender.com/dashboard",
        cta_text="زيارة لوحة التحكم واستكشاف المنح"
    )

    plain_text = f"""أهلاً بك {student_name or 'عزيزي الطالب'} في ScholarPilot AI!

تم تفعيل حسابك وتثبيت معايير ملفك الأكاديمي:
- المرحلة: {degree}
- المعدل: {gpa}
- التخصصات: {majors}

سيعمل النظام آلياً على إرسال تنبيهات المنح المطابقة فور صدورها.

لوحة التحكم:
https://scholarpilot-ai-mkac.onrender.com/dashboard

ScholarPilot AI
"""
    return html, plain_text


def render_weekly_digest_template(
    student_name: str,
    top_matches: List[Dict[str, Any]],
    closing_soon: Optional[List[Dict[str, Any]]] = None,
    advice: str = ""
) -> Tuple[str, str]:
    """4. Weekly Scholarship Digest Template."""
    matches_html = ""
    for item in top_matches[:4]:
        name = item.get("name", "منحة دراسية")
        country = item.get("country", "")
        deadline = item.get("deadline_display") or item.get("deadline", "قريباً")
        score = item.get("matchScore") or item.get("match_score", 90)
        link = item.get("link", "https://scholarpilot-ai-mkac.onrender.com")
        matches_html += f"""
        <div style="background:#111827; border:1px solid #374151; border-radius:6px; padding:12px; margin-bottom:10px;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <strong style="color:#ffffff; font-size:15px;">{name}</strong>
            <span style="color:#38bdf8; font-size:12px; font-weight:bold;">{score}% تطابق</span>
          </div>
          <div style="color:#94a3b8; font-size:13px; margin:4px 0;">🌍 {country} &bull; ⏰ الموعد: {deadline}</div>
          <a href="{link}" target="_blank" style="color:#60a5fa; font-size:13px; text-decoration:none; font-weight:bold;">رابط البوابة الرسمية &larr;</a>
        </div>
        """

    closing_html = ""
    if closing_soon:
        closing_items = "".join([f"<li><strong>{c.get('name')}</strong> ({c.get('country')}) - ينتهي {c.get('deadline_display')}</li>" for c in closing_soon[:3]])
        closing_html = f"""
        <div style="background:#451a03; border:1px solid #78350f; border-radius:8px; padding:14px; margin:18px 0; color:#fef3c7; font-size:14px;">
          <strong>⏳ منح توشك على الإغلاق هذا الأسبوع:</strong>
          <ul style="padding-right:20px; margin:8px 0 0 0;">
            {closing_items}
          </ul>
        </div>
        """

    advice_block = ""
    if advice:
        advice_block = f"""
        <div class="card" style="background:#1e293b; border-left:4px solid #3b82f6; padding:14px; margin:18px 0;">
          <strong style="color:#93c5fd; font-size:14px;">💡 نصيحة المستشار الذكي للأسبوع:</strong>
          <p style="margin:6px 0 0 0; color:#cbd5e1; font-size:13px;">{advice}</p>
        </div>
        """

    body_html = f"""
    <div style="text-align: center; margin-bottom: 20px;">
      <span class="badge" style="background:#1e3a8a; color:#93c5fd; padding:4px 12px; border-radius:999px; font-size:12px;">
        📬 النشرة الأسبوعية
      </span>
      <h2 style="color: #ffffff; margin: 12px 0 6px 0; font-size: 20px;">حصاد المنح الدراسية المفتوحة هذا الأسبوع</h2>
      <p style="color: #94a3b8; font-size: 14px; margin: 0;">إليك قائمة الفرص الأكثر تطابقاً مع تخصصك واهتماماتك الدراسية.</p>
    </div>

    <div style="margin: 18px 0;">
      <h3 style="color:#ffffff; font-size:16px; margin:0 0 12px 0;">أعلى الفرص تطابقاً مع ملفك:</h3>
      {matches_html}
    </div>

    {closing_html}
    {advice_block}
    """

    html = _email_wrapper(
        title="📬 نشرة المنح الأسبوعية - ScholarPilot AI",
        preheader=f"حصاد المنح الأسبوعي: تم رصد {len(top_matches)} منح مطابقة لملفك",
        body_html=body_html,
        cta_url="https://scholarpilot-ai-mkac.onrender.com",
        cta_text="استعراض كامل المنح في رادار المنح المفتوحة"
    )

    plain_text = f"""مرحباً {student_name or 'عزيزي الطالب'}،

إليك ملخص نشرة المنح الأسبوعية من ScholarPilot AI:
تم رصد {len(top_matches)} فرصة جديدة مطابقة لملفك.

يمكنك استعراض كل الفرص والتقديم عليها مباشرة من خلال:
https://scholarpilot-ai-mkac.onrender.com

ScholarPilot AI
"""
    return html, plain_text


# =====================================================================
# EMAIL SERVICE CLASS (ABSTRACTION LAYER)
# =====================================================================

class EmailService:
    """Enterprise-grade Email Delivery Abstraction Layer supporting Resend and SMTP."""

    def __init__(self):
        self.resend_api_key = os.getenv("RESEND_API_KEY")
        self.from_email = os.getenv("RESEND_FROM_EMAIL") or os.getenv("SENDER_EMAIL") or "ScholarPilot AI <onboarding@resend.dev>"

    async def dispatch_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        custom_headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """Dispatches an email with deliverability headers and automated provider fallback."""
        return await dispatch_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            attachments=attachments,
            custom_headers=custom_headers
        )

    async def send_new_match_alert(
        self,
        student_email: str,
        student_name: str,
        scholarship: Dict[str, Any],
        match_score: int = 90,
        reasons: Optional[List[str]] = None
    ) -> bool:
        """Sends a high-conversion new match alert email."""
        html, text = render_new_match_template(student_name, scholarship, match_score, reasons)
        title = scholarship.get("name") or scholarship.get("title", "منحة دراسية جديدة")
        return await self.dispatch_email(
            to_email=student_email,
            subject=f"🎯 فرصة منحة جديدة مطابقة لملفك الأكاديمي: {title}",
            html_content=html,
            text_content=text
        )

    async def send_deadline_reminder(
        self,
        student_email: str,
        student_name: str,
        scholarship: Dict[str, Any],
        days_left: int = 7,
        milestone: str = "تجهيز الوثائق النهائية"
    ) -> bool:
        """Sends an urgent deadline reminder email."""
        html, text = render_deadline_reminder_template(student_name, scholarship, days_left, milestone)
        title = scholarship.get("name") or scholarship.get("title", "المنحة المحفوظة")
        return await self.dispatch_email(
            to_email=student_email,
            subject=f"⚠️ تذكير موعد نهائي: متبقي {days_left} أيام للتقديم على منحة {title}",
            html_content=html,
            text_content=text
        )

    async def send_welcome_email(
        self,
        student_email: str,
        student_name: str,
        profile: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Sends a welcome confirmation email upon registration/subscription."""
        html, text = render_welcome_template(student_name, student_email, profile)
        return await self.dispatch_email(
            to_email=student_email,
            subject="🎉 أهلاً بك في ScholarPilot AI - تم تفعيل نظام رادار المنح بنجاح",
            html_content=html,
            text_content=text
        )

    async def send_weekly_digest(
        self,
        student_email: str,
        student_name: str,
        top_matches: List[Dict[str, Any]],
        closing_soon: Optional[List[Dict[str, Any]]] = None,
        advice: str = ""
    ) -> bool:
        """Sends the weekly curated digest email."""
        html, text = render_weekly_digest_template(student_name, top_matches, closing_soon, advice)
        return await self.dispatch_email(
            to_email=student_email,
            subject="📬 حصاد المنح الأسبوعية المفتوحة والمطابقة لملفك - ScholarPilot AI",
            html_content=html,
            text_content=text
        )


# Global singleton instance
email_service = EmailService()


# =====================================================================
# CORE DISPATCH FUNCTION (PRESERVED FOR BACKWARD COMPATIBILITY)
# =====================================================================

async def dispatch_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
    attachments: Optional[List[Dict[str, Any]]] = None,
    custom_headers: Optional[Dict[str, str]] = None
) -> bool:
    """
    Dispatches an email through Resend (primary cloud provider) or Gmail SMTP (fallback).
    Optimized for deliverability with SPF/DKIM compliance headers and List-Unsubscribe.
    attachments format: [{"filename": "report.csv", "content_bytes": b"..."}]
    """
    global _last_dispatch_meta
    resend_api_key = os.getenv("RESEND_API_KEY")
    resend_from_env = os.getenv("RESEND_FROM_EMAIL", "").strip()
    if resend_from_env and "@gmail.com" not in resend_from_env.lower():
        sender_name_email = resend_from_env
    else:
        sender_name_email = "ScholarPilot AI <onboarding@resend.dev>"

    clean_to = sanitize_email_header(to_email)
    clean_sub = sanitize_email_header(subject)

    _last_dispatch_meta = {
        "success": False,
        "provider": None,
        "recipient": clean_to,
        "error_detail": None,
        "hint": None,
        "raw_resend_error": None
    }

    # Standard deliverability headers (SPF/DKIM friendly, CAN-SPAM compliant)
    deliverability_headers = {
        "List-Unsubscribe": "<https://scholarpilot-ai-mkac.onrender.com/dashboard>, <mailto:unsubscribe@scholarpilot.ai>",
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        "Precedence": "bulk",
        "X-Auto-Response-Suppress": "OOF, AutoReply",
        "X-Entity-Ref-ID": f"sp_{int(os.times().system * 1000)}"
    }
    if custom_headers:
        deliverability_headers.update(custom_headers)

    # 1. Primary Cloud Provider: Resend HTTP REST API (Port 443)
    if resend_api_key and len(resend_api_key.strip()) > 5:
        logger.info(f"Dispatching email to {clean_to} via Resend API...")
        headers = {
            "Authorization": f"Bearer {resend_api_key.strip()}",
            "Content-Type": "application/json"
        }

        resend_attachments = []
        if attachments:
            for att in attachments:
                raw_bytes = att.get("content_bytes", b"")
                if isinstance(raw_bytes, str):
                    raw_bytes = raw_bytes.encode("utf-8")
                b64_content = base64.b64encode(raw_bytes).decode("utf-8")
                resend_attachments.append({
                    "filename": att.get("filename", "attachment.txt"),
                    "content": b64_content
                })

        payload: Dict[str, Any] = {
            "from": sender_name_email,
            "to": [clean_to],
            "subject": clean_sub,
            "html": html_content,
            "headers": deliverability_headers
        }
        if text_content:
            payload["text"] = text_content
        if resend_attachments:
            payload["attachments"] = resend_attachments

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(RESEND_API_URL, headers=headers, json=payload)
                if res.status_code in [200, 201]:
                    logger.info(f"✅ Delivered successfully to {clean_to} via Resend API (ID: {res.json().get('id')})")
                    _last_dispatch_meta["success"] = True
                    _last_dispatch_meta["provider"] = "Resend API"
                    return True
                else:
                    err_text = res.text
                    logger.warning(f"Resend API returned HTTP {res.status_code}: {err_text}")
                    _last_dispatch_meta["raw_resend_error"] = err_text
                    if "only send testing emails to your own email" in err_text:
                        _last_dispatch_meta["error_detail"] = (
                            "حساب Resend المجاني التجريبي مخصص للإرسال لبريد المالك فقط. "
                            "للإرسال لأي طالب في العالم عبر Render، يرجى تفعيل مفتاح Brevo API أو توثيق دومين في Resend."
                        )
                        _last_dispatch_meta["hint"] = "resend_sandbox_restriction"
                    else:
                        _last_dispatch_meta["error_detail"] = f"Resend API ({res.status_code}): {err_text[:160]}"
        except Exception as e:
            logger.warning(f"Resend API dispatch error: {e}")
            _last_dispatch_meta["error_detail"] = f"فشل اتصال Resend: {str(e)[:160]}"

    # 2. Secondary Cloud Provider: Brevo HTTP REST API (Port 443 - Unrestricted on Render)
    brevo_api_key = os.getenv("BREVO_API_KEY")
    if brevo_api_key and len(brevo_api_key.strip()) > 5:
        logger.info(f"Dispatching email to {clean_to} via Brevo HTTP REST API...")
        brevo_sender_email = os.getenv("BREVO_SENDER_EMAIL") or os.getenv("SENDER_EMAIL") or "scholarpilot.ai@gmail.com"
        brevo_sender_name = os.getenv("BREVO_SENDER_NAME") or "ScholarPilot AI"
        brevo_payload = {
            "sender": {"name": brevo_sender_name, "email": brevo_sender_email},
            "to": [{"email": clean_to}],
            "subject": clean_sub,
            "htmlContent": html_content
        }
        if text_content:
            brevo_payload["textContent"] = text_content
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res_b = await client.post(
                    "https://api.brevo.com/v3/smtp/email",
                    headers={"api-key": brevo_api_key.strip(), "Content-Type": "application/json"},
                    json=brevo_payload
                )
                if res_b.status_code in [200, 201]:
                    logger.info(f"✅ Delivered successfully to {clean_to} via Brevo HTTP API!")
                    _last_dispatch_meta["success"] = True
                    _last_dispatch_meta["provider"] = "Brevo HTTP API"
                    _last_dispatch_meta["error_detail"] = None
                    return True
                else:
                    logger.warning(f"Brevo API error {res_b.status_code}: {res_b.text}")
                    _last_dispatch_meta["error_detail"] = f"Brevo API ({res_b.status_code}): {res_b.text[:160]}"
        except Exception as eb:
            logger.warning(f"Brevo HTTP API dispatch exception: {eb}")

    # 3. Tertiary Provider: Universal SMTP (Works locally or on non-blocking hosts)
    smtp_user = os.getenv("SENDER_EMAIL") or os.getenv("EMAIL_USER")
    smtp_pass = os.getenv("GMAIL_APP_PASSWORD") or os.getenv("EMAIL_PASS") or os.getenv("SMTP_PASS")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    try:
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
    except ValueError:
        smtp_port = 587

    if smtp_user and smtp_pass:
        smtp_pass = smtp_pass.replace(" ", "").strip()
        provider_name = "Gmail SMTP" if "gmail" in smtp_host.lower() else f"SMTP ({smtp_host})"
        logger.info(f"Dispatching email to {clean_to} via {provider_name} [{smtp_host}:{smtp_port}]...")
        msg = EmailMessage()
        msg["Subject"] = clean_sub
        msg["From"] = sanitize_email_header(f"ScholarPilot AI <{smtp_user}>")
        msg["To"] = clean_to

        for hk, hv in deliverability_headers.items():
            msg[hk] = hv

        if text_content:
            msg.set_content(text_content)
        else:
            msg.set_content("Please view this email in an HTML-compatible client.")
        msg.add_alternative(html_content, subtype="html")

        if attachments:
            for att in attachments:
                raw_bytes = att.get("content_bytes", b"")
                filename = att.get("filename", "attachment.csv")
                subtype = "csv" if filename.endswith(".csv") else "plain"
                msg.add_attachment(raw_bytes, maintype="text", subtype=subtype, filename=filename)

        try:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=5) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
                logger.info(f"✅ Delivered successfully to {clean_to} via {provider_name} TLS!")
                _last_dispatch_meta["success"] = True
                _last_dispatch_meta["provider"] = provider_name
                _last_dispatch_meta["error_detail"] = None
                return True
        except Exception as e:
            err_msg = str(e)
            logger.error(f"SMTP TLS ({smtp_host}:{smtp_port}) failed: {e}")
            if "101" in err_msg or "unreachable" in err_msg.lower():
                _last_dispatch_meta["error_detail"] = "خادم الاستضافة Render يحظر منافذ SMTP (Port 587/465). يرجى استخدام Brevo API أو توثيق دومين Resend."
            else:
                _last_dispatch_meta["error_detail"] = f"فشل إرسال SMTP: {err_msg[:160]}"

    # 3. Fallback: If in production with RESEND_API_KEY configured and failed, report delivery failure
    if resend_api_key or os.getenv("RENDER"):
        logger.error(f"❌ Delivery to {clean_to} failed: Resend/SMTP could not deliver email.")
        if not _last_dispatch_meta["error_detail"]:
            _last_dispatch_meta["error_detail"] = "تعذر إرسال البريد عبر المزودين المتاحين."
        return False

    # 4. Local/Dev fallback logger
    logger.info(f"[DEV MOCK DISPATCH] Email to {clean_to} | Subject: '{clean_sub}' | (No RESEND_API_KEY or SMTP credentials configured).")
    _last_dispatch_meta["success"] = True
    _last_dispatch_meta["provider"] = "Dev Mock"
    return True


def get_email_provider_info() -> Dict[str, str]:
    """Returns current active email provider and status for health checks."""
    resend_key = os.getenv("RESEND_API_KEY", "").strip()
    if resend_key and len(resend_key) > 5:
        sender = os.getenv("RESEND_FROM_EMAIL") or "ScholarPilot AI <onboarding@resend.dev>"
        return {"provider": "Resend (HTTP REST API)", "sender": sender, "status": "active"}

    smtp_user = os.getenv("SENDER_EMAIL") or os.getenv("EMAIL_USER")
    smtp_pass = os.getenv("GMAIL_APP_PASSWORD") or os.getenv("EMAIL_PASS")
    if smtp_user and smtp_pass:
        return {"provider": "Gmail SMTP", "sender": smtp_user, "status": "active"}

    return {"provider": "Mock / Dev Logger", "sender": "local", "status": "dev_mode"}
