"""Crank-Nicolson Finite Difference Method."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.methods.base import BasePricer, OptionParams, PricingResult
from src.methods.finite_difference.implicit import ImplicitFDM
from src.metrics import PRICE_COMPUTATIONS_TOTAL, PRICE_DURATION_SECONDS


class CrankNicolsonFDM(BasePricer):
    """Crank-Nicolson Finite Difference Method (theta = 0.5)."""

    def __init__(self, s_max_mult: float = 3.0, m: int = 100, n: int = 100) -> None:
        self.s_max_mult = s_max_mult
        self.m = m
        self.n = n

    def price(self, params: OptionParams, **kwargs: Any) -> PricingResult:
        start = self._start_timer()

        S0 = params.underlying_price
        K = params.strike_price
        T = params.time_to_maturity
        sigma = params.volatility
        r = params.risk_free_rate

        S_max = K * self.s_max_mult
        dt = T / self.n

        S_values = np.linspace(0, S_max, self.m + 1)
        grid = np.zeros(self.m + 1)

        if params.option_type == "call":
            grid = np.maximum(S_values - K, 0)
        else:
            grid = np.maximum(K - S_values, 0)

        j = np.arange(1, self.m)
        # CN coefficients (theta=0.5)
        # alpha_j * f_{j-1, i} + (1 + beta_j) * f_{j, i} + gamma_j * f_{j+1, i} = RHS
        # where alpha_j = -dt/4 * (sigma^2*j^2 - r*j)
        #       beta_j = dt/2 * (sigma^2*j^2 + r)
        #       gamma_j = -dt/4 * (sigma^2*j^2 + r*j)

        alpha = 0.25 * dt * (sigma**2 * j**2 - r * j)
        beta = 0.5 * dt * (sigma**2 * j**2 + r)
        gamma = 0.25 * dt * (sigma**2 * j**2 + r * j)

        a = -alpha[1:]
        b = 1.0 + beta
        c = -gamma[:-1]

        for i in range(self.n):
            # RHS: (1 - beta) * f_j + alpha * f_{j-1} + gamma * f_{j+1}
            d = (
                (1.0 - beta) * grid[1 : self.m]
                + alpha * grid[0 : self.m - 1]
                + gamma * grid[2 : self.m + 1]
            )

            # Boundary contributions
            if params.option_type == "call":
                # Average boundary between i and i+1
                b_val = 0.5 * (
                    (S_max - K * np.exp(-r * (T - i * dt)))
                    + (S_max - K * np.exp(-r * (T - (i + 1) * dt)))
                )
                d[-1] += gamma[-1] * b_val
            else:
                b_val = 0.5 * (
                    (K * np.exp(-r * (T - i * dt))) + (K * np.exp(-r * (T - (i + 1) * dt)))
                )
                d[0] += alpha[0] * b_val

            grid[1 : self.m] = ImplicitFDM._thomas_algorithm(a, b, c, d)

            # Update boundaries
            if params.option_type == "call":
                grid[0] = 0
                grid[self.m] = S_max - K * np.exp(-r * (T - (i + 1) * dt))
            else:
                grid[0] = K * np.exp(-r * (T - (i + 1) * dt))
                grid[self.m] = 0

        price = np.interp(S0, S_values, grid)
        exec_time = self._stop_timer(start)

        PRICE_COMPUTATIONS_TOTAL.labels(
            method_type="crank_nicolson", option_type=params.option_type, converged="true"
        ).inc()
        PRICE_DURATION_SECONDS.labels(method_type="crank_nicolson").observe(exec_time)

        return PricingResult(
            method_type="crank_nicolson",
            computed_price=float(price),
            exec_seconds=exec_time,
            parameter_set={"m": self.m, "n": self.n},
        )
