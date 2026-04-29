"""Unit tests for RabbitMQ payload and logic."""

from __future__ import annotations

import json
import pytest
import asyncio
import gzip
from uuid import uuid4
from src.queue.publisher import _create_watchdog_payload, publish_watchdog_task, publish_scraper_task
from src.queue.rabbitmq_client import get_rabbitmq_channel, close_rabbitmq, get_rabbitmq_connection
from src.queue.consumer import process_watchdog_task, start_consumers

@pytest.mark.unit
def test_watchdog_payload_structure() -> None:
    """Verify that the watchdog payload is correctly formatted."""
    file_path = "/data/watch/spy_2024-01-01.csv"
    market = "spy"
    
    payload = _create_watchdog_payload(file_path, market)
    
    assert payload["file_path"] == file_path
    assert payload["market"] == market
    assert payload["type"] == "file_upload"
    
    # Ensure it's JSON serializable
    json_str = json.dumps(payload)
    assert market in json_str


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_and_consume_watchdog_task(db_cleanup: None) -> None:
    """Verify that a task can be published to and consumed from RabbitMQ."""
    file_path = f"test_file_{uuid4()}.csv"
    market = "spy"
    
    # 1. Publish
    await publish_watchdog_task(file_path, market)
    
    # 2. Consume (manual check)
    channel = await get_rabbitmq_channel()
    queue = await channel.declare_queue("bs.watchdog", durable=True)
    
    while True:
        message = await queue.get(timeout=5)
        assert message is not None
        async with message.process():
            payload = json.loads(message.body.decode())
            if payload.get("file_path") == file_path:
                assert payload["market"] == market
                break


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_watchdog_task_compressed(db_cleanup: None) -> None:
    """Verify that large tasks are compressed in RabbitMQ."""
    from src.config import get_settings
    settings = get_settings()
    settings.enable_compression = True
    
    # Make it large enough to compress (> 1024)
    large_val = "x" * 2000
    file_path = f"large_{uuid4()}_{large_val}"
    market = "spy"
    
    await publish_watchdog_task(file_path, market)
    
    channel = await get_rabbitmq_channel()
    queue = await channel.declare_queue("bs.watchdog", durable=True)
    
    while True:
        message = await queue.get(timeout=5)
        assert message is not None
        async with message.process():
            body = message.body
            is_compressed = message.headers.get("content-encoding") == "gzip"
            if is_compressed:
                body = gzip.decompress(body)
            
            try:
                payload = json.loads(body.decode())
                if payload.get("file_path") == file_path:
                    assert is_compressed is True
                    break
            except Exception:
                continue


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_scraper_task(db_cleanup: None) -> None:
    """Verify scraper task publication."""
    run_id = f"run_{uuid4()}"
    await publish_scraper_task("spy", run_id)
    channel = await get_rabbitmq_channel()
    queue = await channel.declare_queue("bs.scrapers", durable=True)
    
    while True:
        message = await queue.get(timeout=5)
        assert message is not None
        async with message.process():
            payload = json.loads(message.body.decode())
            if payload.get("run_id") == run_id:
                assert payload["market"] == "spy"
                break


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_watchdog_task_logic(db_cleanup: None) -> None:
    """Verify the consumer callback logic with a simulated message."""
    file_path = f"test_callback_{uuid4()}.csv"
    await publish_watchdog_task(file_path, "spy")
    channel = await get_rabbitmq_channel()
    queue = await channel.declare_queue("bs.watchdog", durable=True)
    
    while True:
        message = await queue.get(timeout=5)
        assert message is not None
        body = message.body
        if message.headers.get("content-encoding") == "gzip":
            body = gzip.decompress(body)
        
        try:
            payload = json.loads(body.decode())
            if payload.get("file_path") == file_path:
                await process_watchdog_task(message)
                break
        except Exception:
            continue


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_watchdog_task_empty_payload(db_cleanup: None) -> None:
    """Verify consumer handles empty payload gracefully."""
    import aio_pika
    unique_id = str(uuid4())
    channel = await get_rabbitmq_channel()
    await channel.default_exchange.publish(
        aio_pika.Message(body=json.dumps({"_id": unique_id}).encode()),
        routing_key="bs.watchdog"
    )
    
    queue = await channel.declare_queue("bs.watchdog", durable=True)
    while True:
        message = await queue.get(timeout=5)
        assert message is not None
        try:
            payload = json.loads(message.body.decode())
            if payload.get("_id") == unique_id:
                await process_watchdog_task(message)
                break
        except Exception:
            continue


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_watchdog_task_invalid_json(db_cleanup: None) -> None:
    """Verify consumer handles invalid JSON gracefully."""
    import aio_pika
    channel = await get_rabbitmq_channel()
    queue = await channel.declare_queue("bs.watchdog", durable=True)
    await queue.purge()
    
    await channel.default_exchange.publish(
        aio_pika.Message(body=b"invalid json"),
        routing_key="bs.watchdog"
    )
    message = await queue.get(timeout=5)
    assert message is not None
    await process_watchdog_task(message)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_consumers() -> None:
    """Verify consumer startup."""
    await start_consumers()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_close_rabbitmq() -> None:
    """Verify RabbitMQ client closure."""
    await get_rabbitmq_channel()
    await close_rabbitmq()
    from src.queue.rabbitmq_client import RabbitMQManager
    assert RabbitMQManager._connection is None
    assert RabbitMQManager._channel is None
    # Double close should not raise
    await close_rabbitmq()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rabbitmq_reconnect_when_closed() -> None:
    """Verify reconnection logic when closed."""
    conn = await get_rabbitmq_connection()
    await conn.close()
    conn2 = await get_rabbitmq_connection()
    assert conn2 is not conn
    
    chan = await get_rabbitmq_channel()
    await chan.close()
    chan2 = await get_rabbitmq_channel()
    assert chan2 is not chan
