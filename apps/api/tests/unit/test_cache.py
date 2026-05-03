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
