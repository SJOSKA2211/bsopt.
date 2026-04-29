"""Unit tests for scraper factory."""

from __future__ import annotations

import pytest
from src.scrapers.scraper_factory import get_scraper

@pytest.mark.unit
def test_get_scraper_valid():
    assert get_scraper("spy").market == "spy"
    assert get_scraper("nse").market == "nse"

@pytest.mark.unit
def test_get_scraper_invalid():
    with pytest.raises(ValueError, match="No scraper implementation"):
        get_scraper("invalid")
