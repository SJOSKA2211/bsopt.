"""Unit tests for main app — Zero-Mock."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from src.main import app

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def client() -> Generator[TestClient]:
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
