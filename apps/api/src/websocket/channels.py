"""Redis pub/sub integration for WebSocket channels."""

from __future__ import annotations

import asyncio
import json

import structlog

from src.cache.redis_client import get_redis
from src.websocket.manager import manager

logger = structlog.get_logger(__name__)


async def start_redis_pubsub_listener() -> None:
    """Listen to Redis channels and broadcast to WebSockets."""
    redis = await get_redis()
    from typing import Any

    pubsub: Any = redis.pubsub()

    channels = ["metrics", "experiments", "scrapers", "notifications"]
    # Redis channels will be prefixed with 'bsopt:ws:'
    redis_channels = [f"bsopt:ws:{c}" for c in channels]

    await pubsub.subscribe(*redis_channels)
    logger.info("redis_pubsub_listener_started", channels=redis_channels)

    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message["type"] == "message":
                redis_channel = message["channel"].decode("utf-8")
                ws_channel = redis_channel.replace("bsopt:ws:", "")
                data = json.loads(message["data"].decode("utf-8"))

                await manager.broadcast(ws_channel, data)

            await asyncio.sleep(0.01)
    except Exception as exc:
        logger.error("redis_pubsub_listener_failed", error=str(exc))
    finally:
        await pubsub.unsubscribe(*redis_channels)
