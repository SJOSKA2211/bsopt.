"""Redis client for bsopt — loop-aware lazy init."""

from __future__ import annotations

import asyncio
import gzip
import json
from typing import Any

import redis.asyncio as redis
import structlog

from src.config import get_settings
from src.metrics import REDIS_OPERATIONS_TOTAL

logger = structlog.get_logger(__name__)
_redis: redis.Redis | None = None
_loop: asyncio.AbstractEventLoop | None = None


async def get_redis() -> redis.Redis:
    """Return global Redis client; create on first call or loop change."""
    global _redis, _loop
    current_loop = asyncio.get_running_loop()

    if _redis is None or _loop != current_loop:
        _redis = None
        settings = get_settings()
        _redis = redis.from_url(
            settings.redis_url,
            password=settings.redis_password,
            decode_responses=True,
        )
        _loop = current_loop
        logger.info("redis_connected", step="init")

    return _redis


async def close_redis() -> None:
    """Shutdown Redis client."""
    global _redis, _loop
    if _redis is not None:
        try:
            current_loop = asyncio.get_running_loop()
            if _loop == current_loop:
                await _redis.aclose()
        except RuntimeError:
            pass
        _redis = None
        _loop = None
        logger.info("redis_closed", step="shutdown")


async def set_cache(key: str, value: Any, ttl: int = 3600) -> None:
    """Set value in cache with optional Gzip compression."""
    r = await get_redis()
    settings = get_settings()
    data = json.dumps(value)

    if settings.enable_compression and len(data) > settings.compression_threshold_bytes:
        data_bytes = gzip.compress(data.encode())
        # We need to use a different method or prefix to indicate compression
        # For simplicity, we'll just store as bytes if compressed
        await r.set(f"gz:{key}", data_bytes, ex=ttl)
    else:
        await r.set(key, data, ex=ttl)
    REDIS_OPERATIONS_TOTAL.labels(operation="set").inc()


async def get_cache(key: str, endpoint: str = "unknown") -> Any | None:
    """Get value from cache, handling Gzip if present."""
    r = await get_redis()
    # Check for compressed key first
    data = await r.get(f"gz:{key}")
    if data:
        if isinstance(data, bytes):
            data = gzip.decompress(data).decode()
        return json.loads(data)

    data = await r.get(key)
    REDIS_OPERATIONS_TOTAL.labels(operation="get").inc()
    return json.loads(data) if data else None
