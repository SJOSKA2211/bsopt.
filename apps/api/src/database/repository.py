"""Database repository for NeonDB operations."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, cast

from src.database.neon_client import acquire

if TYPE_CHECKING:
    from datetime import date
    from uuid import UUID


async def save_option_parameters(
    underlying_price: float,
    strike_price: float,
    time_to_maturity: float,
    volatility: float,
    risk_free_rate: float,
    option_type: str,
    market_source: str | None = None,
    user_id: UUID | None = None,
) -> UUID:
    """Upsert option parameters and return the record ID."""
    async with acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO option_parameters (
                underlying_price, strike_price, time_to_maturity,
                volatility, risk_free_rate, option_type, market_source, created_by
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (underlying_price, strike_price, time_to_maturity, volatility, risk_free_rate, option_type, market_source)
            DO UPDATE SET underlying_price = EXCLUDED.underlying_price
            RETURNING id
            """,
            underlying_price,
            strike_price,
            time_to_maturity,
            volatility,
            risk_free_rate,
            option_type,
            market_source,
            user_id,
        )
        assert row is not None
        return cast("UUID", row["id"])


async def save_method_result(
    option_id: UUID,
    method_type: str,
    computed_price: float,
    parameter_set: dict[str, Any] | None = None,
    parameter_hash: str | None = None,
    exec_seconds: float | None = None,
    converged: bool | None = None,
    replications: int | None = None,
    mlflow_run_id: str | None = None,
) -> UUID:
    """Save a pricing result."""
    p_hash = parameter_hash or "default"

    async with acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO method_results (
                option_id, method_type, parameter_set, parameter_hash,
                computed_price, exec_seconds, converged, replications, mlflow_run_id
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (option_id, method_type, parameter_hash)
            DO UPDATE SET computed_price = EXCLUDED.computed_price
            RETURNING id
            """,
            option_id,
            method_type,
            json.dumps(parameter_set) if parameter_set else None,
            p_hash,
            computed_price,
            exec_seconds,
            converged,
            replications,
            mlflow_run_id,
        )
        assert row is not None
        return cast("UUID", row["id"])


async def query_recent_mape(method_type: str, days: int = 7) -> float:
    """Query average MAPE for a method over the last N days."""
    async with acquire() as conn:
        val = await conn.fetchval(
            """
            SELECT AVG(mape)
            FROM validation_metrics vm
            JOIN method_results mr ON vm.method_result_id = mr.id
            WHERE mr.method_type = $1
            AND vm.created_at > NOW() - INTERVAL '1 day' * $2
            """,
            method_type,
            days,
        )
        return float(val or 0.0)


async def save_scrape_run(
    market: str,
    scraper_class: str,
    status: str = "running",
    triggered_by: UUID | None = None,
) -> UUID:
    """Create a new scrape run record."""
    async with acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO scrape_runs (market, scraper_class, status, triggered_by)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            market,
            scraper_class,
            status,
            triggered_by,
        )
        assert row is not None
        return cast("UUID", row["id"])


async def update_scrape_run(
    run_id: UUID,
    status: str,
    rows_inserted: int = 0,
) -> None:
    """Update an existing scrape run record."""
    async with acquire() as conn:
        await conn.execute(
            """
            UPDATE scrape_runs
            SET status = $2, rows_inserted = $3, finished_at = NOW()
            WHERE id = $1
            """,
            run_id,
            status,
            rows_inserted,
        )


async def save_market_data(
    option_id: UUID,
    trade_date: date,
    bid: float | None = None,
    ask: float | None = None,
    volume: int | None = None,
    oi: int | None = None,
    implied_vol: float | None = None,
    data_source: str | None = None,
) -> None:
    """Save market data for an option."""
    async with acquire() as conn:
        await conn.execute(
            """
            INSERT INTO market_data (option_id, trade_date, bid, ask, volume, oi, implied_vol, data_source)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (option_id, trade_date)
            DO UPDATE SET bid = EXCLUDED.bid, ask = EXCLUDED.ask, volume = EXCLUDED.volume
            """,
            option_id,
            trade_date,
            bid,
            ask,
            volume,
            oi,
            implied_vol,
            data_source,
        )


async def save_validation_metric(
    option_id: UUID,
    method_result_id: UUID,
    absolute_error: float,
    mape: float,
    market_deviation: float | None = None,
) -> None:
    """Save a validation metric."""
    async with acquire() as conn:
        await conn.execute(
            """
            INSERT INTO validation_metrics (option_id, method_result_id, absolute_error, mape, market_deviation)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (option_id, method_result_id)
            DO UPDATE SET absolute_error = EXCLUDED.absolute_error, mape = EXCLUDED.mape
            """,
            option_id,
            method_result_id,
            absolute_error,
            mape,
            market_deviation,
        )


async def save_audit_log(
    step_name: str,
    status: str,
    pipeline_run_id: UUID | None = None,
    rows_affected: int = 0,
    message: str | None = None,
) -> None:
    """Save an audit log record."""
    async with acquire() as conn:
        await conn.execute(
            """
            INSERT INTO audit_log (pipeline_run_id, step_name, status, rows_affected, message)
            VALUES ($1, $2, $3, $4, $5)
            """,
            pipeline_run_id,
            step_name,
            status,
            rows_affected,
            message,
        )


async def get_market_data(market_source: str, limit: int = 100) -> list[dict[str, Any]]:
    """Retrieve recent market data joined with option parameters."""
    async with acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT md.*, op.underlying_price, op.strike_price, op.volatility, op.time_to_maturity, op.option_type
            FROM market_data md
            JOIN option_parameters op ON md.option_id = op.id
            WHERE md.data_source = $1
            ORDER BY md.trade_date DESC
            LIMIT $2
            """,
            market_source,
            limit,
        )
        return [dict(r) for r in rows]


async def get_latest_metrics(limit: int = 50) -> list[dict[str, Any]]:
    """Retrieve latest validation metrics for dashboard."""
    async with acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT vm.*, mr.method_type, op.underlying_price, op.strike_price
            FROM validation_metrics vm
            JOIN method_results mr ON vm.method_result_id = mr.id
            JOIN option_parameters op ON mr.option_id = op.id
            ORDER BY vm.created_at DESC
            LIMIT $1
            """,
            limit,
        )
        return [dict(r) for r in rows]


async def get_user_push_subscriptions(user_id: str) -> list[str]:
    """Retrieve all web push subscriptions for a user."""
    async with acquire() as conn:
        rows = await conn.fetch(
            "SELECT subscription_json FROM user_push_subscriptions WHERE user_id = $1",
            user_id,
        )
        return [r["subscription_json"] for r in rows]


async def save_user_push_subscription(user_id: str, subscription_json: str) -> None:
    """Save a new web push subscription for a user."""
    async with acquire() as conn:
        await conn.execute(
            """
            INSERT INTO user_push_subscriptions (user_id, subscription_json)
            VALUES ($1, $2)
            ON CONFLICT (user_id, subscription_json) DO NOTHING
            """,
            user_id,
            subscription_json,
        )


async def save_model_metadata(
    name: str,
    version: str,
    uri: str,
    metadata: dict[str, Any],
) -> None:
    """Save model metadata to ml_experiments table."""
    async with acquire() as conn:
        await conn.execute(
            """
            INSERT INTO ml_experiments (experiment_name, model_version, model_uri, metadata)
            VALUES ($1, $2, $3, $4)
            """,
            name,
            version,
            uri,
            json.dumps(metadata),
        )


async def get_latest_model(name: str) -> dict[str, Any]:
    """Retrieve the latest version of a model."""
    async with acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT model_version as version, model_uri as uri, metadata
            FROM ml_experiments
            WHERE experiment_name = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            name,
        )
        if row:
            return {
                "version": row["version"],
                "uri": row["uri"],
                "metadata": json.loads(row["metadata"]),
            }
        return {}


async def save_notification(
    user_id: str,
    title: str,
    body: str,
    severity: str,
) -> None:
    """Persist a notification to the database."""
    async with acquire() as conn:
        await conn.execute(
            """
            INSERT INTO notifications (user_id, title, body, severity)
            VALUES ($1, $2, $3, $4)
            """,
            user_id,
            title,
            body,
            severity,
        )
