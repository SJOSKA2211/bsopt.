"""Integration tests for the FastAPI application — Zero-Mock."""
from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.database.repository import save_user
from src.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"ok", "degraded"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pricing_flow(client: AsyncClient):
    user_id = uuid4()
    await save_user(user_id, f"test_{uuid4().hex[:8]}@example.com", "Test User")
    headers = {"Authorization": f"Bearer {user_id}"}
    payload = {
        "underlying_price": 100.0,
        "strike_price": 105.0,
        "time_to_expiry": 0.5,
        "volatility": 0.2,
        "risk_free_rate": 0.05,
        "option_type": "call",
        "method_type": "analytical"
    }
    response = await client.post("/api/v1/pricing/", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "computed_price" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_experiments_listing(client: AsyncClient):
    user_id = uuid4()
    await save_user(user_id, f"test_{uuid4().hex[:8]}@example.com", "Test User")
    headers = {"Authorization": f"Bearer {user_id}"}
    response = await client.get("/api/v1/experiments/", headers=headers)
    assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mlops_flow(client: AsyncClient):
    user_id = uuid4()
    await save_user(user_id, f"admin_{uuid4().hex[:8]}@example.com", "Admin User", role="admin")
    headers = {"Authorization": f"Bearer {user_id}"}
    payload = {
        "name": f"test_model_{uuid4().hex[:8]}",
        "version": "1.2.3",
        "artifact_uri": "s3://test/v1",
        "metrics": {"rmse": 0.01}
    }
    response = await client.post("/api/v1/mlops/register", json=payload, headers=headers)
    assert response.status_code == 200

    # Check drift
    response = await client.post(
        "/api/v1/mlops/drift/check?method_type=analytical&baseline_mape=0.1",
        json=[str(user_id)],
        headers=headers
    )
    assert response.status_code == 200
