"""MinIO (S3-compatible) client for bsopt — aioboto3."""

from __future__ import annotations

from typing import Any

import aioboto3
import structlog

from src.config import get_settings

logger = structlog.get_logger(__name__)
_session = aioboto3.Session()


def get_minio_client() -> Any:
    """Return an async context manager for MinIO client."""
    settings = get_settings()
    return _session.client(
        "s3",
        endpoint_url=f"http://{settings.minio_endpoint}",
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
    )
