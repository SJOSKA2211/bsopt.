"""RabbitMQ client for bsopt — loop-aware lazy init."""

from __future__ import annotations

import asyncio

import aio_pika
import structlog

from src.config import get_settings

logger = structlog.get_logger(__name__)
_connection: aio_pika.abc.AbstractConnection | None = None
_loop: asyncio.AbstractEventLoop | None = None


async def get_rabbitmq() -> aio_pika.abc.AbstractConnection:
    """Return global RabbitMQ connection; create on first call or loop change."""
    global _connection, _loop
    current_loop = asyncio.get_running_loop()

    if _connection is None or _loop != current_loop or _connection.is_closed:
        _connection = None
        settings = get_settings()
        _connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        _loop = current_loop
        logger.info("rabbitmq_connected", step="init")

    return _connection


async def close_rabbitmq() -> None:
    """Shutdown RabbitMQ connection."""
    global _connection, _loop
    if _connection is not None:
        try:
            current_loop = asyncio.get_running_loop()
            if _loop == current_loop:
                await _connection.close()
        except RuntimeError:
            pass
        _connection = None
        _loop = None
        logger.info("rabbitmq_closed", step="shutdown")
