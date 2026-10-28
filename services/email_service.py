"""
Universal Email Delivery Service for ScholarPilot AI.
Primary provider: Resend API (HTTP REST API, no SMTP blocked ports).
Fallback provider: Gmail / Custom SMTP.
Local test fallback: Safe mock delivery logger.
"""

import os
import base64
import logging
import smtplib
from email.message import EmailMessage
from typing import Optional, List, Dict, Any
import httpx

from services.security_utils import sanitize_email_header

logger = logging.getLogger("scholarpilot.email")

RESEND_API_URL = "https://api.resend.com/emails"


async def dispatch_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
    attachments: Optional[List[Dict[str, Any]]] = None
) -> bool:
    """
    Dispatches an email through Resend (primary cloud provider) or Gmail SMTP (fallback).
    attachments format: [{"filename": "report.csv", "content_bytes": b"..."}]
    """
    resend_api_key = os.getenv("RESEND_API_KEY")
    sender_name_email = os.getenv("RESEND_FROM_EMAIL") or os.getenv("SENDER_EMAIL") or "ScholarPilot AI <onboarding@resend.dev>"
    clean_to = sanitize_email_header(to_email)
    clean_sub = sanitize_email_header(subject)

    # 1. Primary Cloud Provider: Resend HTTP REST API
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
            "html": html_content
        }
        if text_content:
            payload["text"] = text_content
        if resend_attachments:
            payload["attachments"] = resend_attachments

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(RESEND_API_URL, headers=headers, json=payload)
                if res.status_code in [200, 201]:
                    logger.info(f"✅ Delivered successfully to {clean_to} via Resend API (ID: {res.json().get('id')})")
                    return True
                else:
                    err_text = res.text
                    logger.warning(f"Resend API returned HTTP {res.status_code}: {err_text}")
                    if "only send testing emails to your own email" in err_text:
                        logger.warning(
                            "Resend Free Tier Restriction: When using onboarding@resend.dev, "
                            "emails can only be delivered to the account owner's email address. "
                            "To send to any recipient, add Gmail SMTP credentials (SENDER_EMAIL & GMAIL_APP_PASSWORD) "
                            "or verify a custom domain in Resend."
                        )
        except Exception as e:
            logger.warning(f"Resend API dispatch error: {e}. Trying SMTP fallback...")

    # 2. Secondary Provider: SMTP (Gmail / Custom)
    smtp_user = os.getenv("SENDER_EMAIL") or os.getenv("EMAIL_USER")
    smtp_pass = os.getenv("GMAIL_APP_PASSWORD") or os.getenv("EMAIL_PASS")

    if smtp_user and smtp_pass:
        smtp_pass = smtp_pass.replace(" ", "").strip()
        logger.info(f"Dispatching email to {clean_to} via SMTP (smtp.gmail.com)...")
        msg = EmailMessage()
        msg["Subject"] = clean_sub
        msg["From"] = sanitize_email_header(f"ScholarPilot AI <{smtp_user}>")
        msg["To"] = clean_to

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
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
                logger.info(f"✅ Delivered successfully to {clean_to} via SMTP TLS!")
                return True
        except Exception as e:
            logger.error(f"SMTP TLS failed: {e}. Trying SSL port 465...")
            try:
                with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
                    logger.info(f"✅ Delivered successfully to {clean_to} via SMTP SSL!")
                    return True
            except Exception as e2:
                logger.error(f"SMTP SSL also failed: {e2}")

    # 3. Fallback: If in production with RESEND_API_KEY configured and failed, report delivery failure
    if resend_api_key or os.getenv("RENDER"):
        logger.error(f"❌ Delivery to {clean_to} failed: Resend/SMTP could not deliver email.")
        return False

    # 4. Local/Dev fallback logger
    logger.info(f"[DEV MOCK DISPATCH] Email to {clean_to} | Subject: '{clean_sub}' | (No RESEND_API_KEY or SMTP credentials configured).")
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
