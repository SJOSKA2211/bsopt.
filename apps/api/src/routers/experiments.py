"""Router for pricing experiments and historical results."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Query

from src.auth.dependencies import get_current_user_id
from src.database.neon_client import acquire

if TYPE_CHECKING:
    from uuid import UUID

router = APIRouter(prefix="/experiments", tags=["Experiments"])


@router.get("/")
async def list_experiments(
    cursor: UUID | None = Query(None),
    limit: int = Query(50, le=100),
    method_type: str | None = None,
    market_source: str | None = None,
    user_id: UUID = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Retrieve a paginated list of pricing experiments."""
    # Cursor-based pagination logic
    async with acquire() as conn:
        query = """
            SELECT mr.*, op.underlying_price, op.strike_price, op.option_type, op.market_source
            FROM method_results mr
            JOIN option_parameters op ON mr.option_id = op.id
            WHERE ($1::uuid IS NULL OR mr.id < $1)
            AND ($2::text IS NULL OR mr.method_type = $2)
            AND ($3::text IS NULL OR op.market_source = $3)
            ORDER BY mr.id DESC
            LIMIT $4
        """
        rows = await conn.fetch(query, cursor, method_type, market_source, limit)

        results = [dict(row) for row in rows]
        next_cursor = results[-1]["id"] if len(results) == limit else None

        return {
            "results": results,
            "next_cursor": next_cursor,
            "count": len(results),
        }


@router.get("/{experiment_id}")
async def get_experiment_details(
    experiment_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Get detailed metrics for a specific experiment."""
    async with acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT mr.*, vm.absolute_error, vm.mape, vm.market_deviation
            FROM method_results mr
            LEFT JOIN validation_metrics vm ON mr.id = vm.method_result_id
            WHERE mr.id = $1
            """,
            experiment_id,
        )
        if not row:
            return {"error": "Experiment not found"}
        return dict(row)
