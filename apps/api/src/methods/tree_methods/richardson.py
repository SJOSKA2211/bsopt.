"""Richardson Extrapolation for Tree Methods."""

from __future__ import annotations

from typing import Any

from src.methods.base import BasePricer, OptionParams, PricingResult
from src.methods.tree_methods.binomial_crr import BinomialCRR
from src.methods.tree_methods.trinomial import TrinomialTree
from src.metrics import PRICE_COMPUTATIONS_TOTAL, PRICE_DURATION_SECONDS


class RichardsonExtrapolation(BasePricer):
    """
    Richardson Extrapolation for Binomial tree.
    Formula: V_extrapolated = 2 * V(2n) - V(n)
    """

    def __init__(self, steps: int = 500) -> None:
        self.steps = steps

    def price(self, params: OptionParams, **kwargs: Any) -> PricingResult:
        start = self._start_timer()

        # Handle potential override from router
        steps = kwargs.get("steps", self.steps)

        pricer_n = BinomialCRR(steps=steps)
        pricer_2n = BinomialCRR(steps=2 * steps)

        res_n = pricer_n.price(params)
        res_2n = pricer_2n.price(params)

        # Extrapolate
        price = 2.0 * res_2n.computed_price - res_n.computed_price

        exec_time = self._stop_timer(start)
        m_type = "binomial_crr_richardson"

        PRICE_COMPUTATIONS_TOTAL.labels(
            method_type=m_type, option_type=params.option_type, converged="true"
        ).inc()
        PRICE_DURATION_SECONDS.labels(method_type=m_type).observe(exec_time)

        return PricingResult(
            method_type=m_type,
            computed_price=float(price),
            exec_seconds=exec_time,
            parameter_set={
                "steps_n": steps,
                "price_n": res_n.computed_price,
                "price_2n": res_2n.computed_price,
            },
        )


class TrinomialRichardsonExtrapolation(BasePricer):
    """
    Richardson Extrapolation for Trinomial tree.
    Formula: V_extrapolated = 2 * V(2n) - V(n)
    """

    def __init__(self, steps: int = 500) -> None:
        self.steps = steps

    def price(self, params: OptionParams, **kwargs: Any) -> PricingResult:
        start = self._start_timer()

        # Handle potential override from router
        steps = kwargs.get("steps", self.steps)

        pricer_n = TrinomialTree(steps=steps)
        pricer_2n = TrinomialTree(steps=2 * steps)

        res_n = pricer_n.price(params)
        res_2n = pricer_2n.price(params)

        # Extrapolate
        price = 2.0 * res_2n.computed_price - res_n.computed_price

        exec_time = self._stop_timer(start)
        m_type = "trinomial_richardson"

        PRICE_COMPUTATIONS_TOTAL.labels(
            method_type=m_type, option_type=params.option_type, converged="true"
        ).inc()
        PRICE_DURATION_SECONDS.labels(method_type=m_type).observe(exec_time)

        return PricingResult(
            method_type=m_type,
            computed_price=float(price),
            exec_seconds=exec_time,
            parameter_set={
                "steps_n": steps,
                "price_n": res_n.computed_price,
                "price_2n": res_2n.computed_price,
            },
        )
