"""Exhaustive unit tests for data validators."""

from __future__ import annotations

import pytest
from src.data.validators import validate_option_parameters, validate_market_data
from src.exceptions import ValidationError

@pytest.mark.unit
def test_option_parameter_validation_success():
    valid_data = {
        "underlying_price": 100.0,
        "strike_price": 100.0,
        "time_to_maturity": 1.0,
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
def test_option_parameter_validation_missing_fields():
    required = [
        "underlying_price",
        "strike_price",
        "time_to_maturity",
        "volatility",
        "risk_free_rate",
        "option_type",
    ]
    
    for field in required:
        # Create data with all fields except the current one
        data = {f: (10.0 if f != "option_type" else "call") for f in required if f != field}
            
        with pytest.raises(ValidationError) as excinfo:
            validate_option_parameters(data)
        assert f"Missing required field: {field}" in str(excinfo.value.details["errors"])

@pytest.mark.unit
def test_option_parameter_validation_invalid_values():
    # Negative values
    invalid_cases = [
        ("underlying_price", -1, "must be greater than zero"),
        ("underlying_price", 0, "must be greater than zero"),
        ("strike_price", -1, "must be greater than zero"),
        ("time_to_maturity", -0.1, "must be greater than zero"),
        ("volatility", -0.5, "must be greater than zero"),
        ("risk_free_rate", -0.01, "must be non-negative"),
        ("option_type", "invalid", "option_type must be 'call' or 'put'"),
        ("underlying_price", "abc", "must be a number"),
    ]
    
    for field, value, expected_msg in invalid_cases:
        data = {
            "underlying_price": 100.0,
            "strike_price": 100.0,
            "time_to_maturity": 1.0,
            "volatility": 0.2,
            "risk_free_rate": 0.05,
            "option_type": "call",
        }
        data[field] = value
        with pytest.raises(ValidationError) as excinfo:
            validate_option_parameters(data)
        assert expected_msg in str(excinfo.value.details["errors"])

@pytest.mark.unit
def test_option_parameter_multi_error_collection():
    data = {
        "underlying_price": -100,
        "volatility": -0.2,
        "option_type": "binary"
    }
    with pytest.raises(ValidationError) as excinfo:
        validate_option_parameters(data)
    errors = excinfo.value.details["errors"]
    assert len(errors) > 1
    assert any("underlying_price" in e for e in errors)
    assert any("volatility" in e for e in errors)
    assert any("option_type" in e for e in errors)

@pytest.mark.unit
def test_market_data_validation():
    # Success
    validate_market_data({"bid": 10.0, "ask": 10.5, "volume": 100})
    
    # Bid > Ask
    with pytest.raises(ValidationError) as excinfo:
        validate_market_data({"bid": 11.0, "ask": 10.5})
    assert "Bid cannot be greater than ask" in str(excinfo.value.details["errors"])
    
    # Negative volume
    with pytest.raises(ValidationError) as excinfo:
        validate_market_data({"volume": -10})
    assert "Volume cannot be negative" in str(excinfo.value.details["errors"])
    
    # None values (should be ignored or handled)
    validate_market_data({"bid": None, "ask": 10.0})
    validate_market_data({"volume": None})
