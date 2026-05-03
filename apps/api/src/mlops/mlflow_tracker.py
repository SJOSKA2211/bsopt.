"""MLflow tracking integration for pricing experiments."""

from __future__ import annotations

from typing import Any

import mlflow
import structlog

logger = structlog.get_logger(__name__)


class MLflowTracker:
    """Manages MLflow experiment tracking for research runs."""

    def __init__(self, tracking_uri: str) -> None:
        self.tracking_uri = tracking_uri
        mlflow.set_tracking_uri(tracking_uri)

    def log_pricing_run(
        self,
        experiment_name: str,
        run_name: str,
        params: dict[str, Any],
        metrics: dict[str, float],
        tags: dict[str, str] | None = None,
    ) -> str:
        """Log a complete pricing run to MLflow."""
        try:
            mlflow.set_experiment(experiment_name)
            with mlflow.start_run(run_name=run_name) as run:
                mlflow.log_params(params)
                mlflow.log_metrics(metrics)
                if tags is not None:
                    mlflow.set_tags(tags)
                return str(run.info.run_id)
        except Exception as exc:
            logger.error("mlflow_logging_failed", error=str(exc))
            raise
