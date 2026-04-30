"""Custom exceptions for bsopt."""

from __future__ import annotations

from typing import Any


class BsoptError(Exception):
    """Base exception for all bsopt errors."""


class PricingError(BsoptError):
    """Raised when a pricing method fails."""


class CFLViolationError(PricingError):
    """Raised when Stability condition for Explicit FDM is violated."""

    def __init__(
        self, cfl_actual: float, cfl_bound: float = 0.5, suggested_dt: float | None = None
    ) -> None:
        self.cfl_actual = cfl_actual
        self.cfl_bound = cfl_bound
        self.suggested_dt = suggested_dt
        msg = f"CFL violation: {cfl_actual:.4f} > {cfl_bound}. "
        if suggested_dt:
            msg += f"Suggested dt <= {suggested_dt:.6f}"
        super().__init__(msg)


class ValidationError(BsoptError):
    """Raised when data validation fails."""

    def __init__(self, errors: list[str] | list[dict[str, Any]]) -> None:
        self.details = {"errors": errors}
        super().__init__(str(errors))


class DatabaseError(BsoptError):
    """Raised when database operations fail."""


class InfrastructureError(BsoptError):
    """Raised when infrastructure (Redis, RabbitMQ, etc.) fails."""


class ScraperError(BsoptError):
    """Raised when a scraper fails."""
