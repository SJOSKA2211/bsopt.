"""Boyle (1988) Trinomial Tree for smoother convergence."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from src.methods.base import BasePricer, OptionParams, PricingResult
from src.metrics import PRICE_COMPUTATIONS_TOTAL, PRICE_DURATION_SECONDS


class TrinomialTree(BasePricer):

    def __init__(self, steps: int = 500, is_american: bool = False) -> None:
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

        # Trinomial parameters (Boyle 1988)
        u = math.exp(sigma * math.sqrt(2 * dt))

        # Risk-neutral probabilities
        p_u = (
            (math.exp(r * dt / 2) - math.exp(-sigma * math.sqrt(dt / 2)))
            / (math.exp(sigma * math.sqrt(dt / 2)) - math.exp(-sigma * math.sqrt(dt / 2)))
        ) ** 2
        p_d = (
            (math.exp(sigma * math.sqrt(dt / 2)) - math.exp(r * dt / 2))
            / (math.exp(sigma * math.sqrt(dt / 2)) - math.exp(-sigma * math.sqrt(dt / 2)))
        ) ** 2
        p_m = 1.0 - (p_u + p_d)

        df = math.exp(-r * dt)

        # Terminal node prices: S0 * u^j where j ranges from -steps to +steps
        j = np.arange(-self.steps, self.steps + 1)
        prices = S0 * (u**j)

        if params.option_type == "call":
            values = np.maximum(prices - K, 0)
        else:
            values = np.maximum(K - prices, 0)

        # Backward induction
        for i in range(self.steps - 1, -1, -1):
            values = df * (p_d * values[0:-2] + p_m * values[1:-1] + p_u * values[2:])

            if self.is_american:
                j_vals = np.arange(-i, i + 1)
                s_vals = S0 * (u**j_vals)
                if params.option_type == "call":
                    exercise = np.maximum(s_vals - K, 0)
                else:
                    exercise = np.maximum(K - s_vals, 0)
                values = np.maximum(values, exercise)

        price = values[0]
        exec_time = self._stop_timer(start)

        m_type = "trinomial_american" if self.is_american else "trinomial"
        PRICE_COMPUTATIONS_TOTAL.labels(
            method_type=m_type, option_type=params.option_type, converged="true"
        ).inc()
        PRICE_DURATION_SECONDS.labels(m_type).observe(exec_time)

        return PricingResult(
            method_type=m_type,
            computed_price=float(price),
            exec_seconds=exec_time,
            parameter_set={"steps": self.steps, "is_american": self.is_american},
        )
