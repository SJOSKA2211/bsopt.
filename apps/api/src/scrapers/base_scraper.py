"""Base scraper class using Playwright."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import structlog
from playwright.async_api import async_playwright

logger = structlog.get_logger(__name__)


class BaseScraper(ABC):
    """Abstract base class for all market data scrapers."""

    def __init__(self, market: str) -> None:
        self.market = market

    @abstractmethod
    async def scrape(self) -> list[dict[str, Any]]:
        """Perform the scrape and return a list of raw data rows."""

    async def get_page_content(self, url: str) -> str:  # pragma: no cover
        """Helper to fetch page content using headless Chromium."""
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                content = await page.content()
                return content
            finally:
                await browser.close()
