"""NeonDB async connection pool — asyncpg 0.30, Python 3.14 free-threaded."""

from __future__ import annotations

import contextlib
import time
from collections.abc import AsyncIterator

import asyncpg
import structlog

from src.config import get_settings
from src.metrics import NEON_ERRORS_TOTAL, NEON_POOL_IDLE, NEON_POOL_SIZE, NEON_QUERY_DURATION

logger = structlog.get_logger(__name__)
_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Return global asyncpg pool; create on first call (lazy init)."""
    global _pool  # noqa: PLW0603
    if _pool is None:
        settings = get_settings()
        _pool = await asyncpg.create_pool(
            dsn=settings.neon_connection_string,
            min_size=2,
            max_size=10,
            command_timeout=30,
            statement_cache_size=200,
            server_settings={"jit": "off"},  # NeonDB serverless: disable JIT
        )
        NEON_POOL_SIZE.set(10)
        logger.info("neondb_pool_created", min_size=2, max_size=10, step="init", rows=0)
    assert _pool is not None
    NEON_POOL_IDLE.set(_pool.get_idle_size())
    return _pool


async def close_pool() -> None:
    """Close the global pool."""
    global _pool  # noqa: PLW0603
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("neondb_pool_closed", step="shutdown", rows=0)


@contextlib.asynccontextmanager
async def acquire() -> AsyncIterator[asyncpg.Connection]:
    """Acquire a connection; track duration and errors via Prometheus."""
    pool = await get_pool()
    start = time.perf_counter()
    try:
        async with pool.acquire() as conn:
            yield conn
    except Exception as exc:
        NEON_ERRORS_TOTAL.labels(operation="acquire").inc()
        logger.error(
            "neondb_acquire_failed",
            event="error",
            error_type=type(exc).__name__,
            error_message=str(exc),
            component="neon_client",
            severity="error",
            context={},
        )
        raise
    finally:
        NEON_QUERY_DURATION.labels(operation="acquire").observe(time.perf_counter() - start)


if __name__ == "__main__":
    import asyncio

    async def test_conn() -> None:
        async with acquire() as conn:
            val = await conn.fetchval("SELECT 1")
            print(f"NeonDB Connection Test: {val}")

    asyncio.run(test_conn())
