"""Control Variates Monte Carlo pricing using Geometric Asian anchor."""

from __future__ import annotations

import time

import numpy as np
from scipy.stats import norm

from src.methods.base import BasePricer, OptionParams, PricingResult


class ControlVariateMonteCarlo(BasePricer):
    """Monte Carlo pricer using Control Variates for significant variance reduction."""

    def price(
        self, params: OptionParams, num_paths: int = 50000, num_steps: int = 50
    ) -> PricingResult:
        start_time = time.perf_counter()

        underlying_price = params.underlying_price
        strike_price = params.strike_price
        time_to_expiry = params.time_to_expiry
        volatility = params.volatility
        risk_free_rate = params.risk_free_rate
        delta_time = time_to_expiry / num_steps

        rng = np.random.default_rng()
        # Brownian motion increments
        brownian_increments = rng.standard_normal((num_paths, num_steps)) * np.sqrt(delta_time)
        brownian_motion = np.cumsum(brownian_increments, axis=1)

        time_grid = np.linspace(delta_time, time_to_expiry, num_steps)
        # S_t = S_0 * exp((r - 0.5*sigma^2)*t + sigma*W_t)
        paths = underlying_price * np.exp(
            (risk_free_rate - 0.5 * volatility**2) * time_grid + volatility * brownian_motion
        )
        terminal_prices = paths[:, -1]

        # Standard option payoff (undiscounted)
        payoff_standard = (
            np.maximum(terminal_prices - strike_price, 0)
            if params.option_type == "call"
            else np.maximum(strike_price - terminal_prices, 0)
        )

        # Control Variate: Geometric Asian Payoff (undiscounted)
        # Geometric mean: exp(1/T * sum(log(S_t)))
        geometric_means = np.exp(np.mean(np.log(paths), axis=1))
        payoff_asian = (
            np.maximum(geometric_means - strike_price, 0)
            if params.option_type == "call"
            else np.maximum(strike_price - geometric_means, 0)
        )

        # Discount everything to present value
        discount = np.exp(-risk_free_rate * time_to_expiry)
        pv_standard = payoff_standard * discount
        pv_asian = payoff_asian * discount

        # Discrete Geometric Asian Anchor (match the simulation steps)
        # E[ln(G)] = ln(S) + (r - 0.5 * sigma^2) * T * (n+1)/(2n)
        # Var(ln(G)) = (sigma^2 * T / n^2) * sum_{i=1}^n sum_{j=1}^n min(i, j) / n? No.
        # Var(ln(G)) = (sigma^2 * delta_t / n^2) * sum_{i=1}^n (2*n - 2*i + 1) * i
        # A simpler way: use the sum_{i=1}^n sum_{j=1}^n min(i, j) = n(n+1)(2n+1)/6
        n = num_steps
        mu_discrete = np.log(underlying_price) + (
            risk_free_rate - 0.5 * volatility**2
        ) * time_to_expiry * (n + 1) / (2 * n)
        var_discrete = (volatility**2 * delta_time / (n**2)) * (n * (n + 1) * (2 * n + 1) / 6.0)

        # Discrete expected PV of Geometric Asian
        d1_discrete = (mu_discrete - np.log(strike_price) + var_discrete) / np.sqrt(var_discrete)
        d2_discrete = d1_discrete - np.sqrt(var_discrete)
        expected_pv_asian = (
            np.exp(-risk_free_rate * time_to_expiry)
            * (
                np.exp(mu_discrete + 0.5 * var_discrete) * norm.cdf(d1_discrete)
                - strike_price * norm.cdf(d2_discrete)
            )
            if params.option_type == "call"
            else np.exp(-risk_free_rate * time_to_expiry)
            * (
                strike_price * norm.cdf(-d2_discrete)
                - np.exp(mu_discrete + 0.5 * var_discrete) * norm.cdf(-d1_discrete)
            )
        )

        # Optimal Beta = Cov(Y, X) / Var(X)
        cov_matrix = np.cov(pv_standard, pv_asian, ddof=1)
        beta_coefficient = cov_matrix[0, 1] / cov_matrix[1, 1] if cov_matrix[1, 1] > 0 else 1.0

        # Control Variate formula
        pv_cv = pv_standard - beta_coefficient * (pv_asian - expected_pv_asian)

        price = np.mean(pv_cv)
        std_error = np.std(pv_cv) / np.sqrt(num_paths)

        exec_time = time.perf_counter() - start_time
        result = self._create_result(params, float(price), exec_time=exec_time)
        result.parameter_set["num_paths"] = num_paths
        result.parameter_set["num_steps"] = num_steps
        result.parameter_set["std_err"] = float(std_error)
        result.parameter_set["beta"] = float(beta_coefficient)

        return result
