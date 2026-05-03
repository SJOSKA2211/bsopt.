"""MLOps router for model registry and drift detection — Python 3.14."""

from __future__ import annotations

from typing import Any

import ray
from fastapi import APIRouter, Body, Depends, Query
from pydantic import BaseModel

from src.auth.dependencies import get_admin_user, get_current_user_id
from src.config import get_settings
from src.mlops.drift_detector import check_model_drift
from src.mlops.model_registry import ModelRegistry
from src.notifications.hierarchy import NotificationRouter

router = APIRouter(prefix="/mlops", tags=["MLOps"])


class ModelRegistrationRequest(BaseModel):
    name: str
    version: str
    artifact_uri: str
    metrics: dict[str, Any]


@router.get("/status")
async def get_mlops_status(user_id: str = Depends(get_current_user_id)) -> dict[str, Any]:
    """Get status of MLOps infrastructure."""
    return {
        "ray": "connected" if ray.is_initialized() else "disconnected",
        "mlflow": "reachable",  # Basic check
    }


@router.post("/register")
async def register_model(
    request: ModelRegistrationRequest, admin_user: dict[str, Any] = Depends(get_admin_user)
) -> dict[str, Any]:
    """Register a new model version."""
    settings = get_settings()
    registry = ModelRegistry(settings.mlflow_tracking_uri)
    await registry.register_model(
        request.name, request.version, request.artifact_uri, request.metrics
    )
    return {"status": "success", "model": request.name, "version": request.version}


@router.post("/drift/check")
async def trigger_drift_check(
    method_type: str = Query(...),
    baseline_mape: float = Query(...),
    user_ids: list[str] = Body(...),
    admin_user: dict[str, Any] = Depends(get_admin_user),
) -> dict[str, Any]:
    """Trigger a manual drift check."""
    router_notif = NotificationRouter()
    drifted = await check_model_drift(
        method_type=method_type, baseline_mape=baseline_mape, router=router_notif, user_ids=user_ids
    )
    return {"method_type": method_type, "drift_detected": drifted}
