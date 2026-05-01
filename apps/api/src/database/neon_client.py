"""NeonDB async connection pool — loop-aware lazy init."""

from __future__ import annotations

import asyncio
import contextlib
import time
from typing import TYPE_CHECKING

import asyncpg
import structlog

from src.config import get_settings
from src.metrics import NEON_ERRORS_TOTAL, NEON_POOL_IDLE, NEON_POOL_SIZE, NEON_QUERY_DURATION

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = structlog.get_logger(__name__)
_pool: asyncpg.Pool | None = None
_loop: asyncio.AbstractEventLoop | None = None


async def get_pool() -> asyncpg.Pool:
    """Return global asyncpg pool; create on first call or loop change."""
    global _pool, _loop
    current_loop = asyncio.get_running_loop()

    if _pool is None or _loop != current_loop or _pool._closed:
        # DO NOT close the old pool if it belongs to a different loop
        # just drop the reference and let the GC/cleanup handle it.
        _pool = None

        settings = get_settings()
        _pool = await asyncpg.create_pool(
            dsn=settings.neon_connection_string,
            min_size=2,
            max_size=10,
            command_timeout=30,
            statement_cache_size=200,
            server_settings={"jit": "off"},
        )
        _loop = current_loop
        NEON_POOL_SIZE.set(10)
        logger.info("neondb_pool_created", step="init", rows=0)

    assert _pool is not None
    NEON_POOL_IDLE.set(_pool.get_idle_size())
    return _pool


async def close_pool() -> None:
    """Close the global pool."""
    global _pool, _loop
    if _pool:
        try:
            current_loop = asyncio.get_running_loop()
            if _loop == current_loop:
                await _pool.close()
        except RuntimeError:
            pass
        _pool = None
        _loop = None
        logger.info("neondb_pool_closed", step="shutdown", rows=0)


@contextlib.asynccontextmanager
async def acquire() -> AsyncIterator[asyncpg.Connection]:
    """Acquire a connection from the loop-aware pool."""
    pool = await get_pool()
    start = time.perf_counter()
    try:
        async with pool.acquire() as conn:
            yield conn
    except Exception as exc:
        NEON_ERRORS_TOTAL.labels(operation="acquire").inc()
        logger.error("neondb_acquire_failed", error=str(exc))
        raise
    finally:
        NEON_QUERY_DURATION.labels(operation="acquire").observe(time.perf_counter() - start)
