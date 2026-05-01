"""Storage service for abstracting MinIO operations."""

from __future__ import annotations

import gzip

import structlog

from src.config import get_settings
from src.metrics import MINIO_UPLOADS_TOTAL
from src.storage.minio_client import get_minio

logger = structlog.get_logger(__name__)


class StorageService:
    """Storage service for abstracting MinIO operations with compression."""

    @staticmethod
    async def upload_file(
        bucket: str,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        """Upload data to a MinIO bucket, with gzip if enabled and > threshold."""
        settings = get_settings()

        is_compressed = False
        if settings.enable_compression and len(data) > settings.compression_threshold_bytes:
            data = gzip.compress(data)
            is_compressed = True
            if not object_name.endswith(".gz"):
                object_name += ".gz"

        async with get_minio() as client:
            extra_args = {}
            if is_compressed:
                extra_args["ContentEncoding"] = "gzip"

            await client.put_object(
                Bucket=bucket, Key=object_name, Body=data, ContentType=content_type, **extra_args
            )
            MINIO_UPLOADS_TOTAL.labels(bucket=bucket).inc()
            logger.info(
                "minio_upload_success", bucket=bucket, key=object_name, compressed=is_compressed
            )

    @staticmethod
    async def get_presigned_url(bucket: str, object_name: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL for downloading an object."""
        async with get_minio() as client:
            url = await client.generate_presigned_url(
                "get_object", Params={"Bucket": bucket, "Key": object_name}, ExpiresIn=expires_in
            )
            return str(url)
