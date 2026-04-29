"""Unit tests for storage service helpers."""

from __future__ import annotations

import pytest

from src.storage.storage_service import _construct_object_name


@pytest.mark.unit
def test_object_name_construction() -> None:
    """Verify that object names are correctly constructed."""
    assert _construct_object_name("exports", "results.csv") == "exports/results.csv"
    assert _construct_object_name("", "results.csv") == "results.csv"
    assert _construct_object_name("models/", "model.pkl") == "models/model.pkl"


@pytest.mark.unit
def test_object_name_trimming() -> None:
    """Verify that slashes are trimmed correctly."""
    assert _construct_object_name("/exports/", "/results.csv/") == "exports/results.csv"
    assert _construct_object_name("///", "file.txt") == "file.txt"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_storage_upload_and_presigned_url() -> None:
    """Verify file upload to MinIO and presigned URL generation."""
    from src.storage.storage_service import StorageService
    service = StorageService()
    bucket = service.settings.minio_bucket_exports
    object_name = "test_upload.txt"
    data = b"Hello MinIO"
    
    # Ensure bucket exists
    async with service.minio.get_client() as client:
        try:
            await client.create_bucket(Bucket=bucket)
        except Exception:
            pass # Already exists
            
    await service.upload_file(bucket, object_name, data, "text/plain")
    
    url = await service.get_presigned_url(bucket, object_name)
    assert "http" in url
    assert object_name in url


@pytest.mark.unit
@pytest.mark.asyncio
async def test_storage_compression() -> None:
    """Verify that large files are compressed in MinIO."""
    from src.storage.storage_service import StorageService
    service = StorageService()
    service.settings.enable_compression = True
    bucket = service.settings.minio_bucket_exports
    object_name = "large_test.json"
    
    # Create large data > 1KB
    large_data = b"{\"data\": \"" + b"x" * 2000 + b"\"}"
    
    await service.upload_file(bucket, object_name, large_data, "application/json")
    
    # Check if .gz was appended
    compressed_name = f"{object_name}.gz"
    
    async with service.minio.get_client() as client:
        response = await client.get_object(Bucket=bucket, Key=compressed_name)
        body = await response["Body"].read()
        
        # Verify it's smaller or different from original
        assert len(body) < len(large_data)
        
        import gzip
        decompressed = gzip.decompress(body)
        assert decompressed == large_data


@pytest.mark.unit
@pytest.mark.asyncio
async def test_storage_compression_already_gz() -> None:
    """Verify that filenames already ending in .gz are not double-appended."""
    from src.storage.storage_service import StorageService
    service = StorageService()
    service.settings.enable_compression = True
    bucket = service.settings.minio_bucket_exports
    object_name = "already.gz"
    data = b"x" * 2000
    
    await service.upload_file(bucket, object_name, data, "application/octet-stream")
    
    async with service.minio.get_client() as client:
        # Should NOT be already.gz.gz
        response = await client.get_object(Bucket=bucket, Key=object_name)
        assert response is not None
