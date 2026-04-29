"""Cox-Ross-Rubinstein Binomial Tree for European and American options."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from src.methods.base import BasePricer, OptionParams, PricingResult
from src.metrics import PRICE_COMPUTATIONS_TOTAL, PRICE_DURATION_SECONDS


class BinomialCRR(BasePricer):

    def __init__(self, steps: int = 1000, is_american: bool = False) -> None:
        self.steps = steps
        self.is_american = is_american

    def price(self, params: OptionParams, **kwargs: Any) -> PricingResult:
        start = self._start_timer()

        S0 = params.underlying_price
        K = params.strike_price
        T = params.time_to_maturity
        sigma = params.volatility
        r = params.risk_free_rate
        dt = T / self.steps

        # CRR parameters
        u = math.exp(sigma * math.sqrt(dt))
        d = 1.0 / u
        p = (math.exp(r * dt) - d) / (u - d)
        df = math.exp(-r * dt)

        # Initialize terminal payoffs
        # j-th node at time N has price S0 * u^j * d^(N-j)
        j = np.arange(self.steps + 1)
        prices = S0 * (u**j) * (d ** (self.steps - j))

        if params.option_type == "call":
            values = np.maximum(prices - K, 0)
        else:
            values = np.maximum(K - prices, 0)

        # Backward induction
        for i in range(self.steps - 1, -1, -1):
            # Compute expected values at time i
            values = df * (p * values[1 : i + 2] + (1 - p) * values[0 : i + 1])

            # American early exercise check
            if self.is_american:
                j_i = np.arange(i + 1)
                S_i = S0 * (u**j_i) * (d ** (i - j_i))
                if params.option_type == "call":
                    exercise = np.maximum(S_i - K, 0)
                else:
                    exercise = np.maximum(K - S_i, 0)
                values = np.maximum(values, exercise)

        price = values[0]
        exec_time = self._stop_timer(start)

        m_type = "binomial_american" if self.is_american else "binomial_crr"
        PRICE_COMPUTATIONS_TOTAL.labels(
            method_type=m_type, option_type=params.option_type, converged="true"
        ).inc()
        PRICE_DURATION_SECONDS.labels(method_type=m_type).observe(exec_time)

        return PricingResult(
            method_type=m_type,
            computed_price=float(price),
            exec_seconds=exec_time,
            parameter_set={"steps": self.steps, "is_american": self.is_american},
        )
