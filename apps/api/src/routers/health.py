"""Health check router for service monitoring."""

from __future__ import annotations

import sys

from fastapi import APIRouter

from src.database.neon_client import get_pool

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Verify system health, database connectivity, and Python version."""
    db_status = "connected"
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("SELECT 1")
    except Exception:
        db_status = "disconnected"

    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "db": db_status,
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }
