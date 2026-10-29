"""
Asynchronous Notification Queue & Worker for ScholarPilot AI.
Processes email, in-app, and Telegram notification dispatches asynchronously
with deduplication, rate control, and non-blocking background task execution.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Set
from datetime import datetime

from services.db import (
    is_notification_sent,
    record_notification,
    create_in_app_notification,
    record_notification_event
)

logger = logging.getLogger("scholarpilot.queue")

# Max queue size to prevent memory explosion
MAX_QUEUE_CAPACITY = 2000

# Queue instance
_notification_queue: asyncio.Queue = asyncio.Queue(maxsize=MAX_QUEUE_CAPACITY)

# In-memory deduplication set: prevents duplicate enqueuing within application lifecycle
_processed_fingerprints: Set[str] = set()
_worker_task: Optional[asyncio.Task] = None
_worker_running: bool = False

# Statistics
_queue_stats = {
    "enqueued": 0,
    "processed": 0,
    "skipped_duplicate": 0,
    "errors": 0,
    "started_at": None
}


def _make_fingerprint(recipient: str, notification_type: str, target_id: str, channel: str) -> str:
    """Builds a unique composite key for a notification dispatch."""
    return f"{channel.lower()}:{recipient.strip().lower()}:{notification_type.strip()}:{target_id.strip()}"


async def enqueue_notification(
    channel: str,
    recipient: str,
    notification_type: str,
    target_id: str,
    payload: Dict[str, Any],
    skip_dedup_check: bool = False
) -> bool:
    """
    Safely enqueues a notification job if not already processed or currently enqueued.
    Returns True if successfully queued, False if skipped (duplicate) or queue full.
    """
    clean_rec = recipient.strip().lower()
    fingerprint = _make_fingerprint(clean_rec, notification_type, target_id, channel)

    if not skip_dedup_check:
        # Check in-memory processed set
        if fingerprint in _processed_fingerprints:
            logger.debug(f"Queue skipped (in-memory duplicate): {fingerprint}")
            _queue_stats["skipped_duplicate"] += 1
            return False

        # Check database/JSON persistent history for email/alert duplicate prevention
        if is_notification_sent(clean_rec, notification_type, target_id):
            logger.debug(f"Queue skipped (persistent duplicate): {fingerprint}")
            _processed_fingerprints.add(fingerprint)
            _queue_stats["skipped_duplicate"] += 1
            return False

    job = {
        "channel": channel.lower(),
        "recipient": clean_rec,
        "notification_type": notification_type,
        "target_id": target_id,
        "payload": payload,
        "fingerprint": fingerprint,
        "enqueued_at": datetime.now().isoformat()
    }

    try:
        _notification_queue.put_nowait(job)
        _processed_fingerprints.add(fingerprint)
        _queue_stats["enqueued"] += 1
        logger.debug(f"Enqueued {channel} notification for {clean_rec} [{notification_type}:{target_id}]")
        return True
    except asyncio.QueueFull:
        logger.error("Notification queue is full! Job dropped.")
        _queue_stats["errors"] += 1
        return False


async def _process_job(job: Dict[str, Any]):
    """Dispatches an individual notification job by channel."""
    channel = job["channel"]
    recipient = job["recipient"]
    n_type = job["notification_type"]
    target_id = job["target_id"]
    payload = job["payload"]
    fingerprint = job["fingerprint"]

    # Record creation event
    record_notification_event(
        recipient=recipient,
        notification_type=n_type,
        channel=channel,
        target_id=target_id,
        status="created",
        meta={"enqueued_at": job.get("enqueued_at")}
    )

    success = False
    try:
        if channel == "email":
            from services.email_service import dispatch_email
            subject = payload.get("subject", "ScholarPilot AI Alert")
            html_content = payload.get("html_content", "")
            text_content = payload.get("text_content")
            attachments = payload.get("attachments")

            success = await dispatch_email(
                to_email=recipient,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                attachments=attachments
            )
            if success:
                record_notification(
                    recipient=recipient,
                    notification_type=n_type,
                    target_id=target_id,
                    subject=subject,
                    status="sent",
                    details=payload.get("details", {})
                )
                record_notification_event(
                    recipient=recipient,
                    notification_type=n_type,
                    channel="email",
                    target_id=target_id,
                    status="sent"
                )

        elif channel == "telegram":
            from services.telegram_service import telegram_service
            chat_id = payload.get("chat_id") or recipient
            scholarship = payload.get("scholarship")
            if scholarship:
                success = await telegram_service.send_scholarship_alert(chat_id=chat_id, scholarship=scholarship)
            else:
                text = payload.get("text", "")
                success = await telegram_service.send_message(chat_id=chat_id, text=text)

        elif channel == "in_app":
            title = payload.get("title", "تنبيه جديد")
            message = payload.get("message", "")
            notif_type = payload.get("type", "match")
            sch_id = payload.get("scholarship_id")
            link = payload.get("link")

            create_in_app_notification(
                recipient=recipient,
                title=title,
                message=message,
                notif_type=notif_type,
                scholarship_id=sch_id,
                link=link
            )
            record_notification_event(
                recipient=recipient,
                notification_type=n_type,
                channel="in_app",
                target_id=target_id,
                status="delivered"
            )
            success = True

        if success:
            _queue_stats["processed"] += 1
            logger.info(f"Successfully processed {channel} notification for {recipient} [{target_id}]")
        else:
            logger.warning(f"Notification processing completed with non-success state for {recipient}")

    except Exception as e:
        _queue_stats["errors"] += 1
        logger.error(f"Error processing notification job {fingerprint}: {e}", exc_info=True)


async def _worker_loop():
    """Main background queue consumer loop."""
    global _worker_running
    _worker_running = True
    logger.info("Notification Queue Worker started.")
    while _worker_running:
        try:
            job = await _notification_queue.get()
            try:
                await _process_job(job)
            finally:
                _notification_queue.task_done()
            # Small throttle to protect downstream APIs from sudden bursts
            await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            logger.info("Notification Queue Worker received cancellation signal.")
            break
        except Exception as e:
            logger.error(f"Unexpected worker loop exception: {e}")
            await asyncio.sleep(1.0)


def start_notification_worker() -> Optional[asyncio.Task]:
    """Starts the background worker task if not already running."""
    global _worker_task, _worker_running
    if _worker_task is None or _worker_task.done():
        _queue_stats["started_at"] = datetime.now().isoformat()
        _worker_task = asyncio.create_task(_worker_loop())
        logger.info("Notification Queue worker task spawned.")
    return _worker_task


def get_queue_status() -> Dict[str, Any]:
    """Returns runtime metrics for the notification queue."""
    return {
        "pending_jobs": _notification_queue.qsize(),
        "worker_running": _worker_running and (_worker_task is not None and not _worker_task.done()),
        **_queue_stats
    }
