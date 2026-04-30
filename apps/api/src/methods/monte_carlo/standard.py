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

        S = params.underlying_price
        K = params.strike_price
        T = params.time_to_expiry
        sigma = params.volatility
        r = params.risk_free_rate

        # Exact log-normal simulation
        rng = np.random.default_rng()
        z = rng.standard_normal(num_paths)
        ST = S * np.exp((r - 0.5 * sigma**2) * T + sigma * np.sqrt(T) * z)

        payoffs = np.maximum(ST - K, 0) if params.option_type == "call" else np.maximum(K - ST, 0)

        price = np.mean(payoffs) * np.exp(-r * T)
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
