"""Crank-Nicolson Finite Difference Method for option pricing."""

from __future__ import annotations

import time

import numpy as np

from src.methods.base import BasePricer, OptionParams, PricingResult
from src.methods.finite_difference.implicit import ImplicitFDM


class CrankNicolsonFDM(BasePricer):
    """Crank-Nicolson FDM solver (theta=0.5). Reuses Thomas algorithm from ImplicitFDM."""

    def price(self, params: OptionParams, m_steps: int = 100, n_steps: int = 1000) -> PricingResult:
        start_time = time.perf_counter()

        underlying_max = 2.0 * params.strike_price
        delta_time = params.time_to_expiry / n_steps

        spot_values = np.linspace(0, underlying_max, m_steps + 1)

        grid = (
            np.maximum(spot_values - params.strike_price, 0)
            if params.option_type == "call"
            else np.maximum(params.strike_price - spot_values, 0)
        )

        spot_indices = np.arange(1, m_steps)

        # Matrix coefficients (Theta = 0.5)
        # Left-hand side coefficients
        alpha_left = (
            0.25
            * delta_time
            * (params.risk_free_rate * spot_indices - (params.volatility**2) * (spot_indices**2))
        )
        beta_left = 1.0 + 0.5 * delta_time * (
            (params.volatility**2) * (spot_indices**2) + params.risk_free_rate
        )
        gamma_left = (
            0.25
            * delta_time
            * (-params.risk_free_rate * spot_indices - (params.volatility**2) * (spot_indices**2))
        )

        # Right-hand side coefficients
        alpha_right = -alpha_left
        beta_right = 1.0 - 0.5 * delta_time * (
            (params.volatility**2) * (spot_indices**2) + params.risk_free_rate
        )
        gamma_right = -gamma_left

        for step_index in range(n_steps):
            # Boundary conditions at each step
            if params.option_type == "call":
                grid[0] = 0
                grid[m_steps] = underlying_max - params.strike_price * np.exp(
                    -params.risk_free_rate * (step_index * delta_time)
                )
            else:
                grid[0] = params.strike_price * np.exp(
                    -params.risk_free_rate * (step_index * delta_time)
                )
                grid[m_steps] = 0

            # Right-hand side calculation
            rhs_vector = (
                alpha_right * grid[0 : m_steps - 1]
                + beta_right * grid[1:m_steps]
                + gamma_right * grid[2 : m_steps + 1]
            )

            # Solve tridiagonal system using ImplicitFDM helper
            grid[1:m_steps] = ImplicitFDM._thomas_algorithm(
                alpha_left, beta_left, gamma_left, rhs_vector
            )

            # American early exercise
            if params.exercise_type == "american":
                intrinsic = (
                    np.maximum(spot_values - params.strike_price, 0)
                    if params.option_type == "call"
                    else np.maximum(params.strike_price - spot_values, 0)
                )
                grid = np.maximum(grid, intrinsic)

        price = np.interp(params.underlying_price, spot_values, grid)

        exec_time = time.perf_counter() - start_time
        return self._create_result(params, float(price), exec_time=exec_time)
