"""Integration tests for data ingestion pipelines."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.data.pipeline import OptionsPipeline


@pytest.mark.integration
@pytest.mark.asyncio
async def test_options_pipeline_csv_ingestion() -> None:
    """Verify that the pipeline processes a CSV file and saves to NeonDB."""
    # Create a dummy CSV file
    csv_content = (
        "underlying_price,strike_price,time_to_expiry,volatility,risk_free_rate,option_type,trade_date,bid,ask\n"
        "100.0,100.0,1.0,0.2,0.05,call,2024-01-01,10.0,11.0\n"
    )

    with tempfile.NamedTemporaryFile(
        encoding="utf-8", mode="w", suffix=".csv", delete=False
    ) as tmp:
        tmp.write(csv_content)
        tmp_path = tmp.name

    try:
        pipeline = OptionsPipeline(market="spy")
        processed_count = await pipeline.run(tmp_path)
        assert processed_count == 1
    finally:
        if Path(tmp_path).exists():
            Path(tmp_path).unlink()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_options_pipeline_gzip_ingestion() -> None:
    """Verify that the pipeline processes a GZipped CSV file."""
    import gzip

    csv_content = (
        "underlying_price,strike_price,time_to_expiry,volatility,risk_free_rate,option_type,trade_date,bid,ask\n"
        "100.0,105.0,0.5,0.25,0.03,put,2024-02-01,5.0,5.5\n"
    )

    with tempfile.NamedTemporaryFile(suffix=".csv.gz", delete=False) as tmp:
        with gzip.open(tmp.name, "wt", encoding="utf-8") as f:
            f.write(csv_content)
        tmp_path = tmp.name

    try:
        pipeline = OptionsPipeline(market="nse")
        processed_count = await pipeline.run(tmp_path)
        assert processed_count == 1
    finally:
        if Path(tmp_path).exists():
            Path(tmp_path).unlink()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_options_pipeline_json_ingestion() -> None:
    """Verify that the pipeline processes a JSON file."""
    import json

    data = [
        {
            "underlying_price": 110.0,
            "strike_price": 110.0,
            "time_to_expiry": 0.25,
            "volatility": 0.3,
            "risk_free_rate": 0.04,
            "option_type": "call",
            "trade_date": "2024-03-01",
            "bid": 8.0,
            "ask": 8.5,
        }
    ]

    with tempfile.NamedTemporaryFile(
        encoding="utf-8", mode="w", suffix=".json", delete=False
    ) as tmp:
        json.dump(data, tmp)
        tmp_path = tmp.name

    try:
        pipeline = OptionsPipeline(market="spy")
        processed_count = await pipeline.run(tmp_path)
        assert processed_count == 1
    finally:
        if Path(tmp_path).exists():
            Path(tmp_path).unlink()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_options_pipeline_invalid_file() -> None:
    """Verify that the pipeline handles corrupted or invalid files gracefully."""
    with tempfile.NamedTemporaryFile(
        encoding="utf-8", mode="w", suffix=".csv", delete=False
    ) as tmp:
        tmp.write("not,a,valid,csv\ncorrupted,data")
        tmp_path = tmp.name

    try:
        pipeline = OptionsPipeline(market="spy")
        processed_count = await pipeline.run(tmp_path)
        # Should skip rows that fail validation/transformation
        assert processed_count == 0
    finally:
        if Path(tmp_path).exists():
            Path(tmp_path).unlink()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_options_pipeline_json_gz_ingestion() -> None:
    """Verify that the pipeline processes a GZipped JSON file."""
    import gzip
    import json

    data = {
        "underlying_price": 100.0,
        "strike_price": 100.0,
        "time_to_expiry": 1.0,
        "volatility": 0.2,
        "risk_free_rate": 0.05,
        "option_type": "call",
    }

    with tempfile.NamedTemporaryFile(suffix=".json.gz", delete=False) as tmp:
        with gzip.open(tmp.name, "wt", encoding="utf-8") as f:
            json.dump(data, f)
        tmp_path = tmp.name

    try:
        pipeline = OptionsPipeline(market="spy")
        processed_count = await pipeline.run(tmp_path)
        assert processed_count == 1
    finally:
        if Path(tmp_path).exists():
            Path(tmp_path).unlink()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_options_pipeline_unreadable_file() -> None:
    """Verify that the pipeline handles unreadable files gracefully."""
    # A path that definitely doesn't exist
    pipeline = OptionsPipeline(market="spy")
    processed_count = await pipeline.run("/tmp/non_existent_file_bsopt.csv")
    assert processed_count == 0
