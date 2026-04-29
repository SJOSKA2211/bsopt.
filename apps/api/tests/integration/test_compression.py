"""Integration tests for Brotli and GZip compression."""

from __future__ import annotations
import pytest
from fastapi.testclient import TestClient
from src.main import app

@pytest.fixture
def client() -> TestClient:
    return TestClient(app)

def test_gzip_compression(client: TestClient) -> None:
    """Verify that GZip compression is applied for large responses."""
    # Pricing all methods returns a large enough JSON (~3KB)
    params = {
        "underlying_price": 100.0,
        "strike_price": 100.0,
        "time_to_maturity": 1.0,
        "volatility": 0.2,
        "risk_free_rate": 0.05,
        "option_type": "call",
    }
    response = client.post(
        "/api/v1/pricing/", 
        json=params,
        headers={"Accept-Encoding": "gzip"}
    )
    assert response.status_code == 200
    assert "gzip" in response.headers.get("Content-Encoding", "")

def test_brotli_compression(client: TestClient) -> None:
    """Verify that Brotli compression is applied for large responses."""
    params = {
        "underlying_price": 100.0,
        "strike_price": 100.0,
        "time_to_maturity": 1.0,
        "volatility": 0.2,
        "risk_free_rate": 0.05,
        "option_type": "call",
    }
    response = client.post(
        "/api/v1/pricing/", 
        json=params,
        headers={"Accept-Encoding": "br"}
    )
    assert response.status_code == 200
    # Note: Brotli might not be applied if GZip is higher priority or if the response is too small
    # but with 12 methods it should be > 1000 bytes.
    assert "br" in response.headers.get("Content-Encoding", "")
