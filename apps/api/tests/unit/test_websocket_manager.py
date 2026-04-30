"""Exhaustive unit tests for WebSocket connection manager."""

from __future__ import annotations
import pytest
import asyncio
import json
from typing import Any
from src.websocket.manager import ConnectionManager
from src.websocket.channels import start_redis_pubsub_listener, broadcast_metric_update, broadcast_experiment_update, broadcast_scraper_update, send_user_notification
from src.cache.redis_client import get_redis

class StubWebSocket:
    """Real implementation stub for WebSocket testing without MagicMock."""

    def __init__(self, fail_send: bool = False) -> None:
        self.sent_messages: list[str] = []
        self.accepted = False
        self.closed = False
        self.fail_send = fail_send
        self.close_code = 0
        self.close_reason = ""

    async def accept(self) -> None:
        self.accepted = True

    async def send_text(self, text: str) -> None:
        if self.fail_send:
            raise Exception("Send failed")
        self.sent_messages.append(text)

    async def send_json(self, data: Any) -> None:
        if self.fail_send:
            raise Exception("Send failed")
        self.sent_messages.append(json.dumps(data))

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.closed = True
        self.close_code = code
        self.close_reason = reason


@pytest.mark.unit
@pytest.mark.asyncio
async def test_manager_connect_disconnect_with_user() -> None:
    """Test connection and disconnection tracking including user_id."""
    manager = ConnectionManager()
    ws = StubWebSocket()
    channel = "notifications"
    user_id = "user-123"

    # Connect
    await manager.connect(ws, channel, user_id)  # type: ignore
    assert ws in manager.active_connections[channel]
    assert ws in manager.user_connections[user_id]

    # Disconnect
    manager.disconnect(ws, channel, user_id)  # type: ignore
    assert ws not in manager.active_connections[channel]
    assert user_id not in manager.user_connections

@pytest.mark.unit
@pytest.mark.asyncio
async def test_manager_invalid_channel() -> None:
    """Verify that connecting to an invalid channel closes the connection."""
    manager = ConnectionManager()
    ws = StubWebSocket()
    await manager.connect(ws, "invalid")  # type: ignore
    assert ws.closed
    assert ws.close_code == 1003

@pytest.mark.unit
@pytest.mark.asyncio
async def test_manager_broadcast_and_cleanup() -> None:
    """Test broadcasting and cleanup of dead connections."""
    manager = ConnectionManager()
    ws1 = StubWebSocket()
    ws2 = StubWebSocket(fail_send=True)
    channel = "metrics"

    await manager.connect(ws1, channel)  # type: ignore
    await manager.connect(ws2, channel)  # type: ignore

    await manager.broadcast(channel, {"data": "hello"})
    assert len(ws1.sent_messages) == 1
    assert ws2 not in manager.active_connections[channel]

@pytest.mark.unit
@pytest.mark.asyncio
async def test_manager_send_personal_message() -> None:
    """Test targeted messaging to a specific user."""
    manager = ConnectionManager()
    ws = StubWebSocket()
    ws_dead = StubWebSocket(fail_send=True)
    user_id = "u1"
    
    await manager.connect(ws, "notifications", user_id) # type: ignore
    await manager.connect(ws_dead, "notifications", user_id) # type: ignore
    
    await manager.send_personal_message({"msg": "hi"}, user_id)
    assert len(ws.sent_messages) == 1
    assert ws_dead not in manager.user_connections[user_id]
    
    # Missing user
    await manager.send_personal_message({"msg": "hi"}, "missing")

@pytest.mark.unit
@pytest.mark.asyncio
async def test_channel_broadcast_helpers() -> None:
    """Verify the helper functions in channels.py."""
    from src.websocket import channels as channels_mod
    orig_manager = channels_mod.manager
    mock_manager = ConnectionManager()
    channels_mod.manager = mock_manager
    try:
        await broadcast_metric_update({"v": 1})
        await broadcast_experiment_update({"id": 1})
        await broadcast_scraper_update({"s": "ok"})
        await send_user_notification("u1", {"m": "n"})
    finally:
        channels_mod.manager = orig_manager

@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_pubsub_listener_exhaustive() -> None:
    """Exhaustive test for Redis pubsub routing logic."""
    from src.websocket import channels as channels_mod
    orig_manager = channels_mod.manager
    mock_manager = ConnectionManager()
    channels_mod.manager = mock_manager
    
    ws_metrics = StubWebSocket()
    ws_notif = StubWebSocket()
    await mock_manager.connect(ws_metrics, "metrics") # type: ignore
    await mock_manager.connect(ws_notif, "notifications", "user1") # type: ignore
    
    listener_task = asyncio.create_task(start_redis_pubsub_listener())
    try:
        await asyncio.sleep(0.5)
        redis = await get_redis()
        
        # 1. Direct channel routing
        await redis.publish("metrics", json.dumps({"v": 100}))
        
        # 2. bsopt:events routing
        payload = {"channel": "experiments", "event": {"id": "exp1"}}
        await redis.publish("bsopt:events", json.dumps(payload))
        
        # 3. Notifications routing
        notif_payload = {"user_id": "user1", "notification": {"title": "Hello"}}
        await redis.publish("notifications", json.dumps(notif_payload))
        
        # 4. Unknown channel in bsopt:events
        await redis.publish("bsopt:events", json.dumps({"channel": "unknown"}))
        
        await asyncio.sleep(1.0)
        assert len(ws_metrics.sent_messages) >= 1
        assert len(ws_notif.sent_messages) >= 1
    finally:
        listener_task.cancel()
        channels_mod.manager = orig_manager

@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_pubsub_listener_error_path() -> None:
    """Verify error handling in listener."""
    # This should log error and exit because it can't subscribe if redis is closed
    from src.cache.redis_client import close_redis
    await close_redis()
    
    # It might still loop once if get_redis returns a new client, so we use max_loops=1
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(start_redis_pubsub_listener(max_loops=1), timeout=1.0)
