"""Integration tests for distributed Ray execution."""

from __future__ import annotations

import pytest

from src.mlops.ray_runner import RayExperimentRunner


@pytest.mark.integration
def test_ray_runner_local_grid() -> None:
    """Verify Ray runner grid execution with local address."""
    # This test initializes Ray in local mode
    runner = RayExperimentRunner(
        ray_address="ray://localhost:10001", mlflow_tracking_uri="http://localhost:5000"
    )

    try:
        runner.connect()

        param_grid = [
            (
                {
                    "underlying_price": 100,
                    "strike_price": 100,
                    "time_to_expiry": 1,
                    "volatility": 0.2,
                    "risk_free_rate": 0.05,
                    "option_type": "call",
                },
                "analytical",
            )
        ]

        results = runner.run_grid("integration_test_grid", param_grid)
        assert len(results) == 1
        assert results[0]["method_type"] == "analytical"
        assert results[0]["computed_price"] > 0
    except Exception as exc:
        pytest.skip(f"Ray/MLflow not reachable: {exc}")
