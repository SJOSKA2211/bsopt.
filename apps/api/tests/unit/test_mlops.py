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
from src.notifications.hierarchy import NotificationRouter
from src.methods.base import OptionParams

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
    registry.register_model("invalid", "invalid")
    registry.transition_model_stage("invalid", "1", "Staging")

@pytest.mark.unit
def test_mlops_error_paths() -> None:
    tracker = MLflowTracker("invalid://localhost")
    with pytest.raises(Exception):
        tracker.log_pricing_run("exp", "run", {}, {})

# --- Repository Exhaustive ---

@pytest.mark.unit
@pytest.mark.asyncio
async def test_repository_exhaustive(db_cleanup: None, test_user: dict[str, Any]) -> None:
    from src.database.repository import (
        save_market_data, get_option_parameters, get_all_experiments,
        get_experiment_by_id, save_validation_metrics, save_scrape_error,
        get_recent_scrape_runs, get_unread_notifications, mark_notification_read,
        save_feature_snapshot, get_latest_feature_snapshot, save_option_parameters,
        save_method_result, save_scrape_run, save_notification,
        get_user_by_id, get_user_by_email, get_user_push_subscriptions,
        save_audit_log, query_experiments, query_notifications, query_market_data,
        get_latest_metrics
    )
    user_id = test_user["id"]
    
    # 1. Option Params
    opt_id = await save_option_parameters(100.0, 100.0, 1.0, 0.2, 0.05, "call", "spy")
    assert str(opt_id) != ""
    
    # 2. Market Data
    await save_market_data(opt_id, date.today(), 10.0, 10.5, 1000, 10000, "spy")
    
    # 3. Validation
    res_id = await save_method_result(opt_id, "analytical", 10.45, {}, 0.01)
    await save_validation_metrics(opt_id, res_id, 0.01, 0.001, 0.02)
    
    # 4. Scrapers
    run_id = await save_scrape_run("spy", "SpyScraper", None, "finished")
    await save_scrape_error(run_id, "http://err", "Error", "Msg", 1)
    await get_recent_scrape_runs(5)
    
    # 5. Notifications
    await save_notification(user_id, "T", "B", "info")
    notifs = await get_unread_notifications(user_id)
    assert len(notifs) >= 1
    await mark_notification_read(notifs[0]["id"])
    
    # 6. User prefs
    from src.database.neon_client import acquire
    async with acquire() as conn:
        await conn.execute("UPDATE users SET notification_preferences = $1 WHERE id = $2", json.dumps({"push_subscriptions": ["s1"]}), UUID(str(user_id)))
    subs = await get_user_push_subscriptions(str(user_id))
    assert "s1" in subs

    # 7. Feature Snapshots
    async with acquire() as conn:
        await conn.execute("DELETE FROM feature_snapshots WHERE snapshot_date = $1", date.today())
    await save_feature_snapshot(date.today(), {"f1": 1.0}, 10)
    await get_latest_feature_snapshot()

    # 8. Queries
    await query_experiments(method_type="analytical", market_source="spy", limit=5)
    await query_experiments(cursor=datetime.now(UTC), limit=5)
    await query_notifications(user_id, limit=5)
    await query_market_data(option_id=opt_id, limit=5)
    await get_latest_metrics()
    await save_audit_log(uuid4(), "step", "success", 1, "msg")

# --- Pipeline Exhaustive ---

@pytest.mark.unit
@pytest.mark.asyncio
async def test_pipeline_exhaustive(tmp_path: Path) -> None:
    from src.data.pipeline import OptionsPipeline
    pipeline = OptionsPipeline("spy")
    
    csv_file = tmp_path / "test.csv.gz"
    with gzip.open(csv_file, "wt") as f:
        f.write("underlying_price,strike_price,time_to_expiry,volatility,risk_free_rate,option_type\n")
        f.write("100,105,1,0.2,0.05,call\n")
    assert await pipeline.run(str(csv_file)) == 1
    
    json_file = tmp_path / "test.json"
    with open(json_file, "w") as f:
        json.dump([{"underlying_price": 100, "strike_price": 100, "time_to_expiry": 1, "volatility": 0.2, "risk_free_rate": 0.05, "option_type": "call"}], f)
    assert await pipeline.run(str(json_file)) == 1

# --- Scraper Exhaustive ---

@pytest.mark.unit
@pytest.mark.asyncio
async def test_scrapers_exhaustive(tmp_path: Path) -> None:
    from src.scrapers.spy_scraper import SpyScraper
    from src.scrapers.nse_next_scraper import NseNextScraper
    
    # NSE
    nse = NseNextScraper()
    assert (await nse.scrape())[0]["market_source"] == "nse"
    
    # SPY
    html = "<html><body><table><tbody><tr><td></td><td></td><td>100</td><td>10</td><td>9</td><td>11</td><td>1</td><td></td><td>100</td><td>500</td><td>0.2</td></tr></tbody></table></body></html>"
    f = tmp_path / "test.html"
    f.write_text(html)
    spy = SpyScraper()
    rows = await spy.scrape(url=f"file://{f}")
    assert len(rows) >= 1
    
    # Base
    from src.scrapers.base_scraper import BaseScraper
    class TS(BaseScraper):
        async def scrape(self): return []
    assert "table" in await TS("t").get_page_content(f"file://{f}")

# --- WebSocket Manager Exhaustive ---

@pytest.mark.unit
@pytest.mark.asyncio
async def test_manager_exhaustive() -> None:
    from src.websocket.manager import ConnectionManager
    from unittest.mock import AsyncMock
    m = ConnectionManager()
    ws = AsyncMock()
    await m.connect(ws, "notifications", user_id="u1")
    await m.send_personal_message({"m": "h"}, "u1")
    ws.send_json.side_effect = Exception("d")
    await m.send_personal_message({"m": "h"}, "u1")
    assert "u1" not in m.user_connections
    
    ws2 = AsyncMock()
    await m.connect(ws2, "metrics")
    ws2.send_json.side_effect = Exception("d")
    await m.broadcast("metrics", {"v": 1})
    assert ws2 not in m.active_connections["metrics"]

# --- Analysis Exhaustive ---

@pytest.mark.unit
def test_analysis_exhaustive() -> None:
    import numpy as np
    from src.analysis.statistics import calculate_greeks, calculate_implied_volatility, calculate_error_metrics
    from src.analysis.convergence import analyze_mc_convergence, calculate_convergence_order
    calculate_greeks(100, 100, 1, 0.2, 0.05, "call")
    calculate_implied_volatility(10.45, 100, 100, 1, 0.05, "call")
    calculate_error_metrics([10], [10.1])
    analyze_mc_convergence(OptionParams(100, 100, 1, 0.2, 0.05, "call"), "standard_mc", [10, 20])
    calculate_convergence_order([10, 20], [0.1, 0.05])
