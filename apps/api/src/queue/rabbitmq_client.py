"""RabbitMQ async client using aio-pika — Phase 1."""

from __future__ import annotations

import aio_pika
import structlog

from src.config import get_settings

logger = structlog.get_logger(__name__)
_connection: aio_pika.abc.AbstractRobustConnection | None = None


async def get_rabbitmq_connection() -> aio_pika.abc.AbstractRobustConnection:
    """Return global RabbitMQ connection; lazy init with robust reconnect."""
    global _connection  # noqa: PLW0603
    if _connection is None or _connection.is_closed:
        settings = get_settings()
        _connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        logger.info(
            "rabbitmq_connection_established", url=settings.rabbitmq_url, step="init", rows=0
        )
    return _connection


async def close_rabbitmq() -> None:
    """Close RabbitMQ connection."""
    global _connection  # noqa: PLW0603
    if _connection:
        await _connection.close()
        _connection = None
        logger.info("rabbitmq_connection_closed", step="shutdown", rows=0)
