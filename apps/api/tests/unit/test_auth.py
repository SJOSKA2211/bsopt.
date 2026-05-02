"""Unit tests for authentication dependencies."""
from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.auth.dependencies import get_admin_user, get_current_user, get_current_user_id
from src.database.repository import save_user


class MockCredentials:
    pass

    def __init__(self, token: str) -> None:
        self.credentials = token


@pytest.mark.unit
@pytest.mark.asyncio
async def test_auth_dependencies() -> None:
    # 1. Test missing credentials
    with pytest.raises(HTTPException) as exc:
        await get_current_user(None)
    assert exc.value.status_code == 401

    # 2. Test invalid token (not a UUID)
    with pytest.raises(HTTPException) as exc:
        await get_current_user(MockCredentials("invalid-uuid"))  # type: ignore
    assert exc.value.status_code == 401

    # 3. Test user not found
    user_id = uuid4()
    with pytest.raises(HTTPException) as exc:
        await get_current_user(MockCredentials(str(user_id)))  # type: ignore
    assert exc.value.status_code == 401

    # 4. Test success
    email = f"test_{uuid4().hex[:8]}@example.com"
    await save_user(user_id, email, "Test User", "researcher")
    user = await get_current_user(MockCredentials(str(user_id)))  # type: ignore
    assert user["id"] == user_id
    assert user["email"] == email

    # 5. Test get_current_user_id
    ret_id = await get_current_user_id(user)
    assert ret_id == user_id

    # 6. Test admin check failure
    with pytest.raises(HTTPException) as exc:
        await get_admin_user(user)
    assert exc.value.status_code == 403

    # 7. Test admin check success
    admin_id = uuid4()
    await save_user(admin_id, f"admin_{uuid4().hex[:8]}@example.com", "Admin User", "admin")
    admin_user = await get_current_user(MockCredentials(str(admin_id)))  # type: ignore
    ret_admin = await get_admin_user(admin_user)
    assert ret_admin["id"] == admin_id
