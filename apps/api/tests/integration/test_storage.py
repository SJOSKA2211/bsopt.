"""Integration tests for MinIO storage service."""

from __future__ import annotations

import pytest
from src.storage.storage_service import StorageService


@pytest.mark.integration
@pytest.mark.asyncio
async def test_storage_upload_download() -> None:
    """Verify file upload and presigned URL generation with MinIO."""
    service = StorageService()
    bucket = "bsopt-test"
    object_name = "test_file.txt"
    file_data = b"Hello MinIO" * 200  # > 1KB to trigger compression
    content_type = "text/plain"

    # 1. Create bucket if not exists
    async with service.minio.get_client() as client:
        try:
            await client.create_bucket(Bucket=bucket)
        except Exception:
            pass

    # 2. Upload
    await service.upload_file(bucket, object_name, file_data, content_type)

    # 3. Get URL
    url = await service.get_presigned_url(bucket, object_name + ".gz")
    assert "http" in url
    assert bucket in url
