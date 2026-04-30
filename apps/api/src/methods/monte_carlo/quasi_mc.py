"""Quasi-Monte Carlo pricing using Sobol sequences."""

from __future__ import annotations

import time

import numpy as np
from scipy.stats import norm
from scipy.stats.qmc import Sobol

from src.methods.base import BasePricer, OptionParams, PricingResult


class QuasiMonteCarlo(BasePricer):
    """Monte Carlo pricer using low-discrepancy Sobol sequences."""

    def price(self, params: OptionParams, num_paths: int = 65536) -> PricingResult:
        """num_paths should be a power of 2 for Sobol sequences."""
        start_time = time.perf_counter()

        # Ensure num_paths is a power of 2
        power_of_two = int(np.ceil(np.log2(num_paths)))
        num_paths = 2**power_of_two

        underlying_price = params.underlying_price
        strike_price = params.strike_price
        time_to_expiry = params.time_to_expiry
        volatility = params.volatility
        risk_free_rate = params.risk_free_rate

        sampler = Sobol(d=1, scramble=True)
        uniform_samples = sampler.random_base2(m=power_of_two)

        # Transform uniform to normal (clipped to avoid inf)
        standard_normal_samples = norm.ppf(np.clip(uniform_samples, 1e-10, 1 - 1e-10)).flatten()

        terminal_spot_prices = underlying_price * np.exp(
            (risk_free_rate - 0.5 * volatility**2) * time_to_expiry
            + volatility * np.sqrt(time_to_expiry) * standard_normal_samples
        )

        payoffs = (
            np.maximum(terminal_spot_prices - strike_price, 0)
            if params.option_type == "call"
            else np.maximum(strike_price - terminal_spot_prices, 0)
        )

        price = np.mean(payoffs) * np.exp(-risk_free_rate * time_to_expiry)

        exec_time = time.perf_counter() - start_time
        result = self._create_result(params, float(price), exec_time=exec_time)
        result.parameter_set["num_paths"] = num_paths
        return result
