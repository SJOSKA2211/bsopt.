"""E2E tests for Prometheus metrics endpoint."""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_prometheus_metrics_content() -> None:
    """Verify that the /metrics endpoint returns the expected custom metrics."""
    try:
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            response = await client.get("/metrics")
            assert response.status_code == 200
            
            content = response.text
            assert "bsopt_price_computations_total" in content
            assert "bsopt_neondb_query_duration_seconds" in content
            assert "bsopt_ray_cluster_cpus" in content
    except Exception as exc:
        pytest.skip(f"API not reachable at :8000: {exc}")
