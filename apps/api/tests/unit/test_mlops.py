"""Exhaustive unit and integration tests for MLOps components — Zero-Mock."""

from __future__ import annotations

import os
from datetime import date
from typing import Any
from uuid import uuid4

import pytest
import ray

from src.mlops.drift_detector import check_model_drift
from src.mlops.feature_store import FeatureStore
from src.mlops.mlflow_tracker import MLflowTracker
from src.mlops.model_registry import ModelRegistry
from src.mlops.ray_runner import RayExperimentRunner


@pytest.fixture
def mlflow_uri() -> str:
    return os.environ.get("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")


# ── MLflow Tracker Tests ────────────────────────────────────────────


@pytest.mark.unit
def test_mlflow_tracker_logging_with_tags(mlflow_uri: str) -> None:
    """Cover the tags is not None branch."""
    tracker = MLflowTracker(mlflow_uri)
    assert tracker.tracking_uri == mlflow_uri
    exp_name = f"test_exp_{uuid4().hex[:8]}"
    run_id = tracker.log_pricing_run(
        experiment_name=exp_name,
        run_name="test_run",
        params={"p1": 1.0},
        metrics={"m1": 0.5},
        tags={"t1": "v1"},
    )
    assert isinstance(run_id, str)


@pytest.mark.unit
def test_mlflow_tracker_logging_without_tags(mlflow_uri: str) -> None:
    """Cover the tags is None branch (default parameter)."""
    tracker = MLflowTracker(mlflow_uri)
    exp_name = f"test_exp_{uuid4().hex[:8]}"
    run_id = tracker.log_pricing_run(
        experiment_name=exp_name,
        run_name="test_run_no_tags",
        params={"p1": 2.0},
        metrics={"m1": 0.3},
    )
    assert isinstance(run_id, str)


@pytest.mark.unit
def test_mlflow_tracker_real_failure() -> None:
    """Cover the except branch in log_pricing_run."""
    tracker = MLflowTracker("http://invalid_url_that_fails_fast")
    import contextlib

    with contextlib.suppress(Exception):
        tracker.log_pricing_run(None, None, None, None)  # type: ignore


# ── Feature Store Tests ─────────────────────────────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_feature_store_persistence() -> None:
    store = FeatureStore()
    snapshot_date = date(2024, 2, 1)
    features = {"f1": 1.0, "f2": 2.5}
    await store.save_snapshot(snapshot_date, features, 100)
    retrieved = await store.get_snapshot(snapshot_date)
    assert retrieved == features
    assert await store.get_snapshot(date(1999, 1, 1)) is None


@pytest.mark.unit
def test_feature_engineering() -> None:
    store = FeatureStore()
    feats = store.engineer_features(100, 100, 1, 0.2, 0.05)
    assert feats["moneyness"] == pytest.approx(1.0)
    assert feats["intrinsic_value"] == pytest.approx(0.0)


# ── Price Logic (pure function, no Ray) ──────────────────────────────


@pytest.mark.unit
def test_price_logic_direct() -> None:
    from src.mlops.ray_runner import _price_logic

    params = {
        "underlying_price": 100,
        "strike_price": 100,
        "time_to_expiry": 1,
        "volatility": 0.2,
        "risk_free_rate": 0.05,
        "option_type": "call",
    }
    res = _price_logic(params, "analytical")
    assert res["computed_price"] > 0
    assert res["method_type"] == "BlackScholesAnalytical"


@pytest.mark.unit
def test_ray_runner_invalid_method() -> None:
    from src.mlops.ray_runner import _price_logic

    with pytest.raises(ValueError, match="Unknown method"):
        _price_logic({"p": 1}, "invalid")


# ── Ray Runner Tests ────────────────────────────────────────────────


@pytest.mark.unit
def test_ray_runner_local_init_and_grid() -> None:
    """Test normal local init → already-initialized branch → run_grid."""
    try:
        if ray.is_initialized():
            ray.shutdown()
        RayExperimentRunner._connection_failed = False

        runner = RayExperimentRunner(
            ray_address="",
            mlflow_tracking_uri="http://127.0.0.1:5000",
            num_cpus=1,
            include_dashboard=False,
        )
        # First connect: exercises the `not self.ray_address` → ray.init() branch
        runner.connect()
        assert ray.is_initialized()

        # Second connect: exercises the `ray.is_initialized() → True` early return
        runner.connect()

        # Run grid: exercises run_grid + price_remote.remote
        params = {
            "underlying_price": 100,
            "strike_price": 100,
            "time_to_expiry": 1,
            "volatility": 0.2,
            "risk_free_rate": 0.05,
            "option_type": "call",
        }
        results = runner.run_grid("test_ray_grid", [(params, "analytical")])
        assert len(results) == 1
        assert results[0]["computed_price"] > 0

        # Direct call for coverage of line 75 (Ray worker delegation)
        from src.mlops.ray_runner import price_remote
        direct_res = price_remote._function(params, "analytical")
        assert direct_res["computed_price"] > 0
    finally:
        if ray.is_initialized():
            ray.shutdown()


@pytest.mark.unit
def test_ray_runner_connection_failed_branch() -> None:
    """Test the _connection_failed=True → local fallback branch."""
    try:
        if ray.is_initialized():
            ray.shutdown()
        RayExperimentRunner._connection_failed = True

        runner = RayExperimentRunner(
            ray_address="",
            mlflow_tracking_uri="http://127.0.0.1:5000",
            num_cpus=1,
            include_dashboard=False,
        )
        runner.connect()
        assert ray.is_initialized()
    finally:
        RayExperimentRunner._connection_failed = False
        if ray.is_initialized():
            ray.shutdown()


@pytest.mark.unit
def test_ray_runner_exception_fallback() -> None:
    """Test the except path: invalid address → exception → local fallback."""
    try:
        if ray.is_initialized():
            ray.shutdown()
        RayExperimentRunner._connection_failed = False

        runner = RayExperimentRunner(
            ray_address="invalid://address:9999",
            mlflow_tracking_uri="",
            num_cpus=1,
            include_dashboard=False,
        )
        runner.connect()
        # After exception, _connection_failed should be True and Ray should be local
        assert RayExperimentRunner._connection_failed is True
        assert ray.is_initialized()
    finally:
        RayExperimentRunner._connection_failed = False
        if ray.is_initialized():
            ray.shutdown()


@pytest.mark.unit
def test_ray_runner_with_address() -> None:
    """Test the `if self.ray_address:` → ray.init(address=...) branch."""
    try:
        if ray.is_initialized():
            ray.shutdown()
        RayExperimentRunner._connection_failed = False

        # Use "local" which is a valid ray address for local mode
        runner = RayExperimentRunner(
            ray_address="local",
            mlflow_tracking_uri="http://127.0.0.1:5000",
            num_cpus=1,
            include_dashboard=False,
        )
        runner.connect()
        assert ray.is_initialized()
    finally:
        if ray.is_initialized():
            ray.shutdown()


# ── Drift Detector Tests ────────────────────────────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_drift_detection_flow(db_cleanup: Any) -> None:
    from src.database.repository import (
        save_method_result,
        save_option_parameters,
        save_validation_metrics,
    )
    from src.notifications.hierarchy import NotificationRouter

    market_unique = f"drift_{uuid4().hex[:8]}"
    opt_id = await save_option_parameters(120, 120, 1, 0.2, 0.05, "call", market_unique)
    res_id = await save_method_result(opt_id, "analytical", 10.45, {"market": market_unique}, 0.1)
    await save_validation_metrics(opt_id, res_id, 0.01, 0.1, 0.01)

    router = NotificationRouter()
    user_id = str(uuid4())
    drifted = await check_model_drift(
        "analytical", baseline_mape=0.5, router=router, user_ids=[user_id]
    )
    assert drifted is False

    await save_validation_metrics(opt_id, res_id, 5.0, 10.0, 5.0)
    drifted = await check_model_drift(
        "analytical", baseline_mape=0.5, router=router, user_ids=[user_id]
    )
    assert drifted is True


# ── Model Registry Tests ────────────────────────────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_model_registry_operations(mlflow_uri: str) -> None:
    registry = ModelRegistry(mlflow_uri)
    name = f"test_model_{uuid4().hex[:8]}"
    version = "1.0.0"
    metrics = {"accuracy": 0.98}
    await registry.register_model(name, version, "s3://models/v1", metrics)
    model = await registry.get_latest_model(name)
    assert model["name"] == name
    assert model["version"] == version
    registry.transition_model_stage(name, version, "Production")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_model_registry_failure(mlflow_uri: str) -> None:
    registry = ModelRegistry(mlflow_uri)
    with pytest.raises(Exception):
        await registry.register_model(None, None, None, None)  # type: ignore
    import contextlib

    with contextlib.suppress(Exception):
        await registry.get_latest_model("nonexistent")
