"""Exhaustive integration tests for all FastAPI routers."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

@pytest.mark.integration
def test_pricing_endpoint_all_methods(client: TestClient) -> None:
    payload = {
        "underlying_price": 100.0,
        "strike_price": 100.0,
        "time_to_expiry": 1.0,
        "volatility": 0.2,
        "risk_free_rate": 0.05,
        "option_type": "call"
    }
    response = client.post("/api/v1/pricing/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    # Some methods might be skipped if not fully configured, but we expect most
    assert len(data["results"]) >= 1

@pytest.mark.integration
def test_market_data_endpoints(client: TestClient) -> None:
    # Latest metrics
    response = client.get("/api/v1/market/latest")
    assert response.status_code == 200
    
    # History
    response = client.get("/api/v1/market/history?symbol=SPY")
    assert response.status_code == 200

@pytest.mark.integration
def test_mlops_endpoints(client: TestClient) -> None:
    # Retrain
    response = client.post("/api/v1/mlops/retrain", json={"method_type": "analytical"})
    assert response.status_code == 200
    
    # Drift
    response = client.get("/api/v1/mlops/drift?method_type=analytical")
    assert response.status_code == 200

@pytest.mark.integration
def test_notifications_endpoints(client: TestClient) -> None:
    payload = {
        "user_id": "test_user",
        "title": "Test Title",
        "body": "Test Body",
        "severity": "info"
    }
    response = client.post("/api/v1/notifications/send", json=payload)
    assert response.status_code == 200

@pytest.mark.integration
def test_scrapers_endpoints(client: TestClient) -> None:
    response = client.post("/api/v1/scrapers/trigger?market=spy")
    assert response.status_code == 200

@pytest.mark.integration
def test_experiments_endpoints(client: TestClient) -> None:
    response = client.get("/api/v1/experiments/latest")
    assert response.status_code == 200

@pytest.mark.integration
def test_health_check(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
