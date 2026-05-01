"""Unit tests for data transformers."""

from __future__ import annotations

from datetime import date

import pytest

from src.data.transformers import transform_market_row


@pytest.mark.unit
def test_transform_market_row_mappings() -> None:
    """Verify that field name mappings are correctly applied."""
    row = {
        "strike": 100.0,
        "lastPrice": 10.5,
        "expirationDate": "2024-12-31",
        "impliedVolatility": 0.25,
        "underlying_price": "100.0",
        "trade_date": "2024-01-01",
        "v": 100,
    }
    transformed = transform_market_row(row)

    assert "strike_price" in transformed
    assert transformed["strike_price"] == pytest.approx(100.0)
    assert "strike" not in transformed

    assert "mid_price" in transformed
    assert transformed["mid_price"] == pytest.approx(10.5)
    assert "lastPrice" not in transformed

    assert "maturity_date" in transformed
    assert transformed["maturity_date"] == date(2024, 12, 31)
    assert "expirationDate" not in transformed

    assert "volume" in transformed
    assert transformed["volume"] == 100
    assert "v" not in transformed

    assert "implied_vol" in transformed
    assert transformed["implied_vol"] == pytest.approx(0.25)
    assert "impliedVolatility" not in transformed

    assert transformed["underlying_price"] == pytest.approx(100.0)
    assert transformed["trade_date"] == date(2024, 1, 1)


@pytest.mark.unit
def test_transform_market_row_numeric_normalization() -> None:
    """Verify that string values are converted to floats."""
    row = {
        "underlying_price": "100.5",
        "strike_price": "100.0",
        "time_to_expiry": "0.5",
        "risk_free_rate": "0.05",
        "bid": "10.0",
        "ask": "11.0",
        "volatility": "0.2",
        "implied_vol": "0.22",
    }
    transformed = transform_market_row(row)

    for field in [
        "underlying_price",
        "strike_price",
        "time_to_expiry",
        "risk_free_rate",
        "bid",
        "ask",
        "volatility",
        "implied_vol",
    ]:
        assert isinstance(transformed[field], float)


@pytest.mark.unit
def test_transform_market_row_maturity_date_transformation() -> None:
    """Verify maturity_date transformation specifically."""
    row = {"maturity_date": "2025-06-30"}
    transformed = transform_market_row(row)
    assert transformed["maturity_date"] == date(2025, 6, 30)

    # Already a date
    row2 = {"maturity_date": date(2025, 6, 30)}
    transformed2 = transform_market_row(row2)
    assert transformed2["maturity_date"] == date(2025, 6, 30)
