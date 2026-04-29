"""Pricing router for executing numerical methods."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastapi import APIRouter

from src.cache.decorators import cache_response
from src.methods.analytical import BlackScholesAnalytical
from src.methods.base import BasePricer, OptionParams
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

router = APIRouter(prefix="/pricing", tags=["pricing"])
executor = ThreadPoolExecutor(max_workers=12)


def _price_sync(method_name: str, params: OptionParams) -> dict[str, Any]:
    """Helper for thread pool execution."""
    pricer_map = {
        "analytical": BlackScholesAnalytical,
        "explicit_fdm": ExplicitFDM,
        "implicit_fdm": ImplicitFDM,
        "crank_nicolson": CrankNicolsonFDM,
        "standard_mc": StandardMonteCarlo,
        "antithetic_mc": AntitheticMonteCarlo,
        "control_variate_mc": ControlVariateMonteCarlo,
        "quasi_mc": QuasiMonteCarlo,
        "binomial_crr": BinomialCRR,
        "trinomial": TrinomialTree,
        "binomial_crr_richardson": RichardsonExtrapolation,
        "trinomial_richardson": TrinomialRichardsonExtrapolation,
    }
    from typing import cast

    pricer_factory = cast("Callable[[], BasePricer]", pricer_map[method_name])
    pricer = pricer_factory()

    # Adjust steps for some methods to keep response time reasonable
    kwargs = {}
    if method_name == "explicit_fdm":
        kwargs["steps_time"] = 2000

    result = pricer.price(params, **kwargs)
    return {
        "method_type": result.method_type,
        "computed_price": result.computed_price,
        "exec_seconds": result.exec_seconds,
        "converged": result.converged,
        "parameter_set": result.parameter_set,
    }


@router.post("/")
@cache_response(ttl=3600)
async def get_all_prices(params: OptionParams) -> dict[str, Any]:
    """Compute option price across all 12 numerical methods in parallel."""
    loop = asyncio.get_running_loop()
    methods = [
        "analytical",
        "explicit_fdm",
        "implicit_fdm",
        "crank_nicolson",
        "standard_mc",
        "antithetic_mc",
        "control_variate_mc",
        "quasi_mc",
        "binomial_crr",
        "trinomial",
        "binomial_crr_richardson",
        "trinomial_richardson",
    ]

    tasks = [loop.run_in_executor(executor, _price_sync, m, params) for m in methods]
    results = await asyncio.gather(*tasks)

    # Calculate MAPE relative to analytical
    analytical_price = next(
        r["computed_price"] for r in results if r["method_type"] == "analytical"
    )

    for r in results:
        if r["method_type"] == "analytical":
            r["mape"] = 0.0
        else:
            r["mape"] = abs(r["computed_price"] - analytical_price) / analytical_price * 100

    return {
        "parameters": params,
        "results": results,
    }
