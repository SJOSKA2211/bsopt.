"""Authentication dependencies for FastAPI backend."""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import Header, HTTPException, status

logger = structlog.get_logger(__name__)


async def get_current_user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    """
    Extract the authenticated user ID from the request headers.
    In production, this header is set by the reverse proxy (Nginx)
    after validating the session with NextAuth.
    """
    if not x_user_id:
        logger.warning("unauthorized_access_attempt", step="auth")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User-ID header",
        )
    return x_user_id
