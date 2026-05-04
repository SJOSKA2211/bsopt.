"""NeonDB async connection pool — loop-aware lazy init."""

from __future__ import annotations

import asyncio
import contextlib
import time
from typing import TYPE_CHECKING

import asyncpg
import structlog

from src.config import get_settings
from src.metrics import (
    NEON_ERRORS_TOTAL,
    NEON_POOL_IDLE,
    NEON_POOL_SIZE,
    NEON_QUERY_DURATION,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = structlog.get_logger(__name__)


class NeonManager:
    """Manages global NeonDB connection pool with loop-awareness."""

    _pool: asyncpg.Pool[asyncpg.Record] | None = None
    _loop: asyncio.AbstractEventLoop | None = None

    @classmethod
    async def get_pool(cls) -> asyncpg.Pool[asyncpg.Record]:
        """Return global asyncpg pool; create on first call or loop change."""
        current_loop = asyncio.get_running_loop()

        if cls._pool is None or cls._loop != current_loop:
            cls._pool = None
            settings = get_settings()
            cls._pool = await asyncpg.create_pool(
                dsn=settings.neon_connection_string,
                min_size=2,
                max_size=10,
                command_timeout=30,
                statement_cache_size=200,
                server_settings={"jit": "off"},
            )
            cls._loop = current_loop
            NEON_POOL_SIZE.set(10)
            logger.info("neondb_pool_created", step="init", rows=0)

        assert cls._pool is not None
        NEON_POOL_IDLE.set(cls._pool.get_idle_size())
        return cls._pool

    @classmethod
    async def close_pool(cls) -> None:
        """Close the global pool."""
        if cls._pool:
            try:
                current_loop = asyncio.get_running_loop()
                if cls._loop == current_loop:
                    await cls._pool.close()
            except (RuntimeError, Exception):
                pass
            finally:
                cls._pool = None
                cls._loop = None
                logger.info("neondb_pool_closed", step="shutdown", rows=0)


async def get_pool() -> asyncpg.Pool[asyncpg.Record]:
    """Shortcut for NeonManager.get_pool()."""
    return await NeonManager.get_pool()


async def close_pool() -> None:
    """Shortcut for NeonManager.close_pool()."""
    await NeonManager.close_pool()


@contextlib.asynccontextmanager
async def acquire() -> AsyncIterator[asyncpg.Connection[asyncpg.Record]]:
    """Acquire a connection from the loop-aware pool."""
    pool = await get_pool()
    start = time.perf_counter()
    try:
        async with pool.acquire() as conn:
            yield conn
    except Exception as exc:
        NEON_ERRORS_TOTAL.labels(operation="acquire").inc()
        logger.error(
            "neondb_acquire_failed",
            error_type=type(exc).__name__,
            error_message=str(exc),
            component="neon_client",
            severity="error",
            context={},
        )
        raise
    finally:
        NEON_QUERY_DURATION.labels(operation="acquire").observe(time.perf_counter() - start)
