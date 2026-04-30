"""Pricing router for option valuation across multiple numerical methods."""

from __future__ import annotations

import importlib
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException

from src.auth.dependencies import get_current_user
from src.data.validators import validate_option_parameters
from src.methods.base import OptionParams
from src.metrics import PRICE_COMPUTATIONS_TOTAL, PRICE_DURATION_SECONDS

router = APIRouter(prefix="/pricing", tags=["pricing"])
logger = structlog.get_logger(__name__)

# Map method names to their module and class
METHOD_REGISTRY = {
    "analytical": ("src.methods.analytical", "BlackScholesAnalytical"),
    "explicit_fdm": ("src.methods.finite_difference.explicit", "ExplicitFDM"),
    "implicit_fdm": ("src.methods.finite_difference.implicit", "ImplicitFDM"),
    "crank_nicolson": ("src.methods.finite_difference.crank_nicolson", "CrankNicolsonFDM"),
    "standard_mc": ("src.methods.monte_carlo.standard", "StandardMonteCarlo"),
    "antithetic_mc": ("src.methods.monte_carlo.antithetic", "AntitheticMonteCarlo"),
    "control_variate_mc": ("src.methods.monte_carlo.control_variates", "ControlVariateMonteCarlo"),
    "quasi_mc": ("src.methods.monte_carlo.quasi_mc", "QuasiMonteCarlo"),
    "binomial_crr": ("src.methods.tree_methods.binomial_crr", "BinomialCRR"),
    "trinomial": ("src.methods.tree_methods.trinomial", "TrinomialTree"),
    "binomial_crr_richardson": ("src.methods.tree_methods.richardson", "RichardsonExtrapolation"),
    "trinomial_richardson": (
        "src.methods.tree_methods.richardson",
        "TrinomialRichardsonExtrapolation",
    ),
}


@router.post("/")
async def price_option(
    params_dict: dict[str, Any],
    method: str = "analytical",
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Compute option price using the specified numerical method.
    Authenticated users only.
    """
    # 1. Validate
    validate_option_parameters(params_dict)

    # 2. Get Pricer
    if method not in METHOD_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Unsupported pricing method: {method}")

    module_path, cls_name = METHOD_REGISTRY[method]
    try:
        module = importlib.import_module(module_path)
        pricer_cls = getattr(module, cls_name)
        pricer = pricer_cls()
    except Exception as exc:
        logger.error("method_import_failed", method=method, error=str(exc))
        raise HTTPException(status_code=500, detail="Internal pricing engine error") from exc

    # 3. Execute
    params = OptionParams(**params_dict)

    # Track metrics
    with PRICE_DURATION_SECONDS.labels(method_type=method).time():
        result = pricer.price(params)

    PRICE_COMPUTATIONS_TOTAL.labels(
        method_type=method, option_type=params.option_type, converged=str(result.converged)
    ).inc()

    logger.info(
        "option_priced",
        method=method,
        price=result.computed_price,
        user_id=str(user.get("id")),
    )

    return {
        "method_type": result.method_type,
        "computed_price": result.computed_price,
        "exec_seconds": result.exec_seconds,
        "converged": result.converged,
        "parameter_set": result.parameter_set,
    }
