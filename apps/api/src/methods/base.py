"""Base classes and types for numerical pricing methods."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class OptionParams:
    """Standard Black-Scholes input parameters."""

    underlying_price: float
    strike_price: float
    time_to_maturity: float
    volatility: float
    risk_free_rate: float
    option_type: str  # "call" or "put"

    def __post_init__(self) -> None:
        """Validate parameters after construction."""
        if self.underlying_price <= 0:
            raise ValueError("underlying_price must be > 0")
        if self.strike_price <= 0:
            raise ValueError("strike_price must be > 0")
        if self.time_to_maturity <= 0:
            raise ValueError("time_to_maturity must be > 0")
        if self.volatility <= 0:
            raise ValueError("volatility must be > 0")
        if self.risk_free_rate < 0:
            raise ValueError("risk_free_rate must be >= 0")
        if self.option_type not in ("call", "put"):
            raise ValueError("option_type must be 'call' or 'put'")


@dataclass(frozen=True)
class PricingResult:
    """Standard container for pricing method outputs."""

    method_type: str
    computed_price: float
    exec_seconds: float
    converged: bool = True
    parameter_set: dict[str, Any] = field(default_factory=dict)


class BasePricer(ABC):
    """Abstract base class for all pricing implementations."""

    @abstractmethod
    def price(self, params: OptionParams, **kwargs: Any) -> PricingResult:
        """Execute the pricing algorithm and return a standardized result."""

    def _start_timer(self) -> float:
        return time.perf_counter()

    def _stop_timer(self, start_time: float) -> float:
        return time.perf_counter() - start_time
