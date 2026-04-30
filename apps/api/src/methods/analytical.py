"""Black-Scholes analytical pricing and Greeks."""

from __future__ import annotations

import time

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm

from src.methods.base import BasePricer, OptionParams, PricingResult


class BlackScholesAnalytical(BasePricer):
    """Closed-form Black-Scholes solution for European options."""

    def price(self, params: OptionParams) -> PricingResult:
        start_time = time.perf_counter()

        S = params.underlying_price
        K = params.strike_price
        T = params.time_to_expiry
        sigma = params.volatility
        r = params.risk_free_rate

        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        if params.option_type == "call":
            price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        else:
            price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

        exec_time = time.perf_counter() - start_time
        return self._create_result(params, price, exec_time=exec_time)

    @staticmethod
    def greeks(params: OptionParams) -> dict[str, float]:
        """Compute Delta, Gamma, Vega, Theta, Rho."""
        S = params.underlying_price
        K = params.strike_price
        T = params.time_to_expiry
        sigma = params.volatility
        r = params.risk_free_rate

        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        pdf_d1 = norm.pdf(d1)

        delta = norm.cdf(d1) if params.option_type == "call" else norm.cdf(d1) - 1
        gamma = pdf_d1 / (S * sigma * np.sqrt(T))
        vega = S * pdf_d1 * np.sqrt(T)

        if params.option_type == "call":
            theta = -(S * pdf_d1 * sigma) / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * norm.cdf(d2)
            rho = K * T * np.exp(-r * T) * norm.cdf(d2)
        else:
            theta = -(S * pdf_d1 * sigma) / (2 * np.sqrt(T)) + r * K * np.exp(-r * T) * norm.cdf(
                -d2
            )
            rho = -K * T * np.exp(-r * T) * norm.cdf(-d2)

        return {"delta": delta, "gamma": gamma, "vega": vega, "theta": theta, "rho": rho}

    @staticmethod
    def implied_volatility(market_price: float, params: OptionParams) -> float:
        """Invert Black-Scholes to find implied volatility using Brent's method."""

        def objective(sigma: float) -> float:
            p = OptionParams(
                underlying_price=params.underlying_price,
                strike_price=params.strike_price,
                time_to_expiry=params.time_to_expiry,
                volatility=sigma,
                risk_free_rate=params.risk_free_rate,
                option_type=params.option_type,
            )
            return BlackScholesAnalytical().price(p).computed_price - market_price

        try:
            return float(brentq(objective, 1e-6, 5.0))
        except ValueError, RuntimeError:
            return 0.0
