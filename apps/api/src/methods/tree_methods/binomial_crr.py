"""Cox-Ross-Rubinstein Binomial Tree for European/American options."""

from __future__ import annotations

import numpy as np

from src.methods.base import BasePricer, OptionParams, PricingResult


class BinomialCRR(BasePricer):
    """CRR Binomial Tree with O(n) memory efficiency."""

    def price(self, params: OptionParams, num_steps: int = 1000) -> PricingResult:
        start_time = self._start_timer()

        underlying_price = params.underlying_price
        strike_price = params.strike_price
        time_to_expiry = params.time_to_expiry
        volatility = params.volatility
        risk_free_rate = params.risk_free_rate
        delta_time = time_to_expiry / num_steps

        up_factor = np.exp(volatility * np.sqrt(delta_time))
        down_factor = 1.0 / up_factor
        risk_neutral_prob = (np.exp(risk_free_rate * delta_time) - down_factor) / (
            up_factor - down_factor
        )
        discount_factor = np.exp(-risk_free_rate * delta_time)

        # Final state prices
        # nodes at step num_steps: S * u^j * d^(num_steps-j) = S * u^(2j-num_steps)
        node_indices = np.arange(num_steps + 1)
        spot_values = underlying_price * (up_factor ** (2 * node_indices - num_steps))

        if params.option_type == "call":
            grid = np.maximum(spot_values - strike_price, 0)
        else:
            grid = np.maximum(strike_price - spot_values, 0)

        # Backward induction
        for step_index in range(num_steps - 1, -1, -1):
            grid = discount_factor * (
                risk_neutral_prob * grid[1:] + (1 - risk_neutral_prob) * grid[:-1]
            )

            if params.exercise_type == "american":
                # Early exercise check
                current_node_indices = np.arange(step_index + 1)
                current_spot_values = underlying_price * (
                    up_factor ** (2 * current_node_indices - step_index)
                )
                exercise_payoff = (
                    np.maximum(current_spot_values - strike_price, 0)
                    if params.option_type == "call"
                    else np.maximum(strike_price - current_spot_values, 0)
                )
                grid = np.maximum(grid, exercise_payoff)

        price = grid[0]

        exec_time = self._stop_timer(start_time)
        result = self._create_result(params, float(price), exec_time=exec_time)
        result.parameter_set["num_steps"] = num_steps
        result.parameter_set["exercise_type"] = params.exercise_type

        return result
