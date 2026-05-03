"""Unit tests for cache logic (Zero-Mock)."""
from __future__ import annotations

from typing import Any

import pytest


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
