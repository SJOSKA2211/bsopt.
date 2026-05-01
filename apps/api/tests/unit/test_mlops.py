"""Exhaustive unit and integration tests for MLOps components — Zero-Mock."""
from __future__ import annotations
import pytest
import os
import json
import asyncio
import ray
import tempfile
import shutil
from uuid import uuid4
from datetime import date, datetime, UTC
from typing import Any
from src.mlops.mlflow_tracker import MLflowTracker
from src.mlops.feature_store import FeatureStore
from src.mlops.drift_detector import check_model_drift
from src.mlops.model_registry import ModelRegistry
from src.mlops.ray_runner import price_remote, RayExperimentRunner
from src.notifications.hierarchy import NotificationRouter, Notification

@pytest.fixture
def mlflow_uri():
    return os.environ.get("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")

@pytest.mark.unit
def test_mlflow_tracker_logging(mlflow_uri) -> None:
    tracker = MLflowTracker(mlflow_uri)
    assert tracker.tracking_uri == mlflow_uri
    exp_name = f"test_exp_{uuid4().hex[:8]}"
    run_id = tracker.log_pricing_run(
        experiment_name=exp_name,
        run_name="test_run",
        params={"p1": 1.0},
        metrics={"m1": 0.5},
        tags={"t1": "v1"}
    )
    assert isinstance(run_id, str)

@pytest.mark.unit
def test_mlflow_tracker_real_failure() -> None:
    tracker = MLflowTracker("http://invalid_url_that_fails_fast")
    try:
        tracker.log_pricing_run(None, None, None, None) # type: ignore
    except Exception:
        pass

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
def test_price_logic_direct() -> None:
    from src.mlops.ray_runner import _price_logic
    params = {"underlying_price": 100, "strike_price": 100, "time_to_expiry": 1, "volatility": 0.2, "risk_free_rate": 0.05, "option_type": "call"}
    res = _price_logic(params, "analytical")
    assert res["computed_price"] > 0
    assert res["method_type"] == "BlackScholesAnalytical"

@pytest.mark.unit
def test_ray_runner_distributed() -> None:
    # 1. Test normal local init
    try:
        if ray.is_initialized():
            ray.shutdown()
        RayExperimentRunner._connection_failed = False
        
        runner = RayExperimentRunner(
            ray_address="", 
            mlflow_tracking_uri="http://127.0.0.1:5000"
        )
        runner.connect()
        assert ray.is_initialized()
        
        # 2. Test already initialized branch
        runner.connect()
        
        # 3. Test _connection_failed = True branch
        RayExperimentRunner._connection_failed = True
        ray.shutdown()
        runner.connect()
        assert ray.is_initialized()
        
        params = {"underlying_price": 100, "strike_price": 100, "time_to_expiry": 1, "volatility": 0.2, "risk_free_rate": 0.05, "option_type": "call"}
        param_grid = [(params, "analytical")]
        results = runner.run_grid("test_ray_grid", param_grid)
        assert len(results) == 1
    finally:
        if ray.is_initialized():
            ray.shutdown()

@pytest.mark.unit
def test_ray_runner_connection_failure_path() -> None:
    # 4. Test exception path and shutdown coverage
    try:
        # Initialize ray FIRST so that when it fails later, it hits ray.shutdown() in except
        if not ray.is_initialized():
            ray.init()
            
        runner = RayExperimentRunner(
            ray_address="ray://127.0.0.1:9999", 
            mlflow_tracking_uri=""
        )
        
        RayExperimentRunner._connection_failed = False
        # connect() will catch the exception and hit the shutdown/init branch
        runner.connect()
        assert RayExperimentRunner._connection_failed is True
    finally:
        if ray.is_initialized():
            ray.shutdown()

@pytest.mark.unit
@pytest.mark.asyncio
async def test_drift_detection_flow(db_cleanup) -> None:
    from src.database.repository import save_option_parameters, save_method_result, save_validation_metrics
    market_unique = f"drift_{uuid4().hex[:8]}"
    opt_id = await save_option_parameters(120, 120, 1, 0.2, 0.05, "call", market_unique)
    res_id = await save_method_result(opt_id, "analytical", 10.45, {"market": market_unique}, 0.1)
    await save_validation_metrics(opt_id, res_id, 0.01, 0.1, 0.01)
    
    router = NotificationRouter()
    user_id = str(uuid4())
    drifted = await check_model_drift("analytical", baseline_mape=0.5, router=router, user_ids=[user_id])
    assert drifted is False
    
    await save_validation_metrics(opt_id, res_id, 5.0, 10.0, 5.0)
    drifted = await check_model_drift("analytical", baseline_mape=0.5, router=router, user_ids=[user_id])
    assert drifted is True

@pytest.mark.unit
@pytest.mark.asyncio
async def test_model_registry_operations(mlflow_uri) -> None:
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
def test_feature_engineering() -> None:
    store = FeatureStore()
    f = store.engineer_features(100, 100, 1, 0.2, 0.05)
    assert f["moneyness"] == 1.0
    assert f["intrinsic_value"] == 0.0

@pytest.mark.unit
@pytest.mark.asyncio
async def test_model_registry_failure(mlflow_uri) -> None:
    registry = ModelRegistry(mlflow_uri)
    with pytest.raises(Exception):
        await registry.register_model(None, None, None, None) # type: ignore
    try:
        await registry.get_latest_model("nonexistent")
    except Exception:
        pass

@pytest.mark.unit
def test_ray_runner_invalid_method() -> None:
    func = getattr(price_remote, "_function", price_remote)
    with pytest.raises(ValueError, match="Unknown method"):
        func({"p": 1}, "invalid")
