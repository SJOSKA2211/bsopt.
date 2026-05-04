"""Cache decorators for FastAPI routes."""

from __future__ import annotations

import functools
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, TypeVar, cast

import structlog

from src.cache.redis_client import get_cache, set_cache

if TYPE_CHECKING:
    from typing import Any

logger = structlog.get_logger(__name__)
F = TypeVar("F", bound=Callable[..., Awaitable[object]])


def generate_cache_key(
    prefix: str, func_name: str, args: tuple[object, ...], kwargs: dict[str, object]
) -> str:
    """Pure function for key generation."""
    key_parts = [prefix, func_name]
    if args:
        key_parts.append(str(args))
    if kwargs:
        key_parts.append(str(sorted(kwargs.items())))
    return ":".join(key_parts)


def cache_response(ttl: int = 3600, key_prefix: str = "res") -> Callable[[F], F]:
    """Decorator to cache function results in Redis."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: object, **kwargs: object) -> object:
            cache_key = generate_cache_key(key_prefix, func.__name__, args, kwargs)

            cached = await get_cache(cache_key, endpoint=func.__name__)
            if cached:
                return cached

            result = await func(*args, **kwargs)
            await set_cache(cache_key, result, ttl=ttl)  # type: ignore[arg-type]
            return result

        return cast("F", wrapper)

    return decorator
