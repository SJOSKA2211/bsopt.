"""Unit tests for notification system."""

from __future__ import annotations

import pytest
import os
from src.notifications.hierarchy import Notification, NotificationRouter
from src.websocket.manager import ConnectionManager

class StubWebSocket:
    def __init__(self) -> None:
        self.sent_messages: list[str] = []
    async def accept(self): pass
    async def send_json(self, data):
        import json
        self.sent_messages.append(json.dumps(data))
    async def close(self, code=1000, reason=""): pass

@pytest.mark.unit
@pytest.mark.asyncio
async def test_notification_router_dispatch_info() -> None:
    manager = ConnectionManager()
    ws = StubWebSocket()
    await manager.connect(ws, "notifications", user_id="user1")  # type: ignore

    router = NotificationRouter(websocket_manager=manager)
    n = Notification(user_id="user1", title="Info", body="Body", severity="info")
    await router.dispatch(n)

    # Check WebSocket
    assert len(ws.sent_messages) == 1
    assert "Info" in ws.sent_messages[0]

@pytest.mark.unit
@pytest.mark.asyncio
async def test_notification_router_dispatch_critical() -> None:
    # We expect push and email to be skipped because of missing keys
    router = NotificationRouter()
    n = Notification(user_id="user1", title="Critical", body="Body", severity="critical")
    # Should not raise even if keys are missing
    await router.dispatch(n)

@pytest.mark.unit
@pytest.mark.asyncio
async def test_push_notification_skip() -> None:
    from src.notifications.push import send_push_notification
    n = Notification(user_id="user1", title="T", body="B")
    # Ensure keys are NOT set
    os.environ.pop("GH_VAPID_PRIVATE_KEY", None)
    os.environ.pop("GH_VAPID_PUBLIC_KEY", None)
    success = await send_push_notification(n)
    assert success is False

@pytest.mark.unit
@pytest.mark.asyncio
async def test_email_notification_skip() -> None:
    from src.notifications.email import send_email_notification
    n = Notification(user_id="user1", title="T", body="B")
    # Ensure key is NOT set
    os.environ.pop("RESEND_API_KEY", None)
    success = await send_email_notification(n)
    assert success is False
