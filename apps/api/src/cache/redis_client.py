"""Redis client for caching and pub-sub — Phase 1."""

from __future__ import annotations

import redis.asyncio as redis
import structlog

from src.config import get_settings

logger = structlog.get_logger(__name__)
_redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    """Return global Redis client; lazy init."""
    global _redis_client  # noqa: PLW0603
    if _redis_client is None:
        settings = get_settings()
        _redis_client = redis.from_url(
            settings.redis_url,
            password=settings.redis_password,
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info("redis_client_created", url=settings.redis_url, step="init", rows=0)
    return _redis_client


async def close_redis() -> None:
    """Close Redis connection."""
    global _redis_client  # noqa: PLW0603
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("redis_client_closed", step="shutdown", rows=0)
