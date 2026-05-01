"""RabbitMQ task publishers."""

from __future__ import annotations

import json

import aio_pika
import structlog

from src.metrics import RABBITMQ_PUBLISHED
from src.queue.rabbitmq_client import get_rabbitmq

logger = structlog.get_logger(__name__)


async def publish_watchdog_task(file_path: str, market: str) -> None:
    """Publish a task to bs.watchdog queue."""
    connection = await get_rabbitmq()
    async with connection.channel() as channel:
        queue = await channel.declare_queue("bs.watchdog", durable=True)
        payload = {"file_path": file_path, "market": market}
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(payload).encode(), delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=queue.name,
        )
        RABBITMQ_PUBLISHED.labels(queue="bs.watchdog").inc()
        logger.info("watchdog_task_published", file_path=file_path, market=market)


async def publish_scraper_task(market: str, run_id: str | None = None) -> None:
    """Publish a task to bs.scrapers queue."""
    connection = await get_rabbitmq()
    async with connection.channel() as channel:
        queue = await channel.declare_queue("bs.scrapers", durable=True)
        payload = {"market": market, "run_id": run_id}
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(payload).encode(), delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=queue.name,
        )
        RABBITMQ_PUBLISHED.labels(queue="bs.scrapers").inc()
        logger.info("scraper_task_published", market=market)
