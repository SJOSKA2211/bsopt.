"""Black-Scholes analytical closed-form pricer and Greeks."""

from __future__ import annotations

import math
from typing import Any

from scipy.optimize import brentq
from scipy.stats import norm

from src.methods.base import BasePricer, OptionParams, PricingResult
from src.metrics import PRICE_COMPUTATIONS_TOTAL, PRICE_DURATION_SECONDS


class BlackScholesAnalytical(BasePricer):
    """Canonical Black-Scholes-Merton model for European options."""

    def price(self, params: OptionParams, **kwargs: Any) -> PricingResult:
        start = self._start_timer()

        S, K, T, v, r = (
            params.underlying_price,
            params.strike_price,
            params.time_to_maturity,
            params.volatility,
            params.risk_free_rate,
        )

        d1 = (math.log(S / K) + (r + 0.5 * v**2) * T) / (v * math.sqrt(T))
        d2 = d1 - v * math.sqrt(T)

        if params.option_type == "call":
            price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
        else:
            price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

        exec_time = self._stop_timer(start)

        # Track metrics
        PRICE_COMPUTATIONS_TOTAL.labels(
            method_type="analytical", option_type=params.option_type, converged="true"
        ).inc()
        PRICE_DURATION_SECONDS.labels(method_type="analytical").observe(exec_time)

        return PricingResult(
            method_type="analytical",
            computed_price=price,
            exec_seconds=exec_time,
            parameter_set={"d1": d1, "d2": d2},
        )

    def delta(self, params: OptionParams) -> float:
        S, K, T, v, r = (
            params.underlying_price,
            params.strike_price,
            params.time_to_maturity,
            params.volatility,
            params.risk_free_rate,
        )
        d1 = float((math.log(S / K) + (r + 0.5 * v**2) * T) / (v * math.sqrt(T)))
        if params.option_type == "call":
            return float(norm.cdf(d1))
        return float(norm.cdf(d1)) - 1.0

    def gamma(self, params: OptionParams) -> float:
        S, K, T, v, r = (
            params.underlying_price,
            params.strike_price,
            params.time_to_maturity,
            params.volatility,
            params.risk_free_rate,
        )
        d1 = float((math.log(S / K) + (r + 0.5 * v**2) * T) / (v * math.sqrt(T)))
        return float(norm.pdf(d1) / (S * v * math.sqrt(T)))

    def vega(self, params: OptionParams) -> float:
        S, K, T, v, r = (
            params.underlying_price,
            params.strike_price,
            params.time_to_maturity,
            params.volatility,
            params.risk_free_rate,
        )
        d1 = float((math.log(S / K) + (r + 0.5 * v**2) * T) / (v * math.sqrt(T)))
        return float(S * norm.pdf(d1) * math.sqrt(T))

    @staticmethod
    def implied_volatility(market_price: float, params_base: OptionParams) -> float:
        """Invert Black-Scholes price to find volatility using Brent's method."""

        def objective(sigma: float) -> float:
            # We recreate params with the trial sigma
            p = OptionParams(
                underlying_price=params_base.underlying_price,
                strike_price=params_base.strike_price,
                time_to_maturity=params_base.time_to_maturity,
                volatility=sigma,
                risk_free_rate=params_base.risk_free_rate,
                option_type=params_base.option_type,
            )
            return BlackScholesAnalytical().price(p).computed_price - market_price

        try:
            return float(brentq(objective, 1e-6, 5.0))
        except ValueError, RuntimeError:
            return 0.0
