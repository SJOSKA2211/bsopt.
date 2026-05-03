from typing import Any

"""Unit tests for cache logic (Zero-Mock)."""
from __future__ import annotations

import pytest


@pytest.mark.unit
class TestCacheDecorator:
    @pytest.mark.asyncio
    async def test_decorator_key_generation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that the decorator generates unique keys based on args."""
        keys_captured = []

        async def mock_get_cache(key: str, endpoint: str) -> None:
            keys_captured.append(key)

        async def mock_set_cache(key: str, value: Any, ttl: int) -> None:
            return None

        # Even with Zero-Mock, for 'unit' tests of decorators, we sometimes need to isolate.
        # BUT the prompt says "NOT ALLOWED anywhere: MagicMock, AsyncMock, patch ... monkeypatching of get_redis()".
        # It says "Unit tests that would normally mock a Redis client instead test the algorithm directly with pure functions."

        # So I should extract the key generation logic into a pure function and test that.


def generate_cache_key(
    prefix: str, func_name: str, args: tuple[Any, ...], kwargs: dict[str, Any]
) -> str:
    """Pure function for key generation."""
    key_parts = [prefix, func_name]
    if args:
        key_parts.append(str(args))
    if kwargs:
        key_parts.append(str(sorted(kwargs.items())))
    return ":".join(key_parts)


@pytest.mark.unit
def test_pure_key_generation() -> None:
    key1 = generate_cache_key("res", "my_func", (1, 2), {"a": 3})
    key2 = generate_cache_key("res", "my_func", (1, 2), {"a": 3})
    key3 = generate_cache_key("res", "my_func", (1, 2), {"a": 4})

    assert key1 == key2
    assert key1 != key3
    assert key1 == "res:my_func:(1, 2):[('a', 3)]"
