"""Scrapers router for triggering and monitoring market data collection."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from src.auth.dependencies import get_admin_user, get_current_user
from src.queue.publisher import publish_scraper_task

router = APIRouter(prefix="/scrapers", tags=["scrapers"])


@router.post("/trigger")
async def trigger_scraper(
    market: str,
    user: dict[str, Any] = Depends(get_admin_user),
) -> dict[str, str]:
    """
    Trigger a manual scrape run for a specific market.
    Admin only.
    """
    if market not in {"spy", "nse"}:
        raise HTTPException(status_code=400, detail="Unsupported market")

    from src.database.repository import save_scrape_run

    run_id = await save_scrape_run(market=market, scraper_class=f"{market.upper()}Scraper")
    await publish_scraper_task(market=market, run_id=run_id)

    return {
        "status": "success",
        "message": f"Scraper task published for {market}",
        "run_id": run_id,
    }


@router.get("/status")
async def get_scrapers_status(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Get status of current and recent scrape runs."""
    # This would typically query the scrape_runs table
    # For now, return a placeholder or implement query_recent_scrapes
    return {"status": "all systems operational"}
