"""Unit tests for caching logic and key generation."""

from __future__ import annotations

import pytest
import json
import gzip
from pydantic import BaseModel
from src.cache.decorators import _generate_cache_key
from src.cache.redis_client import set_cache, get_cache, get_redis, close_redis


class MockModel(BaseModel):
    id: int
    name: str


@pytest.mark.unit
def test_cache_key_generation_consistency() -> None:
    """Verify that the same inputs produce the same key."""
    prefix = "test"
    func_name = "calculate"
    args = (100, "call")
    kwargs = {"sigma": 0.2, "rate": 0.05}

    key1 = _generate_cache_key(prefix, func_name, args, kwargs)
    key2 = _generate_cache_key(prefix, func_name, args, kwargs)

    assert key1 == key2
    assert "test:calculate" in key1


@pytest.mark.unit
def test_cache_key_sorts_kwargs() -> None:
    """Verify that kwarg order doesn't change the key."""
    prefix = "test"
    func_name = "calculate"
    args = ()
    kwargs1 = {"a": 1, "b": 2}
    kwargs2 = {"b": 2, "a": 1}

    key1 = _generate_cache_key(prefix, func_name, args, kwargs1)
    key2 = _generate_cache_key(prefix, func_name, args, kwargs2)

    assert key1 == key2


@pytest.mark.unit
def test_cache_key_different_prefixes() -> None:
    """Verify that different prefixes produce different keys."""
    key1 = _generate_cache_key("p1", "f", (), {})
    key2 = _generate_cache_key("p2", "f", (), {})
    assert key1 != key2


@pytest.mark.unit
def test_cache_key_handles_empty_args() -> None:
    """Verify key generation with no args or kwargs."""
    key = _generate_cache_key("prefix", "func", (), {})
    assert key == "prefix:func"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_set_get_cache() -> None:
    """Verify basic set/get operation in Redis."""
    key = "test_key"
    value = {"result": 10.45, "method": "analytical"}
    
    await set_cache(key, value)
    cached_value = await get_cache(key)
    
    assert cached_value == value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_compression() -> None:
    """Verify that large data is compressed in Redis."""
    key = "large_cache_key"
    # Large value > 1KB
    large_value = {"data": "x" * 2000}
    
    await set_cache(key, large_value)
    
    # Check directly in Redis if the compressed key exists
    client = await get_redis()
    raw_data = await client.get(f"gz:{key}")
    
    assert raw_data is not None
    # Verify it's compressed
    decompressed = gzip.decompress(raw_data)
    assert json.loads(decompressed.decode("utf-8")) == large_value
    
    # Verify get_cache works transparently
    cached_value = await get_cache(key)
    assert cached_value == large_value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_serialization_pydantic() -> None:
    """Verify that Pydantic models are serialized correctly."""
    key = "pydantic_key"
    model = MockModel(id=1, name="test")
    await set_cache(key, model)
    cached = await get_cache(key)
    assert cached == {"id": 1, "name": "test"}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_serialization_nested() -> None:
    """Verify nested serialization (lists, tuples, dicts)."""
    key = "nested_key"
    value = {"a": [MockModel(id=1, name="t")], "b": (2, 3)}
    await set_cache(key, value)
    cached = await get_cache(key)
    assert cached == {"a": [{"id": 1, "name": "t"}], "b": [2, 3]}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_cache_miss() -> None:
    """Verify that get_cache returns None on miss."""
    assert await get_cache("non_existent") is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_close_redis() -> None:
    """Verify close_redis handles exceptions and clears singleton."""
    from src.cache.redis_client import RedisManager
    client = await get_redis()
    
    # Trigger exception in aclose manually by replacing it
    # Since we are Zero-Mock, we avoid MagicMock but we can manually override
    original_aclose = client.aclose
    async def broken_aclose(): raise Exception("Fail")
    client.aclose = broken_aclose # type: ignore
    
    await close_redis()
    assert RedisManager._redis is None
    
    # Restore (though it's a singleton and we just set it to None)
    
    # Double close should not raise
    await close_redis()
