"""RabbitMQ client using aio-pika."""

from __future__ import annotations

import aio_pika

from src.config import get_settings


class RabbitMQManager:
    """Singleton manager for RabbitMQ connection."""

    _connection: aio_pika.abc.AbstractConnection | None = None
    _channel: aio_pika.abc.AbstractChannel | None = None


async def get_rabbitmq_connection() -> aio_pika.abc.AbstractConnection:
    """Return a global RabbitMQ connection instance, ensuring it's for the current loop."""
    import asyncio

    asyncio.get_running_loop()
    if RabbitMQManager._connection is not None:
        if RabbitMQManager._connection.is_closed:
            RabbitMQManager._connection = None

    if RabbitMQManager._connection is None:
        settings = get_settings()
        RabbitMQManager._connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    return RabbitMQManager._connection


async def get_rabbitmq_channel() -> aio_pika.abc.AbstractChannel:
    """Return a global RabbitMQ channel."""
    if RabbitMQManager._channel is not None:
        if RabbitMQManager._channel.is_closed:
            RabbitMQManager._channel = None

    if RabbitMQManager._channel is None:
        conn = await get_rabbitmq_connection()
        RabbitMQManager._channel = await conn.channel()
    return RabbitMQManager._channel


async def close_rabbitmq() -> None:
    """Close the global RabbitMQ connection and channel."""
    if RabbitMQManager._channel is not None:
        await RabbitMQManager._channel.close()
        RabbitMQManager._channel = None

    if RabbitMQManager._connection is not None:
        try:
            await RabbitMQManager._connection.close()
        except Exception:
            pass
        RabbitMQManager._connection = None
