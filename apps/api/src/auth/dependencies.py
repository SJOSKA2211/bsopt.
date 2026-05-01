"""Authentication dependencies for FastAPI — Python 3.14."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.database.repository import get_user_by_id

security = HTTPBearer(auto_error=False)


class MockCredentials:
    """Helper class to wrap a token for get_current_user without requiring HTTPBearer headers."""

    def __init__(self, token: str) -> None:
        self.credentials = token
        self.scheme = "Bearer"


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(security)],
) -> dict[str, str | UUID]:
    """
    Validate the authentication token and return the user record.
    For this project, we assume the token is a UUID (session ID or sub from NextAuth).
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        user_id = UUID(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_admin_user(
    current_user: Annotated[dict[str, str | UUID], Depends(get_current_user)],
) -> dict[str, str | UUID]:
    """Validate that the current user has the admin role."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


async def get_current_user_id(
    current_user: Annotated[dict[str, str | UUID], Depends(get_current_user)],
) -> UUID:
    """Return the UUID of the currently authenticated user."""
    return current_user["id"]  # type: ignore
