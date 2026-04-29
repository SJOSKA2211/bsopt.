"""Custom exceptions for the bsopt platform."""

from __future__ import annotations

from typing import Any


class BsoptError(Exception):
    """Base exception for all bsopt errors."""



class ConfigurationError(BsoptError):
    """Raised when there is a configuration error."""



class ValidationError(BsoptError):
    """Raised when input validation fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


class DatabaseError(BsoptError):
    """Raised when there is a database error."""



class CacheError(BsoptError):
    """Raised when there is a cache error."""



class QueueError(BsoptError):
    """Raised when there is a message queue error."""



class StorageError(BsoptError):
    """Raised when there is a storage error."""



class PricingError(BsoptError):
    """Raised when there is an error in pricing computations."""



class ScraperError(BsoptError):
    """Raised when there is an error in market data scraping."""



class MLOpsError(BsoptError):
    """Raised when there is an error in MLOps workflows."""



class CFLViolationError(PricingError):
    """Raised when the Courant-Friedrichs-Lewy condition is violated."""

    def __init__(
        self, cfl_actual: float, cfl_bound: float = 0.5, suggested_dt: float | None = None
    ) -> None:
        self.cfl_actual = cfl_actual
        self.cfl_bound = cfl_bound
        self.suggested_dt = suggested_dt
        msg = f"CFL condition violated: {cfl_actual:.4f} > {cfl_bound:.4f}."
        if suggested_dt:
            msg += f" Suggested dt <= {suggested_dt:.6f}."
        super().__init__(msg)
