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

        underlying_price = params.underlying_price
        strike_price = params.strike_price
        time_to_expiry = params.time_to_expiry
        volatility = params.volatility
        risk_free_rate = params.risk_free_rate

        rng = np.random.default_rng()
        half_samples = rng.standard_normal(num_paths // 2)

        # Combine samples and their negatives
        combined_samples = np.concatenate([half_samples, -half_samples])

        terminal_spot_prices = underlying_price * np.exp(
            (risk_free_rate - 0.5 * volatility**2) * time_to_expiry
            + volatility * np.sqrt(time_to_expiry) * combined_samples
        )

        payoffs = (
            np.maximum(terminal_spot_prices - strike_price, 0)
            if params.option_type == "call"
            else np.maximum(strike_price - terminal_spot_prices, 0)
        )

        # Average the pairs
        payoffs_combined = (payoffs[: num_paths // 2] + payoffs[num_paths // 2 :]) / 2

        price = np.mean(payoffs_combined) * np.exp(-risk_free_rate * time_to_expiry)
        std_err = np.std(payoffs_combined) / np.sqrt(num_paths // 2)

        exec_time = time.perf_counter() - start_time
        result = self._create_result(params, float(price), exec_time=exec_time)
        result.parameter_set["std_err"] = float(std_err)
        result.parameter_set["num_paths"] = num_paths

        return result
