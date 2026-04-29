"""Notifications management router."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends

from src.auth.dependencies import get_current_user_id
from src.database.neon_client import acquire

if TYPE_CHECKING:
    from uuid import UUID

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/")
async def get_notifications(
    user_id: UUID = Depends(get_current_user_id),
) -> list[dict[str, Any]]:
    """Retrieve all notifications for the authenticated user."""
    async with acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM notifications WHERE user_id = $1 ORDER BY created_at DESC",
            user_id,
        )
        return [dict(row) for row in rows]


@router.post("/{notification_id}/read")
async def mark_as_read(
    notification_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
) -> dict[str, str]:
    """Mark a specific notification as read."""
    async with acquire() as conn:
        await conn.execute(
            "UPDATE notifications SET read = TRUE WHERE id = $1 AND user_id = $2",
            notification_id,
            user_id,
        )
        return {"status": "success"}
