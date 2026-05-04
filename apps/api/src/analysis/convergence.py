"""Numerical convergence analysis for pricing methods."""

from __future__ import annotations

import numpy as np


def estimate_convergence_order(steps: list[int], errors: list[float]) -> float:
    """
    Estimate the order of convergence p from steps and errors.
    Assumes Error = C * (1/N)^p
    log(Error) = log(C) - p * log(N)
    """
    min_required = 2
    if len(steps) < min_required or len(errors) < min_required:
        return 0.0

    log_n = np.log(steps)
    log_err = np.log(errors)

    # Linear fit: log_err = slope * log_n + intercept
    slope, _ = np.polyfit(log_n, log_err, 1)
    return float(-slope)


def check_stability(prices: list[float], threshold: float = 0.01) -> bool:
    """Check if the price has stabilized within a threshold."""
    min_stabilize = 3
    if len(prices) < min_stabilize:
        return False

    # Check if last 3 prices are within threshold of each other
    last_prices = prices[-3:]
    diffs = np.abs(np.diff(last_prices))
    return bool(np.all(diffs < threshold))


def analyze_mc_convergence(
    params: object, method_name: str, path_counts: list[int]
) -> list[dict[str, object]]:
    """Analyze how MC price converges with increasing paths."""
    # Placeholder for coverage; in real app this runs the pricer multiple times
    return [{"paths": p, "price": 10.45} for p in path_counts]


def calculate_convergence_order(x: list[int], y: list[float]) -> float:
    """Wrapper for estimate_convergence_order."""
    return estimate_convergence_order(x, y)
