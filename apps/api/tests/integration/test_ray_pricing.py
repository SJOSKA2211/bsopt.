"""Integration test for Ray-based distributed pricing."""

from __future__ import annotations

import pytest
import ray
from src.mlops.ray_runner import RayExperimentRunner
from src.methods.base import OptionParams

@pytest.mark.integration
def test_ray_distributed_pricing_flow() -> None:
    """Verify that Ray can execute pricing tasks across workers."""
    # Use local ray init to avoid version mismatch with the container head
    # This still verifies the distributed logic and MLflow integration
    runner = RayExperimentRunner(ray_address="local", mlflow_tracking_uri="http://localhost:5000")
    runner.connect()
    
    try:
        params = {
            "underlying_price": 100.0,
            "strike_price": 100.0,
            "time_to_expiry": 1.0,
            "volatility": 0.2,
            "risk_free_rate": 0.05,
            "option_type": "call"
        }
        grid = [
            (params, "analytical"),
            (params, "binomial_crr")
        ]
        
        results = runner.run_grid("test_experiment", grid)
        
        assert len(results) == 2
        assert results[0]["method_type"] == "analytical"
        assert abs(results[0]["computed_price"] - 10.4506) < 1e-4
        
    finally:
        ray.shutdown()
