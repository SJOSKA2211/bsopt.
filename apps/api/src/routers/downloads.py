"""Downloads router for exporting experiment data — Python 3.14."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from src.analysis.statistics import export_to_csv, export_to_json
from src.auth.dependencies import get_current_user
from src.database.repository import query_experiments
from src.storage.storage_service import StorageService

router = APIRouter(prefix="/downloads", tags=["downloads"])
storage = StorageService()


@router.post("/export")
async def export_data(
    format: str = Query("csv", regex="^(csv|json)$"),
    method_type: str | None = None,
    market_source: str | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """
    Export experiment results to a file and return a presigned download URL.
    Authenticated users only.
    """
    # 1. Fetch data
    results = await query_experiments(
        method_type=method_type, market_source=market_source, limit=1000
    )
    if not results:
        raise HTTPException(status_code=404, detail="No data found to export")

    # 2. Transform
    if format == "csv":
        content = export_to_csv(results)
        content_type = "text/csv"
    else:
        content = export_to_json(results)
        content_type = "application/json"

    # 3. Upload to MinIO
    filename = f"export_{uuid4()}.{format}"
    await storage.upload_file(
        bucket="bsopt-exports",
        object_name=filename,
        file_data=content.encode("utf-8"),
        content_type=content_type,
    )

    # 4. Generate presigned URL
    url = await storage.get_presigned_url(bucket="bsopt-exports", object_name=filename)

    return {"download_url": url, "filename": filename}
