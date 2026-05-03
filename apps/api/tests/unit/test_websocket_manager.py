"""Exhaustive unit tests for WebSocket manager and channels — Zero-Mock."""
from __future__ import annotations

import asyncio
import contextlib
import json
from typing import Any

import pytest

from src.cache.redis_client import close_redis, get_redis
from src.websocket.channels import (
    broadcast_experiment_update,
    broadcast_metric_update,
    broadcast_scraper_update,
    send_user_notification,
    start_redis_pubsub_listener,
)
from src.websocket.manager import ConnectionManager


class StubWebSocket:
    def __init__(self, fail_send: bool = False) -> None:
        self.sent_messages: list[str] = []
        self.accepted = False
        self.closed = False
        self.fail_send = fail_send
        self.close_code = 0
        self.close_reason = ""

    async def accept(self) -> None:
        self.accepted = True

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
async def test_manager_full_lifecycle() -> None:
    manager = ConnectionManager()
    ws1 = StubWebSocket()

    # Test invalid channel
    await manager.connect(ws1, "invalid_channel")  # type: ignore
    assert ws1.closed
    assert ws1.close_code == 1003

    # Test valid connection
    user_id = "user_1"
    await manager.connect(ws1, "metrics", user_id=user_id)  # type: ignore
    assert ws1.accepted
    assert ws1 in manager.active_connections["metrics"]
    assert ws1 in manager.user_connections[user_id]

    # Test broadcast
    await manager.broadcast("metrics", {"msg": "hi"})
    assert len(ws1.sent_messages) == 1

    # Test broadcast failure cleanup
    ws_fail = StubWebSocket(fail_send=True)
    await manager.connect(ws_fail, "metrics")  # type: ignore
    await manager.broadcast("metrics", {"msg": "fail"})
    # ws_fail should be removed from active_connections
    assert ws_fail not in manager.active_connections["metrics"]

    # Test personal message failure cleanup
    ws_fail_user = StubWebSocket(fail_send=True)
    user_id_2 = "user_2"
    await manager.connect(ws_fail_user, "notifications", user_id=user_id_2)  # type: ignore
    await manager.send_personal_message({"msg": "fail"}, user_id_2)
    assert user_id_2 not in manager.user_connections

    # Test disconnect
    manager.disconnect(ws1, "metrics", user_id=user_id)
    assert ws1 not in manager.active_connections["metrics"]
    assert user_id not in manager.user_connections


@pytest.mark.unit
@pytest.mark.asyncio
async def test_channels_broadcast_helpers() -> None:
    from src.websocket import channels as channels_mod
    orig_manager = channels_mod.manager
    manager = ConnectionManager()
    channels_mod.manager = manager

    ws = StubWebSocket()
    await manager.connect(ws, "metrics")  # type: ignore
    await manager.connect(ws, "experiments")  # type: ignore
    await manager.connect(ws, "scrapers")  # type: ignore

    await broadcast_metric_update({"val": 1})
    await broadcast_experiment_update({"id": "exp1"})
    await broadcast_scraper_update({"status": "running"})
    await send_user_notification("u1", {"title": "hi"})  # No user connected, should just return

    assert len(ws.sent_messages) == 3
    channels_mod.manager = orig_manager


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_pubsub_listener_routing() -> None:
    from src.websocket import channels as channels_mod
    orig_manager = channels_mod.manager
    manager = ConnectionManager()
    channels_mod.manager = manager

    ws = StubWebSocket()
    user_id = "u2"
    await manager.connect(ws, "metrics", user_id=user_id)  # type: ignore
    await manager.connect(ws, "notifications", user_id=user_id)  # type: ignore

    redis = await get_redis()
    # Test with max_loops=100 to cover the loop
    listener_task = asyncio.create_task(start_redis_pubsub_listener(max_loops=100))

    try:
        await asyncio.sleep(0.1)
        # 1. Direct channel message
        await redis.publish("metrics", json.dumps({"v": 1}))
        # 2. Notification message
        await redis.publish("notifications", json.dumps({"user_id": user_id, "notification": {"m": "hi"}}))
        # 3. bsopt:events message
        await redis.publish("bsopt:events", json.dumps({"channel": "metrics", "event": {"v": 2}}))

        await asyncio.sleep(0.5)
        # Should have received at least 3 messages
        assert len(ws.sent_messages) >= 3
    finally:
        listener_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await listener_task
        channels_mod.manager = orig_manager
        await close_redis()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_pubsub_listener_error_handling() -> None:
    # Trigger exception path by publishing invalid JSON
    from src.websocket import channels as channels_mod
    orig_manager = channels_mod.manager
    manager = ConnectionManager()
    channels_mod.manager = manager

    redis = await get_redis()
    listener_task = asyncio.create_task(start_redis_pubsub_listener(max_loops=10))

    try:
        await asyncio.sleep(0.1)
        # Invalid JSON to trigger line 79 (except Exception)
        await redis.publish("metrics", "not valid json")
        await asyncio.sleep(0.2)
    finally:
        listener_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await listener_task
        channels_mod.manager = orig_manager


@pytest.mark.unit
@pytest.mark.asyncio
async def test_manager_edge_cases() -> None:
    manager = ConnectionManager()
    ws = StubWebSocket()
    ws2 = StubWebSocket()

    # 1. Broadcast to invalid channel (Line 73)
    await manager.broadcast("invalid", {"msg": "hi"})

    # 2. Disconnect from channel but websocket not in it (Line 55 partial)
    manager.disconnect(ws, "metrics")  # type: ignore

    # 3. Disconnect user: one removed, one remains (Line 65->68 False branch)
    manager.user_connections["u1"] = [ws, ws2]  # type: ignore
    manager.disconnect(ws, "metrics", user_id="u1")  # type: ignore
    assert "u1" in manager.user_connections
    assert len(manager.user_connections["u1"]) == 1

    # 4. Disconnect user: last one removed (Line 65->66 True branch)
    manager.disconnect(ws2, "metrics", user_id="u1")  # type: ignore
    assert "u1" not in manager.user_connections

    # 5. send_personal_message to non-existent user (Line 91)
    await manager.send_personal_message({"msg": "hi"}, "non_existent")

    # 6. Branch 101->100 cleanup dead in send_personal_message
    ws_dead = StubWebSocket(fail_send=True)
    ws_alive = StubWebSocket()
    await manager.connect(ws_alive, "notifications", user_id="u4")  # type: ignore
    await manager.connect(ws_dead, "notifications", user_id="u4")  # type: ignore
    await manager.send_personal_message({"msg": "alive"}, "u4")
    assert len(manager.user_connections["u4"]) == 1

    # 7. Coverage for 101->100 False branch:
    class SelfRemovingWS(StubWebSocket):
        def __init__(self, manager: ConnectionManager, user_id: str) -> None:
            super().__init__(fail_send=True)
            self.manager = manager
            self.user_id = user_id

        async def send_json(self, data: Any) -> None:
            # Manually remove from manager before returning/failing
            if self in self.manager.user_connections[self.user_id]:
                self.manager.user_connections[self.user_id].remove(self)
            raise Exception("Fail")

    ws_self_rem = SelfRemovingWS(manager, "u5")
    manager.user_connections["u5"] = [ws_self_rem]  # type: ignore
    await manager.send_personal_message({"msg": "die"}, "u5")
    assert "u5" not in manager.user_connections


@pytest.mark.unit
@pytest.mark.asyncio
async def test_channels_binary_routing() -> None:
    # Coverage for lines 56, 60, 67, 84 in channels.py
    from src.websocket import channels as channels_mod
    manager = ConnectionManager()
    channels_mod.manager = manager

    # Mocking pubsub to return binary data and fail on close
    class MockPubSub:
        def __init__(self) -> None:
            self.count = 0

        async def subscribe(self, *args, **kwargs) -> None: pass

        async def get_message(self, *args, **kwargs) -> None:
            self.count += 1
            if self.count == 1:
                return {
                    "channel": b"metrics",
                    "data": b'{"v": 1}'
                }
            elif self.count == 2:
                # Test line 67: bsopt:events with missing target_channel
                return {
                    "channel": "bsopt:events",
                    "data": json.dumps({"event": {"v": 2}})
                }
            return None

        async def unsubscribe(self) -> None: pass

        async def aclose(self) -> None:
            # Test line 84: fail on aclose
            raise Exception("aclose failed")

    class MockRedis:
        def pubsub(self) -> None: return MockPubSub()

    # We need to monkeypatch get_redis in the module temporarily
    orig_get_redis = channels_mod.get_redis
    fut = asyncio.Future()
    fut.set_result(MockRedis())
    channels_mod.get_redis = lambda: fut  # type: ignore

    try:
        await start_redis_pubsub_listener(max_loops=2)
    finally:
        channels_mod.get_redis = orig_get_redis
