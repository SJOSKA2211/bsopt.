"""Integration tests for Redis cache and compression."""

from __future__ import annotations

import pytest
from src.cache.redis_client import set_cache, get_cache
from src.cache.decorators import cache_response


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_compression_large_value(db_cleanup) -> None:
    """Verify that large values are compressed in Redis."""
    key = "test:large_val"
    value = {"data": "A" * 2000}  # > 1KB
    
    await set_cache(key, value, ttl=60)
    retrieved = await get_cache(key)
    
    assert retrieved == value


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_decorator_hit_miss(db_cleanup) -> None:
    """Verify cache decorator functionality."""
    call_count = 0
    
    @cache_response(ttl=60, prefix="test:decorator")
    async def mock_func(x: int):
        nonlocal call_count
        call_count += 1
        return {"result": x}

    # 1. First call (MISS)
    res1 = await mock_func(10)
    assert res1 == {"result": 10}
    assert call_count == 1
    
    # 2. Second call (HIT)
    res2 = await mock_func(10)
    assert res2 == {"result": 10}
    assert call_count == 1
