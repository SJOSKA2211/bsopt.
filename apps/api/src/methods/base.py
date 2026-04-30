"""Base classes and types for numerical pricing methods."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class OptionParams:
    """Parameters for Black-Scholes pricing."""

    underlying_price: float
    strike_price: float
    time_to_expiry: float
    volatility: float
    risk_free_rate: float
    option_type: str  # "call" or "put"
    exercise_type: str = "european"  # "european" or "american"
    market_source: str = "unknown"

    def __post_init__(self) -> None:
        if self.underlying_price <= 0:
            raise ValueError("Underlying price must be positive")
        if self.strike_price <= 0:
            raise ValueError("Strike price must be positive")
        if self.time_to_expiry <= 0:
            raise ValueError("Time to expiry must be positive")
        if self.volatility <= 0:
            raise ValueError("Volatility must be positive")
        if self.option_type not in {"call", "put"}:
            raise ValueError("Option type must be 'call' or 'put'")
        if self.exercise_type not in {"european", "american"}:
            raise ValueError("Exercise type must be 'european' or 'american'")


@dataclass(frozen=True)
class PricingResult:
    """Standardized result of a pricing computation."""

    method_type: str
    computed_price: float
    exec_seconds: float
    converged: bool
    parameter_set: dict[str, Any] = field(default_factory=dict)


class BasePricer(ABC):
    """Abstract base class for all pricing methods."""

    @abstractmethod
    def price(self, params: OptionParams) -> PricingResult:
        """Compute the option price."""

    def _create_result(
        self, params: OptionParams, price: float, converged: bool = True, exec_time: float = 0.0
    ) -> PricingResult:
        """Helper to create a PricingResult."""
        return PricingResult(
            method_type=self.__class__.__name__,
            computed_price=price,
            exec_seconds=exec_time,
            converged=converged,
            parameter_set={
                "underlying_price": params.underlying_price,
                "strike_price": params.strike_price,
                "time_to_expiry": params.time_to_expiry,
                "volatility": params.volatility,
                "risk_free_rate": params.risk_free_rate,
                "option_type": params.option_type,
            },
        )

    def _start_timer(self) -> float:
        """Start a high-resolution timer."""
        return time.perf_counter()

    def _stop_timer(self, start_time: float) -> float:
        """Stop the timer and return elapsed time."""
        return time.perf_counter() - start_time
