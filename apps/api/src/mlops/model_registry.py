"""Model registry management using MLflow."""

from __future__ import annotations

import mlflow
import structlog

logger = structlog.get_logger(__name__)


class ModelRegistry:
    """Manages model registration and versioning."""

    def __init__(self, tracking_uri: str) -> None:
        mlflow.set_tracking_uri(tracking_uri)

    def register_model(self, run_id: str, model_name: str) -> None:
        """Register a model from a specific run."""
        try:
            model_uri = f"runs:/{run_id}/model"
            mlflow.register_model(model_uri, model_name)
        except Exception as exc:
            logger.error("model_registration_failed", error=str(exc))

    def transition_model_stage(self, model_name: str, version: str, stage: str) -> None:
        """Transition model version to a new stage (e.g., Staging, Production)."""
        try:
            client = mlflow.tracking.MlflowClient()
            client.transition_model_version_stage(name=model_name, version=version, stage=stage)
        except Exception as exc:
            logger.error("model_transition_failed", error=str(exc))
