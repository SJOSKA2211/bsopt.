"""Main entry point for bsopt FastAPI backend."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_client import make_asgi_app

from src.config import get_settings
from src.data.watchdog_handler import start_watchdog
from src.database.neon_client import get_pool
from src.logging_config import setup_logging
from src.routers import (
    downloads,
    experiments,
    health,
    market_data,
    mlops,
    notifications,
    pricing,
    scrapers,
    websocket,
)
from src.websocket.channels import start_redis_pubsub_listener

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifecycle management for infrastructure connections."""
    settings = get_settings()

    # 1. Initialize DB Pool (non-blocking failure)
    try:
        await get_pool()
    except Exception as exc:
        logger.error("db_connection_failed_at_startup", error=str(exc))

    # 2. Start Redis Pub/Sub listener for WebSockets (runs in background)
    pubsub_task = asyncio.create_task(start_redis_pubsub_listener())

    # 3. Start Watchdog (starts its own background thread)
    observer = start_watchdog(settings.watchdog_watch_dir)

    logger.info("app_startup_complete", step="init", rows=0)

    yield

    # Shutdown sequence
    logger.info("app_shutdown_started")
    observer.stop()
    observer.join()
    pubsub_task.cancel()

    from src.database.neon_client import close_pool

    await close_pool()
    logger.info("app_shutdown_complete")


# Initialize logging
setup_logging(debug=get_settings().debug)

app = FastAPI(
    title="bsopt API",
    version="1.0.0",
    lifespan=lifespan,
    description="Black-Scholes Options Research Platform API",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this in production via env
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compression
app.add_middleware(GZipMiddleware, minimum_size=1000)
try:
    from brotli_asgi import BrotliMiddleware

    app.add_middleware(BrotliMiddleware, minimum_size=1000)
except ImportError:
    logger.warning("brotli_asgi_not_found", msg="Brotli compression disabled")

# Prometheus /metrics endpoint (ASGI mount)
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Router registration
app.include_router(health.router)
app.include_router(pricing.router, prefix="/api/v1")
app.include_router(market_data.router, prefix="/api/v1")
app.include_router(scrapers.router, prefix="/api/v1")
app.include_router(mlops.router, prefix="/api/v1")
app.include_router(experiments.router, prefix="/api/v1")
app.include_router(downloads.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(websocket.router)
