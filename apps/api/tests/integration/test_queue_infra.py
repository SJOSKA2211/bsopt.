"""Integration tests for RabbitMQ infrastructure."""

from __future__ import annotations
import pytest
import json
import asyncio
from src.queue.rabbitmq_client import get_rabbitmq_connection, get_rabbitmq_channel
from src.queue.publisher import publish_watchdog_task

@pytest.mark.asyncio
async def test_rabbitmq_connection_lifecycle() -> None:
    """Verify RabbitMQ connection and channel creation."""
    conn = await get_rabbitmq_connection()
    assert not conn.is_closed
    
    channel = await get_rabbitmq_channel()
    assert not channel.is_closed
    
    # Verify singleton behavior
    channel2 = await get_rabbitmq_channel()
    assert channel is channel2

@pytest.mark.asyncio
async def test_publish_and_consume_roundtrip() -> None:
    """Verify end-to-end task flow through RabbitMQ."""
    # 1. Publish
    await publish_watchdog_task("/tmp/test.csv", "spy")
    
    # 2. Consume (manually for test)
    channel = await get_rabbitmq_channel()
    queue = await channel.declare_queue("bs.watchdog", durable=True)
    
    # Get the message
    message = await queue.get(timeout=5)
    assert message is not None
    
    async with message.process():
        payload = json.loads(message.body.decode())
        assert payload["file_path"] == "/tmp/test.csv"
        assert payload["market"] == "spy"
