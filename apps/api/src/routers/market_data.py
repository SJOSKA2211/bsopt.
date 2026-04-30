"""Market data router for browsing current option prices."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from src.auth.dependencies import get_current_user
from src.database.repository import query_market_data

router = APIRouter(prefix="/market-data", tags=["market_data"])


@router.get("/")
async def list_market_data(
    market_source: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Fetch recent market data for options.
    Authenticated users only.
    """
    results = await query_market_data(market_source=market_source, limit=limit)

    return {
        "results": results,
        "count": len(results),
    }
