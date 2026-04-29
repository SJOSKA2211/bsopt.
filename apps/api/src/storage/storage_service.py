"""Storage service for MinIO operations — Phase 1."""

from __future__ import annotations

import uuid

import structlog

from src.metrics import MINIO_UPLOADS_TOTAL
from src.storage.minio_client import get_minio_client

logger = structlog.get_logger(__name__)


async def upload_object(
    bucket: str, file_data: bytes, filename: str, content_type: str = "application/octet-stream"
) -> str:
    """Upload data to MinIO and return the object name."""
    object_name = f"{uuid.uuid4()}-{filename}"

    async with await get_minio_client() as s3:
        await s3.put_object(
            Bucket=bucket, Key=object_name, Body=file_data, ContentType=content_type
        )

    MINIO_UPLOADS_TOTAL.labels(bucket=bucket).inc()
    logger.info(
        "minio_upload_success", bucket=bucket, object_name=object_name, step="storage", rows=0
    )
    return object_name


async def get_presigned_url(bucket: str, object_name: str, expires_in: int = 3600) -> str:
    """Generate a presigned URL for downloading an object."""
    async with await get_minio_client() as s3:
        url = await s3.generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": object_name}, ExpiresIn=expires_in
        )
    return str(url)
