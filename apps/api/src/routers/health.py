"""Health check router for monitoring service status — Python 3.14."""

from __future__ import annotations

import time

from fastapi import APIRouter

from src.cache.redis_client import get_redis
from src.database.neon_client import acquire

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health_check() -> dict[str, str]:
    """Check connectivity to core infrastructure."""
    status = {"status": "ok", "timestamp": str(time.time())}

    # Check DB
    try:
        async with acquire() as conn:
            await conn.execute("SELECT 1")
        status["database"] = "connected"
    except Exception as exc:
        status["database"] = f"error: {exc!s}"
        status["status"] = "degraded"

    # Check Redis
    try:
        redis = await get_redis()
        await redis.ping()  # type: ignore[misc]
        status["redis"] = "connected"
    except Exception as exc:
        status["redis"] = f"error: {exc!s}"
        status["status"] = "degraded"

    return status
