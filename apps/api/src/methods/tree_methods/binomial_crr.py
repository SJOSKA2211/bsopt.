"""Cox-Ross-Rubinstein Binomial Tree for European/American options."""

from __future__ import annotations

import numpy as np

from src.methods.base import BasePricer, OptionParams, PricingResult


class BinomialCRR(BasePricer):
    """CRR Binomial Tree with O(n) memory efficiency."""

    def price(
        self, params: OptionParams, num_steps: int = 1000, american: bool = False
    ) -> PricingResult:
        start_time = self._start_timer()

        S = params.underlying_price
        K = params.strike_price
        T = params.time_to_expiry
        sigma = params.volatility
        r = params.risk_free_rate
        dt = T / num_steps

        u = np.exp(sigma * np.sqrt(dt))
        d = 1.0 / u
        q = (np.exp(r * dt) - d) / (u - d)
        df = np.exp(-r * dt)

        # Final state prices
        # nodes at step N: S * u^j * d^(N-j) = S * u^(2j-N)
        j = np.arange(num_steps + 1)
        S_values = S * (u ** (2 * j - num_steps))

        if params.option_type == "call":
            grid = np.maximum(S_values - K, 0)
        else:
            grid = np.maximum(K - S_values, 0)

        # Backward induction
        for i in range(num_steps - 1, -1, -1):
            grid = df * (q * grid[1:] + (1 - q) * grid[:-1])

            if american:
                # Early exercise check
                j_i = np.arange(i + 1)
                S_i = S * (u ** (2 * j_i - i))
                exercise = (
                    np.maximum(S_i - K, 0)
                    if params.option_type == "call"
                    else np.maximum(K - S_i, 0)
                )
                grid = np.maximum(grid, exercise)

        price = grid[0]

        exec_time = self._stop_timer(start_time)
        result = self._create_result(params, float(price), exec_time=exec_time)
        result.parameter_set["num_steps"] = num_steps
        result.parameter_set["american"] = american

        return result
