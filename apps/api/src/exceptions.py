"""Custom exceptions for the bsopt platform."""

from __future__ import annotations

from typing import Any


class BsoptError(Exception):
    """Base exception for all bsopt errors."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.context = context or {}


class PricingError(BsoptError):
    """Raised when a pricing computation fails."""


class CFLViolationError(PricingError):
    """Raised when stability conditions (CFL) are violated in FDM."""

    def __init__(
        self, cfl_actual: float, cfl_bound: float = 0.5, suggested_dt: float | None = None
    ) -> None:
        message = (
            f"CFL condition violated: {cfl_actual:.4f} > {cfl_bound}. Stability not guaranteed."
        )
        if suggested_dt:
            message += f" Suggested dt <= {suggested_dt:.6f}."
        super().__init__(
            message,
            {"cfl_actual": cfl_actual, "cfl_bound": cfl_bound, "suggested_dt": suggested_dt},
        )


class ValidationError(BsoptError):
    """Raised when input parameters fail validation."""


class DatabaseError(BsoptError):
    """Raised when database operations fail."""


class InfrastructureError(BsoptError):
    """Raised when external services (Redis, RabbitMQ, MinIO) are unreachable."""
