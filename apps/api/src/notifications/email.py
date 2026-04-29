"""Resend transactional email implementation — Phase 10."""

from __future__ import annotations

import resend
import structlog

from src.config import get_settings
from src.notifications.hierarchy import Notification

logger = structlog.get_logger(__name__)


async def send_email_notification(n: Notification) -> bool:
    """Send transactional email via Resend."""
    settings = get_settings()
    if not settings.resend_api_key:
        logger.warning("email_skipped_no_api_key", user_id=n.user_id, step="notification", rows=0)
        return False

    resend.api_key = settings.resend_api_key

    try:
        # Note: In a real system, we would lookup the user's email from the DB
        # For this implementation, we assume user_id is the email or we use a fallback
        email_to = n.user_id if "@" in n.user_id else "onboarding@resend.dev"

        resend.Emails.send(
            {
                "from": "bsopt@resend.dev",
                "to": email_to,
                "subject": n.title,
                "html": f"<strong>{n.title}</strong><p>{n.body}</p>",
            }
        )
        logger.info("email_sent", user_id=n.user_id, step="notification", rows=0)
        return True
    except Exception as exc:
        logger.error(
            "email_failed",
            user_id=n.user_id,
            error=str(exc),
            severity="error",
            step="notification",
            rows=0,
        )
        return False
