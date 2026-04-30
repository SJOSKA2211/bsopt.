"""Standard Monte Carlo pricing for European options."""

from __future__ import annotations

import time
from typing import cast

import numpy as np
from scipy.stats import norm

from src.methods.base import BasePricer, OptionParams, PricingResult


class StandardMonteCarlo(BasePricer):
    """Vectorized standard Monte Carlo pricer."""

    def price(self, params: OptionParams, num_paths: int = 100000) -> PricingResult:
        start_time = time.perf_counter()

        underlying_price = params.underlying_price
        strike_price = params.strike_price
        time_to_expiry = params.time_to_expiry
        volatility = params.volatility
        risk_free_rate = params.risk_free_rate

        # Exact log-normal simulation
        rng = np.random.default_rng()
        standard_normal_samples = rng.standard_normal(num_paths)
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
        std_err = np.std(payoffs) / np.sqrt(num_paths)

        exec_time = time.perf_counter() - start_time
        result = self._create_result(params, float(price), exec_time=exec_time)
        result.parameter_set["std_err"] = float(std_err)
        result.parameter_set["num_paths"] = num_paths
        result.parameter_set["ci_width"] = float(1.96 * std_err)

        return result

    def price_with_confidence_interval(
        self, params: OptionParams, num_paths: int = 100000, confidence: float = 0.95
    ) -> dict[str, float]:
        """Compute price and the width of the confidence interval."""
        res = self.price(params, num_paths)
        z_score = norm.ppf(1 - (1 - confidence) / 2)
        std_err = cast("float", res.parameter_set["std_err"])
        ci_width = z_score * std_err
        return {
            "price": res.computed_price,
            "ci_lower": res.computed_price - ci_width,
            "ci_upper": res.computed_price + ci_width,
            "ci_width": ci_width,
        }
