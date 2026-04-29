"""Database repository for NeonDB operations — Phase 2."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import cast
from uuid import UUID

import structlog

from src.database.neon_client import acquire

logger = structlog.get_logger(__name__)


async def get_user_push_subscriptions(user_id: str) -> list[str]:
    """Fetch user's push subscriptions from the users table."""
    async with acquire() as conn:
        row = await conn.fetchrow(
            "SELECT notification_preferences FROM users WHERE id = $1", user_id
        )
        if row and row["notification_preferences"]:
            prefs = row["notification_preferences"]
            if isinstance(prefs, str):
                prefs = json.loads(prefs)
            return cast("list[str]", prefs.get("push_subscriptions", []))
    return []


async def query_recent_mape(method_type: str, days: int = 7) -> float:
    """Query recent MAPE for a method from validation_metrics."""
    async with acquire() as conn:
        val = await conn.fetchval(
            """
            SELECT AVG(absolute_error)
            FROM validation_metrics
            WHERE method_result_id IN (
                SELECT id FROM method_results
                WHERE method_type = $1 AND created_at > NOW() - interval '$2 days'
            )
            """,
            method_type,
            days,
        )
        return float(val) if val is not None else 0.0


async def save_audit_log(
    pipeline_run_id: str | UUID,
    step_name: str,
    status: str,
    rows_affected: int = 0,
    message: str = "",
) -> None:
    """Insert a row into the audit_log table."""
    async with acquire() as conn:
        await conn.execute(
            """
            INSERT INTO audit_log (pipeline_run_id, step_name, status, rows_affected, message)
            VALUES ($1, $2, $3, $4, $5)
            """,
            str(pipeline_run_id),
            step_name,
            status,
            rows_affected,
            message,
        )


async def save_market_data(
    option_id: str | UUID,
    trade_date: date,
    bid: float | None,
    ask: float | None,
    volume: int | None,
    oi: int | None,
    data_source: str,
    implied_vol: float | None = None,
) -> None:
    """Upsert market data."""
    async with acquire() as conn:
        await conn.execute(
            """
            INSERT INTO market_data (option_id, trade_date, bid, ask, volume, oi, data_source, implied_vol)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (option_id, trade_date) DO UPDATE
            SET bid = EXCLUDED.bid, ask = EXCLUDED.ask, volume = EXCLUDED.volume, 
                oi = EXCLUDED.oi, implied_vol = EXCLUDED.implied_vol
            """,
            str(option_id),
            trade_date,
            bid,
            ask,
            volume,
            oi,
            data_source,
            implied_vol,
        )


async def save_option_parameters(
    underlying_price: float,
    strike_price: float,
    time_to_maturity: float,
    volatility: float,
    risk_free_rate: float,
    option_type: str,
    market_source: str,
    created_by: str | UUID | None = None,
) -> str:
    """Insert option parameters and return the generated UUID."""
    async with acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO option_parameters (
                underlying_price, strike_price, time_to_expiry,
                volatility, risk_free_rate, option_type, market_source, created_by
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (underlying_price, strike_price, time_to_expiry, volatility, risk_free_rate, option_type, market_source) 
            DO UPDATE SET updated_at = NOW()
            RETURNING id
            """,
            underlying_price,
            strike_price,
            time_to_maturity,
            volatility,
            risk_free_rate,
            option_type,
            market_source,
            str(created_by) if created_by else None,
        )
        return str(row["id"]) if row else ""


async def save_scrape_run(
    market: str, scraper_class: str, started_at: datetime | None = None, status: str = "running"
) -> str:
    """Insert a scrape run and return its UUID."""
    if started_at is None:
        started_at = datetime.now(UTC)
    async with acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO scrape_runs (market, scraper_class, started_at, status)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            market,
            scraper_class,
            started_at,
            status,
        )
        return str(row["id"]) if row else ""


async def update_scrape_run(
    run_id: str | UUID, finished_at: datetime, row_counts: int, status: str
) -> None:
    """Update an existing scrape run."""
    async with acquire() as conn:
        await conn.execute(
            "UPDATE scrape_runs SET finished_at = $1, row_counts = $2, status = $3 WHERE id = $4",
            finished_at,
            row_counts,
            status,
            str(run_id),
        )
