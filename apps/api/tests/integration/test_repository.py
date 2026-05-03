"""Integration tests for NeonDB repository — Phase 2."""
from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest

from src.database import repository

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_user_lifecycle(db_cleanup) -> None:
    """Test user creation and retrieval."""
    user_id = uuid4()
    email = f"test_{user_id}@example.com"
    # Manual insert for test setup
    from src.database.neon_client import acquire
    async with acquire() as conn:
        await conn.execute(
            "INSERT INTO users (id, email, role) VALUES ($1, $2, $3)",
            str(user_id), email, "admin"
        )

    user = await repository.get_user_by_id(user_id)
    assert user is not None
    assert user["email"] == email

    user_by_email = await repository.get_user_by_email(email)
    assert user_by_email is not None
    assert user_by_email["id"] == user_id


@pytest.mark.asyncio
async def test_option_parameters_upsert(db_cleanup) -> None:
    """Test idempotency and retrieval of option parameters."""
    opt_id = await repository.save_option_parameters(
        underlying_price=100.0,
        strike_price=105.0,
        time_to_expiry=0.5,
        volatility=0.2,
        risk_free_rate=0.05,
        option_type="call",
        market_source="test_market"
    )
    assert opt_id != ""

    # Test idempotency
    opt_id_2 = await repository.save_option_parameters(
        underlying_price=100.0,
        strike_price=105.0,
        time_to_expiry=0.5,
        volatility=0.2,
        risk_free_rate=0.05,
        option_type="call",
        market_source="test_market"
    )
    assert opt_id == opt_id_2


@pytest.mark.asyncio
async def test_market_data_upsert(db_cleanup) -> None:
    """Test upserting market data."""
    opt_id = await repository.save_option_parameters(100, 100, 1, 0.2, 0.05, "call", "test")

    await repository.save_market_data(
        option_id=opt_id,
        trade_date=date.today(),
        bid=10.0,
        ask=11.0,
        volume=100,
        oi=500,
        data_source="test"
    )

    data = await repository.query_market_data(option_id=opt_id)
    assert len(data) == 1
    assert data[0]["bid"] == 10.0


@pytest.mark.asyncio
async def test_audit_log(db_cleanup) -> None:
    """Test saving audit logs."""
    run_id = uuid4()
    await repository.save_audit_log(run_id, "test_step", "success", 10, "test message")
    # Verify manually or via query if we had one
