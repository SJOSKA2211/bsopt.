"""Exhaustive unit tests for data validators."""

from __future__ import annotations

import pytest

from src.data.validators import validate_market_data, validate_option_parameters
from src.exceptions import ValidationError


@pytest.mark.unit
def test_option_parameter_validation_success() -> None:
    valid_data = {
        "underlying_price": 100.0,
        "strike_price": 100.0,
        "time_to_expiry": 1.0,
        "volatility": 0.2,
        "risk_free_rate": 0.05,
        "option_type": "call",
    }
    # Should not raise
    validate_option_parameters(valid_data)

    # Test boundary for risk_free_rate (can be 0)
    valid_data["risk_free_rate"] = 0.0
    validate_option_parameters(valid_data)


@pytest.mark.unit
def test_option_parameter_validation_missing_fields() -> None:
    required = [
        "underlying_price",
        "strike_price",
        "time_to_expiry",
        "volatility",
        "risk_free_rate",
        "option_type",
    ]

    for field in required:
        # Create data with all fields except the current one
        data = {f: (10.0 if f != "option_type" else "call") for f in required if f != field}

        with pytest.raises(ValidationError) as excinfo:
            validate_option_parameters(data)
        assert f"Missing required field: {field}" in str(excinfo.value.errors)


@pytest.mark.unit
def test_option_parameter_validation_invalid_values() -> None:
    # Negative values
    invalid_cases = [
        ("underlying_price", -1, "must be greater than zero"),
        ("underlying_price", 0, "must be greater than zero"),
        ("strike_price", -1, "must be greater than zero"),
        ("time_to_expiry", -0.1, "must be greater than zero"),
        ("volatility", -0.5, "must be greater than zero"),
        ("risk_free_rate", -0.01, "must be non-negative"),
        ("option_type", "invalid", "option_type must be 'call' or 'put'"),
        ("underlying_price", "abc", "must be a number"),
    ]

    for field, value, expected_msg in invalid_cases:
        data = {
            "underlying_price": 100.0,
            "strike_price": 100.0,
            "time_to_expiry": 1.0,
            "volatility": 0.2,
            "risk_free_rate": 0.05,
            "option_type": "call",
        }
        data[field] = value
        with pytest.raises(ValidationError) as excinfo:
            validate_option_parameters(data)
        assert expected_msg in str(excinfo.value.errors)


@pytest.mark.unit
def test_option_parameter_multi_error_collection() -> None:
    data = {
        "underlying_price": -100,
        "volatility": -0.2,
        "option_type": "binary"
    }
    with pytest.raises(ValidationError) as excinfo:
        validate_option_parameters(data)
    errors = excinfo.value.errors
    assert len(errors) > 1
    assert any("underlying_price" in e for e in errors)
    assert any("volatility" in e for e in errors)
    assert any("option_type" in e for e in errors)


@pytest.mark.unit
def test_market_data_validation() -> None:
    # Success
    validate_market_data({"bid": 10.0, "ask": 10.5, "volume": 100})

    # Bid > Ask
    with pytest.raises(ValidationError) as excinfo:
        validate_market_data({"bid": 11.0, "ask": 10.5})
    assert "Bid cannot be greater than ask" in str(excinfo.value.errors)

    # Negative volume
    with pytest.raises(ValidationError) as excinfo:
        validate_market_data({"volume": -10})
    assert "Volume cannot be negative" in str(excinfo.value.errors)

    # None values (should be ignored or handled)
    validate_market_data({"bid": None, "ask": 10.0})
    validate_market_data({"volume": None})


@pytest.mark.unit
def test_option_parameter_validation_exercise_type() -> None:
    data = {
        "underlying_price": 100.0,
        "strike_price": 100.0,
        "time_to_expiry": 1.0,
        "volatility": 0.2,
        "risk_free_rate": 0.05,
        "option_type": "call",
        "exercise_type": "invalid",
    }
    with pytest.raises(ValidationError) as excinfo:
        validate_option_parameters(data)
    assert "exercise_type must be 'european' or 'american'" in str(excinfo.value.errors)


@pytest.mark.unit
def test_option_parameter_validation_market_source() -> None:
    data = {
        "underlying_price": 100.0,
        "strike_price": 100.0,
        "time_to_expiry": 1.0,
        "volatility": 0.2,
        "risk_free_rate": 0.05,
        "option_type": "call",
        "market_source": "",
    }
    with pytest.raises(ValidationError) as excinfo:
        validate_option_parameters(data)
    assert "market_source cannot be empty" in str(excinfo.value.errors)


@pytest.mark.unit
def test_market_data_validation_missing_fields() -> None:
    # Market data might have all fields optional but at least one should be present?
    # Actually, our validator requires bid, ask, volume to be valid if present.
    validate_market_data({})  # Empty is fine according to current logic


@pytest.mark.unit
def test_market_data_validation_invalid_values() -> None:
    with pytest.raises(ValidationError) as excinfo:
        validate_market_data({"bid": "high"})
    assert "must be a number" in str(excinfo.value.errors)


@pytest.mark.unit
def test_option_parameter_validation_extremely_large_values() -> None:
    data = {
        "underlying_price": 1e12,
        "strike_price": 100.0,
        "time_to_expiry": 1.0,
        "volatility": 0.2,
        "risk_free_rate": 0.05,
        "option_type": "call",
    }
    # Large values should be fine for math, but we check if validator rejects them (it doesn't currently)
    validate_option_parameters(data)


@pytest.mark.unit
def test_option_parameter_validation_zero_volatility() -> None:
    data = {
        "underlying_price": 100.0,
        "strike_price": 100.0,
        "time_to_expiry": 1.0,
        "volatility": 0.0,
        "risk_free_rate": 0.05,
        "option_type": "call",
    }
    with pytest.raises(ValidationError) as excinfo:
        validate_option_parameters(data)
    assert "must be greater than zero" in str(excinfo.value.errors)


@pytest.mark.unit
def test_market_data_validation_negative_bid() -> None:
    with pytest.raises(ValidationError) as excinfo:
        validate_market_data({"bid": -10.0})
    assert "cannot be negative" in str(excinfo.value.errors)


@pytest.mark.unit
def test_market_data_validation_invalid_volume_type() -> None:
    with pytest.raises(ValidationError) as excinfo:
        validate_market_data({"volume": "lots"})
    assert "Volume must be an integer" in str(excinfo.value.errors)


@pytest.mark.unit
def test_market_data_validation_zero_ask() -> None:
    # Ask can be 0 (unlikely but valid for validator)
    validate_market_data({"ask": 0.0, "bid": 0.0})
