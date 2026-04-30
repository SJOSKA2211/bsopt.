"""WebSocket router for real-time bidirectional communication."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from src.websocket.manager import manager

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.websocket("/ws/{channel}")
async def websocket_endpoint(
    websocket: WebSocket,
    channel: str,
    user_id: str | None = Query(None),
) -> None:
    """
    Handle WebSocket connections for specific channels.
    Includes user_id for targeted notifications.
    """
    await manager.connect(websocket, channel, user_id)
    try:
        while True:
            # Keep the connection alive and handle incoming messages if needed
            data = await websocket.receive_json()
            logger.debug("websocket_message_received", channel=channel, data=data)
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel, user_id)
    except Exception as exc:
        logger.error("websocket_error", error=str(exc), channel=channel)
        manager.disconnect(websocket, channel, user_id)
