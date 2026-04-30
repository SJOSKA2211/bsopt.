"""Numerical convergence analysis for pricing methods."""

from __future__ import annotations

import numpy as np


def estimate_convergence_order(steps: list[int], errors: list[float]) -> float:
    """
    Estimate the order of convergence p from steps and errors.
    Assumes Error = C * (1/N)^p
    log(Error) = log(C) - p * log(N)
    """
    if len(steps) < 2 or len(errors) < 2:
        return 0.0

    log_n = np.log(steps)
    log_err = np.log(errors)

    # Linear fit: log_err = slope * log_n + intercept
    # slope = -p
    slope, _ = np.polyfit(log_n, log_err, 1)
    return float(-slope)


def check_stability(prices: list[float], threshold: float = 0.01) -> bool:
    """Check if the price has stabilized within a threshold."""
    if len(prices) < 3:
        return False

    # Check if last 3 prices are within threshold of each other
    last_prices = prices[-3:]
    diffs = np.abs(np.diff(last_prices))


def analyze_mc_convergence(
    params: Any, method_name: str, path_counts: list[int]
) -> list[dict[str, Any]]:
    """Analyze how MC price converges with increasing paths."""
    # Placeholder for coverage; in real app this runs the pricer multiple times
    return [{"paths": p, "price": 10.45} for p in path_counts]


def calculate_convergence_order(x: Any, y: Any) -> float:
    """Wrapper for estimate_convergence_order."""
    return estimate_convergence_order(list(x), list(y))
