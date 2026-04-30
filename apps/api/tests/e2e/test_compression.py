"""E2E tests for API response compression (Gzip/Brotli)."""

from __future__ import annotations

import asyncio
import httpx
import pytest


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_gzip_compression() -> None:
    """Verify that the API returns Gzipped responses when requested."""
    # Wait for API to be ready (up to 30s)
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        ready = False
        for _ in range(30):
            try:
                resp = await client.get("/health")
                if resp.status_code == 200:
                    ready = True
                    break
            except Exception:
                pass
            await asyncio.sleep(1)
        
        if not ready:
            pytest.fail("API not ready after 30s")

        params = {
            "underlying_price": 100.0,
            "strike_price": 100.0,
            "time_to_expiry": 1.0,
            "volatility": 0.2,
            "risk_free_rate": 0.05,
            "option_type": "call"
        }
        
        headers = {"Accept-Encoding": "gzip"}
        response = await client.post("/api/v1/pricing/", json=params, headers=headers)
        
        assert response.status_code == 200
        assert response.headers.get("Content-Encoding") == "gzip"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_brotli_compression() -> None:
    """Verify that the API returns Brotli compressed responses when requested."""
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        params = {
            "underlying_price": 100.0,
            "strike_price": 100.0,
            "time_to_expiry": 1.0,
            "volatility": 0.2,
            "risk_free_rate": 0.05,
            "option_type": "call"
        }
        
        headers = {"Accept-Encoding": "br"}
        response = await client.post("/api/v1/pricing/", json=params, headers=headers)
        
        assert response.status_code == 200
        assert response.headers.get("Content-Encoding") == "br"
