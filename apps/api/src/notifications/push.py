"""Web Push API implementation using pywebpush — Phase 10."""

from __future__ import annotations

import json

import structlog
from pywebpush import WebPushException, webpush

from src.config import get_settings
from src.database.repository import get_user_push_subscriptions
from src.notifications.hierarchy import Notification

logger = structlog.get_logger(__name__)


async def send_push_notification(n: Notification) -> bool:
    """Send web push notification using pywebpush."""
    settings = get_settings()
    if not settings.gh_vapid_private_key or not settings.gh_vapid_public_key:
        logger.warning("push_skipped_no_keys", user_id=n.user_id, step="notification", rows=0)
        return False

    # 1. Fetch user's push subscriptions from DB
    subscriptions = await get_user_push_subscriptions(n.user_id)

    if not subscriptions:
        logger.debug("push_no_subscriptions", user_id=n.user_id, step="notification", rows=0)
        return False

    success_count = 0
    for sub_json in subscriptions:
        try:
            subscription_info = json.loads(sub_json)
            webpush(
                subscription_info=subscription_info,
                data=json.dumps(
                    {
                        "title": n.title,
                        "body": n.body,
                        "url": n.action_url or "/",
                        "tag": f"bsopt-{n.severity}",
                    }
                ),
                vapid_private_key=settings.gh_vapid_private_key,
                vapid_claims={"sub": "mailto:admin@bsopt.example.com"},
            )
            success_count += 1
        except WebPushException as exc:
            logger.warning(
                "push_individual_failed",
                user_id=n.user_id,
                error=str(exc),
                step="notification",
                rows=0,
            )
        except Exception as exc:
            logger.error(
                "push_error", error=str(exc), severity="error", step="notification", rows=0
            )

    if success_count > 0:
        logger.info(
            "push_sent", user_id=n.user_id, count=success_count, step="notification", rows=0
        )
        return True
    return False
