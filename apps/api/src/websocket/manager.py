"""WebSocket connection manager for real-time updates."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from src.metrics import WS_CONNECTIONS_ACTIVE

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = structlog.get_logger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections and broadcasting."""

    def __init__(self) -> None:
        # Map channel names to lists of connected WebSockets
        self.active_connections: dict[str, list[WebSocket]] = {
            "metrics": [],
            "experiments": [],
            "scrapers": [],
            "notifications": [],
        }
        # Map user_ids to lists of connected WebSockets (specifically for notifications)
        self.user_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str, user_id: str | None = None) -> None:
        """Accept a connection and add it to the specified channel."""
        if channel not in self.active_connections:
            await websocket.close(code=1003, reason=f"Channel {channel} not supported")
            return

        await websocket.accept()
        self.active_connections[channel].append(websocket)

        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(websocket)

        WS_CONNECTIONS_ACTIVE.labels(channel=channel).inc()
        logger.info(
            "websocket_connected",
            channel=channel,
            user_id=user_id,
            connections=len(self.active_connections[channel]),
        )

    def disconnect(self, websocket: WebSocket, channel: str, user_id: str | None = None) -> None:
        """Remove a connection from the specified channel."""
        if channel in self.active_connections and websocket in self.active_connections[channel]:
            self.active_connections[channel].remove(websocket)
            WS_CONNECTIONS_ACTIVE.labels(channel=channel).dec()

        if (
            user_id
            and user_id in self.user_connections
            and websocket in self.user_connections[user_id]
        ):
            self.user_connections[user_id].remove(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

        logger.info("websocket_disconnected", channel=channel, user_id=user_id)

    async def broadcast(self, channel: str, message: dict[str, Any]) -> None:
        """Broadcast a message to all connections in a channel."""
        if channel not in self.active_connections:
            return

        dead_connections = []
        for connection in self.active_connections[channel]:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)

        # Cleanup dead connections
        for dead in dead_connections:
            # Note: without user_id tracking in broadcast, we might miss
            # disconnecting from user_connections but usually they'll be cleaned
            # up on next specific message or disconnect call.
            self.disconnect(dead, channel)

    async def send_personal_message(self, message: dict[str, Any], user_id: str) -> None:
        """Send a message to all connections belonging to a specific user."""
        if user_id not in self.user_connections:
            return

        dead_connections = []
        for connection in self.user_connections[user_id]:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)

        for dead in dead_connections:
            if user_id in self.user_connections and dead in self.user_connections[user_id]:
                self.user_connections[user_id].remove(dead)

        if user_id in self.user_connections and not self.user_connections[user_id]:
            del self.user_connections[user_id]


# Global manager instance
manager = ConnectionManager()
