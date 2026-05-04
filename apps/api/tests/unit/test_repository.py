"""Unit tests for database repository — Zero-Mock."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

import pytest

from src.database.repository import (
    get_all_experiments,
    get_experiment_by_id,
    get_latest_feature_snapshot,
    get_latest_metrics,
    get_latest_model,
    get_option_parameters,
    get_recent_scrape_runs,
    get_unread_notifications,
    get_user_by_email,
    get_user_by_id,
    get_user_push_subscriptions,
    mark_notification_read,
    query_experiments,
    query_market_data,
    query_notifications,
    query_recent_mape,
    save_audit_log,
    save_feature_snapshot,
    save_market_data,
    save_method_result,
    save_model_metadata,
    save_notification,
    save_option_parameters,
    save_scrape_error,
    save_scrape_run,
    save_user,
    save_user_push_subscription,
    update_scrape_run,
    save_validation_metrics,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_user_repository_operations(db_cleanup: Any) -> None:
    user_id = uuid4()
    email = "repo_test@example.com"
    
    # Save and Get
    await save_user(user_id, email, "Repo Test", "researcher")
    u1 = await get_user_by_id(user_id)
    assert u1["email"] == email
    
    u2 = await get_user_by_email(email)
    assert str(u2["id"]) == str(user_id)
    
    # Non-existent
    assert await get_user_by_id(uuid4()) is None
    assert await get_user_by_email("none@example.com") is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_user_push_subscriptions(db_cleanup: Any) -> None:
    user_id = str(uuid4())
    sub1 = {"endpoint": "e1"}
    sub2 = {"endpoint": "e2"}
    
    await save_user_push_subscription(user_id, sub1)
    subs = await get_user_push_subscriptions(user_id)
    # If asyncpg decodes it, it's a dict. If not, it's a string.
    # We'll handle both in the test to avoid flakiness, but the repo should be consistent.
    processed_subs = [json.loads(s) if isinstance(s, str) else s for s in subs]
    assert sub1 in processed_subs
    
    # Duplicate sub
    await save_user_push_subscription(user_id, sub1)
    subs = await get_user_push_subscriptions(user_id)
    processed_subs = [json.loads(s) if isinstance(s, str) else s for s in subs]
    assert len(processed_subs) == 1
    
    await save_user_push_subscription(user_id, sub2)
    subs = await get_user_push_subscriptions(user_id)
    assert sub1 in subs
    assert sub2 in subs


@pytest.mark.unit
@pytest.mark.asyncio
async def test_market_and_option_parameters(db_cleanup: Any) -> None:
    opt_id = await save_option_parameters(
        150.0, 150.0, 0.5, 0.25, 0.04, option_type="call", market_source="test_source"
    )
    assert isinstance(opt_id, str)
    
    # Get params
    params = await get_option_parameters(opt_id)
    assert params["underlying_price"] == 150.0
    
    # Save market data
    await save_market_data(
        opt_id, date.today(), 10.0, 11.0, 100, 500, data_source="test_source"
    )
    data = await query_market_data(opt_id)
    assert len(data) == 1
    assert data[0]["bid"] == 10.0
    
    # Branch: market_source in query_market_data
    data_ms = await query_market_data(opt_id, market_source="test_source")
    assert len(data_ms) == 1
    
    # Non-existent
    assert await get_option_parameters(uuid4()) is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_method_results_and_metrics(db_cleanup: Any) -> None:
    opt_id = await save_option_parameters(
        100.0, 100.0, 1.0, 0.2, 0.05, option_type="put", market_source="m1"
    )
    res_id = await save_method_result(
        opt_id, "analytical", 5.5, {"p": 1}, exec_seconds=0.01
    )
    assert isinstance(res_id, str)
    
    # Query experiments
    exps = await query_experiments(method_type="analytical")
    assert len(exps) == 1
    assert exps[0]["computed_price"] == 5.5
    
    # Branch: method_type is None
    all_exps_q = await query_experiments(method_type=None)
    assert len(all_exps_q) >= 1
    
    # Branch: market_source
    m_exps = await query_experiments(market_source="m1")
    assert len(m_exps) >= 1
    
    # Branch: cursor
    c_exps = await query_experiments(cursor=datetime.now(UTC))
    assert len(c_exps) >= 1
    
    # Latest metrics
    metrics = await get_latest_metrics()
    assert len(metrics) >= 1
    
    # MAPE query
    await save_validation_metrics(opt_id, res_id, 0.1, 0.02, 0.1)
    mape = await query_recent_mape("analytical")
    assert mape == 0.02


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scrape_runs_and_errors(db_cleanup: Any) -> None:
    # Test branch: started_at is NOT None
    now = datetime.now(UTC)
    run_id = await save_scrape_run("NSE", "NseScraper", started_at=now)
    assert isinstance(run_id, str)
    
    # Test branch: started_at IS None
    run_id2 = await save_scrape_run("CBOE", "CboeScraper")
    assert isinstance(run_id2, str)
    
    await update_scrape_run(run_id, datetime.now(UTC), 10, "success")
    runs = await get_recent_scrape_runs()
    # Find the specific run
    run = next(r for r in runs if str(r["id"]) == str(run_id))
    assert run["status"] == "success"
    
    await save_scrape_error(run_id, "http://fail", "Timeout", "Msg", 2)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_repository_empty_results(db_cleanup: Any) -> None:
    """Cover the 'if not row' / 'if not exps' branches."""
    assert await get_latest_metrics() == []
    assert await get_all_experiments() == []
    assert await query_experiments(method_type="none") == []
    assert await query_market_data(None) == []
    assert await query_market_data(uuid4()) == []
    assert await get_unread_notifications(uuid4()) == []
    assert await query_notifications(uuid4()) == []
    assert await get_user_push_subscriptions(str(uuid4())) == []
    assert await get_experiment_by_id(uuid4()) is None
    assert await get_recent_scrape_runs() == []
    assert await get_latest_feature_snapshot() is None
    assert await query_recent_mape("none") == 0.0
    
    # save_user_push_subscription for non-existent user
    non_user_id = str(uuid4())
    await save_user_push_subscription(non_user_id, {"endpoint": "new"})
    subs = await get_user_push_subscriptions(non_user_id)
    assert len(subs) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_audit_logs(db_cleanup: Any) -> None:
    await save_audit_log(uuid4(), "step1", "started", 0, "starting")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_notifications_repository(db_cleanup: Any, test_user: dict[str, Any]) -> None:
    user_id = test_user["id"]
    nid = await save_notification(user_id, "Title", "Body", "warning")
    
    unread = await get_unread_notifications(user_id)
    assert len(unread) == 1
    assert str(unread[0]["id"]) == str(nid)
    
    await mark_notification_read(nid)
    unread2 = await get_unread_notifications(user_id)
    assert len(unread2) == 0
    
    # Query recent
    all_notifs = await query_notifications(user_id)
    assert len(all_notifs) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ml_experiments_registry(db_cleanup: Any) -> None:
    name = "test_model"
    await save_model_metadata(name, "v1", "s3://", {"m": 0.9})
    
    model = await get_latest_model(name)
    assert model["name"] == name
    assert model["version"] == "v1"
    
    all_exps = await get_all_experiments()
    assert len(all_exps) == 1
    
    eid = all_exps[0]["id"]
    exp = await get_experiment_by_id(eid)
    assert str(exp["id"]) == str(eid)
    
    assert await get_experiment_by_id(uuid4()) is None
    assert await get_latest_model("unknown") == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_feature_snapshots_repository(db_cleanup: Any) -> None:
    d = date(2024, 1, 1)
    await save_feature_snapshot(d, {"f1": 1}, 10)
    
    snap = await get_latest_feature_snapshot()
    assert snap["snapshot_date"] == d
    assert snap["option_count"] == 10
    
    # Upsert
    await save_feature_snapshot(d, {"f1": 2}, 20)
    snap2 = await get_latest_feature_snapshot()
    assert snap2["option_count"] == 20
