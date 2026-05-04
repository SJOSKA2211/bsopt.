"""Feature store for market data snapshots."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import numpy as np

from src.database.repository import get_latest_feature_snapshot, save_feature_snapshot

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
        await save_feature_snapshot(snapshot_date, features, option_count)

    async def get_snapshot(self, _snapshot_date: date) -> dict[str, Any] | None:
        """Retrieve the latest feature snapshot (date parameter ignored for now)."""
        row = await get_latest_feature_snapshot()
        if not row:
            return None

        features = row.get("features")
        if isinstance(features, str):
            return json.loads(features)  # type: ignore[no-any-return]
        return features  # type: ignore[no-any-return]
