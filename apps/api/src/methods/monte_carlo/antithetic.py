"""Antithetic Variates Monte Carlo pricing."""

from __future__ import annotations

import time

import numpy as np

from src.methods.base import BasePricer, OptionParams, PricingResult


class AntitheticMonteCarlo(BasePricer):
    """Monte Carlo pricer using antithetic variates for variance reduction."""

    def price(self, params: OptionParams, num_paths: int = 50000) -> PricingResult:
        start_time = time.perf_counter()

        # Ensure num_paths is even for pairs
        if num_paths % 2 != 0:
            num_paths += 1

        S = params.underlying_price
        K = params.strike_price
        T = params.time_to_expiry
        sigma = params.volatility
        r = params.risk_free_rate

        rng = np.random.default_rng()
        z = rng.standard_normal(num_paths // 2)

        # Combine Z and -Z
        z_antithetic = np.concatenate([z, -z])

        ST = S * np.exp((r - 0.5 * sigma**2) * T + sigma * np.sqrt(T) * z_antithetic)

        payoffs = np.maximum(ST - K, 0) if params.option_type == "call" else np.maximum(K - ST, 0)

        # Average the pairs
        payoffs_combined = (payoffs[: num_paths // 2] + payoffs[num_paths // 2 :]) / 2

        price = np.mean(payoffs_combined) * np.exp(-r * T)
        std_err = np.std(payoffs_combined) / np.sqrt(num_paths // 2)

        exec_time = time.perf_counter() - start_time
        result = self._create_result(params, float(price), exec_time=exec_time)
        result.parameter_set["std_err"] = float(std_err)
        result.parameter_set["num_paths"] = num_paths

        return result
