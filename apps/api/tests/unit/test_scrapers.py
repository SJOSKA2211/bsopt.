"""Unit tests for scraper factory."""

from __future__ import annotations

import pytest

from src.scrapers.nse_next_scraper import NseNextScraper
from src.scrapers.scraper_factory import get_scraper
from src.scrapers.spy_scraper import SpyScraper


@pytest.mark.unit
def test_get_scraper_valid() -> None:
    assert isinstance(get_scraper("spy"), SpyScraper)
    assert isinstance(get_scraper("nse"), NseNextScraper)


@pytest.mark.unit
def test_get_scraper_invalid() -> None:
    with pytest.raises(ValueError, match="No scraper implementation"):
        get_scraper("invalid")
