"""Explicit Finite Difference Method (FTCS) for option pricing."""

from __future__ import annotations

import time

import numpy as np

from src.exceptions import CFLViolationError
from src.methods.base import BasePricer, OptionParams, PricingResult


class ExplicitFDM(BasePricer):
    """Explicit FDM solver. Requires CFL condition maintenance (dt/dS^2 < 0.5)."""

    def price(self, params: OptionParams, m_steps: int = 100, n_steps: int = 1000) -> PricingResult:
        start_time = time.perf_counter()

        S_max = 2.0 * params.strike_price
        dt = params.time_to_expiry / n_steps
        dS = S_max / m_steps

        # CFL Condition Check
        cfl = (params.volatility**2 * params.underlying_price**2 * dt) / (dS**2)
        if cfl > 0.5:
            suggested_dt = (0.5 * dS**2) / (params.volatility**2 * params.underlying_price**2)
            raise CFLViolationError(
                cfl_actual=float(cfl), cfl_bound=0.5, suggested_dt=float(suggested_dt)
            )

        S_values = np.linspace(0, S_max, m_steps + 1)
        grid = (
            np.maximum(S_values - params.strike_price, 0)
            if params.option_type == "call"
            else np.maximum(params.strike_price - S_values, 0)
        )

        j = np.arange(1, m_steps)
        alpha = 0.5 * dt * ((params.volatility**2) * (j**2) - params.risk_free_rate * j)
        beta = 1.0 - dt * ((params.volatility**2) * (j**2) + params.risk_free_rate)
        gamma = 0.5 * dt * ((params.volatility**2) * (j**2) + params.risk_free_rate * j)

        for _ in range(n_steps):
            next_grid = grid.copy()
            next_grid[1:m_steps] = (
                alpha * grid[0 : m_steps - 1]
                + beta * grid[1:m_steps]
                + gamma * grid[2 : m_steps + 1]
            )

            # Boundary conditions
            if params.option_type == "call":
                next_grid[0] = 0
                next_grid[m_steps] = S_max - params.strike_price * np.exp(
                    -params.risk_free_rate * _
                )
            else:
                next_grid[0] = params.strike_price * np.exp(-params.risk_free_rate * _)
                next_grid[m_steps] = 0

            grid = next_grid

        price = np.interp(params.underlying_price, S_values, grid)

        exec_time = time.perf_counter() - start_time
        return self._create_result(params, float(price), exec_time=exec_time)
