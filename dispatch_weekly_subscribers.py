import asyncio
import logging
from datetime import datetime
from services.subscriber_service import SubscriberService
from services.scholarship_engine import ScholarshipEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def dispatch_all():
    """Loops through all active subscribers and dispatches their tailored scholarship reports."""
    sub_service = SubscriberService()
    engine = ScholarshipEngine()

    subscribers = sub_service.get_all(active_only=True)
    logger.info(f"=== Starting Weekly Scholarship Dispatch for {len(subscribers)} Active Subscribers ===")

    success_count = 0
    fail_count = 0

    for idx, sub in enumerate(subscribers, 1):
        email = sub.get("email")
        full_name = sub.get("full_name", "Student")
        degree = sub.get("degree", "Undergraduate (Bachelor's)")
        majors = sub.get("majors", ["Software Engineering", "Cybersecurity"])
        country = sub.get("country", "Palestine")

        logger.info(f"[{idx}/{len(subscribers)}] Processing report for: {full_name} ({email}) - {degree}")

        try:
            ok = await engine.send_personalized_report(
                recipient_email=email,
                student_name=full_name,
                degree=degree,
                majors=majors,
                country=country
            )
            if ok:
                success_count += 1
                sub_service.update_last_sent(email)
                logger.info(f"✅ Delivered successfully to: {email}")
            else:
                fail_count += 1
                logger.warning(f"❌ Failed delivery to: {email}")
        except Exception as e:
            fail_count += 1
            logger.error(f"Error processing subscriber {email}: {e}")

        # Short pause between student sends to respect Gmail rate limits
        await asyncio.sleep(2)

    logger.info(f"=== Dispatch Completed: {success_count} Succeeded, {fail_count} Failed ===")


if __name__ == "__main__":
    asyncio.run(dispatch_all())
