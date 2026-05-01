"""Implicit Finite Difference Method (BTCS) for option pricing."""

from __future__ import annotations

import time

import numpy as np

from src.methods.base import BasePricer, OptionParams, PricingResult


class ImplicitFDM(BasePricer):
    """Implicit FDM solver using the Thomas algorithm for tridiagonal matrices."""

    def price(self, params: OptionParams, m_steps: int = 100, n_steps: int = 1000) -> PricingResult:
        start_time = time.perf_counter()

        underlying_max = 2.0 * params.strike_price
        delta_time = params.time_to_expiry / n_steps

        # Grid setup
        spot_values = np.linspace(0, underlying_max, m_steps + 1)

        # Initial condition (payoff at expiry)
        grid = (
            np.maximum(spot_values - params.strike_price, 0)
            if params.option_type == "call"
            else np.maximum(params.strike_price - spot_values, 0)
        )

        # Coefficients for tridiagonal matrix
        spot_indices = np.arange(1, m_steps)
        alpha = (
            0.5
            * delta_time
            * (params.risk_free_rate * spot_indices - (params.volatility**2) * (spot_indices**2))
        )
        beta = 1.0 + delta_time * (
            (params.volatility**2) * (spot_indices**2) + params.risk_free_rate
        )
        gamma = (
            0.5
            * delta_time
            * (-params.risk_free_rate * spot_indices - (params.volatility**2) * (spot_indices**2))
        )

        # Time-stepping
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

            # Right-hand side
            rhs_vector = grid[1:m_steps].copy()
            rhs_vector[0] -= alpha[0] * grid[0]
            rhs_vector[-1] -= gamma[-1] * grid[m_steps]

            # Solve tridiagonal system
            grid[1:m_steps] = self._thomas_algorithm(alpha, beta, gamma, rhs_vector)

            # American early exercise
            if params.exercise_type == "american":
                intrinsic = (
                    np.maximum(spot_values - params.strike_price, 0)
                    if params.option_type == "call"
                    else np.maximum(params.strike_price - spot_values, 0)
                )
                grid = np.maximum(grid, intrinsic)

        # Linear interpolation to find price at underlying_price
        price = np.interp(params.underlying_price, spot_values, grid)

        exec_time = time.perf_counter() - start_time
        return self._create_result(params, float(price), exec_time=exec_time)

    @staticmethod
    def _thomas_algorithm(
        lower_diag: np.ndarray,
        main_diag: np.ndarray,
        upper_diag: np.ndarray,
        rhs_vector: np.ndarray,
    ) -> np.ndarray:
        """
        Thomas algorithm for tridiagonal matrix inversion O(n).
        """
        system_size = len(rhs_vector)
        c_prime = np.zeros(system_size)
        d_prime = np.zeros(system_size)

        c_prime[0] = upper_diag[0] / main_diag[0]
        d_prime[0] = rhs_vector[0] / main_diag[0]

        for i in range(1, system_size - 1):
            denom = main_diag[i] - lower_diag[i] * c_prime[i - 1]
            c_prime[i] = upper_diag[i] / denom
            d_prime[i] = (rhs_vector[i] - lower_diag[i] * d_prime[i - 1]) / denom

        d_prime[system_size - 1] = (
            rhs_vector[system_size - 1] - lower_diag[system_size - 1] * d_prime[system_size - 2]
        ) / (main_diag[system_size - 1] - lower_diag[system_size - 1] * c_prime[system_size - 2])

        solution_vector = np.zeros(system_size)
        solution_vector[system_size - 1] = d_prime[system_size - 1]
        for i in range(system_size - 2, -1, -1):
            solution_vector[i] = d_prime[i] - c_prime[i] * solution_vector[i + 1]

        return solution_vector
