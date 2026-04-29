"""Cache decorators for FastAPI routes — Phase 1."""

from __future__ import annotations

import functools
import hashlib
import json
from collections.abc import Callable
from typing import Any, TypeVar, cast

import structlog
from fastapi import Request

from src.cache.redis_client import get_redis
from src.metrics import REDIS_CACHE_HITS, REDIS_CACHE_MISSES

logger = structlog.get_logger(__name__)
F = TypeVar("F", bound=Callable[..., Any])


def cache_response(ttl: int = 3600, prefix: str = "bsopt:cache") -> Callable[[F], F]:
    """Decorator to cache FastAPI route responses in Redis."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 1. Find request object in args/kwargs
            request: Request | None = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                request = kwargs.get("request")

            if not request:
                # Fallback: if no request, just run the function (shouldn't happen in routes)
                return await func(*args, **kwargs)

            # 2. Generate cache key based on URL and query params
            key_source = f"{request.url.path}:{sorted(request.query_params.items())}"
            key_hash = hashlib.blake2b(key_source.encode(), digest_size=16).hexdigest()
            cache_key = f"{prefix}:{key_hash}"

            redis_client = await get_redis()

            # 3. Check cache
            try:
                cached_data = await redis_client.get(cache_key)
                if cached_data:
                    REDIS_CACHE_HITS.labels(endpoint=request.url.path).inc()
                    return json.loads(cached_data)
            except Exception as exc:
                logger.warning("cache_lookup_failed", error=str(exc), key=cache_key)

            # 4. Cache miss: run function
            result = await func(*args, **kwargs)
            REDIS_CACHE_MISSES.labels(endpoint=request.url.path).inc()

            # 5. Store in cache
            try:
                await redis_client.setex(cache_key, ttl, json.dumps(result))
            except Exception as exc:
                logger.warning("cache_store_failed", error=str(exc), key=cache_key)

            return result

        return cast("F", wrapper)

    return decorator
