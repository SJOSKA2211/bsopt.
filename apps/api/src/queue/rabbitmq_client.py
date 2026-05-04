"""RabbitMQ client for bsopt — loop-aware lazy init."""

from __future__ import annotations

import asyncio

import aio_pika
import structlog

from src.config import get_settings

logger = structlog.get_logger(__name__)


class RabbitManager:
    """Manages global RabbitMQ connection with loop-awareness."""

    _connection: aio_pika.abc.AbstractConnection | None = None
    _loop: asyncio.AbstractEventLoop | None = None

    @classmethod
    async def get_instance(cls) -> aio_pika.abc.AbstractConnection:
        """Return global RabbitMQ connection; create on first call or loop change."""
        current_loop = asyncio.get_running_loop()

        if cls._connection is None or cls._loop != current_loop or cls._connection.is_closed:
            cls._connection = None
            settings = get_settings()
            cls._connection = await aio_pika.connect_robust(settings.rabbitmq_url)
            cls._loop = current_loop
            logger.info("rabbitmq_connected", step="init")

        return cls._connection

    @classmethod
    async def close(cls) -> None:
        """Shutdown RabbitMQ connection."""
        if cls._connection is not None:
            try:
                current_loop = asyncio.get_running_loop()
                if cls._loop == current_loop:
                    await cls._connection.close()
            except (RuntimeError, Exception):
                pass
            finally:
                cls._connection = None
                cls._loop = None
                logger.info("rabbitmq_closed", step="shutdown")


async def get_rabbitmq() -> aio_pika.abc.AbstractConnection:
    """Shortcut for RabbitManager.get_instance()."""
    return await RabbitManager.get_instance()


async def close_rabbitmq() -> None:
    """Shortcut for RabbitManager.close()."""
    await RabbitManager.close()
