"""Data collection script to trigger manual scrapes."""

from __future__ import annotations

import argparse
import asyncio

import structlog

from src.scrapers.scraper_factory import get_scraper

logger = structlog.get_logger(__name__)


async def collect_market_data(market: str) -> None:
    """Trigger a scrape for the specified market."""
    logger.info("manual_collection_started", market=market)

    try:
        scraper = get_scraper(market)
        data = await scraper.scrape()

        if data:
            import gzip
            import json
            import os
            from datetime import datetime

            from src.config import get_settings

            settings = get_settings()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{market}_{timestamp}.json.gz"
            filepath = os.path.join(settings.watchdog_watch_dir, filename)

            with gzip.open(filepath, "wt", encoding="utf-8") as f:
                json.dump(data, f)

            logger.info("manual_collection_saved", market=market, rows=len(data), path=filepath)
        else:
            logger.warning("manual_collection_empty", market=market)

    except Exception as exc:
        logger.error("manual_collection_failed", market=market, error=str(exc))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", required=True, help="Market to scrape (e.g., spy)")
    args = parser.parse_argument()

    asyncio.run(collect_market_data(args.market))
