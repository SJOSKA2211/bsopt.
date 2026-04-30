"""RabbitMQ client for bsopt — aio-pika, async."""

from __future__ import annotations

import aio_pika
import structlog

from src.config import get_settings

logger = structlog.get_logger(__name__)
_connection: aio_pika.abc.AbstractConnection | None = None


async def get_rabbitmq_connection() -> aio_pika.abc.AbstractConnection:
    """Lazy init of global RabbitMQ connection."""
    global _connection
    if _connection is None or _connection.is_closed:
        settings = get_settings()
        _connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        logger.info("rabbitmq_connected", url=settings.rabbitmq_url, step="init", rows=0)
    return _connection


async def close_rabbitmq() -> None:
    """Shutdown RabbitMQ connection."""
    global _connection
    if _connection is not None:
        await _connection.close()
        _connection = None
        logger.info("rabbitmq_closed", step="shutdown", rows=0)
