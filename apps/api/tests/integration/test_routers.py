"""Exhaustive integration tests for all FastAPI routers — Zero-Mock."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

@pytest.mark.integration
@pytest.mark.asyncio
async def test_pricing_endpoint(async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
    payload = {
        "underlying_price": 100.0,
        "strike_price": 100.0,
        "time_to_expiry": 1.0,
        "volatility": 0.2,
        "risk_free_rate": 0.05,
        "option_type": "call"
    }
    # Test with valid auth
    response = await async_client.post("/api/v1/pricing/", json=payload, headers=auth_headers)
    assert response.status_code == 200
    assert "computed_price" in response.json()

    # Test unauthorized
    response = await async_client.post("/api/v1/pricing/", json=payload)
    assert response.status_code == 401

@pytest.mark.integration
@pytest.mark.asyncio
async def test_market_data_endpoint(async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
    response = await async_client.get("/api/v1/market-data/", headers=auth_headers)
    assert response.status_code == 200
    assert "results" in response.json()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_mlops_endpoints(async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
    # 1. Status
    response = await async_client.get("/api/v1/mlops/status", headers=auth_headers)
    assert response.status_code == 200
    assert "ray" in response.json()

    # 2. Drift check (Admin only)
    drift_params = {
        "method_type": "analytical",
        "baseline_mape": 0.05,
    }
    drift_json = {
        "user_ids": ["test-uuid"]
    }
    response = await async_client.post(
        "/api/v1/mlops/drift/check", 
        params=drift_params, 
        json=drift_json["user_ids"], # Wait! Signature was user_ids: list[str]
        headers=auth_headers
    )
    assert response.status_code == 200

@pytest.mark.integration
@pytest.mark.asyncio
async def test_notifications_endpoints(async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
    response = await async_client.get("/api/v1/notifications/", headers=auth_headers)
    assert response.status_code == 200
    assert "results" in response.json()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_scrapers_endpoints(async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
    # Trigger (Admin only)
    response = await async_client.post("/api/v1/scrapers/trigger?market=spy", headers=auth_headers)
    if response.status_code != 200:
        print(f"DEBUG: Scrapers fail: {response.status_code} - {response.text}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_experiments_endpoints(async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
    response = await async_client.get("/api/v1/experiments/", headers=auth_headers)
    assert response.status_code == 200
    assert "results" in response.json()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient) -> None:
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
