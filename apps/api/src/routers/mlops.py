"""MLOps router for managing Ray jobs and MLflow experiments."""

from __future__ import annotations

from typing import Any

import ray
from fastapi import APIRouter, Depends, HTTPException

from src.auth.dependencies import get_admin_user, get_current_user
from src.config import get_settings
from src.mlops.drift_detector import check_model_drift
from src.mlops.ray_runner import RayExperimentRunner

router = APIRouter(prefix="/mlops", tags=["mlops"])
settings = get_settings()


@router.get("/status")
async def get_mlops_status(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Get status of Ray cluster and MLflow tracking."""
    try:
        if not ray.is_initialized():
            ray.init(address=settings.ray_address, ignore_reinit_error=True)

        from typing import cast
        # Use getattr and cast to Any to bypass Mypy's disallow-untyped-calls for the Ray library
        cluster_resources_func = cast("Any", ray.cluster_resources)
        nodes_func = cast("Any", ray.nodes)

        resources = cluster_resources_func()
        return {
            "ray": {
                "initialized": True,
                "cpus": resources.get("CPU", 0),
                "memory": resources.get("memory", 0),
                "nodes": len(nodes_func()),
            },
            "mlflow": {
                "tracking_uri": settings.mlflow_tracking_uri,
            },
        }
    except Exception as exc:
        return {
            "ray": {"initialized": False, "error": str(exc)},
            "mlflow": {"tracking_uri": settings.mlflow_tracking_uri},
        }


@router.post("/experiments/run")
async def trigger_experiment(
    experiment_name: str,
    param_grid: list[tuple[dict[str, Any], str]],
    user: dict[str, Any] = Depends(get_admin_user),
) -> dict[str, Any]:
    """Trigger a distributed Ray experiment. Admin only."""
    runner = RayExperimentRunner(settings.ray_address, settings.mlflow_tracking_uri)
    try:
        results = runner.run_grid(experiment_name, param_grid)
        return {"status": "success", "results_count": len(results)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/drift/check")
async def trigger_drift_check(
    method_type: str,
    baseline_mape: float,
    user_ids: list[str],
    user: dict[str, Any] = Depends(get_admin_user),
) -> dict[str, Any]:
    """Manually trigger model drift detection. Admin only."""
    from src.notifications.hierarchy import notification_router

    drift_detected = await check_model_drift(
        method_type=method_type,
        baseline_mape=baseline_mape,
        router=notification_router,
        user_ids=user_ids,
    )
    return {"method_type": method_type, "drift_detected": drift_detected}
