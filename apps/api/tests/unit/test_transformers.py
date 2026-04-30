"""Unit tests for data transformers."""
from __future__ import annotations
from datetime import date
from src.data.transformers import transform_market_row

def test_transform_market_row_mappings():
    row = {
        "strike": 100,
        "lastPrice": 10.5,
        "expirationDate": "2024-12-31",
        "impliedVolatility": 0.25,
        "underlying_price": 100
    }
    transformed = transform_market_row(row)
    assert transformed["strike_price"] == 100
    assert transformed["mid_price"] == 10.5
    assert transformed["maturity_date"] == date(2024, 12, 31)
    assert transformed["implied_vol"] == 0.25

def test_transform_market_row_types():
    row = {
        "underlying_price": "100.5",
        "strike_price": "100",
        "trade_date": "2024-01-01",
        "bid": "10.1",
        "ask": "10.9",
        "volatility": "0.2"
    }
    transformed = transform_market_row(row)
    assert isinstance(transformed["underlying_price"], float)
    assert transformed["underlying_price"] == 100.5
    assert isinstance(transformed["trade_date"], date)
    assert transformed["trade_date"] == date(2024, 1, 1)

def test_transform_market_row_missing_optional():
    row = {"underlying_price": 100}
    transformed = transform_market_row(row)
    assert transformed["underlying_price"] == 100.0
    assert "bid" not in transformed
