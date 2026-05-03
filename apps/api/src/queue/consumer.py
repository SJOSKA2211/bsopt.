"""RabbitMQ task consumers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import structlog

from src.metrics import RABBITMQ_CONSUMED
from src.queue.rabbitmq_client import get_rabbitmq

if TYPE_CHECKING:
    from collections.abc import Callable

logger = structlog.get_logger(__name__)


async def start_consumer(queue_name: str, callback: Callable[[dict[str, Any]], Any]) -> None:
    """Generic consumer starter."""
    connection = await get_rabbitmq()
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)
    queue = await channel.declare_queue(queue_name, durable=True)

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                try:
                    payload = json.loads(message.body.decode())
                    await callback(payload)
                    RABBITMQ_CONSUMED.labels(queue=queue_name, status="success").inc()
                except Exception as exc:
                    RABBITMQ_CONSUMED.labels(queue=queue_name, status="error").inc()
                    logger.error("consumer_error", queue=queue_name, error=str(exc))
                    raise


class ScraperConsumer:
    """Specialized consumer for scraper tasks."""

    def __init__(self, callback: Callable[[dict[str, Any]], Any]) -> None:
        self.callback = callback

    async def start(self) -> None:
        await start_consumer("scraper_tasks", self.callback)
