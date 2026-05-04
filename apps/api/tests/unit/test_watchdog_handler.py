"""Unit tests for watchdog handler — Section 15.1 Implementation."""

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
    assert _detect_market("") == "unknown"


@pytest.mark.unit
def test_handler_logic(tmp_path: Path) -> None:
    """Test handler logic. Note: No @pytest.mark.asyncio because on_created uses asyncio.run."""
    handler = BsoptFileHandler()

    # Valid file (SPY)
    file_path = tmp_path / "spy_data.csv"
    file_path.touch()
    event = FileCreatedEvent(str(file_path))
    # This will call asyncio.run(publish_watchdog_task). 
    # Since RabbitMQ is up (conftest provides it), it should work or fail gracefully.
    handler.on_created(event)

    # Valid file (NSE)
    nse_path = tmp_path / "nse_data.json"
    nse_path.touch()
    handler.on_created(FileCreatedEvent(str(nse_path)))

    # Invalid extension
    txt_path = tmp_path / "data.txt"
    txt_path.touch()
    handler.on_created(FileCreatedEvent(str(txt_path)))

    # Directory event (should be ignored)
    dir_path = tmp_path / "sub_dir"
    dir_path.mkdir()
    event_dir = DirCreatedEvent(str(dir_path))
    handler.on_created(event_dir) # type: ignore[arg-type]


@pytest.mark.unit
def test_start_watchdog(tmp_path: Path) -> None:
    from src.data.watchdog_handler import start_watchdog

    watch_dir = tmp_path / "watch"
    watch_dir.mkdir() # Create it manually as start_watchdog doesn't do it in MIP
    observer = start_watchdog(str(watch_dir))
    assert observer.is_alive()
    observer.stop()
    observer.join()


@pytest.mark.unit
def test_supported_extensions_content() -> None:
    from src.data.watchdog_handler import SUPPORTED_EXTENSIONS

    assert ".csv" in SUPPORTED_EXTENSIONS
    assert ".json" in SUPPORTED_EXTENSIONS
    assert len(SUPPORTED_EXTENSIONS) == 2
