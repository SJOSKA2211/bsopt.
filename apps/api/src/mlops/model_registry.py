"""Model registry management using MLflow and NeonDB."""
from __future__ import annotations

from typing import Any

import mlflow
import structlog

from src.database.repository import get_latest_model, save_model_metadata

logger = structlog.get_logger(__name__)


class ModelRegistry:
    """Manages model registration and versioning."""

    def __init__(self, tracking_uri: str) -> None:
        self.tracking_uri = tracking_uri
        mlflow.set_tracking_uri(tracking_uri)

    async def register_model(self, name: str, version: str, artifact_uri: str, metrics: dict[str, Any]) -> None:
        """Register a model in the database registry."""
        try:
            # In a real scenario, we might also call mlflow.register_model
            await save_model_metadata(name, version, artifact_uri, metrics)
            logger.info("model_registered", name=name, version=version)
        except Exception as exc:
            logger.error("model_registration_failed", error=str(exc))
            raise

    async def get_latest_model(self, name: str) -> dict[str, Any]:
        """Fetch the latest model metadata from the database."""
        return await get_latest_model(name)

    def transition_model_stage(self, model_name: str, version: str, stage: str) -> None:
        """Transition model version to a new stage (e.g., Production)."""
        try:
            client = mlflow.tracking.MlflowClient()
            # Note: This requires the model to be in MLflow model registry
            client.transition_model_version_stage(name=model_name, version=version, stage=stage)
        except Exception as exc:
            logger.warn("mlflow_stage_transition_skipped", error=str(exc))
