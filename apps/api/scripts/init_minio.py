"""Initialize MinIO buckets for bsopt."""
from __future__ import annotations

import asyncio

import structlog

from src.config import get_settings
from src.storage.minio_client import get_minio

logger = structlog.get_logger(__name__)


async def init_minio() -> None:
    settings = get_settings()
    buckets = [
        settings.minio_bucket_exports,
        settings.minio_bucket_models,
        settings.minio_bucket_scraper
    ]

    async with get_minio() as client:
        for bucket in buckets:
            try:
                await client.create_bucket(Bucket=bucket)
                logger.info("minio_bucket_created", bucket=bucket)
            except Exception as exc:
                if "BucketAlreadyOwnedByYou" in str(exc) or "BucketAlreadyExists" in str(exc):
                    logger.info("minio_bucket_exists", bucket=bucket)
                else:
                    logger.error("minio_bucket_creation_failed", bucket=bucket, error=str(exc))


if __name__ == "__main__":
    asyncio.run(init_minio())
