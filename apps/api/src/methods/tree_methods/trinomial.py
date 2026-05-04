"""Trinomial Tree pricing method (Boyle 1988)."""

from __future__ import annotations

import numpy as np

from src.methods.base import BasePricer, OptionParams, PricingResult


class TrinomialTree(BasePricer):
    """Trinomial Tree with smoother convergence than binomial."""

    def price(self, params: OptionParams, num_steps: int = 500) -> PricingResult:
        start_time = self._start_timer()

        underlying_price = params.underlying_price
        strike_price = params.strike_price
        time_to_expiry = params.time_to_expiry
        volatility = params.volatility
        risk_free_rate = params.risk_free_rate
        delta_time = time_to_expiry / num_steps

        delta_log_price = volatility * np.sqrt(3 * delta_time)
        up_factor = np.exp(delta_log_price)

        # Boyle / Hull-White probabilities
        drift_rate = risk_free_rate - 0.5 * volatility**2
        variance_term = (volatility**2 * delta_time + drift_rate**2 * delta_time**2) / (
            delta_log_price**2
        )
        drift_term = drift_rate * delta_time / delta_log_price

        prob_up = 0.5 * (variance_term + drift_term)
        prob_down = 0.5 * (variance_term - drift_term)
        prob_mid = 1.0 - prob_up - prob_down

        # Final nodes: 2*num_steps + 1
        node_indices = np.arange(2 * num_steps + 1) - num_steps
        spot_values = underlying_price * (up_factor**node_indices)

        if params.option_type == "call":
            grid = np.maximum(spot_values - strike_price, 0)
        else:
            grid = np.maximum(strike_price - spot_values, 0)

        discount_factor = np.exp(-risk_free_rate * delta_time)

        for step_index in range(num_steps - 1, -1, -1):
            grid = discount_factor * (
                prob_up * grid[2:] + prob_mid * grid[1:-1] + prob_down * grid[:-2]
            )

            if params.exercise_type == "american":
                current_node_indices = np.arange(2 * step_index + 1) - step_index
                current_spot_values = underlying_price * (up_factor**current_node_indices)
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
