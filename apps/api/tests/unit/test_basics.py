"""Unit tests for Phase 0 files."""
from __future__ import annotations

import pytest

from src.config import get_settings
from src.exceptions import BsoptError, CFLViolationError
from src.logging_config import setup_logging


@pytest.mark.unit
def test_exceptions() -> None:
    with pytest.raises(BsoptError):
        raise BsoptError("test")

    exc = CFLViolationError(cfl_actual=0.6, suggested_dt=0.01)
    assert "0.6000" in str(exc)
    assert "0.010000" in str(exc)


@pytest.mark.unit
def test_config() -> None:
    settings = get_settings()
    assert settings.env in {"production", "development", "test"}


@pytest.mark.unit
def test_logging_init() -> None:
    # Just ensure it runs without error
    setup_logging()
