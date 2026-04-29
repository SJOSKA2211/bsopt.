"""Data validators for market and option data."""

from __future__ import annotations

from typing import Any

from src.exceptions import ValidationError


def validate_option_parameters(data: dict[str, Any]) -> None:
    """Validate raw option parameter inputs."""
    errors = []
    required = [
        "underlying_price",
        "strike_price",
        "time_to_maturity",
        "volatility",
        "risk_free_rate",
        "option_type",
    ]

    for field in required:
        if field not in data or data[field] is None:
            errors.append(f"Missing required field: {field}")
            continue

        val = data[field]
        if field != "option_type":
            try:
                f_val = float(val)
                if field != "risk_free_rate" and f_val <= 0:
                    errors.append(f"{field} must be greater than zero")
                elif field == "risk_free_rate" and f_val < 0:
                    errors.append(f"{field} must be non-negative")
            except ValueError, TypeError:
                errors.append(f"{field} must be a number")
        elif val not in ("call", "put"):
            errors.append("option_type must be 'call' or 'put'")

    if errors:
        raise ValidationError("Option parameter validation failed", {"errors": errors})


def validate_market_data(data: dict[str, Any]) -> None:
    """Validate market data inputs (bid/ask/volume)."""
    errors = []
    if (
        "bid" in data
        and "ask" in data
        and data["bid"] is not None
        and data["ask"] is not None
        and data["bid"] > data["ask"]
    ):
        errors.append("Bid cannot be greater than ask")

    if "volume" in data and data["volume"] is not None and data["volume"] < 0:
        errors.append("Volume cannot be negative")

    if errors:
        raise ValidationError("Market data validation failed", {"errors": errors})
