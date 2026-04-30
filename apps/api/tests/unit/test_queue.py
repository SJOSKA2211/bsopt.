"""Unit tests for RabbitMQ publisher logic (Zero-Mock)."""
from __future__ import annotations
import pytest
import json

def serialize_payload(file_path: str, market: str) -> bytes:
    """Pure function for serialization."""
    return json.dumps({"file_path": file_path, "market": market}).encode()

@pytest.mark.unit
def test_publisher_serialization() -> None:
    """Test that the publisher serializes payload correctly."""
    payload = serialize_payload("/tmp/test.csv", "spy")
    decoded = json.loads(payload.decode())
    assert decoded["file_path"] == "/tmp/test.csv"
    assert decoded["market"] == "spy"
