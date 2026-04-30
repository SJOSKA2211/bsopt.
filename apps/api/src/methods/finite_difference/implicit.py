"""Implicit Finite Difference Method (BTCS) for option pricing."""

from __future__ import annotations

import time

import numpy as np

from src.methods.base import BasePricer, OptionParams, PricingResult


class ImplicitFDM(BasePricer):
    """Implicit FDM solver using the Thomas algorithm for tridiagonal matrices."""

    def price(self, params: OptionParams, m_steps: int = 100, n_steps: int = 1000) -> PricingResult:
        start_time = time.perf_counter()

        S_max = 2.0 * params.strike_price
        dt = params.time_to_expiry / n_steps

        # Grid setup
        S_values = np.linspace(0, S_max, m_steps + 1)

        # Initial condition (payoff at expiry)
        grid = (
            np.maximum(S_values - params.strike_price, 0)
            if params.option_type == "call"
            else np.maximum(params.strike_price - S_values, 0)
        )

        # Coefficients for tridiagonal matrix
        j = np.arange(1, m_steps)
        alpha = 0.5 * dt * (params.risk_free_rate * j - (params.volatility**2) * (j**2))
        beta = 1.0 + dt * ((params.volatility**2) * (j**2) + params.risk_free_rate)
        gamma = 0.5 * dt * (-params.risk_free_rate * j - (params.volatility**2) * (j**2))

        # Time-stepping
        for _ in range(n_steps):
            # Boundary conditions at each step
            if params.option_type == "call":
                grid[0] = 0
                grid[m_steps] = S_max - params.strike_price * np.exp(-params.risk_free_rate * _)
            else:
                grid[0] = params.strike_price * np.exp(-params.risk_free_rate * _)
                grid[m_steps] = 0

            # Right-hand side
            b = grid[1:m_steps].copy()
            b[0] -= alpha[0] * grid[0]
            b[-1] -= gamma[-1] * grid[m_steps]

            # Solve tridiagonal system
            grid[1:m_steps] = self._thomas_algorithm(alpha, beta, gamma, b)

        # Linear interpolation to find price at S
        price = np.interp(params.underlying_price, S_values, grid)

        exec_time = time.perf_counter() - start_time
        return self._create_result(params, float(price), exec_time=exec_time)

    @staticmethod
    def _thomas_algorithm(a: np.ndarray, b: np.ndarray, c: np.ndarray, d: np.ndarray) -> np.ndarray:
        """
        Thomas algorithm for tridiagonal matrix inversion O(n).
        """
        n = len(d)
        c_prime = np.zeros(n)
        d_prime = np.zeros(n)

        c_prime[0] = c[0] / b[0]
        d_prime[0] = d[0] / b[0]

        for i in range(1, n - 1):
            denom = b[i] - a[i] * c_prime[i - 1]
            c_prime[i] = c[i] / denom
            d_prime[i] = (d[i] - a[i] * d_prime[i - 1]) / denom

        d_prime[n - 1] = (d[n - 1] - a[n - 1] * d_prime[n - 2]) / (
            b[n - 1] - a[n - 1] * c_prime[n - 2]
        )

        x = np.zeros(n)
        x[n - 1] = d_prime[n - 1]
        for i in range(n - 2, -1, -1):
            x[i] = d_prime[i] - c_prime[i] * x[i + 1]

        return x
