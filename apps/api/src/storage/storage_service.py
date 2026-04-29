"""Storage service for handling file uploads to MinIO with compression support."""

from __future__ import annotations

import gzip

from src.config import get_settings
from src.metrics import MINIO_UPLOADS_TOTAL
from src.storage.minio_client import MinioClient


def _construct_object_name(prefix: str, filename: str) -> str:
    """Pure function to construct a MinIO object name."""
    p = prefix.strip("/")
    f = filename.strip("/")
    if not p:
        return f
    return f"{p}/{f}"


class StorageService:
    """Service layer for MinIO operations."""

    def __init__(self) -> None:
        self.minio = MinioClient()
        self.settings = get_settings()

    async def upload_file(
        self, bucket: str, object_name: str, file_data: bytes, content_type: str
    ) -> None:
        """Upload a file to a specific MinIO bucket with optional compression."""
        if self.settings.enable_compression and len(file_data) > 1024:
            # Compress if > 1KB
            file_data = gzip.compress(file_data)
            if not object_name.endswith(".gz"):
                object_name += ".gz"
            content_type = "application/gzip"

        async with self.minio.get_client() as client:
            await client.put_object(
                Bucket=bucket,
                Key=object_name,
                Body=file_data,
                ContentType=content_type,
            )
            MINIO_UPLOADS_TOTAL.labels(bucket=bucket).inc()

    async def get_presigned_url(self, bucket: str, object_name: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL for downloading a file."""
        async with self.minio.get_client() as client:
            url: str = await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": object_name},
                ExpiresIn=expires_in,
            )
            return url
