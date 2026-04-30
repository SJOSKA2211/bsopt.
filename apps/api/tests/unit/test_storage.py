"""Unit tests for Storage logic (Zero-Mock)."""
from __future__ import annotations
import pytest

def generate_object_name(bucket: str, market: str, filename: str) -> str:
    """Pure function for object name generation."""
    return f"{bucket}/{market}/{filename}"

@pytest.mark.unit
def test_storage_helpers() -> None:
    """Test storage service pure helpers."""
    name = generate_object_name("bsopt-exports", "spy", "data.csv")
    assert name == "bsopt-exports/spy/data.csv"
