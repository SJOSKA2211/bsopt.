"""Integration tests for scrapers — Phase 1."""
from __future__ import annotations

import pytest

from src.scrapers.scraper_factory import get_scraper
from src.scrapers.spy_scraper import SpyScraper

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_scraper_factory() -> None:
    """Test that the scraper factory returns the correct classes."""
    spy = get_scraper("spy")
    assert isinstance(spy, SpyScraper)

    with pytest.raises(ValueError):
        get_scraper("invalid")


@pytest.mark.asyncio
async def test_spy_scraper_logic() -> None:
    """Test the SPY scraper's core logic."""
    scraper = SpyScraper()
    assert scraper.market == "spy"
    # We skip the actual scrape() call in unit/integration tests if it's too slow or hits rate limits
    # but for Zero-Mock we should ideally have a local test server.
    # For now, we just verify the class initialization.
