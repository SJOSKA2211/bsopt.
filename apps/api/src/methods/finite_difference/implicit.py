"""Implicit Finite Difference Method (BTCS)."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.methods.base import BasePricer, OptionParams, PricingResult
from src.metrics import PRICE_COMPUTATIONS_TOTAL, PRICE_DURATION_SECONDS


class ImplicitFDM(BasePricer):
    """Implicit Finite Difference Method (Backward Time, Central Space)."""

    def __init__(self, s_max_mult: float = 3.0, m: int = 100, n: int = 100) -> None:
        self.s_max_mult = s_max_mult
        self.m = m
        self.n = n

    @staticmethod
    def _thomas_algorithm(a: np.ndarray, b: np.ndarray, c: np.ndarray, d: np.ndarray) -> np.ndarray:
        """
        Solve tridiagonal system Ax = d in O(n).
        A has 'a' on lower, 'b' on diagonal, 'c' on upper.
        len(b) = n, len(a) = n-1, len(c) = n-1.
        """
        n = len(d)
        cp = np.zeros(n - 1)
        dp = np.zeros(n)
        x = np.zeros(n)

        cp[0] = c[0] / b[0]
        dp[0] = d[0] / b[0]

        for i in range(1, n):
            denom = b[i] - a[i - 1] * cp[i - 1]
            if i < n - 1:
                cp[i] = c[i] / denom
            dp[i] = (d[i] - a[i - 1] * dp[i - 1]) / denom

        x[n - 1] = dp[n - 1]
        for i in range(n - 2, -1, -1):
            x[i] = dp[i] - cp[i] * x[i + 1]

        return x

    def price(self, params: OptionParams, **kwargs: Any) -> PricingResult:
        start = self._start_timer()

        m = kwargs.get("m", self.m)
        n = kwargs.get("n", kwargs.get("steps_time", self.n))

        S0 = params.underlying_price
        K = params.strike_price
        T = params.time_to_maturity
        sigma = params.volatility
        r = params.risk_free_rate

        S_max = K * self.s_max_mult
        dt = T / n

        S_values = np.linspace(0, S_max, m + 1)
        grid = np.zeros(m + 1)

        grid = (
            np.maximum(S_values - K, 0)
            if params.option_type == "call"
            else np.maximum(K - S_values, 0)
        )

        j = np.arange(1, m)
        alpha = 0.5 * dt * (sigma**2 * j**2 - r * j)
        beta = dt * (sigma**2 * j**2 + r)
        gamma = 0.5 * dt * (sigma**2 * j**2 + r * j)

        # Diagonals for Thomas
        lower = -alpha[1:]
        diag = 1.0 + beta
        upper = -gamma[:-1]

        for i in range(n):
            d = grid[1:m].copy()

            if params.option_type == "call":
                d[-1] += gamma[-1] * (S_max - K * np.exp(-r * (T - (i + 1) * dt)))
            else:
                d[0] += alpha[0] * (K * np.exp(-r * (T - (i + 1) * dt)))

            grid[1:m] = self._thomas_algorithm(lower, diag, upper, d)

            if params.option_type == "call":
                grid[0] = 0
                grid[m] = S_max - K * np.exp(-r * (T - (i + 1) * dt))
            else:
                grid[0] = K * np.exp(-r * (T - (i + 1) * dt))
                grid[m] = 0

        price = np.interp(S0, S_values, grid)
        exec_time = self._stop_timer(start)

        PRICE_COMPUTATIONS_TOTAL.labels(
            method_type="implicit_fdm", option_type=params.option_type, converged="true"
        ).inc()
        PRICE_DURATION_SECONDS.labels(method_type="implicit_fdm").observe(exec_time)

        return PricingResult(
            method_type="implicit_fdm",
            computed_price=float(price),
            exec_seconds=exec_time,
            parameter_set={"m": m, "n": n},
        )
