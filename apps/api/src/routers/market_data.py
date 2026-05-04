"""Market data router for browsing current option prices — Python 3.14."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Query

from src.auth.dependencies import get_current_user_id
from src.database.repository import query_market_data

if TYPE_CHECKING:
    from typing import Any

router = APIRouter(prefix="/market-data", tags=["Market Data"])


@router.get("/")
async def get_market_data(
    user_id: Annotated[str, Depends(get_current_user_id)],
    option_id: str | None = None,
    market_source: str | None = None,
    limit: Annotated[int, Query(le=500)] = 100,
) -> dict[str, object]:
    """Fetch recent market data."""
    results = await query_market_data(option_id=option_id, market_source=market_source, limit=limit)
    return {"results": results}
