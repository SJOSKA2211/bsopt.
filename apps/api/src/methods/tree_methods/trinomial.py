"""Trinomial Tree pricing method (Boyle 1988)."""

from __future__ import annotations

import numpy as np

from src.methods.base import BasePricer, OptionParams, PricingResult


class TrinomialTree(BasePricer):
    """Trinomial Tree with smoother convergence than binomial."""

    def price(self, params: OptionParams, num_steps: int = 500) -> PricingResult:
        start_time = self._start_timer()

        S = params.underlying_price
        K = params.strike_price
        T = params.time_to_expiry
        sigma = params.volatility
        r = params.risk_free_rate
        dt = T / num_steps

        dx = sigma * np.sqrt(3 * dt)
        u = np.exp(dx)

        # Probabilities (Boyle / Hull-White)
        nu = r - 0.5 * sigma**2
        common = (sigma**2 * dt + nu**2 * dt**2) / (dx**2)
        drift = nu * dt / dx

        pu = 0.5 * (common + drift)
        pd = 0.5 * (common - drift)
        pm = 1.0 - pu - pd

        # Final nodes: 2*num_steps + 1
        j = np.arange(2 * num_steps + 1) - num_steps
        S_values = S * (u**j)

        if params.option_type == "call":
            grid = np.maximum(S_values - K, 0)
        else:
            grid = np.maximum(K - S_values, 0)

        df = np.exp(-r * dt)

        for _ in range(num_steps):
            grid = df * (pu * grid[2:] + pm * grid[1:-1] + pd * grid[:-2])

        price = grid[0]

        exec_time = self._stop_timer(start_time)
        result = self._create_result(params, float(price), exec_time=exec_time)
        result.parameter_set["num_steps"] = num_steps

        return result
