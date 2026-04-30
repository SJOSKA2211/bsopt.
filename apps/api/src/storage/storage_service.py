"""Storage service for abstracting MinIO operations."""

from __future__ import annotations

import structlog

from src.metrics import MINIO_UPLOADS_TOTAL
from src.storage.minio_client import get_minio_client

logger = structlog.get_logger(__name__)


async def upload_object(
    bucket: str, object_name: str, data: bytes, content_type: str = "application/octet-stream"
) -> None:
    """Upload data to a MinIO bucket."""
    async with get_minio_client() as client:
        await client.put_object(Bucket=bucket, Key=object_name, Body=data, ContentType=content_type)
        MINIO_UPLOADS_TOTAL.labels(bucket=bucket).inc()
        logger.info("minio_upload_success", bucket=bucket, key=object_name)


async def get_presigned_url(bucket: str, object_name: str, expires_in: int = 3600) -> str:
    """Generate a presigned URL for downloading an object."""
    async with get_minio_client() as client:
        return await client.generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": object_name}, ExpiresIn=expires_in
        )
