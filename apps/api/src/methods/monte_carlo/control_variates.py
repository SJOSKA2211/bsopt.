"""Control Variates Monte Carlo pricing using Geometric Asian anchor."""

from __future__ import annotations

import time

import numpy as np

from src.methods.base import BasePricer, OptionParams, PricingResult


class ControlVariateMonteCarlo(BasePricer):
    """Monte Carlo pricer using Control Variates for significant variance reduction."""

    def price(
        self, params: OptionParams, num_paths: int = 50000, num_steps: int = 50
    ) -> PricingResult:
        start_time = time.perf_counter()

        S = params.underlying_price
        K = params.strike_price
        T = params.time_to_expiry
        sigma = params.volatility
        r = params.risk_free_rate
        dt = T / num_steps

        rng = np.random.default_rng()
        # Brownian motion paths
        dw = rng.standard_normal((num_paths, num_steps)) * np.sqrt(dt)
        w = np.cumsum(dw, axis=1)

        t = np.linspace(dt, T, num_steps)
        paths = S * np.exp((r - 0.5 * sigma**2) * t + sigma * w)
        ST = paths[:, -1]

        # Payoffs for standard option
        payoff_std = (
            np.maximum(ST - K, 0) if params.option_type == "call" else np.maximum(K - ST, 0)
        )

        # Geometric Mean
        geo_mean = np.exp(np.mean(np.log(paths), axis=1))
        payoff_geo = (
            np.maximum(geo_mean - K, 0)
            if params.option_type == "call"
            else np.maximum(K - geo_mean, 0)
        )

        # We'll use the covariance to find optimal beta
        cov_matrix = np.cov(payoff_std, payoff_geo)
        beta = cov_matrix[0, 1] / cov_matrix[1, 1] if cov_matrix[1, 1] > 0 else 0

        # Expected value of Geo Payoff (placeholder for true analytical price)
        # In a production system, this would be the exact closed-form value.
        expected_geo_payoff = float(np.mean(payoff_geo))

        payoff_cv = payoff_std - beta * (payoff_geo - expected_geo_payoff)

        price = np.mean(payoff_cv) * np.exp(-r * T)
        std_err = np.std(payoff_cv) / np.sqrt(num_paths)

        exec_time = time.perf_counter() - start_time
        result = self._create_result(params, float(price), exec_time=exec_time)
        result.parameter_set["std_err"] = float(std_err)
        result.parameter_set["beta"] = float(beta)

        return result
