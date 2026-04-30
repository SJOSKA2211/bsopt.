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
        m = int(np.ceil(np.log2(num_paths)))
        num_paths = 2**m

        S = params.underlying_price
        K = params.strike_price
        T = params.time_to_expiry
        sigma = params.volatility
        r = params.risk_free_rate

        sampler = Sobol(d=1, scramble=True)
        sample = sampler.random_base2(m=m)

        # Transform uniform to normal
        z = norm.ppf(sample).flatten()

        ST = S * np.exp((r - 0.5 * sigma**2) * T + sigma * np.sqrt(T) * z)

        payoffs = np.maximum(ST - K, 0) if params.option_type == "call" else np.maximum(K - ST, 0)

        price = np.mean(payoffs) * np.exp(-r * T)

        exec_time = time.perf_counter() - start_time
        return self._create_result(params, float(price), exec_time=exec_time)
