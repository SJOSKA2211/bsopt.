"""Ray 2.10 distributed experiment runner — Python 3.14 free-threaded."""

from __future__ import annotations

from typing import Any

import mlflow
import ray
import structlog

from src.metrics import RAY_CLUSTER_CPUS, RAY_TASKS_COMPLETED, RAY_TASKS_SUBMITTED
from itertools import starmap

logger = structlog.get_logger(__name__)


def _price_logic(params_dict: dict[str, Any], method_name: str) -> dict[str, Any]:
    """Core pricing logic extracted for unit testing without Ray."""
    import importlib

    module_map: dict[str, str] = {
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

    cls_map: dict[str, str] = {
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
    cls_name = cls_map.get(method_name, method_name)
    pricer_cls = getattr(module, cls_name)

    from src.methods.base import OptionParams

    params = OptionParams(**params_dict)
    result = pricer_cls().price(params)
    return {
        "method_type": result.method_type,
        "computed_price": result.computed_price,
        "exec_seconds": result.exec_seconds,
        "converged": result.converged,
        "parameter_set": result.parameter_set,
    }


@ray.remote
def price_remote(params_dict: dict[str, Any], method_name: str) -> dict[str, Any]:
    """Ray remote task: delegation to _price_logic."""
    return _price_logic(params_dict, method_name)


class RayExperimentRunner:
    """Manages Ray cluster connection and distributed experiment execution."""

    _connection_failed: bool = False

    def __init__(self, ray_address: str, mlflow_tracking_uri: str, **ray_kwargs: Any) -> None:
        self.ray_address = ray_address
        self.mlflow_tracking_uri = mlflow_tracking_uri
        self.ray_kwargs = ray_kwargs

    def connect(self) -> None:
        """Connect to Ray cluster; fallback to local on failure."""
        if not ray.is_initialized():
            if RayExperimentRunner._connection_failed:
                ray.init(ignore_reinit_error=True, **self.ray_kwargs)
                return

            try:
                if self.ray_address:
                    ray.init(
                        address=self.ray_address,
                        ignore_reinit_error=True,
                        runtime_env={},
                        **self.ray_kwargs,
                    )
                else:
                    ray.init(
                        ignore_reinit_error=True,
                        runtime_env={},
                        **self.ray_kwargs,
                    )
            except Exception as exc:
                logger.warning(
                    "ray_remote_connect_failed", error=str(exc), fallback="local"
                )
                RayExperimentRunner._connection_failed = True
                ray.init(ignore_reinit_error=True, runtime_env={}, **self.ray_kwargs)

        self._report_cluster_status()

    def _report_cluster_status(self) -> None:
        """Read cluster resources and configure MLflow tracking URI."""
        from typing import cast

        cluster_func = cast("Any", ray.cluster_resources)
        cluster_resources = cast("dict[str, float]", cluster_func())
        RAY_CLUSTER_CPUS.set(float(cluster_resources.get("CPU", 0)))
        mlflow.set_tracking_uri(self.mlflow_tracking_uri)
        logger.info("ray_connected", address=self.ray_address, step="init", rows=0)

    def run_grid(
        self,
        experiment_name: str,
        param_grid: list[tuple[dict[str, Any], str]],
    ) -> list[dict[str, Any]]:
        """Run all (params, method) pairs in parallel. Log to MLflow."""
        mlflow.set_experiment(experiment_name)
        with mlflow.start_run(run_name=f"grid_{experiment_name}") as run:
            mlflow.log_param("grid_size", len(param_grid))
            RAY_TASKS_SUBMITTED.labels(task_type="pricing").inc(len(param_grid))
            if ray.is_initialized():
                futures = list(starmap(price_remote.remote, param_grid))
                results: list[dict[str, Any]] = ray.get(futures)
            else:
                logger.warning("ray_not_initialized_using_direct_fallback")
                results = list(starmap(_price_logic, param_grid))
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
