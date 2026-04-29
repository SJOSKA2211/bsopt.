"""Scraper management router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.database.repository import save_scrape_run
from src.queue.publisher import publish_scraper_task

router = APIRouter(prefix="/scrapers", tags=["scrapers"])


@router.post("/trigger")
async def trigger_scraper(market: str) -> dict[str, Any]:
    """Manually trigger a scraper run for a specific market."""
    if market not in ("spy", "nse"):
        raise HTTPException(status_code=400, detail="Unsupported market")

    # 1. Create a run record in NeonDB
    run_id = await save_scrape_run(
        market=market,
        scraper_class=f"{market.capitalize()}Scraper",
        status="pending",
    )

    # 2. Publish task to RabbitMQ
    await publish_scraper_task(market=market, run_id=str(run_id))

    return {
        "status": "triggered",
        "run_id": run_id,
        "market": market,
    }
