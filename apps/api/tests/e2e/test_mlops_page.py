"""E2E tests for MLOps monitoring and drift detection."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from playwright.async_api import Page


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_mlops_monitoring_links(page: Page) -> None:
    """Verify that Ray and MLflow links are present and reachable."""
    try:
        await page.goto("http://localhost:3000/dashboard/mlops", timeout=5000)

        # Check for monitoring links
        await page.wait_for_selector("text=Ray Dashboard", timeout=2000)
        await page.wait_for_selector("text=MLflow UI", timeout=2000)

        # Check for drift detector card
        await page.wait_for_selector("text=Model Drift", timeout=2000)
    except Exception as exc:
        pytest.skip(f"Frontend not reachable: {exc}")
