"""Unit tests for main app — Zero-Mock."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.mark.unit
def test_app_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome to Bsopt API" in response.json()["message"]


@pytest.mark.unit
def test_app_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
