"""RabbitMQ client using aio-pika."""

from __future__ import annotations

import aio_pika
import structlog

from src.config import get_settings

logger = structlog.get_logger(__name__)


class RabbitMQManager:
    """Singleton manager for RabbitMQ connection."""

    _connection: aio_pika.abc.AbstractRobustConnection | None = None
    _channel: aio_pika.abc.AbstractChannel | None = None


async def get_rabbitmq_connection() -> aio_pika.abc.AbstractRobustConnection:
    """Return a global RabbitMQ connection instance, ensuring it's for the current loop."""
    if RabbitMQManager._connection is None or RabbitMQManager._connection.is_closed:
        settings = get_settings()
        RabbitMQManager._connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        logger.info("rabbitmq_connection_established", step="init", rows=0)
    return RabbitMQManager._connection


async def get_rabbitmq_channel() -> aio_pika.abc.AbstractChannel:
    """Return a global RabbitMQ channel."""
    if RabbitMQManager._channel is None or RabbitMQManager._channel.is_closed:
        conn = await get_rabbitmq_connection()
        RabbitMQManager._channel = await conn.channel()
    return RabbitMQManager._channel


async def close_rabbitmq() -> None:
    """Close the global RabbitMQ connection and channel."""
    if RabbitMQManager._channel is not None:
        try:
            await RabbitMQManager._channel.close()
        except Exception:
            pass
        RabbitMQManager._channel = None

    if RabbitMQManager._connection is not None:
        try:
            await RabbitMQManager._connection.close()
        except Exception:
            pass
        RabbitMQManager._connection = None
        logger.info("rabbitmq_connection_closed", step="shutdown", rows=0)
