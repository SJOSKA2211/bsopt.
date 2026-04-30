"""Richardson Extrapolation for Binomial Trees."""

from __future__ import annotations

from src.methods.base import BasePricer, OptionParams, PricingResult
from src.methods.tree_methods.binomial_crr import BinomialCRR
from src.methods.tree_methods.trinomial import TrinomialTree


class RichardsonExtrapolation(BasePricer):
    """Richardson extrapolation on CRR: 2*V(2n) - V(n). O(n^-2) convergence."""

    def price(self, params: OptionParams, num_steps: int = 500) -> PricingResult:
        start_time = self._start_timer()

        crr = BinomialCRR()

        # Compute V(n)
        v_n = crr.price(params, num_steps=num_steps).computed_price

        # Compute V(2n)
        v_2n = crr.price(params, num_steps=2 * num_steps).computed_price

        # Extrapolate
        price = 2 * v_2n - v_n

        exec_time = self._stop_timer(start_time)
        result = self._create_result(params, float(price), exec_time=exec_time)
        result.parameter_set["num_steps_base"] = num_steps
        result.parameter_set["price_n"] = v_n
        result.parameter_set["price_2n"] = v_2n

        return result


class TrinomialRichardsonExtrapolation(BasePricer):
    """Richardson extrapolation on Trinomial Tree: 2*V(2n) - V(n)."""

    def price(self, params: OptionParams, num_steps: int = 500) -> PricingResult:
        start_time = self._start_timer()

        tree = TrinomialTree()

        # Compute V(n)
        v_n = tree.price(params, num_steps=num_steps).computed_price

        # Compute V(2n)
        v_2n = tree.price(params, num_steps=2 * num_steps).computed_price

        # Extrapolate
        price = 2 * v_2n - v_n

        exec_time = self._stop_timer(start_time)
        result = self._create_result(params, float(price), exec_time=exec_time)
        result.parameter_set["num_steps_base"] = num_steps
        result.parameter_set["price_n"] = v_n
        result.parameter_set["price_2n"] = v_2n

        return result
