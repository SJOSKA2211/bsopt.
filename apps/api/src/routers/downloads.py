"""Download router for exporting research results."""

from __future__ import annotations

import io
from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/downloads", tags=["downloads"])


@router.get("/{export_format}")
async def download_results(export_format: str, experiment_id: str | None = None) -> Any:
    """Export experiment results in CSV, JSON, or XLSX format."""
    if export_format not in ("csv", "json", "xlsx"):
        raise HTTPException(status_code=400, detail="Unsupported format")

    # In a real scenario, we'd fetch method_results for the experiment_id
    from src.database.neon_client import acquire

    async with acquire() as conn:
        query = """
            SELECT mr.method_type, mr.computed_price, op.underlying_price, op.strike_price
            FROM method_results mr
            JOIN option_parameters op ON mr.option_id = op.id
            ORDER BY mr.id DESC
            LIMIT 100
        """
        rows = await conn.fetch(query)
        data = [dict(r) for r in rows]

    if not data:
        raise HTTPException(status_code=404, detail="No results found to export")

    df = pd.DataFrame(data)

    if export_format == "csv":
        stream = io.StringIO()
        df.to_csv(stream, index=False)
        return Response(
            content=stream.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=results.csv"},
        )

    if export_format == "json":
        return Response(
            content=df.to_json(orient="records"),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=results.json"},
        )

    if export_format == "xlsx":
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False)
        return StreamingResponse(
            io.BytesIO(output.getvalue()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=results.xlsx"},
        )
