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

        underlying_price = params.underlying_price
        strike_price = params.strike_price
        time_to_expiry = params.time_to_expiry
        volatility = params.volatility
        risk_free_rate = params.risk_free_rate

        d1 = (
            np.log(underlying_price / strike_price)
            + (risk_free_rate + 0.5 * volatility**2) * time_to_expiry
        ) / (volatility * np.sqrt(time_to_expiry))
        d2 = d1 - volatility * np.sqrt(time_to_expiry)

        if params.option_type == "call":
            price = underlying_price * norm.cdf(d1) - strike_price * np.exp(
                -risk_free_rate * time_to_expiry
            ) * norm.cdf(d2)
        else:
            price = strike_price * np.exp(-risk_free_rate * time_to_expiry) * norm.cdf(
                -d2
            ) - underlying_price * norm.cdf(-d1)

        exec_time = time.perf_counter() - start_time
        return self._create_result(params, price, exec_time=exec_time)

    @staticmethod
    def greeks(params: OptionParams) -> dict[str, float]:
        """Compute Delta, Gamma, Vega, Theta, Rho."""
        underlying_price = params.underlying_price
        strike_price = params.strike_price
        time_to_expiry = params.time_to_expiry
        volatility = params.volatility
        risk_free_rate = params.risk_free_rate

        d1 = (
            np.log(underlying_price / strike_price)
            + (risk_free_rate + 0.5 * volatility**2) * time_to_expiry
        ) / (volatility * np.sqrt(time_to_expiry))
        d2 = d1 - volatility * np.sqrt(time_to_expiry)

        pdf_d1 = norm.pdf(d1)

        delta = norm.cdf(d1) if params.option_type == "call" else norm.cdf(d1) - 1
        gamma = pdf_d1 / (underlying_price * volatility * np.sqrt(time_to_expiry))
        vega = underlying_price * pdf_d1 * np.sqrt(time_to_expiry)

        if params.option_type == "call":
            theta = -(underlying_price * pdf_d1 * volatility) / (
                2 * np.sqrt(time_to_expiry)
            ) - risk_free_rate * strike_price * np.exp(-risk_free_rate * time_to_expiry) * norm.cdf(
                d2
            )
            rho = (
                strike_price
                * time_to_expiry
                * np.exp(-risk_free_rate * time_to_expiry)
                * norm.cdf(d2)
            )
        else:
            theta = -(underlying_price * pdf_d1 * volatility) / (
                2 * np.sqrt(time_to_expiry)
            ) + risk_free_rate * strike_price * np.exp(-risk_free_rate * time_to_expiry) * norm.cdf(
                -d2
            )
            rho = (
                -strike_price
                * time_to_expiry
                * np.exp(-risk_free_rate * time_to_expiry)
                * norm.cdf(-d2)
            )

        return {"delta": delta, "gamma": gamma, "vega": vega, "theta": theta, "rho": rho}

    @staticmethod
    def implied_volatility(market_price: float, params: OptionParams) -> float:
        """Invert Black-Scholes to find implied volatility using Brent's method."""

        def objective(volatility: float) -> float:
            p = OptionParams(
                underlying_price=params.underlying_price,
                strike_price=params.strike_price,
                time_to_expiry=params.time_to_expiry,
                volatility=volatility,
                risk_free_rate=params.risk_free_rate,
                option_type=params.option_type,
            )
            return BlackScholesAnalytical().price(p).computed_price - market_price

        try:
            return float(brentq(objective, 1e-6, 5.0))
        except (ValueError, RuntimeError):
            return 0.0

    @staticmethod
    def geometric_asian_price(params: OptionParams) -> float:
        """Analytical price for a Geometric Asian option (continuous average)."""
        underlying_price = params.underlying_price
        strike_price = params.strike_price
        time_to_expiry = params.time_to_expiry
        volatility = params.volatility
        risk_free_rate = params.risk_free_rate

        # Adjusted volatility and drift for geometric average
        vol_adj = volatility / np.sqrt(3.0)
        rho_adj = 0.5 * (risk_free_rate - 0.5 * (volatility**2 - (vol_adj**2)))

        d1 = (
            np.log(underlying_price / strike_price) + (rho_adj + 0.5 * vol_adj**2) * time_to_expiry
        ) / (vol_adj * np.sqrt(time_to_expiry))
        d2 = d1 - vol_adj * np.sqrt(time_to_expiry)

        if params.option_type == "call":
            price = underlying_price * np.exp(
                (rho_adj - risk_free_rate) * time_to_expiry
            ) * norm.cdf(d1) - strike_price * np.exp(-risk_free_rate * time_to_expiry) * norm.cdf(
                d2
            )
        else:
            price = strike_price * np.exp(-risk_free_rate * time_to_expiry) * norm.cdf(
                -d2
            ) - underlying_price * np.exp((rho_adj - risk_free_rate) * time_to_expiry) * norm.cdf(
                -d1
            )

        return float(price)
