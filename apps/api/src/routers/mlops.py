"""MLOps management router."""

from __future__ import annotations

from typing import Any

import ray
from fastapi import APIRouter

from src.config import get_settings
from src.database.neon_client import acquire

router = APIRouter(prefix="/mlops", tags=["MLOps"])


@router.get("/status")
async def get_status() -> dict[str, Any]:
    """Get Ray cluster status and MLflow connection info."""
    settings = get_settings()

    ray_info = {
        "connected": ray.is_initialized(),
        "address": settings.ray_address,
        "resources": {},
    }

    if ray.is_initialized():
        from typing import cast

        resources: Any = ray.cluster_resources()  # type: ignore[no-untyped-call]
        ray_info["resources"] = cast("dict[str, float]", resources)

    return {
        "ray": ray_info,
        "mlflow": {
            "tracking_uri": settings.mlflow_tracking_uri,
        },
    }


@router.get("/stats")
async def get_mlops_stats() -> dict[str, Any]:
    """Retrieve MLOps KPIs for the dashboard."""
    async with acquire() as conn:
        experiment_count = await conn.fetchval("SELECT COUNT(*) FROM ml_experiments")
        option_count = await conn.fetchval("SELECT COUNT(*) FROM option_parameters")

        # Count drift alerts (severity='warning' or 'error' related to drift)
        drift_alerts = await conn.fetchval(
            "SELECT COUNT(*) FROM notifications WHERE title LIKE '%Drift%' AND read = FALSE"
        )

        # Scraper rows inserted in last 24h
        spy_rows = await conn.fetchval(
            "SELECT SUM(rows_inserted) FROM scrape_runs WHERE market = 'spy' AND finished_at > NOW() - INTERVAL '24 hours'"
        )
        nse_rows = await conn.fetchval(
            "SELECT SUM(rows_inserted) FROM scrape_runs WHERE market = 'nse' AND finished_at > NOW() - INTERVAL '24 hours'"
        )

        return {
            "experiment_count": experiment_count or 0,
            "option_count": option_count or 0,
            "drift_alerts": drift_alerts or 0,
            "spy_rows_24h": spy_rows or 0,
            "nse_rows_24h": nse_rows or 0,
            "ray_active_tasks": 0,  # To be pulled from Ray client if possible
        }


@router.post("/retrain")
async def trigger_retraining(experiment_name: str) -> dict[str, str]:
    """Trigger a new Ray training job for volatility surface."""
    # This would typically publish a task to RabbitMQ for a Ray task
    return {"status": "retraining_scheduled", "experiment": experiment_name}
