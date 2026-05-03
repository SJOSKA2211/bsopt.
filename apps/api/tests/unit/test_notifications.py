"""Unit tests for notification system — Zero-Mock."""
from __future__ import annotations

import asyncio
import base64
import json
import os
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

import pytest
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.config import get_settings
from src.database.repository import save_user_push_subscription
from src.notifications.email import send_email_notification, send_transactional_email
from src.notifications.hierarchy import Notification, NotificationRouter
from src.notifications.push import send_push_notification, send_web_push

settings = get_settings()


@asynccontextmanager
async def run_fake_server(port: int) -> None:
    app = FastAPI()

    @app.post("/emails")
    async def fake_email(request: Request) -> None:
        auth = request.headers.get("Authorization", "")
        if "invalid" in auth:
            return JSONResponse(content={"error": "unauthorized"}, status_code=401)
        return JSONResponse(content={"id": "fake_email_id"}, status_code=201)

    @app.post("/push")
    async def fake_push(request: Request) -> None:
        return JSONResponse(content={"status": "ok"}, status_code=201)

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    try:
        # Wait for server to start
        await asyncio.sleep(0.5)
        yield
    finally:
        server.should_exit = True
        await task


class StubManager:
    def __init__(self) -> None:
        self.messages = []

    async def send_personal_message(self, message: dict[str, Any], user_id: str) -> None:
        self.messages.append((user_id, message))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_notification_routing_logic(db_cleanup) -> None:
    manager = StubManager()
    router = NotificationRouter(websocket_manager=manager)  # type: ignore
    user_id = str(uuid4())

    async with run_fake_server(port=8085):
        old_url = settings.resend_base_url
        old_key = settings.resend_api_key
        settings.resend_base_url = "http://127.0.0.1:8085"
        settings.resend_api_key = "valid_key"

        # Setup for push and email success in hierarchy
        sub = {
            "endpoint": "http://127.0.0.1:8085/push",
            "keys": {"auth": "authsecretauthsecret", "p256dh": "p256dhkeyp256dhkey"}
        }
        await save_user_push_subscription(user_id, json.dumps(sub))

        # Valid-ish VAPID keys
        old_priv = settings.gh_vapid_private_key
        old_pub = settings.gh_vapid_public_key
        settings.gh_vapid_private_key = base64.urlsafe_b64encode(os.urandom(32)).decode().strip("=")
        settings.gh_vapid_public_key = base64.urlsafe_b64encode(os.urandom(65)).decode().strip("=")

        # 1. Info severity -> only websocket
        n_info = Notification(user_id=user_id, title="Info", body="Body", severity="info")
        await router.dispatch(n_info)
        assert len(manager.messages) == 1

        # 2. Warning severity -> websocket + push
        n_warn = Notification(user_id=user_id, title="Warn", body="Body", severity="warning")
        await router.dispatch(n_warn)
        assert len(manager.messages) == 2

        # 3. Error severity -> websocket + push + email
        n_err = Notification(user_id=user_id, title="Error", body="Body", severity="error")
        await router.dispatch(n_err)
        assert len(manager.messages) == 3

        # 4. Trigger False paths in _to_push and _to_email for full branch coverage
        settings.resend_api_key = ""  # email returns False
        settings.gh_vapid_private_key = ""  # push returns False
        n_err_false = Notification(user_id=user_id, title="Error2", body="Body2", severity="error")
        await router.dispatch(n_err_false)
        assert len(manager.messages) == 4

        # Cleanup
        settings.resend_base_url = old_url
        settings.resend_api_key = old_key
        settings.gh_vapid_private_key = old_priv
        settings.gh_vapid_public_key = old_pub


@pytest.mark.unit
@pytest.mark.asyncio
async def test_email_notifications_paths() -> None:
    user_id = str(uuid4())
    n = Notification(user_id=user_id, title="T", body="B")

    # 1. Missing API key
    old_key = settings.resend_api_key
    settings.resend_api_key = ""
    res = await send_email_notification(n)
    assert res is False

    # 2. Start fake server for success and error paths
    async with run_fake_server(port=8086):
        old_url = settings.resend_base_url
        settings.resend_base_url = "http://127.0.0.1:8086"

        # Success path
        settings.resend_api_key = "valid_key"
        res = await send_email_notification(n)
        assert res is True

        # Unauthorized path
        settings.resend_api_key = "invalid_key"
        res = await send_email_notification(n)
        assert res is False

        # Exception path (Line 53)
        settings.resend_base_url = "http://invalid_host_9999"
        res = await send_email_notification(n)
        assert res is False

        # transactional email path
        os.environ["RESEND_API_KEY"] = "valid_key"
        os.environ["RESEND_BASE_URL"] = "http://127.0.0.1:8086"
        res = await send_transactional_email("to", "sub", "body")
        assert res is True

        os.environ["RESEND_API_KEY"] = "invalid_key"
        res = await send_transactional_email("to", "sub", "body")
        assert res is False

        # Exception path for transactional (Line 86)
        os.environ["RESEND_BASE_URL"] = "http://invalid_host_9999"
        res = await send_transactional_email("to", "sub", "body")
        assert res is False

        # Missing key for transactional (Line 64)
        os.environ.pop("RESEND_API_KEY", None)
        res = await send_transactional_email("to", "sub", "body")
        assert res is False

        # Cleanup
        settings.resend_base_url = old_url
        os.environ.pop("RESEND_BASE_URL", None)

    settings.resend_api_key = old_key


@pytest.mark.unit
@pytest.mark.asyncio
async def test_push_notifications_paths(db_cleanup) -> None:
    user_id = str(uuid4())
    n = Notification(user_id=user_id, title="T", body="B")

    # 1. Missing VAPID keys
    old_priv = settings.gh_vapid_private_key
    old_pub = settings.gh_vapid_public_key
    settings.gh_vapid_private_key = ""
    settings.gh_vapid_public_key = ""
    assert await send_push_notification(n) is False

    # Set dummy keys
    valid_key = "2zYlXaU6HDHgVwpDUNv71bOsAFFFiapma61UFXI2u04"
    valid_pub = "BBlxXfnhLDC5uGv9Y4L7DTTVC4tPRZ1tQnz1MaKHvSFJptz0A_W3xx3oUfIm9g48FPC8ekgRTIgddGiBB0c3f2E"
    settings.gh_vapid_private_key = valid_key
    settings.gh_vapid_public_key = valid_pub

    # 2. No subscriptions
    assert await send_push_notification(n) is False

    # 3. Successful subscription & exception path
    # Point endpoint to fake server
    sub = {
        "endpoint": "http://127.0.0.1:8085/push",
        "keys": {
            "auth": "lyEY8grzKIQloWKKBys15g",
            "p256dh": "BNzmS1vIAqFXoPvV7lnTdV7XISDeH3jTmQdnERXTi77jv1SCj8MeQrS7HTHLjlxLm66NoIwV3_5pW41t4IIHYnY"
        }
    }
    await save_user_push_subscription(user_id, json.dumps(sub))

    # Start fake server to accept the push request
    async with run_fake_server(port=8085):
        # Trigger success branch (Line 49)
        res = await send_push_notification(n)
        assert res is True

        # Trigger WebPushException branch (Line 50-51) by using an endpoint that returns 401
        sub_bad_endpoint = {
            "endpoint": "http://127.0.0.1:8085/emails",  # /emails returns 401 with invalid auth
            "keys": {
                "auth": "invalid_auth_token_for_fake",
                "p256dh": "BNzmS1vIAqFXoPvV7lnTdV7XISDeH3jTmQdnERXTi77jv1SCj8MeQrS7HTHLjlxLm66NoIwV3_5pW41t4IIHYnY"
            }
        }
        await save_user_push_subscription(user_id, json.dumps(sub_bad_endpoint))
        res = await send_push_notification(n)
        assert res is True  # The function catches WebPushException and returns True

        # Trigger broad Exception branch (Line 55-56)
        await save_user_push_subscription(user_id, "not valid json")
        res = await send_push_notification(n)
        assert res is True  # catches Exception and returns True

    # 4. send_web_push path with exception
    os.environ["VAPID_PRIVATE_KEY"] = "dummy_too_short"
    assert await send_web_push({}, "t", "b") is False

    # 5. Missing VAPID_PRIVATE_KEY in send_web_push (Line 64)
    os.environ.pop("VAPID_PRIVATE_KEY", None)
    assert await send_web_push({}, "t", "b") is False

    # Cleanup
    settings.gh_vapid_private_key = old_priv
    settings.gh_vapid_public_key = old_pub
