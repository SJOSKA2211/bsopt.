"""Experiments router for browsing historical pricing results."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Query

from src.auth.dependencies import get_current_user
from src.database.repository import query_experiments

if TYPE_CHECKING:
    from datetime import datetime

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.get("/")
async def list_experiments(
    method_type: str | None = Query(None),
    market_source: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    cursor: datetime | None = Query(None),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Fetch historical experiment results with pagination.
    Authenticated users only.
    """
    results = await query_experiments(
        method_type=method_type,
        market_source=market_source,
        limit=limit,
        cursor=cursor,
    )

    next_cursor = results[-1]["created_at"] if len(results) == limit else None

    return {
        "results": results,
        "next_cursor": next_cursor,
        "count": len(results),
    }
