"""Quasi-Monte Carlo using Sobol sequences."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.stats import norm
from scipy.stats.qmc import Sobol

from src.methods.base import BasePricer, OptionParams, PricingResult
from src.metrics import PRICE_COMPUTATIONS_TOTAL, PRICE_DURATION_SECONDS


class QuasiMonteCarlo(BasePricer):
    """Quasi-Monte Carlo for European options using Sobol sequences."""

    def __init__(self, num_paths: int = 65536, seed: int | None = 42) -> None:
        """
        Args:
            num_paths: Number of paths (should be power of 2 for Sobol).
            seed: Seed for scrambling.
        """
        # Enforce power of 2
        p = math.log2(num_paths)
        if not p.is_integer():
            raise ValueError(f"num_paths must be a power of 2 for Sobol, got {num_paths}")
        self.num_paths = int(num_paths)
        self.seed = seed

    def price(self, params: OptionParams, **kwargs: Any) -> PricingResult:
        start = self._start_timer()

        S0 = params.underlying_price
        K = params.strike_price
        T = params.time_to_maturity
        sigma = params.volatility
        r = params.risk_free_rate

        # Sobol sequence in 1D
        engine = Sobol(d=1, scramble=True, seed=self.seed)
        u = engine.random(self.num_paths).flatten()

        # Clip to avoid Inf at boundaries
        u = np.clip(u, 1e-10, 1.0 - 1e-10)
        z = norm.ppf(u)

        # Exact solution of GBM
        ST = S0 * np.exp((r - 0.5 * sigma**2) * T + sigma * math.sqrt(T) * z)

        payoffs = np.maximum(ST - K, 0) if params.option_type == "call" else np.maximum(K - ST, 0)

        discounted_payoffs = math.exp(-r * T) * payoffs
        price = np.mean(discounted_payoffs)

        # QMC standard error is O(1/N) roughly, but harder to estimate from one run.
        # We'll use a placeholder or multi-run if needed, but here we just report N.

        exec_time = self._stop_timer(start)
        PRICE_COMPUTATIONS_TOTAL.labels(
            method_type="quasi_mc", option_type=params.option_type, converged="true"
        ).inc()
        PRICE_DURATION_SECONDS.labels(method_type="quasi_mc").observe(exec_time)

        return PricingResult(
            method_type="quasi_mc",
            computed_price=float(price),
            exec_seconds=exec_time,
            parameter_set={"num_paths": self.num_paths, "sequence": "Sobol", "scrambled": True},
        )
