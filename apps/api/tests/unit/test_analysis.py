"""Unit tests for analysis modules — Python 3.14."""
from __future__ import annotations

import numpy as np
import pytest

from src.analysis.convergence import (
    analyze_mc_convergence,
    calculate_convergence_order,
    check_stability,
    estimate_convergence_order,
)
from src.analysis.statistics import (
    calculate_error_metrics,
    calculate_greeks,
    calculate_implied_volatility,
    compute_basic_stats,
    export_to_csv,
    export_to_json,
)


@pytest.mark.unit
def test_export_to_csv():
    data = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    csv_str = export_to_csv(data)
    assert "a,b" in csv_str
    assert "1,2" in csv_str
    assert "3,4" in csv_str

    assert export_to_csv([]) == ""


@pytest.mark.unit
def test_export_to_json():
    data = [{"a": 1, "b": 2}]
    json_str = export_to_json(data)
    assert '"a": 1' in json_str


@pytest.mark.unit
def test_compute_basic_stats():
    prices = [10.0, 11.0, 12.0]
    stats = compute_basic_stats(prices)
    assert stats["mean"] == 11.0
    assert stats["min"] == 10.0
    assert stats["max"] == 12.0
    assert stats["median"] == 11.0
    assert stats["std"] > 0

    assert compute_basic_stats([]) == {}


@pytest.mark.unit
def test_calculate_greeks():
    greeks = calculate_greeks(100, 100, 1, 0.2, 0.05)
    assert "delta" in greeks
    assert "gamma" in greeks


@pytest.mark.unit
def test_calculate_implied_volatility():
    iv = calculate_implied_volatility(10, 100, 100, 1, 0.05)
    assert iv == 0.2


@pytest.mark.unit
def test_calculate_error_metrics():
    computed = [10.1, 20.2]
    benchmark = [10.0, 20.0]
    metrics = calculate_error_metrics(computed, benchmark)
    assert metrics["mape"] == pytest.approx(1.0)
    assert metrics["absolute_error"] == pytest.approx(0.15)


@pytest.mark.unit
def test_estimate_convergence_order():
    steps = [10, 20, 40, 80]
    # Assume Error = 1/N^2 -> log(Err) = -2 * log(N)
    errors = [1.0 / (s**2) for s in steps]
    order = estimate_convergence_order(steps, errors)
    assert order == pytest.approx(2.0)

    assert estimate_convergence_order([10], [0.1]) == 0.0


@pytest.mark.unit
def test_check_stability():
    prices = [10.4501, 10.4502, 10.4503]
    assert check_stability(prices, threshold=0.01) is True

    prices_unstable = [10.0, 11.0, 12.0]
    assert check_stability(prices_unstable, threshold=0.1) is False

    assert check_stability([10.0, 10.1]) is False


@pytest.mark.unit
def test_analyze_mc_convergence():
    res = analyze_mc_convergence(None, "standard_mc", [100, 200])
    assert len(res) == 2
    assert res[0]["paths"] == 100


@pytest.mark.unit
def test_calculate_convergence_order_wrapper():
    steps = np.array([10, 20, 40])
    errors = np.array([0.1, 0.025, 0.00625])  # 1/N^2 approx
    order = calculate_convergence_order(steps, errors)
    assert order == pytest.approx(2.0)
