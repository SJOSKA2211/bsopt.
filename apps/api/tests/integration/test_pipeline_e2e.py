"""Integration tests for the data ingestion pipeline."""

from __future__ import annotations
import csv
import gzip
import json
import pytest
from pathlib import Path
from src.data.pipeline import OptionsPipeline

@pytest.fixture
def pipeline() -> OptionsPipeline:
    return OptionsPipeline(market="spy")

@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    return tmp_path

@pytest.mark.asyncio
async def test_pipeline_csv_processing(pipeline: OptionsPipeline, temp_dir: Path, db_cleanup) -> None:
    """Test processing a standard CSV file."""
    csv_file = temp_dir / "test.csv"
    data = [
        {
            "underlying_price": "100.0",
            "strike_price": "100.0",
            "time_to_expiry": "1.0",
            "volatility": "0.2",
            "risk_free_rate": "0.05",
            "option_type": "call",
            "bid": "10.4",
            "ask": "10.6"
        }
    ]
    with open(csv_file, "w", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        
    count = await pipeline.run(str(csv_file))
    assert count == 1

@pytest.mark.asyncio
async def test_pipeline_json_gz_processing(pipeline: OptionsPipeline, temp_dir: Path, db_cleanup) -> None:
    """Test processing a gzipped JSON file."""
    gz_file = temp_dir / "test.json.gz"
    data = [
        {
            "underlying_price": 105.0,
            "strike_price": 100.0,
            "time_to_expiry": 0.5,
            "volatility": 0.25,
            "risk_free_rate": 0.04,
            "option_type": "put",
            "bid": 2.1,
            "ask": 2.3
        }
    ]
    with gzip.open(gz_file, "wt", encoding="utf-8") as f:
        json.dump(data, f)
        
    count = await pipeline.run(str(gz_file))
    assert count == 1

@pytest.mark.asyncio
async def test_pipeline_invalid_file(pipeline: OptionsPipeline, temp_dir: Path) -> None:
    """Test pipeline behavior with a corrupted file."""
    bad_file = temp_dir / "corrupt.json"
    bad_file.write_text("{ invalid json }")
    
    count = await pipeline.run(str(bad_file))
    assert count == 0

@pytest.mark.asyncio
async def test_pipeline_row_error(pipeline: OptionsPipeline, temp_dir: Path, db_cleanup) -> None:
    """Test pipeline behavior when a row is invalid but others are fine."""
    csv_file = temp_dir / "partial.csv"
    data = [
        {"underlying_price": "invalid"}, # Should fail validation
        {
            "underlying_price": "100.0",
            "strike_price": "100.0",
            "time_to_expiry": "1.0",
            "volatility": "0.2",
            "risk_free_rate": "0.05",
            "option_type": "call",
        }
    ]
    with open(csv_file, "w", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["underlying_price", "strike_price", "time_to_expiry", "volatility", "risk_free_rate", "option_type"])
        writer.writeheader()
        writer.writerows(data)
        
    count = await pipeline.run(str(csv_file))
    assert count == 1 # One succeeded, one failed
