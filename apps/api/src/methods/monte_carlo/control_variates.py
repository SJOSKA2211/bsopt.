"""Control Variates Monte Carlo pricing using Geometric Asian anchor."""

from __future__ import annotations

import time

import numpy as np

from src.methods.base import BasePricer, OptionParams, PricingResult


class ControlVariateMonteCarlo(BasePricer):
    """Monte Carlo pricer using Control Variates for significant variance reduction."""

    def price(
        self, params: OptionParams, num_paths: int = 50000, num_steps: int = 50
    ) -> PricingResult:
        start_time = time.perf_counter()

        underlying_price = params.underlying_price
        strike_price = params.strike_price
        time_to_expiry = params.time_to_expiry
        volatility = params.volatility
        risk_free_rate = params.risk_free_rate
        delta_time = time_to_expiry / num_steps

        rng = np.random.default_rng()
        # Brownian motion increments
        brownian_increments = rng.standard_normal((num_paths, num_steps)) * np.sqrt(delta_time)
        brownian_motion = np.cumsum(brownian_increments, axis=1)

        time_grid = np.linspace(delta_time, time_to_expiry, num_steps)
        paths = underlying_price * np.exp(
            (risk_free_rate - 0.5 * volatility**2) * time_grid + volatility * brownian_motion
        )
        terminal_prices = paths[:, -1]

        # Payoffs for standard option
        payoff_standard = (
            np.maximum(terminal_prices - strike_price, 0)
            if params.option_type == "call"
            else np.maximum(strike_price - terminal_prices, 0)
        )

        # Control Variate: Terminal Spot Price
        # E[S_T] = S_0 * exp(r*T)
        expected_terminal_spot = underlying_price * np.exp(risk_free_rate * time_to_expiry)

        cov_matrix = np.cov(payoff_standard, terminal_prices)
        beta_coefficient = cov_matrix[0, 1] / cov_matrix[1, 1] if cov_matrix[1, 1] > 0 else 0

        payoff_control_variate = payoff_standard - beta_coefficient * (
            terminal_prices - expected_terminal_spot
        )

        price = np.mean(payoff_control_variate) * np.exp(-risk_free_rate * time_to_expiry)
        std_error = np.std(payoff_control_variate) / np.sqrt(num_paths)

        exec_time = time.perf_counter() - start_time
        result = self._create_result(params, float(price), exec_time=exec_time)
        result.parameter_set["num_paths"] = num_paths
        result.parameter_set["num_steps"] = num_steps
        result.parameter_set["std_err"] = float(std_error)
        result.parameter_set["beta"] = float(beta_coefficient)

        return result
