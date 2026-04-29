"""Caching decorators for API responses with compression support."""

from __future__ import annotations

import functools
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

from src.cache.redis_client import get_cache, set_cache
from src.metrics import REDIS_CACHE_HITS, REDIS_CACHE_MISSES


def _generate_cache_key(
    prefix: str, func_name: str, args: tuple[Any, ...], kwargs: dict[str, Any]
) -> str:
    """Pure function to generate a stable cache key."""
    key_parts = [prefix, func_name]
    if args:
        # Filter out Request objects or other un-serializable objects if necessary
        # For simplicity, we just use string representation for unit test compatibility
        key_parts.append(str(args))

    def _serialize(obj: Any) -> Any:
        from pydantic import BaseModel

        if isinstance(obj, BaseModel):
            return obj.model_dump()
        if isinstance(obj, dict):
            return {k: _serialize(v) for k, v in obj.items()}
        if isinstance(obj, list | tuple):
            return [_serialize(i) for i in obj]
        return obj

    if kwargs:
        key_parts.append(json.dumps(_serialize(kwargs), sort_keys=True))
    return ":".join(key_parts)


def cache_response(ttl: int = 3600, prefix: str = "bsopt:cache") -> Callable[..., Any]:
    """Decorator to cache function results in Redis."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_key = _generate_cache_key(prefix, func.__name__, args, kwargs)

            # Try to get from cache
            result = await get_cache(cache_key)
            if result is not None:
                REDIS_CACHE_HITS.labels(endpoint=func.__name__).inc()
                return result

            # If not in cache, call the function
            REDIS_CACHE_MISSES.labels(endpoint=func.__name__).inc()
            result = await func(*args, **kwargs)

            # Save to cache (handles compression internally)
            await set_cache(cache_key, result, ttl=ttl)
            return result

        return wrapper

    return decorator
