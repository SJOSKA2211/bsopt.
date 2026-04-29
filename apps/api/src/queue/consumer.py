"""RabbitMQ task consumer for bsopt."""

from __future__ import annotations

import json

import structlog
from aio_pika import IncomingMessage

from src.data.pipeline import OptionsPipeline
from src.queue.rabbitmq_client import get_rabbitmq_channel

logger = structlog.get_logger(__name__)


async def process_watchdog_task(message: IncomingMessage) -> None:
    """Callback for processing watchdog file drop tasks."""
    async with message.process():
        try:
            payload = json.loads(message.body.decode())
            file_path = payload.get("file_path")
            market = payload.get("market", "unknown")

            logger.info("consumer_received_task", market=market, file=file_path)

            if not file_path:
                logger.warning("consumer_empty_payload")
                return

            pipeline = OptionsPipeline(market=market)
            await pipeline.run(file_path)

        except Exception as exc:
            logger.error("consumer_task_failed", error=str(exc))


async def start_consumers() -> None:
    """Initialize and start all RabbitMQ consumers."""
    channel = await get_rabbitmq_channel()

    # 1. Watchdog queue
    queue = await channel.declare_queue("bs.watchdog", durable=True)
    await queue.consume(process_watchdog_task)  # type: ignore[arg-type]

    logger.info("consumers_started", queues=["bs.watchdog"])
