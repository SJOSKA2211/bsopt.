"""Scrapers router for managing market data collection — Python 3.14."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from src.auth.dependencies import get_admin_user, get_current_user_id
from src.database.repository import get_recent_scrape_runs
from src.queue.publisher import publish_scraper_task

router = APIRouter(prefix="/scrapers", tags=["Scrapers"])


@router.get("/runs")
async def get_scrape_runs(
    limit: int = Query(10, le=50), user_id: str = Depends(get_current_user_id)
) -> list[dict[str, Any]]:
    """Fetch recent scraper runs."""
    return await get_recent_scrape_runs(limit=limit)


@router.post("/trigger")
async def trigger_scraper(
    market: str = Query(...), admin_user: dict[str, Any] = Depends(get_admin_user)
) -> dict[str, str]:
    """Trigger a scraper run via RabbitMQ."""
    try:
        await publish_scraper_task(market)
        return {"status": "success", "message": f"Scraper triggered for {market}"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
