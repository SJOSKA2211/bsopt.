"""Unit tests for cache logic (Zero-Mock)."""

from __future__ import annotations

from typing import Any

import pytest

from src.cache.decorators import cache_response, generate_cache_key
from src.cache.redis_client import get_cache, get_redis, set_cache


@pytest.mark.unit
def test_pure_key_generation() -> None:
    key1 = generate_cache_key("res", "my_func", (1, 2), {"a": 3})
    key2 = generate_cache_key("res", "my_func", (1, 2), {"a": 3})
    key3 = generate_cache_key("res", "my_func", (1, 2), {"a": 4})

    assert key1 == key2
    assert key1 != key3
    assert key1 == "res:my_func:(1, 2):[('a', 3)]"


@pytest.mark.unit
def test_key_generation_no_args() -> None:
    key = generate_cache_key("res", "my_func", (), {})
    assert key == "res:my_func"


@pytest.mark.unit
def test_key_generation_only_args() -> None:
    key = generate_cache_key("res", "my_func", (1, "b"), {})
    assert key == "res:my_func:(1, 'b')"


@pytest.mark.unit
def test_key_generation_only_kwargs() -> None:
    key = generate_cache_key("res", "my_func", (), {"x": 10, "y": 20})
    assert key == "res:my_func:[('x', 10), ('y', 20)]"


@pytest.mark.unit
def test_key_generation_prefix_uniqueness() -> None:
    key1 = generate_cache_key("p1", "f", (), {})
    key2 = generate_cache_key("p2", "f", (), {})
    assert key1 != key2


@pytest.mark.unit
def test_key_generation_sorted_kwargs() -> None:
    key1 = generate_cache_key("res", "f", (), {"b": 2, "a": 1})
    key2 = generate_cache_key("res", "f", (), {"a": 1, "b": 2})
    assert key1 == key2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_client_real() -> None:
    """Test real Redis client set/get/ttl."""
    key = "test_key_real"
    value = {"foo": "bar"}
    await set_cache(key, value, ttl=10)

    # Test cache hit
    cached = await get_cache(key)
    assert cached == value

    # Test cache miss
    assert await get_cache("non_existent") is None

    # Test compression (large value)
    large_value = "x" * 2000
    await set_cache("large_key", large_value)
    cached_large = await get_cache("large_key")
    assert cached_large == large_value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_decorator_real() -> None:
    """Test cache_response decorator with real Redis."""
    call_count = 0

    @cache_response(ttl=10, key_prefix="test_dec")
    async def my_cached_func(a: int, b: int) -> dict[str, int]:
        nonlocal call_count
        call_count += 1
        return {"sum": a + b}

    # First call - should call func
    res1 = await my_cached_func(1, 2)
    assert res1 == {"sum": 3}
    assert call_count == 1

    # Second call - should return cached
    res2 = await my_cached_func(1, 2)
    assert res2 == {"sum": 3}
    assert call_count == 1

    # Call with different args - should call func
    res3 = await my_cached_func(2, 2)
    assert res3 == {"sum": 4}
    assert call_count == 2
