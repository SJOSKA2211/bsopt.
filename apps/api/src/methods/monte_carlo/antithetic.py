"""Monte Carlo with Antithetic Variates."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from src.methods.base import BasePricer, OptionParams, PricingResult
from src.metrics import PRICE_COMPUTATIONS_TOTAL, PRICE_DURATION_SECONDS


class AntitheticMonteCarlo(BasePricer):
    """Monte Carlo with Antithetic Variates for variance reduction."""

    def __init__(self, num_paths: int = 100_000, seed: int | None = 42) -> None:
        # Ensure even number of paths for pairs
        self.num_paths = (num_paths // 2) * 2
        self.seed = seed

    def price(self, params: OptionParams, **kwargs: Any) -> PricingResult:
        start = self._start_timer()

        S0 = params.underlying_price
        K = params.strike_price
        T = params.time_to_maturity
        sigma = params.volatility
        r = params.risk_free_rate

        if self.seed is not None:
            np.random.seed(self.seed)

        num_pairs = self.num_paths // 2
        z = np.random.standard_normal(num_pairs)

        # S(T) with Z and -Z
        drift = (r - 0.5 * sigma**2) * T
        diffusion = sigma * math.sqrt(T)

        ST1 = S0 * np.exp(drift + diffusion * z)
        ST2 = S0 * np.exp(drift + diffusion * (-z))

        is_call = {"call": 1.0, "put": 0.0}[params.option_type]
        payoffs1 = is_call * np.maximum(ST1 - K, 0) + (1.0 - is_call) * np.maximum(K - ST1, 0)
        payoffs2 = is_call * np.maximum(ST2 - K, 0) + (1.0 - is_call) * np.maximum(K - ST2, 0)

        # Average payoffs per pair first
        pair_payoffs = 0.5 * (payoffs1 + payoffs2)
        discounted_payoffs = math.exp(-r * T) * pair_payoffs

        price = np.mean(discounted_payoffs)
        std_err = np.std(discounted_payoffs) / math.sqrt(num_pairs)

        exec_time = self._stop_timer(start)
        PRICE_COMPUTATIONS_TOTAL.labels(
            method_type="antithetic_mc", option_type=params.option_type, converged="true"
        ).inc()
        PRICE_DURATION_SECONDS.labels(method_type="antithetic_mc").observe(exec_time)

        return PricingResult(
            method_type="antithetic_mc",
            computed_price=float(price),
            exec_seconds=exec_time,
            parameter_set={"num_paths": self.num_paths, "num_pairs": num_pairs, "std_err": std_err},
        )
