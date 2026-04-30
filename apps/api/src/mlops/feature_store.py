"""Feature store for market data snapshots."""
from __future__ import annotations
import numpy as np

class FeatureStore:
    """Manages market features for research."""
    
    def engineer_features(self, spot: float, strike: float, time_to_expiry: float, sigma: float, r_rate: float) -> dict[str, float]:
        """Compute derived features for models."""
        return {
            "moneyness": spot / strike if strike > 0 else 0.0,
            "time_sqrt": np.sqrt(time_to_expiry) if time_to_expiry >= 0 else 0.0,
            "vol_time": sigma * np.sqrt(time_to_expiry) if time_to_expiry >= 0 else 0.0,
            "intrinsic_value": max(spot - strike, 0.0)
        }
