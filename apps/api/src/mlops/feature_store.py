"""Feature store for market data snapshots."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from datetime import date


class FeatureStore:
    """Manages market features for research."""

    def engineer_features(
        self, spot: float, strike: float, time_to_expiry: float, sigma: float, r_rate: float
    ) -> dict[str, float]:
        """Compute derived features for models."""
        return {
            "moneyness": spot / strike if strike > 0 else 0.0,
            "time_sqrt": np.sqrt(time_to_expiry) if time_to_expiry >= 0 else 0.0,
            "vol_time": sigma * np.sqrt(time_to_expiry) if time_to_expiry >= 0 else 0.0,
            "intrinsic_value": max(spot - strike, 0.0),
        }

    async def save_snapshot(
        self, snapshot_date: date, features: dict[str, float], option_count: int
    ) -> None:
        """Persist a feature snapshot to the database."""
        import json

        from src.database.neon_client import acquire

        async with acquire() as conn:
            await conn.execute(
                """
                INSERT INTO feature_snapshots (snapshot_date, features, option_count)
                VALUES ($1, $2, $3)
                ON CONFLICT (snapshot_date) DO UPDATE
                SET features = EXCLUDED.features, option_count = EXCLUDED.option_count
                """,
                snapshot_date,
                json.dumps(features),
                option_count,
            )

    async def get_snapshot(self, snapshot_date: date) -> dict[str, float] | None:
        """Retrieve a feature snapshot from the database."""
        import json

        from src.database.neon_client import acquire

        async with acquire() as conn:
            row = await conn.fetchrow(
                "SELECT features FROM feature_snapshots WHERE snapshot_date = $1",
                snapshot_date,
            )
            if row and row["features"]:
                data = row["features"]
                return json.loads(data) if isinstance(data, str) else dict(data)
            return None
