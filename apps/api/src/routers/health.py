"""Healthcheck router for bsopt."""

from __future__ import annotations

import sys

from fastapi import APIRouter

from src.database.neon_client import get_pool

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Check system health including database connectivity."""
    db_status = "disconnected"
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("SELECT 1")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    return {
        "status": "ok",
        "db": db_status,
        "python": python_version,
    }
