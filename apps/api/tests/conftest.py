"""Pytest configuration and global fixtures."""
from __future__ import annotations
import pytest
import asyncio
from typing import AsyncIterator
from src.database.neon_client import get_pool
from src.cache.redis_client import get_redis, close_redis
from src.queue.rabbitmq_client import get_rabbitmq_connection, close_rabbitmq

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session", autouse=True)
async def infrastructure_setup() -> AsyncIterator[None]:
    """Ensure infrastructure is available for tests."""
    # In a real environment, this would check if services are up.
    # The Zero-Mock policy means we hit real services.
    yield
    # Cleanup
    await close_redis()
    await close_rabbitmq()
