"""Main FastAPI application for Bsopt — Phase 10."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
from typing import TYPE_CHECKING

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from src.cache.redis_client import close_redis, get_redis
from src.database.neon_client import close_pool, get_pool
from src.queue.rabbitmq_client import close_rabbitmq, get_rabbitmq
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
    from collections.abc import AsyncGenerator

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown events."""
    logger.info("app_starting")

    # Initialize infrastructure
    await get_pool()
    await get_redis()
    await get_rabbitmq()

    # Start background tasks
    pubsub_task = asyncio.create_task(start_redis_pubsub_listener())

    yield

    # Shutdown infrastructure
    pubsub_task.cancel()
    with suppress(asyncio.CancelledError):
        await pubsub_task

    await close_pool()
    await close_redis()
    await close_rabbitmq()

    logger.info("app_stopped")


app = FastAPI(
    title="Bsopt API",
    description="Black-Scholes Options Research Platform API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Health check (unprefixed)
app.include_router(health.router)

# API v1 (prefixed)
app.include_router(pricing.router, prefix="/api/v1")
app.include_router(experiments.router, prefix="/api/v1")
app.include_router(mlops.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(market_data.router, prefix="/api/v1")
app.include_router(scrapers.router, prefix="/api/v1")
app.include_router(websocket.router, prefix="/api/v1")
app.include_router(downloads.router, prefix="/api/v1")


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Welcome to Bsopt API", "docs": "/docs"}
