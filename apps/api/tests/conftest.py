"""Pytest configuration and shared fixtures for Zero-Mock testing."""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

import os
import structlog

# Override settings for local testing against docker-compose infrastructure
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["RABBITMQ_URL"] = "amqp://bsopt_user:placeholder_rabbitmq_password_20chars_min@localhost:5672/"
os.environ["MINIO_ENDPOINT"] = "http://localhost:9000"
os.environ["RAY_ADDRESS"] = ""
os.environ["MLFLOW_TRACKING_URI"] = "http://localhost:5000"
os.environ["NEON_CONNECTION_STRING"] = "postgresql://neondb_owner:npg_imM05wPNOUX8@localhost:5432/neondb"
os.environ["WATCHDOG_WATCH_DIR"] = "/tmp/bsopt_watch"

from src.main import app


@pytest.fixture
def client() -> TestClient:
    """Synchronous test client for FastAPI with lifespan support."""
    with TestClient(app) as c:
        yield c


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Asynchronous test client for FastAPI."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Backend for anyio (required by some async tests)."""
    return "asyncio"


@pytest_asyncio.fixture(autouse=True)
async def db_lifecycle():
    """Ensure all infrastructure clients are closed after each test."""
    yield
    from src.database.neon_client import close_pool
    from src.cache.redis_client import close_redis
    from src.queue.rabbitmq_client import close_rabbitmq
    
    try:
        await close_pool()
    except Exception:
        pass
        
    try:
        await close_redis()
    except Exception:
        pass
        
    try:
        await close_rabbitmq()
    except Exception:
        pass


@pytest_asyncio.fixture
async def db_cleanup() -> AsyncGenerator[None, None]:
    """Truncate tables and flush Redis/RabbitMQ before each integration test."""
    from src.database.neon_client import acquire
    from src.cache.redis_client import get_redis
    from src.queue.rabbitmq_client import get_rabbitmq_channel
    
    async with acquire() as conn:
        try:
            await conn.execute(
                """
                TRUNCATE users, option_parameters, method_results, market_data, 
                         validation_metrics, scrape_runs, notifications, 
                         ml_experiments, feature_snapshots CASCADE
                """
            )
        except Exception:
            pass
    
    try:
        redis = await get_redis()
        await redis.flushdb()
    except Exception:
        pass
        
    try:
        channel = await get_rabbitmq_channel()
        await channel.queue_purge("bs.watchdog")
    except Exception:
        pass
        
    yield
