"""
CLI Entry point for GitHub Actions and scheduled cron jobs.
Executes weekly personalized scholarship digests and deadline reminder monitors.
"""
import asyncio
import logging
import sys
from services.automation_service import AutomationService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("scholarpilot.dispatcher")

async def main():
    logger.info("Initializing ScholarPilotAI Weekly Dispatcher...")
    service = AutomationService()
    
    # 1. Run live scholarship discovery to refresh catalogue
    try:
        logger.info("Discovering live scholarship opportunities...")
        await service.run_automated_scholarship_discovery()
    except Exception as e:
        logger.warning(f"Scholarship discovery step warning: {e}")

    # 2. Dispatch weekly personalized digests
    try:
        logger.info("Dispatching weekly digests to active subscribers...")
        digest_res = await service.auto_dispatch_weekly_digests()
        logger.info(f"Weekly digest dispatch finished: {digest_res}")
    except Exception as e:
        logger.error(f"Weekly digest dispatch error: {e}")

    # 3. Dispatch approaching deadline reminders
    try:
        logger.info("Evaluating approaching scholarship deadlines...")
        await service.auto_dispatch_deadline_reminders()
        logger.info("Deadline monitor cycle finished.")
    except Exception as e:
        logger.error(f"Deadline reminder monitor error: {e}")

    logger.info("ScholarPilotAI Dispatcher tasks completed.")

if __name__ == "__main__":
    asyncio.run(main())
