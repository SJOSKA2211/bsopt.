"""SPY options scraper for Yahoo Finance."""

from __future__ import annotations

from typing import Any

import structlog
from playwright.async_api import async_playwright

from src.scrapers.base_scraper import BaseScraper

logger = structlog.get_logger(__name__)


class SpyScraper(BaseScraper):
    """Scraper for SPY options using Yahoo Finance."""

    def __init__(self) -> None:
        super().__init__(market="spy")
        self.base_url = "https://finance.yahoo.com/quote/SPY/options"

    async def scrape(self, url: str | None = None) -> list[dict[str, Any]]:  # pragma: no cover
        """Scrape SPY options data and return raw rows."""
        target_url = url or self.base_url
        logger.info("scraping_started", market=self.market, url=target_url)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            page = await browser.new_page()
            try:
                await page.goto(target_url, wait_until="networkidle", timeout=30000)

                # Extract rows (simplified logic for demonstration)
                # In production, we would iterate through expiries and calls/puts
                rows = await page.evaluate("""() => {
                    const data = [];
                    const tableRows = document.querySelectorAll('table tbody tr');
                    tableRows.forEach(row => {
                        const cols = row.querySelectorAll('td');
                        if (cols.length >= 10) {
                            data.push({
                                strike: cols[2].innerText,
                                last_price: cols[3].innerText,
                                bid: cols[4].innerText,
                                ask: cols[5].innerText,
                                change: cols[6].innerText,
                                volume: cols[8].innerText,
                                open_interest: cols[9].innerText,
                                implied_vol: cols[10].innerText
                            });
                        }
                    });
                    return data;
                }""")

                from typing import cast

                return cast("list[dict[str, Any]]", rows)
            except Exception as exc:
                logger.error("scraping_failed", market=self.market, error=str(exc))
                raise
            finally:
                await browser.close()
