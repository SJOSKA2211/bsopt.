"""RabbitMQ consumer — Phase 1."""

from __future__ import annotations

import gzip
import json

import aio_pika
import structlog

from src.metrics import RABBITMQ_CONSUMED
from src.queue.rabbitmq_client import get_rabbitmq_connection

logger = structlog.get_logger(__name__)


async def start_consumer() -> None:
    """Start consuming from all queues."""
    connection = await get_rabbitmq_connection()
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)

    # Watchdog queue
    watchdog_queue = await channel.declare_queue("bs.watchdog", durable=True)
    await watchdog_queue.consume(_process_watchdog_message)

    # Scraper queue
    scraper_queue = await channel.declare_queue("bs.scrapers", durable=True)
    await scraper_queue.consume(_process_scraper_message)

    logger.info("consumers_started", queues=["bs.watchdog", "bs.scrapers"], step="init", rows=0)


async def _process_watchdog_message(message: aio_pika.abc.AbstractIncomingMessage) -> None:
    """Process message from bs.watchdog queue."""
    async with message.process():
        try:
            body = message.body
            if message.headers.get("content-encoding") == "gzip":
                body = gzip.decompress(body)

            data = json.loads(body)
            logger.info("watchdog_message_received", data=data, step="queue", rows=0)

            # TODO: Call pipeline in later phase
            RABBITMQ_CONSUMED.labels(queue="bs.watchdog", status="success").inc()
        except Exception as exc:
            RABBITMQ_CONSUMED.labels(queue="bs.watchdog", status="error").inc()
            logger.error("watchdog_message_failed", error=str(exc), step="queue", rows=0)


async def _process_scraper_message(message: aio_pika.abc.AbstractIncomingMessage) -> None:
    """Process message from bs.scrapers queue."""
    async with message.process():
        try:
            data = json.loads(message.body)
            logger.info("scraper_message_received", data=data, step="queue", rows=0)

            # TODO: Call scraper in later phase
            RABBITMQ_CONSUMED.labels(queue="bs.scrapers", status="success").inc()
        except Exception as exc:
            RABBITMQ_CONSUMED.labels(queue="bs.scrapers", status="error").inc()
            logger.error("scraper_message_failed", error=str(exc), step="queue", rows=0)
