"""Scraper factory to retrieve market-specific scrapers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.scrapers.nse_next_scraper import NseNextScraper
from src.scrapers.spy_scraper import SpyScraper

if TYPE_CHECKING:
    from src.scrapers.base_scraper import BaseScraper


def get_scraper(market: str) -> BaseScraper:
    """Retrieve the appropriate scraper instance for the given market."""
    if market == "spy":
        return SpyScraper()
    if market == "nse":
        return NseNextScraper()

    raise ValueError(f"No scraper implementation for market: {market}")
