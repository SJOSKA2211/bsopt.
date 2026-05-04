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
    
    # Case 1: Doesn't end with .gz, should add it
    obj_name1 = "test_comp.txt"
    data = b"A" * 2000
    await StorageService.upload_file(bucket, obj_name1, data)

    # Case 2: Already ends with .gz, should NOT add another
    obj_name2 = "test_already.gz"
    await StorageService.upload_file(bucket, obj_name2, data)

    async with get_minio() as client:
        res = await client.list_objects_v2(Bucket=bucket, Prefix="test_")
        keys = [obj["Key"] for obj in res.get("Contents", [])]
        assert "test_comp.txt.gz" in keys
        assert "test_already.gz" in keys
        assert "test_already.gz.gz" not in keys
