"""WebSocket channel definitions and event broadcasting — Python 3.14."""

from __future__ import annotations

import asyncio
from typing import Any

from src.websocket.manager import manager as manager


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
    import json

    import structlog

    from src.cache.redis_client import get_redis

    logger = structlog.get_logger(__name__)
    redis = await get_redis()
    pubsub = redis.pubsub()

    # Subscribe to system-wide and specific channels
    await pubsub.subscribe("bsopt:events", "metrics", "experiments", "scrapers", "notifications")

    logger.info("redis_pubsub_listener_started")

    loops = 0
    try:
        while max_loops is None or loops < max_loops:
            loops += 1
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                channel = message["channel"].decode("utf-8")
                data = json.loads(message["data"].decode("utf-8"))

                # Route messages
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
    except Exception as exc:
        logger.error("redis_pubsub_listener_failed", error=str(exc))
    finally:
        await pubsub.unsubscribe()
        await pubsub.aclose()
