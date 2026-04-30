"""Redis client for bsopt — Python 3.14 free-threaded, gzip compression."""

from __future__ import annotations

import gzip
import json
from typing import Any

import redis.asyncio as redis
import structlog

from src.config import get_settings
from src.metrics import REDIS_CACHE_HITS, REDIS_CACHE_MISSES

logger = structlog.get_logger(__name__)
_redis: redis.Redis[bytes] | None = None


async def get_redis() -> redis.Redis[bytes]:
    """Lazy init of global Redis client."""
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = redis.from_url(
            settings.redis_url, password=settings.redis_password, decode_responses=False
        )
        logger.info("redis_connected", url=settings.redis_url, step="init", rows=0)
    return _redis


async def close_redis() -> None:
    """Shutdown Redis client."""
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None
        logger.info("redis_closed", step="shutdown", rows=0)


async def set_cache(key: str, value: Any, ttl: int = 3600) -> None:
    """Serialize and store value, with gzip if > threshold."""
    settings = get_settings()
    client = await get_redis()

    def _default(obj: Any) -> Any:
        from pydantic import BaseModel

        if isinstance(obj, BaseModel):
            return obj.model_dump()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    data = json.dumps(value, default=_default).encode("utf-8")
    is_compressed = False
    if settings.enable_compression and len(data) > settings.compression_threshold_bytes:
        data = gzip.compress(data)
        is_compressed = True

    # Store compression flag in key or value. Here we use a prefix for simple detection.
    full_key = f"gz:{key}" if is_compressed else key
    await client.set(full_key, data, ex=ttl)


async def get_cache(key: str, endpoint: str = "default") -> Any | None:
    """Retrieve and deserialize value, handling gzip."""
    client = await get_redis()

    # Try compressed key first
    data = await client.get(f"gz:{key}")
    if data:
        data = gzip.decompress(data)
    else:
        data = await client.get(key)

    if data:
        REDIS_CACHE_HITS.labels(endpoint=endpoint).inc()
        return json.loads(data.decode("utf-8"))

    REDIS_CACHE_MISSES.labels(endpoint=endpoint).inc()
    return None
