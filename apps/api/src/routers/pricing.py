"""Pricing router for single and batch option pricing — Python 3.14."""
from __future__ import annotations

import asyncio
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.auth.dependencies import get_current_user_id
from src.config import get_settings
from src.database.repository import save_method_result, save_option_parameters
from src.mlops.ray_runner import RayExperimentRunner

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/pricing", tags=["Pricing"])


class PricingRequest(BaseModel):
    underlying_price: float = Field(..., gt=0)
    strike_price: float = Field(..., gt=0)
    time_to_expiry: float = Field(..., gt=0)
    volatility: float = Field(..., gt=0)
    risk_free_rate: float = Field(..., gt=0)
    option_type: str = Field(..., pattern="^(call|put)$")
    method_type: str = Field("analytical", pattern="^(analytical|explicit_fdm|implicit_fdm|crank_nicolson|standard_mc|antithetic_mc|control_variate_mc|quasi_mc|binomial_crr|trinomial|binomial_crr_richardson|trinomial_richardson)$")


@router.post("/")
async def calculate_price(
    request: PricingRequest,
    user_id: str = Depends(get_current_user_id)
) -> dict[str, Any]:
    """Calculate option price using the specified method."""
    settings = get_settings()
    runner = RayExperimentRunner(ray_address=settings.ray_address, mlflow_tracking_uri=settings.mlflow_tracking_uri)

    try:
        # Retry logic for Ray connection
        for _ in range(3):
            try:
                runner.connect()
                break
            except Exception:
                await asyncio.sleep(1)
        else:
            # Fallback to local execution if address is empty or connection fails
            runner.ray_address = ""
            runner.connect()

        param_dict = request.model_dump()
        method = param_dict.pop("method_type")

        # Save params to DB
        opt_id = await save_option_parameters(
            **param_dict,
            market_source="api_request",
            created_by=user_id
        )

        # Run on Ray (or locally if ray_address is empty)
        results = runner.run_grid(f"api_pricing_{user_id}", [(param_dict, method)])
        result = results[0]

        # Save result to DB
        await save_method_result(
            option_id=opt_id,
            method_type=method,
            computed_price=result["computed_price"],
            parameter_set=result["parameter_set"],
            exec_seconds=result["exec_seconds"],
            converged=result["converged"]
        )

        return {
            "option_id": opt_id,
            "computed_price": result["computed_price"],
            "exec_seconds": result["exec_seconds"],
            "method": method
        }
    except Exception as exc:
        logger.error("pricing_calculation_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))
