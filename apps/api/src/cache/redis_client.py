"""Redis client for bsopt — loop-aware lazy init."""

from __future__ import annotations

import asyncio
import gzip
import json
from collections.abc import Mapping
from typing import Any, cast

import redis.asyncio as redis
import structlog

from src.config import get_settings
from src.metrics import (
    REDIS_CACHE_HITS,
    REDIS_CACHE_MISSES,
    REDIS_OPERATIONS_TOTAL,
)

logger = structlog.get_logger(__name__)


class RedisManager:
    """Manages global Redis connection with loop-awareness."""

    _redis: redis.Redis | None = None
    _loop: asyncio.AbstractEventLoop | None = None

    @classmethod
    async def get_instance(cls) -> redis.Redis:
        """Return global Redis client; create on first call or loop change."""
        current_loop = asyncio.get_running_loop()

        if cls._redis is None or cls._loop != current_loop:
            cls._redis = None
            settings = get_settings()
            # We use decode_responses=False to handle both binary (gzip) and text
            cls._redis = redis.from_url(
                settings.redis_url,
                password=settings.redis_password,
                decode_responses=False,
            )
            cls._loop = current_loop
            logger.info("redis_connected", step="init")

        return cls._redis

    @classmethod
    async def close(cls) -> None:
        """Shutdown Redis client."""
        if cls._redis is not None:
            try:
                current_loop = asyncio.get_running_loop()
                if cls._loop == current_loop:
                    await cls._redis.aclose()
            except (RuntimeError, Exception):
                pass
            finally:
                cls._redis = None
                cls._loop = None
                logger.info("redis_closed", step="shutdown")


async def get_redis() -> redis.Redis:
    """Shortcut for RedisManager.get_instance()."""
    return await RedisManager.get_instance()


async def close_redis() -> None:
    """Shortcut for RedisManager.close()."""
    await RedisManager.close()


CacheValue = Mapping[str, object] | list[object] | str | float | int | bool


async def set_cache(key: str, value: CacheValue, ttl: int = 3600) -> None:
    """Set value in cache with optional Gzip compression."""
    r = await get_redis()
    settings = get_settings()
    data_str = json.dumps(value)

    if settings.enable_compression and len(data_str) > settings.compression_threshold_bytes:
        data_bytes = gzip.compress(data_str.encode())
        await r.set(f"gz:{key}", data_bytes, ex=ttl)
    else:
        await r.set(key, data_str.encode(), ex=ttl)
    REDIS_OPERATIONS_TOTAL.labels(operation="set").inc()


async def get_cache(key: str, endpoint: str = "unknown") -> object | None:
    """Get value from cache, handling Gzip if present."""
    r = await get_redis()
    # Check for compressed key first
    raw_data = await r.get(f"gz:{key}")
    if raw_data:
        REDIS_CACHE_HITS.labels(endpoint=endpoint).inc()
        decompressed = gzip.decompress(cast(bytes, raw_data)).decode()
        return cast(object, json.loads(decompressed))

    raw_data = await r.get(key)
    if raw_data:
        REDIS_CACHE_HITS.labels(endpoint=endpoint).inc()
        return cast(object, json.loads(cast(bytes, raw_data).decode()))

    REDIS_CACHE_MISSES.labels(endpoint=endpoint).inc()
    return None
