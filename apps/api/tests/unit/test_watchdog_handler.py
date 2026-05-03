"""Unit tests for watchdog handler — Phase 3."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from watchdog.events import DirCreatedEvent, FileCreatedEvent

from src.data.watchdog_handler import BsoptFileHandler, _detect_market

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.unit
def test_detect_market() -> None:
    assert _detect_market("spy_data.csv") == "spy"
    assert _detect_market("NSE_data.csv") == "nse"
    assert _detect_market("random.csv") == "unknown"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handler_logic(tmp_path: Path) -> None:
    handler = BsoptFileHandler()

    # Valid file
    file_path = tmp_path / "spy_data.csv"
    file_path.touch()
    event = FileCreatedEvent(str(file_path))
    # Should not raise, even if it tries to publish (real RabbitMQ is up)
    handler.on_created(event)

    # Gzip file
    gz_path = tmp_path / "nse_data.csv.gz"
    gz_path.touch()
    event_gz = FileCreatedEvent(str(gz_path))
    handler.on_created(event_gz)

    # Invalid extension
    txt_path = tmp_path / "data.txt"
    txt_path.touch()
    event_txt = FileCreatedEvent(str(txt_path))
    handler.on_created(event_txt)

    # Directory event (should be ignored)
    dir_path = tmp_path / "sub_dir"
    dir_path.mkdir()
    event_dir = DirCreatedEvent(str(dir_path))
    handler.on_created(event_dir)

    # Bare .gz
    bare_gz = tmp_path / "spy_raw.gz"
    bare_gz.touch()
    handler.on_created(FileCreatedEvent(str(bare_gz)))

    # Invalid .gz (e.g. .txt.gz)
    invalid_gz = tmp_path / "spy_raw.txt.gz"
    invalid_gz.touch()
    handler.on_created(FileCreatedEvent(str(invalid_gz)))


@pytest.mark.unit
def test_handler_sync_loop_fallback(tmp_path: Path) -> None:
    # This test runs without a pytest-asyncio loop in this thread
    handler = BsoptFileHandler()
    file_path = tmp_path / "spy_sync.csv"
    file_path.touch()
    event = FileCreatedEvent(str(file_path))
    # Should trigger the 'except RuntimeError' and call asyncio.run
    handler.on_created(event)


@pytest.mark.unit
def test_start_watchdog(tmp_path: Path) -> None:
    from src.data.watchdog_handler import start_watchdog

    observer = start_watchdog(str(tmp_path / "watch"))
    assert observer.is_alive()
    observer.stop()
    observer.join()
