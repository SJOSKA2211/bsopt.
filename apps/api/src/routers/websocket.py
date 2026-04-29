"""WebSocket router for real-time updates."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.websocket.manager import manager

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/{channel}")
async def websocket_endpoint(websocket: WebSocket, channel: str) -> None:
    """Accept and manage WebSocket connections per channel."""
    await manager.connect(websocket, channel)
    try:
        while True:
            # Keep-alive or handle incoming messages (though mainly for broadcast)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)
    except Exception:
        manager.disconnect(websocket, channel)
