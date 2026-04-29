"""MinIO client using aioboto3 — Phase 1."""

from __future__ import annotations

from typing import Any

import aioboto3
import structlog

from src.config import get_settings

logger = structlog.get_logger(__name__)
_session = aioboto3.Session()


async def get_minio_client() -> Any:
    """Return an async MinIO (S3) client context manager."""
    settings = get_settings()
    return _session.client(
        "s3",
        endpoint_url=f"http://{settings.minio_endpoint}",
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        region_name="us-east-1",
    )


async def ensure_buckets() -> None:
    """Ensure required buckets exist in MinIO."""
    settings = get_settings()
    buckets = [
        settings.minio_bucket_exports,
        settings.minio_bucket_models,
        settings.minio_bucket_scraper,
    ]

    async with await get_minio_client() as s3:
        for bucket in buckets:
            try:
                await s3.head_bucket(Bucket=bucket)
            except Exception:
                await s3.create_bucket(Bucket=bucket)
                logger.info("minio_bucket_created", bucket=bucket, step="init", rows=0)
