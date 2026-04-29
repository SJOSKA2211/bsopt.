"""Distributed experiment execution script."""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from src.config import get_settings
from src.mlops.ray_runner import RayExperimentRunner

logger = structlog.get_logger(__name__)


async def run_experiments() -> None:
    """Initialize Ray and run a sample grid of pricing experiments."""
    settings = get_settings()
    
    runner = RayExperimentRunner(
        ray_address=settings.ray_address,
        mlflow_tracking_uri=settings.mlflow_tracking_uri,
    )
    
    runner.connect()
    
    # Example parameter grid matching OptionParams schema
    param_grid: list[tuple[dict[str, Any], str]] = [
        ({
            "underlying_price": 100.0,
            "strike_price": 100.0,
            "time_to_maturity": 1.0,
            "volatility": 0.2,
            "risk_free_rate": 0.05,
            "option_type": "call"
        }, "analytical"),
        ({
            "underlying_price": 100.0,
            "strike_price": 100.0,
            "time_to_maturity": 1.0,
            "volatility": 0.2,
            "risk_free_rate": 0.05,
            "option_type": "binomial_crr"
        }, "binomial_crr"),
    ]
    
    results = runner.run_grid("grid_test", param_grid)
    logger.info("experiments_finished", total=len(results))


if __name__ == "__main__":
    asyncio.run(run_experiments())
