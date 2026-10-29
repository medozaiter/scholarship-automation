"""
Telegram Notification Service for ScholarPilot AI.
Delivers real-time scholarship alerts and deadline reminders via Telegram Bot API.
"""

import os
import logging
from typing import Dict, Any, Optional
import httpx

from services.db import record_notification_event

logger = logging.getLogger("scholarpilot.telegram")

TELEGRAM_API_BASE = "https://api.telegram.org"


class TelegramService:
    """Service to send direct scholarship alert notifications via Telegram Bot."""

    def __init__(self, bot_token: Optional[str] = None):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")

    def is_configured(self) -> bool:
        """Returns True if a valid bot token is provided."""
        return bool(self.bot_token and len(self.bot_token.strip()) > 10)

    async def send_message(self, chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
        """Sends a generic text message to a user or channel chat_id."""
        if not self.is_configured():
            logger.debug("Telegram notifications skipped: TELEGRAM_BOT_TOKEN is not set.")
            return False

        if not chat_id or not chat_id.strip():
            logger.warning("Telegram dispatch aborted: Empty chat_id provided.")
            return False

        url = f"{TELEGRAM_API_BASE}/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id.strip(),
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": False
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    logger.info(f"Telegram alert delivered to chat {chat_id}")
                    return True
                else:
                    logger.warning(f"Telegram API returned status {resp.status_code}: {resp.text}")
                    return False
        except Exception as e:
            logger.error(f"Error dispatching Telegram message to {chat_id}: {e}")
            return False

    async def send_scholarship_alert(self, chat_id: str, scholarship: Dict[str, Any]) -> bool:
        """
        Formats and delivers a high-priority scholarship match alert.
        Contains: Title, Country, Degree, Deadline, and Official Apply Link.
        """
        title = scholarship.get("name") or scholarship.get("title", "منحة دراسية جديدة")
        university = scholarship.get("university", "")
        country = scholarship.get("country", "")
        degree = scholarship.get("degree", "جميع المراحل")
        deadline = scholarship.get("deadline_display") or scholarship.get("deadline", "قريباً")
        coverage = scholarship.get("coverage", "تمويل كامل / جزئي")
        link = scholarship.get("link", "https://scholarpilot-ai-mkac.onrender.com")

        lines = [
            "🎯 <b>فرصة منحة دراسية جديدة مطابقة لملفك الأكاديمي!</b>",
            "━━━━━━━━━━━━━━━━━━━",
            f"🎓 <b>المنحة:</b> {title}",
        ]
        if university:
            lines.append(f"🏛️ <b>الجهة / الجامعة:</b> {university}")
        if country:
            lines.append(f"🌍 <b>الدولة:</b> {country}")
        lines.append(f"📜 <b>المرحلة:</b> {degree}")
        lines.append(f"💰 <b>التمويل:</b> {coverage}")
        lines.append(f"⏰ <b>الموعد النهائي:</b> {deadline}")
        lines.append("━━━━━━━━━━━━━━━━━━━")
        lines.append(f'🔗 <a href="{link}"><b>اضغط هنا للتقديم عبر البوابة الرسمية للمنحة</b></a>')
        lines.append("")
        lines.append("<i>🚀 مرسلة عبر ScholarPilot AI - مستشارك الأكاديمي للتقديم والقبول</i>")

        text = "\n".join(lines)
        success = await self.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
        if success:
            record_notification_event(
                recipient=str(chat_id),
                notification_type="new_match_alert",
                channel="telegram",
                target_id=str(scholarship.get("id") or title),
                status="sent",
                meta={"title": title, "country": country, "degree": degree}
            )
        return success


# Global instance
telegram_service = TelegramService()
