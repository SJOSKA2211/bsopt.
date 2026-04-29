"""Redis client for caching and pub/sub with optional compression."""

from __future__ import annotations

import gzip
import json
from typing import Any

import redis.asyncio as redis
import structlog

from src.config import get_settings

logger = structlog.get_logger(__name__)


class RedisManager:
    """Singleton manager for Redis connection."""

    _redis: redis.Redis[bytes] | None = None


async def get_redis() -> redis.Redis[bytes]:
    """Return a global Redis client instance, ensuring it's for the current loop."""
    if RedisManager._redis is None:
        settings = get_settings()
        RedisManager._redis = redis.from_url(
            settings.redis_url,
            password=settings.redis_password,
            decode_responses=False,
        )
        logger.info("redis_client_created", url=settings.redis_url, step="init", rows=0)
    return RedisManager._redis


async def close_redis() -> None:
    """Close the global Redis client instance."""
    if RedisManager._redis is not None:
        try:
            await RedisManager._redis.aclose()
        except Exception:
            pass
        RedisManager._redis = None
        logger.info("redis_client_closed", step="shutdown", rows=0)


async def set_cache(key: str, value: Any, ttl: int = 3600) -> None:
    """Set a value in cache with optional compression."""
    settings = get_settings()
    client = await get_redis()

    def _serialize(obj: Any) -> Any:
        from pydantic import BaseModel

        if isinstance(obj, BaseModel):
            return obj.model_dump()
        if isinstance(obj, dict):
            return {k: _serialize(v) for k, v in obj.items()}
        if isinstance(obj, list | tuple):
            return [_serialize(i) for i in obj]
        return obj

    data = json.dumps(_serialize(value)).encode("utf-8")

    if settings.enable_compression and len(data) > 1024:  # Compress if > 1KB
        data = gzip.compress(data)
        key = f"gz:{key}"

    await client.set(key, data, ex=ttl)


async def get_cache(key: str) -> Any | None:
    """Get a value from cache and decompress if needed."""
    client = await get_redis()

    # Try compressed key first
    data = await client.get(f"gz:{key}")
    if data:
        data = gzip.decompress(data)
    else:
        # Try uncompressed key
        data = await client.get(key)

    if data:
        return json.loads(data.decode("utf-8"))
    return None
