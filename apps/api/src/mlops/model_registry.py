"""MLflow model registry interface."""

from __future__ import annotations

import mlflow
import structlog

logger = structlog.get_logger(__name__)


class ModelRegistry:
    """Interface for managing models in MLflow registry."""

    def __init__(self, tracking_uri: str) -> None:
        self.tracking_uri = tracking_uri
        mlflow.set_tracking_uri(tracking_uri)

    def register_model(self, run_id: str, model_name: str) -> None:
        """Register a model from a specific run."""
        try:
            model_uri = f"runs:/{run_id}/model"
            mlflow.register_model(model_uri, model_name)
            logger.info("model_registered", name=model_name, run_id=run_id)
        except Exception as exc:
            logger.error("model_registration_failed", error=str(exc))

    def transition_model_stage(self, name: str, version: str, stage: str) -> None:
        """Transition a model version to a new stage (e.g. Staging, Production)."""
        client = mlflow.tracking.MlflowClient()
        client.transition_model_version_stage(
            name=name, version=version, stage=stage, archive_existing_versions=True
        )
        logger.info("model_stage_transitioned", name=name, version=version, stage=stage)
