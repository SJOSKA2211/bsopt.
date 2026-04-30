"""Unit/Integration tests for OptionsPipeline — Phase 5."""
from __future__ import annotations
import pytest
import csv
from pathlib import Path
from src.data.pipeline import OptionsPipeline
from src.database.neon_client import acquire

@pytest.mark.asyncio
async def test_options_pipeline_run(tmp_path):
    # 1. Create a dummy CSV file
    csv_path = tmp_path / "spy_options.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "underlying_price", "strike_price", "time_to_expiry", 
            "volatility", "risk_free_rate", "option_type", "bid", "ask"
        ])
        writer.writeheader()
        writer.writerow({
            "underlying_price": 100.0,
            "strike_price": 100.0,
            "time_to_expiry": 1.0,
            "volatility": 0.2,
            "risk_free_rate": 0.05,
            "option_type": "call",
            "bid": 10.4,
            "ask": 10.5
        })

    # 2. Run the pipeline
    pipeline = OptionsPipeline(market="spy")
    count = await pipeline.run(str(csv_path))
    
    assert count == 1
    
    # 3. Verify in NeonDB (Zero-Mock)
    async with acquire() as conn:
        row = await conn.fetchrow("SELECT COUNT(*) FROM market_data")
        assert row["count"] >= 1
