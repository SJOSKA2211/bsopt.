"""Ray 2.10 distributed experiment runner — Python 3.14 free-threaded."""

from __future__ import annotations

import importlib
from typing import Any, cast

import mlflow
import ray
import structlog

from src.methods.base import OptionParams
from src.metrics import RAY_CLUSTER_CPUS, RAY_TASKS_COMPLETED, RAY_TASKS_SUBMITTED

logger = structlog.get_logger(__name__)


@ray.remote
def price_remote(params_dict: dict[str, Any], method_name: str) -> dict[str, Any]:
    """Ray remote task: import method at runtime and compute price."""
    # Dynamic method import — no global state pollution between workers
    module_map = {
        "analytical": "src.methods.analytical",
        "explicit_fdm": "src.methods.finite_difference.explicit",
        "implicit_fdm": "src.methods.finite_difference.implicit",
        "crank_nicolson": "src.methods.finite_difference.crank_nicolson",
        "standard_mc": "src.methods.monte_carlo.standard",
        "antithetic_mc": "src.methods.monte_carlo.antithetic",
        "control_variate_mc": "src.methods.monte_carlo.control_variates",
        "quasi_mc": "src.methods.monte_carlo.quasi_mc",
        "binomial_crr": "src.methods.tree_methods.binomial_crr",
        "trinomial": "src.methods.tree_methods.trinomial",
        "binomial_crr_richardson": "src.methods.tree_methods.richardson",
        "trinomial_richardson": "src.methods.tree_methods.richardson",
    }

    cls_map = {
        "analytical": "BlackScholesAnalytical",
        "explicit_fdm": "ExplicitFDM",
        "implicit_fdm": "ImplicitFDM",
        "crank_nicolson": "CrankNicolsonFDM",
        "standard_mc": "StandardMonteCarlo",
        "antithetic_mc": "AntitheticMonteCarlo",
        "control_variate_mc": "ControlVariateMonteCarlo",
        "quasi_mc": "QuasiMonteCarlo",
        "binomial_crr": "BinomialCRR",
        "trinomial": "TrinomialTree",
        "binomial_crr_richardson": "RichardsonExtrapolation",
        "trinomial_richardson": "TrinomialRichardsonExtrapolation",
    }

    module_path = module_map.get(method_name)
    if not module_path:
        raise ValueError(f"Unknown method: {method_name}")

    module = importlib.import_module(module_path)
    cls_name = cls_map.get(method_name)
    if cls_name is None:
        raise ValueError(f"No class mapped for method: {method_name}")
    pricer_cls = getattr(module, cls_name)

    params = OptionParams(**params_dict)
    result = pricer_cls().price(params)

    return {
        "method_type": result.method_type,
        "computed_price": result.computed_price,
        "exec_seconds": result.exec_seconds,
        "converged": result.converged,
        "parameter_set": result.parameter_set,
    }


class RayExperimentRunner:
    """Manager for distributed Ray pricing experiments."""

    def __init__(self, ray_address: str, mlflow_tracking_uri: str) -> None:
        self.ray_address = ray_address
        self.mlflow_tracking_uri = mlflow_tracking_uri

    def connect(self) -> None:
        """Connect to the Ray cluster and initialize MLflow."""
        if not ray.is_initialized():
            if self.ray_address:
                ray.init(address=self.ray_address, ignore_reinit_error=True)
            else:
                ray.init(ignore_reinit_error=True)
        resources = cast("dict[str, float]", ray.cluster_resources())  # type: ignore[no-untyped-call]
        RAY_CLUSTER_CPUS.set(float(resources.get("CPU", 0)))
        mlflow.set_tracking_uri(self.mlflow_tracking_uri)
        logger.info("ray_connected", address=self.ray_address, step="init", rows=0)

    def run_grid(
        self,
        experiment_name: str,
        param_grid: list[tuple[dict[str, Any], str]],  # (params, method_name)
    ) -> list[dict[str, Any]]:
        """Run all (params, method) pairs in parallel. Log to MLflow."""
        mlflow.set_experiment(experiment_name)
        with mlflow.start_run(run_name=f"grid_{experiment_name}") as run:
            mlflow.log_param("grid_size", len(param_grid))
            RAY_TASKS_SUBMITTED.labels(task_type="pricing").inc(len(param_grid))

            futures = [price_remote.remote(p, m) for p, m in param_grid]
            results: list[dict[str, Any]] = ray.get(futures)

            RAY_TASKS_COMPLETED.labels(task_type="pricing", status="success").inc(len(results))
            mlflow.log_metric("total_computations", len(results))

        logger.info(
            "ray_grid_complete",
            experiment=experiment_name,
            total=len(results),
            run_id=run.info.run_id,
            step="ray",
            rows=len(results),
        )
        return results
