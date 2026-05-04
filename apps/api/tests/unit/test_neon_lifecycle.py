"""Unit tests for Neon lifecycle and error paths (Zero-Mock)."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from src.database.neon_client import NeonManager, acquire


@pytest.mark.unit
@pytest.mark.asyncio
async def test_neon_manager_lifecycle() -> None:
    """Test NeonManager pool lifecycle."""
    await NeonManager.get_pool()
    # Test reuse
    p1 = await NeonManager.get_pool()
    p2 = await NeonManager.get_pool()
    assert p1 is p2
    
    await NeonManager.close_pool()
    assert NeonManager._pool is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_neon_manager_loop_change() -> None:
    """Test NeonManager re-init on loop change."""
    await NeonManager.get_pool()
    
    # Simulate loop change
    NeonManager._loop = "different" # type: ignore
    
    p2 = await NeonManager.get_pool()
    assert NeonManager._loop != "different"
    await NeonManager.close_pool()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_neon_acquire_error() -> None:
    """Trigger the except block in acquire()."""
    # We set pool to something that will fail on acquire()
    # Since we can't mock, we try to use a closed pool or similar.
    await NeonManager.get_pool()
    pool = NeonManager._pool
    assert pool is not None
    await pool.close()
    
    # Now acquire should fail
    with pytest.raises(Exception):
        async with acquire() as conn:
            pass
    
    # Reset NeonManager so other tests don't fail
    NeonManager._pool = None
    NeonManager._loop = None


@pytest.mark.unit
def test_neon_manager_close_no_loop() -> None:
    """Trigger RuntimeError in close_pool logic."""
    class FakePool:
        async def close(self):
            pass
    NeonManager._pool = FakePool() # type: ignore
    async def run_close():
        await NeonManager.close_pool()
    
    asyncio.run(run_close())
    assert NeonManager._pool is None
