"""Router for market data and option parameters."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from src.database.neon_client import acquire

router = APIRouter(prefix="/market", tags=["Market Data"])


@router.get("/options")
async def list_options(
    market: str | None = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """Retrieve a paginated list of option parameters."""
    async with acquire() as conn:
        query = """
            SELECT * FROM option_parameters
            WHERE ($1::text IS NULL OR market_source = $1)
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        """
        rows = await conn.fetch(query, market, limit, offset)

        count = await conn.fetchval(
            "SELECT COUNT(*) FROM option_parameters WHERE ($1::text IS NULL OR market_source = $1)",
            market,
        )

        return {
            "items": [dict(row) for row in rows],
            "total": count,
            "limit": limit,
            "offset": offset,
        }


@router.get("/quotes")
async def get_market_quotes(
    market: str = Query(..., description="e.g., spy, nse"),
    limit: int = Query(100, le=500),
) -> list[dict[str, Any]]:
    """Retrieve recent market quotes for a specific market."""
    async with acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT md.*, op.strike_price, op.option_type
            FROM market_data md
            JOIN option_parameters op ON md.option_id = op.id
            WHERE op.market_source = $1
            ORDER BY md.trade_date DESC, md.created_at DESC
            LIMIT $2
            """,
            market,
            limit,
        )
        return [dict(row) for row in rows]
