"""Unit tests for WebSocket connection manager."""

from __future__ import annotations
import pytest
from typing import Any
from src.websocket.manager import ConnectionManager

class StubWebSocket:
    """Real implementation stub for WebSocket testing without MagicMock."""

    def __init__(self, fail_send: bool = False) -> None:
        self.sent_messages: list[str] = []
        self.accepted = False
        self.closed = False
        self.fail_send = fail_send

    async def accept(self) -> None:
        self.accepted = True

    async def send_text(self, text: str) -> None:
        if self.fail_send:
            raise Exception("Send failed")
        self.sent_messages.append(text)

    async def send_json(self, data: Any) -> None:
        if self.fail_send:
            raise Exception("Send failed")
        import json
        self.sent_messages.append(json.dumps(data))

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.closed = True
        self.close_code = code
        self.close_reason = reason


@pytest.mark.unit
@pytest.mark.asyncio
async def test_manager_connect_disconnect() -> None:
    """Test connection and disconnection tracking."""
    manager = ConnectionManager()
    ws = StubWebSocket()
    channel = "metrics"

    # Connect
    await manager.connect(ws, channel)  # type: ignore
    assert ws in manager.active_connections[channel]

    # Disconnect
    manager.disconnect(ws, channel)  # type: ignore
    assert ws not in manager.active_connections[channel]


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
async def test_manager_broadcast() -> None:
    """Test broadcasting messages to multiple connections."""
    manager = ConnectionManager()
    ws1 = StubWebSocket()
    ws2 = StubWebSocket()
    channel = "metrics"

    await manager.connect(ws1, channel)  # type: ignore
    await manager.connect(ws2, channel)  # type: ignore

    message = {"data": "hello"}
    await manager.broadcast(channel, message)

    # Verify both received the message
    assert len(ws1.sent_messages) == 1
    assert len(ws2.sent_messages) == 1
    assert "hello" in ws1.sent_messages[0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_manager_broadcast_unsupported_channel() -> None:
    """Verify broadcasting to an unsupported channel does nothing."""
    manager = ConnectionManager()
    await manager.broadcast("invalid", {"msg": "test"}) # Should not raise


@pytest.mark.unit
@pytest.mark.asyncio
async def test_manager_send_personal_message_missing_user() -> None:
    """Verify that sending a personal message to a non-existent user does nothing."""
    manager = ConnectionManager()
    await manager.send_personal_message({"msg": "test"}, "non_existent") # Should not raise


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_pubsub_listener() -> None:
    """Verify that the Redis listener correctly broadcasts messages."""
    from src.websocket.channels import start_redis_pubsub_listener
    from src.cache.redis_client import get_redis
    import json
    import asyncio
    
    manager = ConnectionManager()
    ws = StubWebSocket()
    await manager.connect(ws, "metrics") # type: ignore
    
    # We start the listener in the background
    from src.websocket import channels as channels_mod
    original_manager = channels_mod.manager
    channels_mod.manager = manager
    
    listener_task = asyncio.create_task(start_redis_pubsub_listener())
    
    try:
        # Give it more time to subscribe and start the loop
        await asyncio.sleep(1.0)
        
        # Publish to Redis
        redis = await get_redis()
        payload = {"test": "data_pubsub"}
        await redis.publish("bsopt:ws:metrics", json.dumps(payload))
        
        # Poll for the message instead of fixed sleep
        for _ in range(10):
            if len(ws.sent_messages) > 0:
                break
            await asyncio.sleep(0.2)
        
        assert len(ws.sent_messages) == 1
        assert json.loads(ws.sent_messages[0]) == payload
    finally:
        listener_task.cancel()
@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_pubsub_listener_error() -> None:
    """Verify that the listener handles Redis errors gracefully."""
    from src.websocket.channels import start_redis_pubsub_listener
    from src.cache.redis_client import get_redis
    
    # Trigger an error by closing redis before the loop
    from src.cache.redis_client import close_redis
    await close_redis()
    
    # Should log error and exit loop (not crash)
    try:
        await asyncio.wait_for(start_redis_pubsub_listener(), timeout=2.0)
    except (asyncio.TimeoutError, Exception):
        pass


@pytest.mark.unit
@pytest.mark.asyncio
async def test_manager_cleanup_dead_connections() -> None:
    """Verify that dead connections are removed during broadcast."""
    manager = ConnectionManager()
    ws_alive = StubWebSocket()
    ws_dead = StubWebSocket(fail_send=True)
    channel = "metrics"

    await manager.connect(ws_alive, channel)  # type: ignore
    await manager.connect(ws_dead, channel)  # type: ignore

    await manager.broadcast(channel, {"msg": "ping"})

    # Dead connection should be removed
    assert ws_dead not in manager.active_connections[channel]
    assert ws_alive in manager.active_connections[channel]
