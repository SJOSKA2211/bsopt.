"""Database initialization and schema migration script."""

from __future__ import annotations

import asyncio
from pathlib import Path

import structlog

from src.database.neon_client import get_pool

logger = structlog.get_logger(__name__)


async def init_db() -> None:
    """Read the initial schema SQL and execute it against NeonDB."""
    schema_path = (
        Path(__file__).parent.parent.parent.parent / "migrations" / "001_initial_schema.sql"
    )

    if not schema_path.exists():
        logger.error("schema_file_missing", path=str(schema_path))
        return

    logger.info("db_init_started", path=str(schema_path))

    schema_sql = Path(schema_path).read_text(encoding="utf-8")

    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            await conn.execute(schema_sql)
            logger.info("db_init_completed")
        except Exception as exc:
            logger.error("db_init_failed", error=str(exc))
        finally:
            await pool.close()


if __name__ == "__main__":
    asyncio.run(init_db())
