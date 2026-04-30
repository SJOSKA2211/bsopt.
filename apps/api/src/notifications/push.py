"""Web Push notification service using pywebpush — Python 3.14."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import structlog
from pywebpush import WebPushException, webpush

from src.config import get_settings
from src.database.repository import get_user_push_subscriptions

if TYPE_CHECKING:
    from src.notifications.hierarchy import Notification

logger = structlog.get_logger(__name__)
settings = get_settings()


async def send_push_notification(n: Notification) -> bool:
    """Send a Web Push alert to all registered devices for a user."""
    if not settings.gh_vapid_private_key or not settings.gh_vapid_public_key:
        logger.warning("vapid_keys_missing", user_id=n.user_id)
        return False

    # Fetch subscriptions from the DB
    subscriptions = await get_user_push_subscriptions(n.user_id)
    if not subscriptions:
        return False

    success_count = 0
    payload = {
        "title": n.title,
        "body": n.body,
        "icon": "/icons/icon-192x192.png",
        "data": {"url": n.action_url or "/dashboard"},
    }

    for sub_item in subscriptions:
        try:
            subscription_info = json.loads(sub_item) if isinstance(sub_item, str) else sub_item
            webpush(
                subscription_info=subscription_info,
                data=json.dumps(payload),
                vapid_private_key=settings.gh_vapid_private_key,
                vapid_claims={"sub": f"mailto:{settings.resend_from_email}"},
            )
            success_count += 1
        except WebPushException as exc:
            logger.error("push_failed", user_id=n.user_id, error=str(exc))
        except Exception as exc:
            logger.error("push_exception", user_id=n.user_id, error=str(exc))


async def send_web_push(subscription_info: Any, title: str, body: str) -> bool:
    """Utility to send a direct web push."""
    import os

    private_key = os.environ.get("VAPID_PRIVATE_KEY")
    if not private_key:
        return False
    try:
        webpush(
            subscription_info=(
                subscription_info
                if not isinstance(subscription_info, str)
                else json.loads(subscription_info)
            ),
            data=json.dumps({"title": title, "body": body}),
            vapid_private_key=private_key,
            vapid_claims={"sub": "mailto:admin@example.com"},
        )
        return True
    except Exception as exc:
        logger.error("web_push_utility_failed", error=str(exc))
        return False
