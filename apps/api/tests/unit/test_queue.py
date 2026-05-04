import asyncio
from typing import Any

import pytest

from src.queue.consumer import start_consumer
from src.queue.publisher import publish_scraper_task, publish_watchdog_task

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


async def test_publisher_and_consumer_integration() -> None:
    """Test full cycle: publish -> consume -> callback."""
    queue_name = "test_queue_integration"
    received_payloads: list[dict[str, Any]] = []

    async def callback(payload: dict[str, Any]) -> None:
        received_payloads.append(payload)

    # Start consumer in background
    consumer_task = asyncio.create_task(start_consumer(queue_name, callback))

    # Publish a few messages
    from src.queue.rabbitmq_client import get_rabbitmq

    connection = await get_rabbitmq()
    channel = await connection.channel()
    import json

    import aio_pika

    await channel.default_exchange.publish(
        aio_pika.Message(body=json.dumps({"test": "data"}).encode()), routing_key=queue_name
    )

    # Wait for consumption
    for _ in range(20):
        if received_payloads:
            break
        await asyncio.sleep(0.1)

    assert len(received_payloads) == 1
    assert received_payloads[0]["test"] == "data"

    consumer_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await consumer_task


async def test_publish_watchdog_task_real() -> None:
    """Test publish_watchdog_task hits the real broker."""
    await publish_watchdog_task("test.csv", "spy")


async def test_publish_scraper_task_real() -> None:
    """Test publish_scraper_task hits the real broker."""
    await publish_scraper_task("nse", "run_123")


async def test_consumer_error_handling() -> None:
    """Test that consumer handles callback errors without crashing the loop."""
    queue_name = "test_queue_error"

    async def failing_callback(payload: dict[str, Any]) -> None:
        raise ValueError("Simulated error")

    consumer_task = asyncio.create_task(start_consumer(queue_name, failing_callback))

    from src.queue.rabbitmq_client import get_rabbitmq

    connection = await get_rabbitmq()
    channel = await connection.channel()
    import json

    import aio_pika

    await channel.default_exchange.publish(
        aio_pika.Message(body=json.dumps({"error": "test"}).encode()), routing_key=queue_name
    )

    # Wait a bit
    await asyncio.sleep(0.5)

    # Task should still be running
    assert not consumer_task.done()

    consumer_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await consumer_task


async def test_redis_pubsub_integration() -> None:
    """Test Redis PubSub listener logic."""
    from src.cache.redis_client import get_redis
    from src.websocket.channels import start_redis_pubsub_listener

    # Start listener with 1 loop limit
    listener_task = asyncio.create_task(start_redis_pubsub_listener(max_loops=2))

    redis = await get_redis()
    import json

    # Publish to a channel the listener is watching
    await redis.publish("metrics", json.dumps({"cpu": 45}))

    # Wait for listener to process
    await asyncio.sleep(0.5)

    # We don't easily check the broadcast without mocking manager,
    # but we ensure it runs without error.
    await listener_task
