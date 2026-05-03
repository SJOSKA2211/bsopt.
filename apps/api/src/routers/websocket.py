"""WebSocket router for real-time communication — Python 3.14."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from src.auth.dependencies import get_current_user
from src.websocket.manager import manager

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/ws", tags=["WebSocket"])


@router.websocket("/{channel}")
async def websocket_endpoint(websocket: WebSocket, channel: str, token: str = Query(...)) -> None:
    """Handle WebSocket connections with token-based authentication."""
    # We use Query(token) because standard headers are hard for browser WebSockets
    from src.auth.dependencies import MockCredentials

    try:
        user = await get_current_user(MockCredentials(token))  # type: ignore
        user_id = str(user["id"])
    except Exception:
        await websocket.close(code=4001, reason="Invalid authentication token")
        return

    await manager.connect(websocket, channel, user_id=user_id)
    try:
        while True:
            # Keep connection alive and wait for client messages if needed
            # For now, we only push data, so we just wait for disconnection
            data = await websocket.receive_text()
            logger.info("websocket_message_received", channel=channel, user_id=user_id, data=data)
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel, user_id=user_id)
    except Exception as exc:
        logger.error("websocket_error", error=str(exc))
        manager.disconnect(websocket, channel, user_id=user_id)
