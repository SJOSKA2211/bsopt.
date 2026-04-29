"""Data transformers for market data cleaning and normalization."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def transform_market_row(row: dict[str, Any]) -> dict[str, Any]:
    """Clean and normalize a single market data row."""
    transformed = row.copy()

    # Normalize field names (e.g. from Yahoo Finance or NSE format)
    mappings = {
        "strike": "strike_price",
        "lastPrice": "mid_price",
        "expirationDate": "maturity_date",
        "impliedVolatility": "implied_vol",
    }

    for key, target in mappings.items():
        if key in transformed and target not in transformed:
            transformed[target] = transformed.pop(key)

    # Date transformation
    if "trade_date" in transformed and isinstance(transformed["trade_date"], str):
        transformed["trade_date"] = datetime.fromisoformat(transformed["trade_date"]).date()

    if "maturity_date" in transformed and isinstance(transformed["maturity_date"], str):
        transformed["maturity_date"] = datetime.fromisoformat(transformed["maturity_date"]).date()

    # Numeric normalization
    for field in [
        "underlying_price",
        "strike_price",
        "time_to_maturity",
        "risk_free_rate",
        "bid",
        "ask",
        "volatility",
        "implied_vol",
    ]:
        if field in transformed and transformed[field] is not None:
            transformed[field] = float(transformed[field])

    return transformed
