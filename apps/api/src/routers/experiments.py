"""Experiments router for managing and querying pricing experiments — Python 3.14."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Query

from src.auth.dependencies import get_current_user_id
from src.database.repository import get_all_experiments, get_experiment_by_id, query_experiments

if TYPE_CHECKING:
    from datetime import datetime

router = APIRouter(prefix="/experiments", tags=["Experiments"])


@router.get("/")
async def list_experiments(
    method_type: str | None = None,
    market_source: str | None = None,
    limit: int = Query(50, le=100),
    cursor: datetime | None = None,
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Query experiments with pagination and filtering."""
    results = await query_experiments(
        method_type=method_type, market_source=market_source, limit=limit, cursor=cursor
    )
    return {
        "results": results,
        "count": len(results),
        "next_cursor": results[-1]["created_at"] if results else None,
    }


@router.get("/all")
async def get_ml_experiments(user_id: str = Depends(get_current_user_id)) -> list[dict[str, Any]]:
    """Fetch all ML experiments from the ml_experiments table."""
    return await get_all_experiments()


@router.get("/{experiment_id}")
async def get_experiment(
    experiment_id: str, user_id: str = Depends(get_current_user_id)
) -> dict[str, Any]:
    """Fetch details of a specific experiment."""
    result = await get_experiment_by_id(experiment_id)
    if not result:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Experiment not found")
    return result
