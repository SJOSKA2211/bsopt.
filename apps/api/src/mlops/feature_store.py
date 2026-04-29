"""Feature store for capturing data snapshots for ML training."""

from __future__ import annotations

import json
import math
from typing import TYPE_CHECKING, Any

import structlog

from src.database.neon_client import acquire

if TYPE_CHECKING:
    from datetime import date

logger = structlog.get_logger(__name__)


class FeatureStore:
    """Manages snapshots of market data features for model lineage."""

    @staticmethod
    def engineer_features(
        underlying_price: float,
        strike_price: float,
        time_to_maturity: float,
        volatility: float,
        risk_free_rate: float,
    ) -> dict[str, float]:
        """Pure function to engineer features for ML models."""
        return {
            "moneyness": underlying_price / strike_price,
            "time_sqrt": math.sqrt(time_to_maturity),
            "volatility": volatility,
            "risk_free_rate": risk_free_rate,
            "log_s": math.log(underlying_price),
        }

    @staticmethod
    async def save_snapshot(
        snapshot_date: date,
        features: dict[str, Any],
        option_count: int,
    ) -> None:
        """Persist a feature snapshot to NeonDB."""
        async with acquire() as conn:
            await conn.execute(
                """
                INSERT INTO feature_snapshots (snapshot_date, features, option_count)
                VALUES ($1, $2, $3)
                ON CONFLICT (snapshot_date)
                DO UPDATE SET features = EXCLUDED.features, option_count = EXCLUDED.option_count
                """,
                snapshot_date,
                json.dumps(features),
                option_count,
            )
            logger.info("feature_snapshot_saved", date=str(snapshot_date), count=option_count)

    @staticmethod
    async def get_snapshot(snapshot_date: date) -> dict[str, Any] | None:
        """Retrieve a specific feature snapshot."""
        async with acquire() as conn:
            row = await conn.fetchrow(
                "SELECT features FROM feature_snapshots WHERE snapshot_date = $1",
                snapshot_date,
            )
            if row:
                from typing import cast

                return cast("dict[str, Any]", json.loads(row["features"]))
            return None
