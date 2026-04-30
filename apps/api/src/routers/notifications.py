"""Notifications router for managing user alerts."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from src.auth.dependencies import get_current_user
from src.database.repository import mark_notification_read, query_notifications

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/")
async def list_notifications(
    limit: int = Query(20, ge=1, le=100),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Fetch recent notifications for the current user.
    Authenticated users only.
    """
    user_id = user.get("id")
    if not user_id:
        return {"results": [], "count": 0}

    results = await query_notifications(user_id=user_id, limit=limit)

    return {
        "results": results,
        "count": len(results),
    }


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """Mark a notification as read."""
    await mark_notification_read(notification_id)
    return {"status": "success"}
