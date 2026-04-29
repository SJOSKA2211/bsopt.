"""Exhaustive integration tests for NeonDB repository operations."""

from __future__ import annotations

from uuid import UUID
import pytest
from datetime import date
from src.database.repository import (
    save_method_result,
    save_option_parameters,
    get_latest_metrics,
    query_recent_mape,
    save_scrape_run,
    save_model_metadata,
    get_latest_model,
    save_notification,
)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_repository_full_lifecycle(db_cleanup):
    # 1. Save Option Params
    opt_id = await save_option_parameters(100.0, 100.0, 1.0, 0.2, 0.05, "call")
    assert isinstance(opt_id, UUID)
    
    # 2. Save Method Result
    res_id = await save_method_result(opt_id, "analytical", 10.45, {"d1": 0.5}, 0.01)
    assert isinstance(res_id, UUID)
    
    # 3. Get Latest Metrics
    metrics = await get_latest_metrics()
    assert len(metrics) >= 1
    assert any(m["method_type"] == "analytical" for m in metrics)
    
    # 4. Query Recent MAPE (should be 0.0 if no validation_metrics rows)
    mape = await query_recent_mape("analytical")
    assert mape == 0.0
    
    # 5. Save Scrape Run
    run_id = await save_scrape_run("spy", "SpyScraper", 10, 0)
    assert isinstance(run_id, UUID)
    
    # 6. Save Model Metadata
    await save_model_metadata("test_model", "v1", "s3://path", {"mape": 0.01})
    
    # 7. Get Latest Model
    model = await get_latest_model("test_model")
    assert model["version"] == "v1"
    
    # 8. Save Notification
    await save_notification("user1", "Title", "Body", "info")
