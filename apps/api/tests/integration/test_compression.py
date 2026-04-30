"""Integration tests for Brotli and GZip compression."""

from __future__ import annotations
import pytest
from httpx import AsyncClient
from src.main import app


@pytest.mark.asyncio
async def test_gzip_compression(async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
    """Verify that GZip compression is applied for large responses."""
    # Seed 10 experiments to make the response large
    from src.database.repository import save_option_parameters, save_method_result
    opt_id = await save_option_parameters(100.0, 100.0, 1.0, 0.2, 0.05, "call", "spy")
    for i in range(10):
        await save_method_result(opt_id, f"method_{i}", 10.0, {"p": i}, 0.01)

    response = await async_client.get(
        "/api/v1/experiments/", 
        headers={"Accept-Encoding": "gzip", **auth_headers}
    )
    assert response.status_code == 200
    assert "gzip" in response.headers.get("Content-Encoding", "")


@pytest.mark.asyncio
async def test_brotli_compression(async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
    """Verify that Brotli compression is applied for large responses."""
    # Seed 10 experiments to make the response large
    from src.database.repository import save_option_parameters, save_method_result
    opt_id = await save_option_parameters(100.0, 100.0, 1.0, 0.2, 0.05, "call", "spy")
    for i in range(10):
        await save_method_result(opt_id, f"method_{i}", 10.0, {"p": i}, 0.01)

    response = await async_client.get(
        "/api/v1/experiments/", 
        headers={"Accept-Encoding": "br", **auth_headers}
    )
    assert response.status_code == 200
    assert "br" in response.headers.get("Content-Encoding", "")
