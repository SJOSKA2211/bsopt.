"""Statistics and data export utilities — Python 3.14."""

from __future__ import annotations

import csv
import io
import json
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from src.methods.base import OptionParams


def export_to_csv(data: list[dict[str, object]]) -> str:
    """Convert a list of dictionaries to a CSV string."""
    if not data:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()


def export_to_json(data: list[dict[str, object]]) -> str:
    """Convert a list of dictionaries to a formatted JSON string."""
    return json.dumps(data, indent=2, default=str)


def compute_basic_stats(prices: list[float]) -> dict[str, float]:
    """Compute basic descriptive statistics for a list of prices."""
    import numpy as np

    if not prices:
        return {}

    arr = np.array(prices)
    return {
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "median": float(np.median(arr)),
    }


def calculate_greeks(params: OptionParams) -> dict[str, float]:
    """Calculate option Greeks using analytical formulas."""
    from src.methods.analytical import BlackScholesAnalytical

    return BlackScholesAnalytical.greeks(params)


def calculate_implied_volatility(price: float, params: OptionParams) -> float:
    """Invert Black-Scholes to find implied volatility."""
    from src.methods.analytical import BlackScholesAnalytical

    return BlackScholesAnalytical.implied_volatility(price, params)


def calculate_error_metrics(
    computed: list[float] | np.ndarray[Any, Any], benchmark: list[float] | np.ndarray[Any, Any]
) -> dict[str, float]:
    """Calculate MAPE and other error metrics."""
    computed_arr = np.array(computed)
    benchmark_arr = np.array(benchmark)
    mape = np.mean(np.abs((computed_arr - benchmark_arr) / benchmark_arr)) * 100
    return {
        "mape": float(mape),
        "absolute_error": float(np.mean(np.abs(computed_arr - benchmark_arr))),
    }
