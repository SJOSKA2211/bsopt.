"""Pytest configuration and global fixtures."""
from __future__ import annotations

import asyncio
import os

import pytest

# Override environment variables for local testing against Docker containers
# These should match the values in docker-compose.yml
os.environ["REDIS_URL"] = "redis://:admin@127.0.0.1:6379/0"
os.environ["REDIS_PASSWORD"] = "admin"
os.environ["RABBITMQ_URL"] = "amqp://user:admin@127.0.0.1:5672/"
os.environ["MINIO_ENDPOINT"] = "127.0.0.1:9000"
os.environ["MINIO_ACCESS_KEY"] = "admin"
os.environ["MINIO_SECRET_KEY"] = "admin_password"
os.environ["NEON_CONNECTION_STRING"] = "postgresql://neondb_owner:password@127.0.0.1:5432/neondb"
os.environ["MLFLOW_TRACKING_URI"] = "http://127.0.0.1:5000"
os.environ["RAY_ADDRESS"] = ""
os.environ["WATCHDOG_WATCH_DIR"] = "/home/kamau/bsopt./apps/api/tests/watch"

from typing import TYPE_CHECKING

from src.cache.redis_client import close_redis
from src.database.neon_client import close_pool
from src.queue.rabbitmq_client import close_rabbitmq

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_client():
    """Asynchronous FastAPI test client."""
    from httpx import ASGITransport, AsyncClient

    from src.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def auth_headers(test_user):
    """Auth headers using the test_user's ID as a Bearer token."""
    return {
        "Authorization": f"Bearer {test_user['id']}"
    }


@pytest.fixture
def client():
    """FastAPI test client."""
    from fastapi.testclient import TestClient

    from src.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session", autouse=True)
async def infrastructure_setup() -> AsyncIterator[None]:
    """Ensure infrastructure is available for tests."""
    yield
    # Cleanup
    import ray
    if ray.is_initialized():
        ray.shutdown()
    await close_redis()
    await close_rabbitmq()
    await close_pool()


@pytest.fixture
async def db_cleanup():
    """Clean up database tables after tests."""
    from src.database.neon_client import acquire
    async with acquire() as conn:
        # Note: truncate tables as needed
        await conn.execute("TRUNCATE TABLE validation_metrics, ml_experiments, scrape_runs, notifications, feature_snapshots CASCADE")
    yield


@pytest.fixture
async def test_user():
    """Create a test user in the database."""
    from uuid import uuid4

    from src.database.neon_client import acquire
    user_id = uuid4()
    async with acquire() as conn:
        await conn.execute(
            "INSERT INTO users (id, email, display_name, role) VALUES ($1, $2, $3, $4) ON CONFLICT DO NOTHING",
            user_id, f"test_{user_id}@example.com", "Test User", "admin"
        )
    return {"id": user_id}
