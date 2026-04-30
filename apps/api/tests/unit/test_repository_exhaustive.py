"""Exhaustive unit tests for repository methods."""

from __future__ import annotations

import pytest
from uuid import UUID, uuid4
from datetime import date
from src.database.repository import (
    save_market_data,
    get_option_parameters,
    get_all_experiments,
    get_experiment_by_id,
    save_validation_metrics,
    save_scrape_error,
    get_recent_scrape_runs,
    get_unread_notifications,
    mark_notification_read,
    save_feature_snapshot,
    get_latest_feature_snapshot,
    save_option_parameters,
    save_method_result,
    save_scrape_run,
    save_notification
)

@pytest.mark.unit
@pytest.mark.asyncio
async def test_repository_exhaustive(db_cleanup: None) -> None:
    # 1. Option Params
    opt_id = await save_option_parameters(100.0, 100.0, 1.0, 0.2, 0.05, "call", "spy")
    assert isinstance(opt_id, UUID)
    
    # 2. Market Data
    await save_market_data(opt_id, date.today(), 10.0, 10.5, 1000, 10000, "spy")
    
    # 3. Option Params query
    params = await get_option_parameters(opt_id)
    assert params is not None
    assert params["underlying_price"] == 100.0
    
    # 4. Method Results & Validation
    res_id = await save_method_result(opt_id, "analytical", 10.45, {}, 0.01)
    await save_validation_metrics(opt_id, res_id, 0.01, 0.001, 0.02)
    
    # 5. Scrapers
    run_id = await save_scrape_run("spy", "SpyScraper", 10, 0)
    await save_scrape_error(run_id, "http://err", "Error", "Message", 1)
    runs = await get_recent_scrape_runs(5)
    assert len(runs) >= 1
    
    # 6. Notifications
    await save_notification("user1", "T", "B", "info")
    notifs = await get_unread_notifications("user1")
    assert len(notifs) >= 1
    await mark_notification_read(notifs[0]["id"])
    
    # 7. Feature Snapshots
    await save_feature_snapshot(date.today(), {"f1": 1.0}, 10)
    snapshot = await get_latest_feature_snapshot()
    assert snapshot is not None
    
    # 8. Experiments
    experiments = await get_all_experiments()
    if experiments:
        exp_id = experiments[0]["id"]
        exp = await get_experiment_by_id(exp_id)
        assert exp is not None

@pytest.mark.unit
@pytest.mark.asyncio
async def test_repository_misses() -> None:
    assert await get_option_parameters(uuid4()) is None
    assert await get_experiment_by_id(uuid4()) is None
