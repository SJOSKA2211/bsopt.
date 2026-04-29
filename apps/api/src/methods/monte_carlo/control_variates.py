"""Monte Carlo with Control Variates."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.stats import norm

from src.methods.base import BasePricer, OptionParams, PricingResult
from src.metrics import PRICE_COMPUTATIONS_TOTAL, PRICE_DURATION_SECONDS


class ControlVariateMonteCarlo(BasePricer):
    """
    Monte Carlo with Control Variates.
    Uses the geometric Asian option as a control variate for a European option.
    """

    def __init__(
        self, num_paths: int = 100_000, num_steps: int = 50, seed: int | None = 42
    ) -> None:
        self.num_paths = num_paths
        self.num_steps = num_steps
        self.seed = seed

    def _geometric_asian_analytical(self, params: OptionParams) -> float:
        """Closed form for discrete Geometric Asian call/put."""
        S, K, T, sigma, r = (
            params.underlying_price,
            params.strike_price,
            params.time_to_maturity,
            params.volatility,
            params.risk_free_rate,
        )
        n = self.num_steps
        dt = T / n

        var_sum = sigma**2 * dt * n * (n + 1) * (2 * n + 1) / 6.0
        var_g = var_sum / (n**2)
        mean_g = math.log(S) + (r - 0.5 * sigma**2) * dt * (n + 1) / 2.0

        sigma_adj = math.sqrt(var_g / T)
        r_adj = (mean_g - math.log(S) + 0.5 * var_g) / T

        d1 = (math.log(S / K) + (r_adj + 0.5 * sigma_adj**2) * T) / (sigma_adj * math.sqrt(T))
        d2 = d1 - sigma_adj * math.sqrt(T)

        # Branchless dictionary lookup
        is_call = {"call": 1.0, "put": 0.0}[params.option_type]
        call_p = math.exp(-r * T) * (S * math.exp(r_adj * T) * norm.cdf(d1) - K * norm.cdf(d2))
        put_p = math.exp(-r * T) * (K * norm.cdf(-d2) - S * math.exp(r_adj * T) * norm.cdf(-d1))
        return float(is_call * call_p + (1.0 - is_call) * put_p)

    def price(self, params: OptionParams, **kwargs: Any) -> PricingResult:
        start = self._start_timer()

        num_paths = kwargs.get("num_paths", self.num_paths)
        num_steps = kwargs.get("num_steps", self.num_steps)

        S0 = params.underlying_price
        K = params.strike_price
        T = params.time_to_maturity
        sigma = params.volatility
        r = params.risk_free_rate
        dt = T / num_steps

        if self.seed is not None:
            np.random.seed(self.seed)

        z = np.random.standard_normal((num_paths, num_steps))
        log_drifts = (r - 0.5 * sigma**2) * dt + sigma * math.sqrt(dt) * z
        log_paths = np.cumsum(log_drifts, axis=1) + math.log(S0)

        ST = np.exp(log_paths[:, -1])
        is_call = {"call": 1.0, "put": 0.0}[params.option_type]

        y = (is_call * np.maximum(ST - K, 0) + (1.0 - is_call) * np.maximum(K - ST, 0)) * math.exp(
            -r * T
        )

        log_geom_mean = np.mean(log_paths, axis=1)
        geom_mean = np.exp(log_geom_mean)
        cv_payoff = (
            is_call * np.maximum(geom_mean - K, 0) + (1.0 - is_call) * np.maximum(K - geom_mean, 0)
        ) * math.exp(-r * T)

        cv_expected = self._geometric_asian_analytical(params)

        cov_matrix = np.cov(y, cv_payoff)
        beta = cov_matrix[0, 1] / cov_matrix[1, 1]

        y_cv = y - beta * (cv_payoff - cv_expected)

        price = np.mean(y_cv)
        std_err = np.std(y_cv) / math.sqrt(num_paths)

        exec_time = self._stop_timer(start)
        PRICE_COMPUTATIONS_TOTAL.labels(
            method_type="control_variate_mc", option_type=params.option_type, converged="true"
        ).inc()
        PRICE_DURATION_SECONDS.labels(method_type="control_variate_mc").observe(exec_time)

        return PricingResult(
            method_type="control_variate_mc",
            computed_price=float(price),
            exec_seconds=exec_time,
            parameter_set={
                "num_paths": num_paths,
                "num_steps": num_steps,
                "beta": beta,
                "std_err": std_err,
            },
        )
