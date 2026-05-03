"""WebSocket channel definitions and event broadcasting — Python 3.14."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import structlog

from src.cache.redis_client import get_redis
from src.websocket.manager import manager

logger = structlog.get_logger(__name__)

__all__ = [
    "broadcast_experiment_update",
    "broadcast_metric_update",
    "broadcast_scraper_update",
    "get_redis",
    "manager",
    "send_user_notification",
    "start_redis_pubsub_listener",
]


async def broadcast_metric_update(metric_data: dict[str, Any]) -> None:
    """Broadcast real-time metric updates to the 'metrics' channel."""
    await manager.broadcast("metrics", {"type": "metric_update", "data": metric_data})


async def broadcast_experiment_update(experiment_data: dict[str, Any]) -> None:
    """Broadcast experiment status changes to the 'experiments' channel."""
    await manager.broadcast("experiments", {"type": "experiment_update", "data": experiment_data})


async def broadcast_scraper_update(scraper_data: dict[str, Any]) -> None:
    """Broadcast scraper status updates to the 'scrapers' channel."""
    await manager.broadcast("scrapers", {"type": "scraper_update", "data": scraper_data})


async def send_user_notification(user_id: str, notification: dict[str, Any]) -> None:
    """Send a targeted notification to a specific user via WebSocket."""
    await manager.send_personal_message(
        {"type": "notification", "data": notification}, user_id=user_id
    )


async def start_redis_pubsub_listener(max_loops: int | None = None) -> None:
    """Listen for global system events on Redis and broadcast them via WebSockets."""
    redis = await get_redis()
    pubsub = redis.pubsub()

    await pubsub.subscribe("bsopt:events", "metrics", "experiments", "scrapers", "notifications")
    logger.info("redis_pubsub_listener_started")

    loops = 0
    try:
        while max_loops is None or loops < max_loops:
            loops += 1
            # Note: get_message with timeout=1.0 will wait up to 1 second
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                channel = message["channel"]
                if isinstance(channel, bytes):
                    channel = channel.decode("utf-8")

                raw_data = message["data"]
                if isinstance(raw_data, bytes):
                    raw_data = raw_data.decode("utf-8")

                data = json.loads(raw_data)

                if channel == "bsopt:events":
                    target_channel = data.get("channel")
                    event = data.get("event")
                    if target_channel and event:
                        await manager.broadcast(target_channel, event)
                elif channel == "notifications" and "user_id" in data:
                    await send_user_notification(data["user_id"], data["notification"])
                else:
                    await manager.broadcast(channel, data)

            await asyncio.sleep(0.01)
    except asyncio.CancelledError:
        logger.info("redis_pubsub_listener_cancelled")
        raise
    except Exception as exc:
        logger.error("redis_pubsub_listener_failed", error=str(exc))
    finally:
        try:
            await pubsub.unsubscribe()
            await pubsub.aclose()  # type: ignore[no-untyped-call]
        except Exception as exc:
            logger.warning("redis_pubsub_cleanup_failed", error=str(exc))
