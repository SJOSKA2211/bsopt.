"""Email notification service using Resend — Python 3.14."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import structlog

from src.config import get_settings

if TYPE_CHECKING:
    from src.notifications.hierarchy import Notification

logger = structlog.get_logger(__name__)
settings = get_settings()


async def send_email_notification(n: Notification) -> bool:
    """Send an email alert via Resend API."""
    if not settings.resend_api_key:
        logger.warning("resend_api_key_missing", user_id=n.user_id)
        return False

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {settings.resend_api_key}",
        "Content-Type": "application/json",
    }

    # In a real app, we would fetch the user's email from the DB
    # For now, we use a placeholder or assume user_id is the email for demo
    payload = {
        "from": "bsopt@resend.dev",
        "to": [n.user_id if "@" in n.user_id else "alerts@bsopt.example.com"],
        "subject": n.title,
        "html": (
            f"<p>{n.body}</p><a href='{n.action_url}'>View Details</a>"
            if n.action_url
            else f"<p>{n.body}</p>"
        ),
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 201:
                logger.info("email_sent", user_id=n.user_id, title=n.title)
                return True
            else:
                logger.error("email_failed", status=response.status_code, body=response.text)
                return False
    except Exception as exc:
        logger.error("email_exception", error=str(exc))
        return False


async def send_transactional_email(to: str, subject: str, body: str) -> bool:
    """Utility to send a direct transactional email."""
    import os

    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        return False
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "from": "onboarding@resend.dev",
                    "to": [to],
                    "subject": subject,
                    "html": body,
                },
            )
            return response.status_code == 201
    except Exception as exc:
        logger.error("transactional_email_failed", error=str(exc))
        return False
