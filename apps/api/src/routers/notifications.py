"""Notifications router — Python 3.14."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from src.auth.dependencies import get_current_user_id
from src.database.repository import mark_notification_read, query_notifications

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/")
async def get_user_notifications(
    limit: int = 20,
    user_id: str = Depends(get_current_user_id)
) -> dict[str, Any]:
    """Fetch notifications for the current user."""
    results = await query_notifications(user_id=user_id, limit=limit)
    return {"results": results}


@router.post("/{notification_id}/read")
async def read_notification(
    notification_id: str,
    user_id: str = Depends(get_current_user_id)
) -> dict[str, str]:
    """Mark a notification as read."""
    await mark_notification_read(notification_id)
    return {"status": "success"}
