"""Standard Monte Carlo pricing."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from src.methods.base import BasePricer, OptionParams, PricingResult
from src.metrics import PRICE_COMPUTATIONS_TOTAL, PRICE_DURATION_SECONDS


class StandardMonteCarlo(BasePricer):
    """Standard Monte Carlo for European options using exact GBM simulation."""

    def __init__(self, num_paths: int = 100_000, seed: int | None = 42) -> None:
        self.num_paths = num_paths
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

        # Exact solution of GBM at time T
        # S(T) = S0 * exp((r - 0.5*sigma^2)*T + sigma*sqrt(T)*Z)
        z = np.random.standard_normal(self.num_paths)
        ST = S0 * np.exp((r - 0.5 * sigma**2) * T + sigma * math.sqrt(T) * z)

        payoffs = np.maximum(ST - K, 0) if params.option_type == "call" else np.maximum(K - ST, 0)

        discounted_payoffs = math.exp(-r * T) * payoffs
        price = np.mean(discounted_payoffs)
        std_err = np.std(discounted_payoffs) / math.sqrt(self.num_paths)

        exec_time = self._stop_timer(start)
        PRICE_COMPUTATIONS_TOTAL.labels(
            method_type="standard_mc", option_type=params.option_type, converged="true"
        ).inc()
        PRICE_DURATION_SECONDS.labels(method_type="standard_mc").observe(exec_time)

        return PricingResult(
            method_type="standard_mc",
            computed_price=float(price),
            exec_seconds=exec_time,
            parameter_set={
                "num_paths": self.num_paths,
                "std_err": std_err,
                "confidence_interval_95": 1.96 * std_err,
            },
        )

    def price_with_confidence_interval(
        self, params: OptionParams, confidence: float = 0.95
    ) -> tuple[float, float]:
        """Return (price, ci_width)."""
        res = self.price(params)
        # For simplicity, we just return the width from the parameter_set
        return res.computed_price, res.parameter_set["confidence_interval_95"]
