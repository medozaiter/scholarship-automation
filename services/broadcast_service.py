import os
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from services.search_service import SearchService
from services.gemini_service import GeminiService

load_dotenv()

logger = logging.getLogger(__name__)

search_service = SearchService(max_results=8)
gemini_service: GeminiService | None = None

def get_gemini_service() -> GeminiService:
    global gemini_service
    if gemini_service is None:
        gemini_service = GeminiService()
    return gemini_service

CORE_TRACKS = [
    {"degree": "Undergraduate", "majors": ["Cybersecurity", "Software Engineering"], "country": "Palestine"},
    {"degree": "Undergraduate", "majors": ["Artificial Intelligence", "Computer Science"], "country": "Palestine"},
    {"degree": "Master's Degree", "majors": ["Computer Science", "Information Technology"], "country": "Palestine"},
]

async def broadcast_to_channel_if_configured(
    bot,
    title: str,
    institution: str,
    deadline: str,
    coverage: str,
    official_url: str
) -> None:
    """Broadcasts urgent scholarship announcement to the public Telegram channel if configured."""
    channel_id = os.getenv("TELEGRAM_CHANNEL_ID")
    if not channel_id or channel_id.strip() == "":
        return

    # Check if already broadcasted
    if await db.is_broadcasted(official_url):
        return

    bot_username = (await bot.get_me()).username or "ScholarshipFinderBot"

    message = (
        "📢 <b>إعلان منحة عاجلة وممولة | Urgent Scholarship Alert</b> 🎓\n\n"
        f"🏛 <b>البرنامج:</b> {title}\n"
        f"📍 <b>الجهة/الدولة:</b> {institution}\n"
        f"⏳ <b>الموعد النهائي:</b> {deadline}\n"
        f"💰 <b>التغطية:</b> {coverage}\n\n"
        "⚠️ <i>ملاحظة: يرجى التأكد من تاريخ الإغلاق عبر الرابط الرسمي.</i>"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 الرابط الرسمي للتقديم", url=official_url)],
        [InlineKeyboardButton("🤖 افتح البوت للبحث الشامل", url=f"https://t.me/{bot_username}?start=channel")]
    ])

    try:
        await bot.send_message(
            chat_id=channel_id,
            text=message,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        await db.mark_broadcasted(official_url)
        logger.info(f"Successfully broadcasted scholarship to channel {channel_id}: {title}")
    except Exception as e:
        logger.warning(f"Could not broadcast to channel {channel_id}: {e}")


async def daily_scholarship_indexing_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Automated background crawler running every 24 hours:
    1. Crawls active scholarships for core tracks.
    2. Updates SQLite cache and repository.
    3. Notifies subscribed students.
    4. Posts urgent discoveries to the public Telegram channel.
    """
    logger.info("Starting automated 24-hour scholarship background indexing job...")
    bot = context.bot

    for track in CORE_TRACKS:
        degree = track["degree"]
        majors = track["majors"]
        country = track["country"]

        try:
            results = await search_service.search_scholarships(
                degree=degree,
                majors=majors,
                funding="Fully Funded",
                country=country
            )

            if not results:
                continue

            # Analyze and cache report
            report_html = await get_gemini_service().analyze_and_format_scholarships(
                search_results=results,
                degree=degree,
                majors=majors,
                funding="Fully Funded",
                country=country
            )

            cache_key = f"{degree}:{' '.join(majors)}:Fully Funded:{country}"
            await db.set_cached_search(cache_key, report_html)

            # Check individual top entries to index and notify subscribers
            for item in results[:3]:
                url = item.get("url")
                title = item.get("title", "International Scholarship")
                if not url:
                    continue

                is_new = await db.save_scholarship({
                    "title": title,
                    "institution": "Global / Official",
                    "country": country,
                    "degree": degree,
                    "major": majors[0],
                    "funding_type": "Fully Funded",
                    "deadline": "Open / Check Portal",
                    "status": "Active",
                    "coverage": "Full Tuition & Living",
                    "requirements": "See official portal for GPA & IELTS requirements",
                    "official_url": url,
                    "raw_content": item.get("snippet", "")
                })

                if is_new:
                    # Notify channel
                    await broadcast_to_channel_if_configured(
                        bot=bot,
                        title=title,
                        institution="International University / Partner",
                        deadline="قريباً / راجع البوابة الرسمية",
                        coverage="ممولة بالكامل",
                        official_url=url
                    )

                    # Notify subscribed users
                    subscribers = await db.get_matching_subscribers(degree, majors[0])
                    for sub_chat_id in subscribers:
                        try:
                            alert_msg = (
                                "🔔 <b>تنبيه منحة جديدة متوافقة مع تخصصك!</b> 🎓\n\n"
                                f"📌 <b>المنحة:</b> {title}\n"
                                f"🎓 <b>الدرجة:</b> {degree} - {majors[0]}\n"
                                "⚠️ <i>يرجى التأكد من تاريخ الإغلاق والشروط عبر الرابط الرسمي:</i>\n\n"
                                f"🔗 <a href=\"{url}\">اضغط هنا للانتقال للبوابة الرسمية</a>"
                            )
                            await bot.send_message(
                                chat_id=sub_chat_id,
                                text=alert_msg,
                                parse_mode=ParseMode.HTML,
                                disable_web_page_preview=True
                            )
                        except Exception as e:
                            logger.debug(f"Failed to push alert to subscriber {sub_chat_id}: {e}")

        except Exception as e:
            logger.error(f"Error during background indexing for {track}: {e}")

    logger.info("24-hour background scholarship indexing job completed successfully.")
