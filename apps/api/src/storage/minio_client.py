"""MinIO client using aioboto3."""

from __future__ import annotations

from typing import Any

import aioboto3

from src.config import get_settings


class MinioClient:
    """Async client for MinIO (S3-compatible)."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.session = aioboto3.Session()

    def get_client(self) -> Any:
        """Return an async context manager for the S3 client."""
        # Ensure endpoint_url has protocol
        endpoint = self.settings.minio_endpoint
        if not endpoint.startswith("http"):
            endpoint = f"http://{endpoint}"

        return self.session.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=self.settings.minio_access_key,
            aws_secret_access_key=self.settings.minio_secret_key,
            region_name="us-east-1",
        )
