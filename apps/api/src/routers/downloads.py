"""Downloads router for exporting research data — Python 3.14."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException

from src.auth.dependencies import get_current_user_id
from src.storage.storage_service import StorageService

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/downloads", tags=["Downloads"])


@router.get("/generate-url")
async def get_download_url(
    bucket: str, object_name: str, user_id: str = Depends(get_current_user_id)
) -> dict[str, str]:
    """Generate a presigned URL for downloading an artifact."""
    try:
        url = await StorageService.get_presigned_url(bucket, object_name)
        return {"url": url}
    except Exception as exc:
        logger.error(
            "presigned_url_generation_failed", bucket=bucket, key=object_name, error=str(exc)
        )
        raise HTTPException(status_code=500, detail="Could not generate download URL")
