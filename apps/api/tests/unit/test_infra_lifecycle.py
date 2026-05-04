"""Unit tests for infrastructure lifecycle and edge cases (Zero-Mock)."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from src.cache.redis_client import RedisManager
from src.queue.rabbitmq_client import RabbitManager
from src.queue.consumer import ScraperConsumer


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_manager_lifecycle() -> None:
    """Test RedisManager close logic."""
    await RedisManager.get_instance()
    await RedisManager.close()
    assert RedisManager._redis is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rabbitmq_manager_lifecycle() -> None:
    """Test RabbitManager close logic."""
    await RabbitManager.get_instance()
    await RabbitManager.close()
    assert RabbitManager._connection is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rabbitmq_manager_reuse() -> None:
    """Test RabbitManager reuses open connection."""
    conn1 = await RabbitManager.get_instance()
    conn2 = await RabbitManager.get_instance()
    assert conn1 is conn2
    await RabbitManager.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scraper_consumer_logic() -> None:
    """Test ScraperConsumer class coverage."""
    received = []
    async def cb(p: dict[str, Any]) -> None:
        received.append(p)
    
    consumer = ScraperConsumer(cb)
    assert consumer.callback == cb
    
    task = asyncio.create_task(consumer.start())
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rabbitmq_manager_reconnect() -> None:
    """Test RabbitManager reconnection logic."""
    conn1 = await RabbitManager.get_instance()
    await conn1.close()
    conn2 = await RabbitManager.get_instance()
    assert conn1 is not conn2
    assert not conn2.is_closed
    await RabbitManager.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_manager_loop_change() -> None:
    """Test RedisManager re-init on loop change."""
    await RedisManager.get_instance()
    original_loop = RedisManager._loop
    
    # Simulate loop change by manually setting it to something else
    RedisManager._loop = "different" # type: ignore
    
    conn2 = await RedisManager.get_instance()
    assert RedisManager._loop != "different"
    assert RedisManager._loop == asyncio.get_running_loop()
    await RedisManager.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rabbitmq_manager_loop_change() -> None:
    """Test RabbitManager re-init on loop change."""
    await RabbitManager.get_instance()
    
    # Simulate loop change
    RabbitManager._loop = "different" # type: ignore
    
    conn2 = await RabbitManager.get_instance()
    assert RabbitManager._loop != "different"
    assert RabbitManager._loop == asyncio.get_running_loop()
    await RabbitManager.close()
