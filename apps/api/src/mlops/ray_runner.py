"""Ray distributed runner for research experiments."""

from __future__ import annotations

from typing import Any

import ray
import structlog

from src.methods.analytical import BlackScholesAnalytical
from src.methods.base import OptionParams
from src.methods.finite_difference.crank_nicolson import CrankNicolsonFDM
from src.methods.finite_difference.explicit import ExplicitFDM
from src.methods.finite_difference.implicit import ImplicitFDM
from src.methods.monte_carlo.antithetic import AntitheticMonteCarlo
from src.methods.monte_carlo.control_variates import ControlVariateMonteCarlo
from src.methods.monte_carlo.quasi_mc import QuasiMonteCarlo
from src.methods.monte_carlo.standard import StandardMonteCarlo
from src.methods.tree_methods.binomial_crr import BinomialCRR
from src.methods.tree_methods.richardson import (
    RichardsonExtrapolation,
    TrinomialRichardsonExtrapolation,
)
from src.methods.tree_methods.trinomial import TrinomialTree

logger = structlog.get_logger(__name__)


@ray.remote
def price_remote(params_dict: dict[str, Any], method: str) -> dict[str, Any]:
    """Ray task to compute option price using any supported method."""
    params = OptionParams(**params_dict)

    methods = {
        "analytical": BlackScholesAnalytical(),
        "explicit_fdm": ExplicitFDM(),
        "implicit_fdm": ImplicitFDM(),
        "crank_nicolson": CrankNicolsonFDM(),
        "standard_mc": StandardMonteCarlo(),
        "antithetic_mc": AntitheticMonteCarlo(),
        "control_variate_mc": ControlVariateMonteCarlo(),
        "quasi_mc": QuasiMonteCarlo(),
        "binomial_crr": BinomialCRR(),
        "trinomial": TrinomialTree(),
        "binomial_crr_richardson": RichardsonExtrapolation(),
        "trinomial_richardson": TrinomialRichardsonExtrapolation(),
    }

    if method not in methods:
        raise ValueError(f"Unknown method: {method}")

    res = methods[method].price(params)
    return {
        "method_type": res.method_type,
        "computed_price": res.computed_price,
        "exec_seconds": res.exec_seconds,
        "parameter_set": res.parameter_set,
    }


class RayExperimentRunner:
    """Manages distributed pricing experiments."""

    def __init__(self, ray_address: str, tracking_uri: str) -> None:
        self.ray_address = ray_address
        self.tracking_uri = tracking_uri

    def connect(self) -> None:
        """Initialize Ray connection."""
        if not ray.is_initialized():
            if not self.ray_address:
                ray.init(ignore_reinit_error=True)
            else:
                ray.init(address=self.ray_address, ignore_reinit_error=True)

    def run_batch(self, params_list: list[dict[str, Any]], method: str) -> list[Any]:
        """Execute a batch of pricing tasks."""
        self.connect()
        futures = [price_remote.remote(p, method) for p in params_list]
        return ray.get(futures)
