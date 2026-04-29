"""RabbitMQ task publisher with optional compression — Phase 1."""

from __future__ import annotations

import gzip
import json
from typing import Any

import aio_pika
import structlog

from src.config import get_settings
from src.metrics import RABBITMQ_PUBLISHED
from src.queue.rabbitmq_client import get_rabbitmq_connection

logger = structlog.get_logger(__name__)


async def publish_watchdog_task(file_path: str, market: str) -> None:
    """Publish a file detection task to bs.watchdog queue."""
    payload = {"file_path": file_path, "market": market, "type": "file_upload"}
    await _publish("bs.watchdog", payload)


async def publish_scraper_task(market: str, run_id: str) -> None:
    """Publish a scraper trigger task to bs.scrapers queue."""
    payload = {"market": market, "run_id": run_id, "type": "scrape_trigger"}
    await _publish("bs.scrapers", payload)


async def _publish(queue_name: str, payload: dict[str, Any]) -> None:
    """Internal helper to publish a JSON message with optional compression."""
    settings = get_settings()
    connection = await get_rabbitmq_connection()

    async with connection.channel() as channel:
        queue = await channel.declare_queue(queue_name, durable=True)

        body = json.dumps(payload).encode("utf-8")
        headers = {}

        if settings.enable_compression and len(body) > 1024:
            body = gzip.compress(body)
            headers["content-encoding"] = "gzip"

        await channel.default_exchange.publish(
            aio_pika.Message(
                body=body,
                headers=headers,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
            ),
            routing_key=queue_name,
        )
        RABBITMQ_PUBLISHED.labels(queue=queue_name).inc()
        logger.info(
            "message_published",
            queue=queue_name,
            compressed="gzip" in headers,
            step="queue",
            rows=0,
        )
