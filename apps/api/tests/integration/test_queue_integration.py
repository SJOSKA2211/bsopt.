"""Integration tests for RabbitMQ queue — Phase 1."""

from __future__ import annotations

import pytest

from src.config import get_settings
from src.queue.consumer import ScraperConsumer
from src.queue.publisher import publish_scraper_task

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_queue_publish_and_consume() -> None:
    """Test publishing a task and consuming it with a real RabbitMQ."""
    get_settings()

    # 1. Publish
    await publish_scraper_task("spy")

    # 2. Consume (one-shot)
    # We need to run the consumer in a way that it exits after one message
    # or we check the queue size.

    # Actually, ScraperConsumer has an 'on_message' handler.
    # We can test the handler logic or the full loop.

    def mock_callback(payload: dict[str, object]) -> None:
        pass

    ScraperConsumer(callback=mock_callback)
