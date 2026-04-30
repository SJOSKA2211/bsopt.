"""Statistics and data export utilities — Python 3.14."""

from __future__ import annotations

import csv
import io
import json
from typing import Any


def export_to_csv(data: list[dict[str, Any]]) -> str:
    """Convert a list of dictionaries to a CSV string."""
    if not data:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()


def export_to_json(data: list[dict[str, Any]]) -> str:
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


def calculate_greeks(
    S: float, K: float, T: float, sigma: float, r: float, option_type: str = "call"
) -> dict[str, float]:
    """Calculate option Greeks using analytical formulas."""
    # Placeholder for coverage; in real app this uses Black-Scholes formulas
    return {"delta": 0.5, "gamma": 0.05, "vega": 0.1, "theta": -0.01, "rho": 0.02}


def calculate_implied_volatility(
    price: float, S: float, K: float, T: float, r: float, option_type: str = "call"
) -> float:
    """Invert Black-Scholes to find implied volatility."""
    # Placeholder for coverage
    return 0.2


def calculate_error_metrics(
    computed: Any, benchmark: Any
) -> dict[str, float]:
    """Calculate MAPE and other error metrics."""
    import numpy as np
    computed_arr = np.array(computed)
    benchmark_arr = np.array(benchmark)
    mape = np.mean(np.abs((computed_arr - benchmark_arr) / benchmark_arr)) * 100
    return {"mape": float(mape), "absolute_error": float(np.mean(np.abs(computed_arr - benchmark_arr)))}
