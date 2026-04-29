"""Abstract base class for data ingestion pipelines."""

from __future__ import annotations

import csv
import gzip
import json
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path
from typing import Any
from uuid import uuid4

import structlog

from src.data.transformers import transform_market_row
from src.data.validators import validate_market_data, validate_option_parameters
from src.database.repository import save_audit_log, save_market_data, save_option_parameters

logger = structlog.get_logger(__name__)


class BasePipeline(ABC):

    @abstractmethod
    async def run(self, source_path: str) -> int:
        """Run the pipeline on a file source and return processed row count."""


class OptionsPipeline(BasePipeline):
    """General pipeline for processing option data files."""

    def __init__(self, market: str) -> None:
        self.market = market

    async def run(self, source_path: str) -> int:
        """Process CSV or JSON file from the watch directory (supports .gz)."""
        path = Path(source_path)
        logger.info("pipeline_started", market=self.market, source=source_path)

        is_gz = path.suffix == ".gz"
        effective_suffix = Path(path.stem).suffix if is_gz else path.suffix

        rows: list[dict[str, Any]] = []

        try:
            if is_gz:
                with gzip.open(path, "rt", encoding="utf-8") as f:
                    if effective_suffix == ".json":
                        data = json.load(f)
                        rows = data if isinstance(data, list) else [data]
                    else:
                        reader = csv.DictReader(f)
                        rows = list(reader)
            else:
                with open(path, encoding="utf-8", newline="") as f:
                    if path.suffix == ".json":
                        data = json.load(f)
                        rows = data if isinstance(data, list) else [data]
                    else:
                        reader = csv.DictReader(f)
                        rows = list(reader)
        except Exception as exc:
            logger.error("file_load_failed", error=str(exc), path=source_path)
            return 0

        count = 0
        for row in rows:
            try:
                # 1. Transform
                clean_row = transform_market_row(row)

                # 2. Validate
                validate_option_parameters(clean_row)
                validate_market_data(clean_row)

                # 3. Persistence (Zero-Mock hits real NeonDB)
                # First save parameters to get option_id
                option_id = await save_option_parameters(
                    underlying_price=clean_row["underlying_price"],
                    strike_price=clean_row["strike_price"],
                    time_to_maturity=clean_row["time_to_maturity"],
                    volatility=clean_row["volatility"],
                    risk_free_rate=clean_row["risk_free_rate"],
                    option_type=clean_row["option_type"],
                    market_source=self.market,
                )

                # Then save market data
                await save_market_data(
                    option_id=option_id,
                    trade_date=clean_row.get("trade_date", date.today()),
                    bid=clean_row.get("bid"),
                    ask=clean_row.get("ask"),
                    volume=int(clean_row.get("volume", 0)) if clean_row.get("volume") else None,
                    oi=int(clean_row.get("oi", 0)) if clean_row.get("oi") else None,
                    implied_vol=clean_row.get("implied_vol"),
                    data_source=self.market,
                )

                count += 1
            except Exception as exc:
                logger.error("row_processing_failed", error=str(exc), row=row)
                continue

        # Final audit log
        await save_audit_log(
            step_name=f"pipeline_{self.market}",
            status="success",
            pipeline_run_id=uuid4(),
            rows_affected=count,
        )

        logger.info("pipeline_finished", market=self.market, processed=count)
        return count
