"""
Telegram Notification & Channel Automation Service for ScholarPilot AI.
Delivers real-time scholarship alerts, deadline reminders, and automated channel broadcasts via Telegram Bot API.
"""

import os
import logging
from typing import Dict, Any, Optional
import httpx

from services.db import (
    record_notification_event,
    is_scholarship_published_to_telegram,
    save_scholarship_telegram_post,
    get_scholarship_telegram_post_id
)

logger = logging.getLogger("scholarpilot.telegram")

TELEGRAM_API_BASE = "https://api.telegram.org"


class TelegramService:
    """Service to send direct alerts and broadcast newly discovered scholarships to Telegram channel."""

    def __init__(self, bot_token: Optional[str] = None):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")

    def is_configured(self) -> bool:
        """Returns True if a valid bot token is provided."""
        return bool(self.bot_token and len(self.bot_token.strip()) > 10)

    def get_channel_id(self) -> str:
        """Returns the configured Telegram channel username or numeric chat ID."""
        return (
            os.getenv("TELEGRAM_CHANNEL_ID")
            or os.getenv("TELEGRAM_CHANNEL_USERNAME")
            or "@ScholarPilot"
        ).strip()

    def get_channel_url(self) -> str:
        """Returns the public web URL for students to join the Telegram channel."""
        explicit_url = os.getenv("TELEGRAM_CHANNEL_URL")
        if explicit_url and explicit_url.strip():
            return explicit_url.strip()

        ch_id = self.get_channel_id()
        if ch_id.startswith("@"):
            return f"https://t.me/{ch_id.lstrip('@')}"
        if ch_id.startswith("https://t.me/"):
            return ch_id
        return "https://t.me/ScholarPilot"

    async def send_message_raw(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "HTML",
        disable_preview: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Sends a message and returns the Telegram API result dict containing message_id."""
        if not self.is_configured():
            logger.debug("Telegram dispatch skipped: TELEGRAM_BOT_TOKEN is not set.")
            return None

        if not chat_id or not chat_id.strip():
            logger.warning("Telegram dispatch aborted: Empty chat_id provided.")
            return None

        url = f"{TELEGRAM_API_BASE}/bot{self.bot_token.strip()}/sendMessage"
        payload = {
            "chat_id": chat_id.strip(),
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_preview
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("ok"):
                        return data.get("result")
                    logger.warning(f"Telegram response error: {data}")
                    return None
                else:
                    logger.warning(f"Telegram API status {resp.status_code}: {resp.text}")
                    return None
        except Exception as e:
            logger.error(f"Error dispatching Telegram message to {chat_id}: {e}")
            return None

    async def send_message(self, chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
        """Sends a generic text message to a user or channel chat_id."""
        res = await self.send_message_raw(chat_id=chat_id, text=text, parse_mode=parse_mode)
        return bool(res)

    def format_scholarship_post(self, scholarship: Dict[str, Any]) -> str:
        """
        Formats a clean, high-conversion scholarship card post for the Telegram channel.
        Includes: title, country, degree level, deadline, funding coverage, and direct link.
        """
        title = scholarship.get("name") or scholarship.get("title", "منحة دراسية جديدة")
        university = scholarship.get("university") or scholarship.get("provider", "")
        country = scholarship.get("country", "")
        degree = scholarship.get("degree", "جميع المراحل الأكاديمية")
        deadline = scholarship.get("deadline_display") or scholarship.get("deadline", "قريباً")
        coverage = scholarship.get("coverage", "تمويل دراسي كامل أو جزئي")
        link = scholarship.get("link") or scholarship.get("official_link") or "https://scholarpilot-ai-mkac.onrender.com"

        lines = [
            "🎓 <b>منحة دراسية جديدة متاحة للتقديم الآن!</b>",
            "━━━━━━━━━━━━━━━━━━━━",
            f"📌 <b>المنحة:</b> {title}",
        ]
        if university or country:
            location_parts = [p for p in [country, university] if p]
            lines.append(f"🌍 <b>الدولة / الجهة:</b> {' - '.join(location_parts)}")
        lines.append(f"📜 <b>المرحلة الدراسية:</b> {degree}")
        lines.append(f"💰 <b>التمويل:</b> {coverage}")
        lines.append(f"⏰ <b>الموعد النهائي:</b> {deadline}")
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append(f'🔗 <a href="{link}"><b>اضغط هنا للتقديم عبر الرابط الرسمي</b></a>')
        lines.append("")
        lines.append("📢 <i>تابع أحدث المنح المعتمدة يومياً عبر قناة ScholarPilot الرسمية</i>")

        return "\n".join(lines)

    async def publish_scholarship_to_channel(
        self,
        scholarship: Dict[str, Any],
        channel_id: Optional[str] = None
    ) -> Optional[int]:
        """
        Automatically publishes a newly discovered scholarship to the official Telegram channel.
        - Prevents duplicate scholarship posts.
        - Stores the Telegram post message_id in the database.
        - Returns the Telegram message_id on success, or None on failure/skip.
        """
        s_id = str(scholarship.get("id") or "").strip()
        title = scholarship.get("name") or scholarship.get("title", "منحة دراسية")

        if not s_id:
            logger.warning("Telegram channel publish skipped: Scholarship missing valid ID.")
            return None

        # 1. Deduplication check
        if is_scholarship_published_to_telegram(s_id):
            existing_msg_id = get_scholarship_telegram_post_id(s_id)
            logger.info(f"Scholarship '{s_id}' already published to Telegram channel (Post ID: {existing_msg_id}). Skipping duplicate.")
            return int(existing_msg_id) if existing_msg_id and existing_msg_id.isdigit() else 1

        target_channel = (channel_id or self.get_channel_id()).strip()
        formatted_text = self.format_scholarship_post(scholarship)

        logger.info(f"Publishing scholarship '{title}' ({s_id}) to Telegram channel {target_channel}...")
        result = await self.send_message_raw(
            chat_id=target_channel,
            text=formatted_text,
            parse_mode="HTML"
        )

        if result and "message_id" in result:
            msg_id = result["message_id"]
            save_scholarship_telegram_post(
                scholarship_id=s_id,
                telegram_message_id=msg_id,
                channel_id=target_channel
            )
            logger.info(f"✅ Published scholarship '{s_id}' to Telegram channel successfully (Post ID: {msg_id})")
            return int(msg_id)
        else:
            logger.warning(f"Could not publish scholarship '{s_id}' to Telegram channel. Check bot channel administrator permissions.")
            return None

    async def send_scholarship_alert(self, chat_id: str, scholarship: Dict[str, Any]) -> bool:
        """
        Formats and delivers a high-priority personal scholarship match alert to a user.
        """
        title = scholarship.get("name") or scholarship.get("title", "منحة دراسية جديدة")
        university = scholarship.get("university", "")
        country = scholarship.get("country", "")
        degree = scholarship.get("degree", "جميع المراحل")
        deadline = scholarship.get("deadline_display") or scholarship.get("deadline", "قريباً")
        coverage = scholarship.get("coverage", "تمويل كامل / جزئي")
        link = scholarship.get("link") or scholarship.get("official_link") or "https://scholarpilot-ai-mkac.onrender.com"

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
