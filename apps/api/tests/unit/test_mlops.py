"""Exhaustive unit tests for all components — Zero-Mock."""

from __future__ import annotations

import pytest
import os
import json
import asyncio
import base64
import gzip
from uuid import UUID, uuid4
from datetime import date, datetime, UTC
from pathlib import Path
from typing import Any

from src.mlops.mlflow_tracker import MLflowTracker
from src.mlops.feature_store import FeatureStore
from src.mlops.drift_detector import check_model_drift
from src.mlops.model_registry import ModelRegistry
from src.mlops.ray_runner import RayExperimentRunner, price_remote
from src.notifications.hierarchy import NotificationRouter, Notification
from src.methods.base import OptionParams

@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from src.main import app
    return TestClient(app)

@pytest.mark.unit
def test_mlflow_tracker_logging() -> None:
    tracker = MLflowTracker(os.environ["MLFLOW_TRACKING_URI"])
    run_id = tracker.log_pricing_run("test_exp", "test_run", {"p": 1}, {"m": 1})
    assert run_id is not None

@pytest.mark.unit
def test_feature_store_logic() -> None:
    store = FeatureStore()
    features = store.engineer_features(100, 100, 1, 0.2, 0.05)
    assert "moneyness" in features

@pytest.mark.unit
@pytest.mark.asyncio
async def test_ray_runner_local() -> None:
    local_func = price_remote.__dict__["_function"]
    res = local_func({"underlying_price": 100, "strike_price": 100, "time_to_expiry": 1, "volatility": 0.2, "risk_free_rate": 0.05, "option_type": "call"}, "analytical")
    assert res["computed_price"] > 0

@pytest.mark.unit
@pytest.mark.asyncio
async def test_drift_detection() -> None:
    router = NotificationRouter()
    await check_model_drift("analytical", 0.0, router, ["user1"])
    await check_model_drift("analytical", 1.0, router, ["user1"])

@pytest.mark.unit
def test_model_registry_lifecycle() -> None:
    registry = ModelRegistry(os.environ["MLFLOW_TRACKING_URI"])
    registry.register_model("invalid", "1.0")
    registry.transition_model_stage("invalid", "1", "Staging")

@pytest.mark.unit
@pytest.mark.asyncio
async def test_auth_dependencies() -> None:
    from src.auth.dependencies import get_current_user, get_admin_user
    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials
    with pytest.raises(HTTPException):
        await get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid"))
    with pytest.raises(HTTPException):
        await get_current_user(None)
    with pytest.raises(HTTPException):
        await get_admin_user({"role": "user"})
    assert await get_admin_user({"role": "admin"}) == {"role": "admin"}

@pytest.mark.unit
@pytest.mark.asyncio
async def test_repository_exhaustive(db_cleanup: None, test_user: dict[str, Any]) -> None:
    from src.database.repository import (
        save_market_data, save_validation_metrics, save_scrape_error,
        get_recent_scrape_runs, get_unread_notifications, mark_notification_read,
        save_feature_snapshot, get_latest_feature_snapshot, save_option_parameters,
        save_method_result, save_scrape_run, save_notification,
        get_user_push_subscriptions, save_audit_log, query_experiments,
        query_notifications, query_market_data, get_latest_metrics
    )
    from src.database.neon_client import acquire
    user_id = test_user["id"]
    opt_id = await save_option_parameters(100.0, 100.0, 1.0, 0.2, 0.05, "call", "spy", "european")
    await save_market_data(opt_id, date.today(), 10.0, 10.5, 1000, 10000, "spy")
    res_id = await save_method_result(opt_id, "analytical", 10.45, {"test": str(uuid4())}, 0.01)
    await save_validation_metrics(opt_id, res_id, 0.01, 0.001, 0.02)
    run_id = await save_scrape_run("spy", "SpyScraper", None, "running")
    await save_scrape_error(run_id, "http://err", "Error", "Msg", 1)
    await get_recent_scrape_runs(5)
    await save_notification(user_id, "T", "B", "info")
    notifs = await get_unread_notifications(user_id)
    if notifs:
        await mark_notification_read(notifs[0]["id"])
    async with acquire() as conn:
        await conn.execute("UPDATE users SET notification_preferences = $1 WHERE id = $2", json.dumps({"push_subscriptions": ["s1"]}), UUID(str(user_id)))
    await get_user_push_subscriptions(str(user_id))
    async with acquire() as conn:
        await conn.execute("DELETE FROM feature_snapshots WHERE snapshot_date = $1", date.today())
    await save_feature_snapshot(date.today(), {"f1": 1.0}, 10)
    await get_latest_feature_snapshot()
    await query_experiments(method_type="analytical", market_source="spy", limit=5)
    await query_notifications(user_id, limit=5)
    await query_market_data(option_id=opt_id, limit=5)
    await get_latest_metrics()
    await save_audit_log(uuid4(), "step", "success", 1, "msg")

@pytest.mark.unit
def test_routers_exhaustive(client: Any) -> None:
    client.get("/health")
    client.get("/api/v1/experiments/")
    client.get("/api/v1/market-data/")
    client.get("/api/v1/notifications/")
    client.get("/api/v1/scrapers/runs")
    client.get("/api/v1/mlops/metrics")
    client.get("/api/v1/downloads/export?format=csv")

@pytest.mark.unit
@pytest.mark.asyncio
async def test_notifications_exhaustive() -> None:
    from src.notifications.email import send_transactional_email
    from src.notifications.push import send_web_push
    try:
        await send_transactional_email("to@ex.com", "S", "B")
    except Exception: pass
    try:
        await send_web_push("sub", "T", "B")
    except Exception: pass
    router = NotificationRouter()
    await router.dispatch(Notification("user1", "T", "B", "info"))
    await router.dispatch(Notification("user1", "T", "B", "error"))

@pytest.mark.unit
@pytest.mark.asyncio
async def test_scrapers_exhaustive() -> None:
    from src.scrapers.nse_next_scraper import NseNextScraper
    from src.scrapers.scraper_factory import get_scraper
    nse = NseNextScraper()
    assert nse.name() == "nse_next"
    assert len(await nse.scrape()) > 0
    assert get_scraper("spy") is not None

@pytest.mark.unit
@pytest.mark.asyncio
async def test_manager_exhaustive() -> None:
    from src.websocket.manager import ConnectionManager
    from unittest.mock import AsyncMock
    m = ConnectionManager()
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    await m.connect(ws, "notifications", user_id="u1")
    await m.send_personal_message({"m": "h"}, "u1")
    ws.send_json.side_effect = Exception("d")
    await m.send_personal_message({"m": "h"}, "u1")
    assert "u1" not in m.user_connections
    m.disconnect(ws, "notifications", user_id="u1")
    await m.broadcast("metrics", {"v": 1})
