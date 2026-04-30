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

        S_max = 2.0 * params.strike_price
        dt = params.time_to_expiry / n_steps

        S_values = np.linspace(0, S_max, m_steps + 1)

        grid = (
            np.maximum(S_values - params.strike_price, 0)
            if params.option_type == "call"
            else np.maximum(params.strike_price - S_values, 0)
        )

        j = np.arange(1, m_steps)

        # Matrix coefficients (Theta = 0.5)
        # Left-hand side coefficients
        alpha_L = 0.25 * dt * (params.risk_free_rate * j - (params.volatility**2) * (j**2))
        beta_L = 1.0 + 0.5 * dt * ((params.volatility**2) * (j**2) + params.risk_free_rate)
        gamma_L = 0.25 * dt * (-params.risk_free_rate * j - (params.volatility**2) * (j**2))

        # Right-hand side coefficients
        alpha_R = -alpha_L
        beta_R = 1.0 - 0.5 * dt * ((params.volatility**2) * (j**2) + params.risk_free_rate)
        gamma_R = -gamma_L

        for _ in range(n_steps):
            # Boundary conditions at each step
            if params.option_type == "call":
                grid[0] = 0
                grid[m_steps] = S_max - params.strike_price * np.exp(-params.risk_free_rate * _)
            else:
                grid[0] = params.strike_price * np.exp(-params.risk_free_rate * _)
                grid[m_steps] = 0

            # Right-hand side calculation
            b = (
                alpha_R * grid[0 : m_steps - 1]
                + beta_R * grid[1:m_steps]
                + gamma_R * grid[2 : m_steps + 1]
            )

            # Solve tridiagonal system using ImplicitFDM helper
            grid[1:m_steps] = ImplicitFDM._thomas_algorithm(alpha_L, beta_L, gamma_L, b)

        price = np.interp(params.underlying_price, S_values, grid)

        exec_time = time.perf_counter() - start_time
        return self._create_result(params, float(price), exec_time=exec_time)
