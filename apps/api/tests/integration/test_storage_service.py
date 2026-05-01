"""Integration tests for storage service — Phase 1."""
from __future__ import annotations

import gzip

import pytest

from src.config import get_settings
from src.storage.storage_service import StorageService

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_upload_and_presigned_url():
    """Test uploading a file (with compression) and generating a presigned URL."""
    settings = get_settings()
    storage = StorageService()
    bucket = settings.minio_bucket_exports
    object_name = "test_upload.txt"
    # Small data (no compression)
    data = b"hello world"

    await storage.upload_file(bucket, object_name, data)

    url = await storage.get_presigned_url(bucket, object_name)
    assert "http" in url
    assert object_name in url


@pytest.mark.asyncio
async def test_upload_with_compression():
    """Test that files above threshold are gzipped."""
    settings = get_settings()
    storage = StorageService()
    bucket = settings.minio_bucket_exports
    # Large data (> 1024 bytes threshold from settings)
    data = b"a" * 2000
    object_name = "large_file.txt"

    await storage.upload_file(bucket, object_name, data)

    # Check if object exists with .gz extension
    from src.storage.minio_client import get_minio
    async with get_minio() as client:
        res = await client.get_object(Bucket=bucket, Key=f"{object_name}.gz")
        body = await res["Body"].read()
        assert gzip.decompress(body) == data
        assert res["ContentEncoding"] == "gzip"


@pytest.mark.asyncio
async def test_upload_already_gzipped_extension():
    """Test that .gz is not appended twice."""
    settings = get_settings()
    storage = StorageService()
    bucket = settings.minio_bucket_exports
    data = b"a" * 2000
    object_name = "manual.gz"

    await storage.upload_file(bucket, object_name, data)

    from src.storage.minio_client import get_minio
    async with get_minio() as client:
        # Should NOT be manual.gz.gz
        res = await client.get_object(Bucket=bucket, Key=object_name)
        assert res is not None
