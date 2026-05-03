"""Unit tests for storage service — Zero-Mock."""

from __future__ import annotations

import pytest

from src.config import get_settings
from src.storage.minio_client import get_minio
from src.storage.storage_service import StorageService


@pytest.mark.unit
@pytest.mark.asyncio
async def test_storage_upload_lifecycle() -> None:
    settings = get_settings()
    bucket = settings.minio_bucket_exports
    obj_name = "test_upload.txt"
    data = b"Hello MinIO"

    # Ensure bucket exists
    async with get_minio() as client:
        try:
            await client.head_bucket(Bucket=bucket)
        except Exception:
            await client.create_bucket(Bucket=bucket)

    await StorageService.upload_file(bucket, obj_name, data)

    # Verify via presigned URL (just check if it returns a string)
    url = await StorageService.get_presigned_url(bucket, obj_name)
    assert isinstance(url, str)
    assert "http" in url


@pytest.mark.unit
@pytest.mark.asyncio
async def test_storage_upload_compression() -> None:
    settings = get_settings()
    bucket = settings.minio_bucket_exports
    obj_name = "test_comp.txt"
    # Create data larger than 1024 threshold
    data = b"A" * 2000

    await StorageService.upload_file(bucket, obj_name, data)

    # Verify it was compressed (object name should have .gz)
    async with get_minio() as client:
        res = await client.list_objects_v2(Bucket=bucket, Prefix="test_comp")
        keys = [obj["Key"] for obj in res.get("Contents", [])]
        assert "test_comp.txt.gz" in keys
