"""Statistical analysis helpers for option pricing methods."""

from __future__ import annotations

import numpy as np


def calculate_mape(actual: float, predicted: float) -> float:
    """Calculate Mean Absolute Percentage Error."""
    if actual == 0:
        return 0.0
    return abs((actual - predicted) / actual) * 100.0


def calculate_summary_stats(values: list[float]) -> dict[str, float]:
    """Calculate basic summary statistics for a list of values."""
    if not values:
        return {}

    arr = np.array(values)
    return {
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "median": float(np.median(arr)),
    }


def calculate_confidence_interval(
    values: list[float], confidence: float = 0.95
) -> tuple[float, float]:
    """Calculate confidence interval using normal approximation."""
    if not values:
        return 0.0, 0.0

    arr = np.array(values)
    mean = np.mean(arr)
    std = np.std(arr, ddof=1)
    n = len(arr)

    from scipy import stats

    h = std * stats.t.ppf((1 + confidence) / 2.0, n - 1) / np.sqrt(n)
    return float(mean - h), float(mean + h)
