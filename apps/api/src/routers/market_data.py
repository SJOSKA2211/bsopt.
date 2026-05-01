"""Market data router for browsing current option prices — Python 3.14."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from src.auth.dependencies import get_current_user_id
from src.database.repository import query_market_data

router = APIRouter(prefix="/market-data", tags=["Market Data"])


@router.get("/")
async def get_market_data(
    option_id: str | None = None,
    market_source: str | None = None,
    limit: int = Query(100, le=500),
    user_id: str = Depends(get_current_user_id)
) -> dict[str, Any]:
    """Fetch recent market data."""
    results = await query_market_data(option_id=option_id, market_source=market_source, limit=limit)
    return {"results": results}
