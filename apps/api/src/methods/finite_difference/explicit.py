"""Explicit Finite Difference Method (FTCS)."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.exceptions import CFLViolationError
from src.methods.base import BasePricer, OptionParams, PricingResult
from src.metrics import PRICE_COMPUTATIONS_TOTAL, PRICE_DURATION_SECONDS


class ExplicitFDM(BasePricer):
    """Explicit Finite Difference Method (Forward Time, Central Space)."""

    def __init__(self, s_max_mult: float = 3.0, m: int = 100, n: int = 1000) -> None:
        """
        Args:
            s_max_mult: Multiplier for S_max relative to strike.
            m: Number of spatial steps (stock price).
            n: Number of time steps.
        """
        self.s_max_mult = s_max_mult
        self.m = m
        self.n = n

    def price(self, params: OptionParams, **kwargs: Any) -> PricingResult:
        start = self._start_timer()

        # Handle overrides from router
        m = kwargs.get("m", self.m)
        n = kwargs.get("n", kwargs.get("steps_time", self.n))

        S0 = params.underlying_price
        K = params.strike_price
        T = params.time_to_maturity
        sigma = params.volatility
        r = params.risk_free_rate

        S_max = K * self.s_max_mult
        dS = S_max / m
        dt = T / n

        cfl_actual = (dt * (sigma**2 * S_max**2)) / (dS**2)

        if cfl_actual > 0.5:
            suggested_dt = 0.5 * (dS**2) / (sigma**2 * S_max**2)
            raise CFLViolationError(cfl_actual=cfl_actual, suggested_dt=suggested_dt)

        # Grid setup
        S_values = np.linspace(0, S_max, m + 1)
        grid = np.zeros(m + 1)

        # Terminal condition
        if params.option_type == "call":
            grid = np.maximum(S_values - K, 0)
        else:
            grid = np.maximum(K - S_values, 0)

        # Coefficients
        j = np.arange(1, m)
        alpha = 0.5 * dt * (sigma**2 * j**2 - r * j)
        beta = 1.0 - dt * (sigma**2 * j**2 + r)
        gamma = 0.5 * dt * (sigma**2 * j**2 + r * j)

        # Time stepping
        for i in range(n):
            new_grid = np.zeros(m + 1)

            # Boundary conditions
            if params.option_type == "call":
                new_grid[0] = 0
                new_grid[m] = S_max - K * np.exp(-r * (T - i * dt))
            else:
                new_grid[0] = K * np.exp(-r * (T - i * dt))
                new_grid[m] = 0

            # Central space update
            new_grid[1:m] = alpha * grid[0 : m - 1] + beta * grid[1:m] + gamma * grid[2 : m + 1]
            grid = new_grid

        # Interpolate result at S0
        price = np.interp(S0, S_values, grid)

        exec_time = self._stop_timer(start)
        PRICE_COMPUTATIONS_TOTAL.labels(
            method_type="explicit_fdm", option_type=params.option_type, converged="true"
        ).inc()
        PRICE_DURATION_SECONDS.labels(method_type="explicit_fdm").observe(exec_time)

        return PricingResult(
            method_type="explicit_fdm",
            computed_price=float(price),
            exec_seconds=exec_time,
            parameter_set={"m": m, "n": n, "cfl": cfl_actual},
        )
