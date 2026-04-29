"""Notification hierarchy and routing logic — Phase 10."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import structlog

from src.metrics import NOTIFICATIONS_SENT
from src.websocket.manager import manager

logger = structlog.get_logger(__name__)

Severity = Literal["info", "warning", "error", "critical"]
Channel = Literal["email", "websocket", "push"]


@dataclass(frozen=True)
class Notification:
    user_id: str
    title: str
    body: str
    severity: Severity = "info"
    action_url: str | None = None


class NotificationRouter:
    """Dispatches notifications to multiple channels based on severity."""

    async def dispatch(self, notification: Notification) -> None:
        """Route notification to appropriate channels."""
        # 1. Always send to WebSocket for in-app real-time update
        await self._to_websocket(notification)

        # 2. Critical/Error severity triggers Push and Email
        if notification.severity in ("critical", "error"):
            await self._to_push(notification)
            await self._to_email(notification)

        # 3. Warnings trigger Push
        elif notification.severity == "warning":
            await self._to_push(notification)

        logger.info(
            "notification_dispatched",
            user_id=notification.user_id,
            severity=notification.severity,
            title=notification.title,
            step="notification",
            rows=0,
        )

    async def _to_websocket(self, n: Notification) -> None:
        """Internal: Send to WebSocket."""
        payload = {
            "type": "notification",
            "data": {
                "title": n.title,
                "body": n.body,
                "severity": n.severity,
                "action_url": n.action_url,
            },
        }
        await manager.send_personal_message(payload, n.user_id)
        NOTIFICATIONS_SENT.labels(channel="websocket", severity=n.severity).inc()

    async def _to_push(self, n: Notification) -> None:
        """Internal: Send to Web Push API."""
        from src.notifications.push import send_push_notification

        success = await send_push_notification(n)
        if success:
            NOTIFICATIONS_SENT.labels(channel="push", severity=n.severity).inc()

    async def _to_email(self, n: Notification) -> None:
        """Internal: Send to Resend email service."""
        from src.notifications.email import send_email_notification

        success = await send_email_notification(n)
        if success:
            NOTIFICATIONS_SENT.labels(channel="email", severity=n.severity).inc()
