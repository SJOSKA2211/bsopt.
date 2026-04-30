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

        underlying_max = 2.0 * params.strike_price
        delta_time = params.time_to_expiry / n_steps
        delta_spot = underlying_max / m_steps

        # CFL Condition Check
        cfl_stability_bound = 0.5
        cfl = (params.volatility**2 * params.underlying_price**2 * delta_time) / (delta_spot**2)
        if cfl > cfl_stability_bound:
            suggested_delta_time = (cfl_stability_bound * delta_spot**2) / (
                params.volatility**2 * params.underlying_price**2
            )
            raise CFLViolationError(
                cfl_actual=float(cfl),
                cfl_bound=cfl_stability_bound,
                suggested_dt=float(suggested_delta_time),
            )

        spot_values = np.linspace(0, underlying_max, m_steps + 1)
        grid = (
            np.maximum(spot_values - params.strike_price, 0)
            if params.option_type == "call"
            else np.maximum(params.strike_price - spot_values, 0)
        )

        spot_indices = np.arange(1, m_steps)
        alpha = (
            0.5
            * delta_time
            * ((params.volatility**2) * (spot_indices**2) - params.risk_free_rate * spot_indices)
        )
        beta = 1.0 - delta_time * (
            (params.volatility**2) * (spot_indices**2) + params.risk_free_rate
        )
        gamma = (
            0.5
            * delta_time
            * ((params.volatility**2) * (spot_indices**2) + params.risk_free_rate * spot_indices)
        )

        for step_index in range(n_steps):
            next_grid = grid.copy()
            next_grid[1:m_steps] = (
                alpha * grid[0 : m_steps - 1]
                + beta * grid[1:m_steps]
                + gamma * grid[2 : m_steps + 1]
            )

            # Boundary conditions
            if params.option_type == "call":
                next_grid[0] = 0
                next_grid[m_steps] = underlying_max - params.strike_price * np.exp(
                    -params.risk_free_rate * (step_index * delta_time)
                )
            else:
                next_grid[0] = params.strike_price * np.exp(
                    -params.risk_free_rate * (step_index * delta_time)
                )
                next_grid[m_steps] = 0

            # American early exercise: floor at intrinsic each step
            if params.exercise_type == "american":
                intrinsic = (
                    np.maximum(spot_values - params.strike_price, 0)
                    if params.option_type == "call"
                    else np.maximum(params.strike_price - spot_values, 0)
                )
                next_grid = np.maximum(next_grid, intrinsic)

            grid = next_grid

        price = np.interp(params.underlying_price, spot_values, grid)

        exec_time = time.perf_counter() - start_time
        return self._create_result(params, float(price), exec_time=exec_time)
