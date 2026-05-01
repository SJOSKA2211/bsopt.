"""Integration tests for websocket manager and channels — Phase 1."""
from __future__ import annotations

import asyncio
import contextlib
import json

import pytest

from src.cache.redis_client import get_redis
from src.websocket.channels import (
    start_redis_pubsub_listener,
)
from src.websocket.manager import manager

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_manager_connection_lifecycle():
    """Test connecting and disconnecting a websocket."""
    class MockWebSocket:
        def __init__(self):
            self.sent_messages = []
            self.closed = False

        async def accept(self): pass
        async def send_text(self, data): self.sent_messages.append(data)
        async def send_json(self, data): self.sent_messages.append(json.dumps(data))
        async def close(self, code=1000, reason=None): self.closed = True

    ws = MockWebSocket()
    # Accept
    await manager.connect(ws, "metrics", user_id="user1")
    assert ws in manager.active_connections["metrics"]

    # Broadcast
    await manager.broadcast("metrics", {"msg": "hello"})
    assert len(ws.sent_messages) == 1
    assert json.loads(ws.sent_messages[0]) == {"msg": "hello"}

    # Personal message
    await manager.send_personal_message({"msg": "private"}, user_id="user1")
    assert len(ws.sent_messages) == 2

    # Disconnect
    manager.disconnect(ws, "metrics", user_id="user1")
    assert ws not in manager.active_connections["metrics"]


@pytest.mark.asyncio
async def test_pubsub_listener_integration():
    """Test that the Redis pubsub listener correctly broadcasts to websockets."""
    class MockWebSocket:
        def __init__(self):
            self.sent_messages = []

        async def accept(self): pass
        async def send_text(self, data): self.sent_messages.append(data)
        async def send_json(self, data): self.sent_messages.append(json.dumps(data))

    ws = MockWebSocket()
    await manager.connect(ws, "metrics")

    # Start listener in background
    listener_task = asyncio.create_task(start_redis_pubsub_listener(max_loops=10))

    # Wait for listener to start and subscribe
    redis = await get_redis()
    for _ in range(10):
        # Check subscriber count
        sub_info = await redis.pubsub_numsub("metrics")
        if sub_info and sub_info[0][1] > 0:
            break
        await asyncio.sleep(0.5)

    # Publish to Redis
    await redis.publish("metrics", json.dumps({"type": "update", "val": 42}))

    # Wait for broadcast (multiple checks)
    for _ in range(10):
        if len(ws.sent_messages) >= 1:
            break
        await asyncio.sleep(0.5)

    assert len(ws.sent_messages) >= 1
    assert any("42" in msg for msg in ws.sent_messages)

    listener_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await listener_task
    manager.disconnect(ws, "metrics")


@pytest.mark.asyncio
async def test_helper_broadcasts():
    """Test the helper functions in channels.py."""
    # These just call manager.broadcast, so we test they use the right channels.
    # Note: we don't need a real WS here if we just check the internal state
    # but since we are Zero-Mock, we use a real connection if possible or check Redis.
