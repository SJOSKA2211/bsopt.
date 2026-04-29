"""MLflow experiment tracking for bsopt."""

from __future__ import annotations

from typing import Any

import mlflow
import structlog

from src.metrics import MLFLOW_RUNS_TOTAL

logger = structlog.get_logger(__name__)


class MLflowTracker:
    """Manages logging of experiments and runs to MLflow."""

    def __init__(self, tracking_uri: str) -> None:
        self.tracking_uri = tracking_uri
        mlflow.set_tracking_uri(tracking_uri)

    def log_pricing_run(
        self,
        experiment_name: str,
        run_name: str,
        params: dict[str, Any],
        metrics: dict[str, Any],
        tags: dict[str, str] | None = None,
    ) -> str:
        """Log a pricing model run with parameters and metrics."""
        mlflow.set_experiment(experiment_name)

        try:
            with mlflow.start_run(run_name=run_name) as run:
                mlflow.log_params(params)
                mlflow.log_metrics(metrics)
                if tags:
                    mlflow.set_tags(tags)

                MLFLOW_RUNS_TOTAL.labels(experiment=experiment_name, status="success").inc()
                logger.info("mlflow_run_logged", experiment=experiment_name, run_id=run.info.run_id)
                return str(run.info.run_id)
        except Exception as exc:
            MLFLOW_RUNS_TOTAL.labels(experiment=experiment_name, status="failed").inc()
            logger.error("mlflow_logging_failed", error=str(exc), experiment=experiment_name)
            raise
