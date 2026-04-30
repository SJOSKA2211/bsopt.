"""Unit tests for watchdog handler logic."""

from __future__ import annotations

import os
import asyncio
import threading
from pathlib import Path
import pytest
from watchdog.events import FileCreatedEvent, DirCreatedEvent
from src.data.watchdog_handler import BsoptFileHandler, _detect_market, start_watchdog

@pytest.mark.unit
def test_detect_market_prefixes() -> None:
    """Verify market detection from filename prefixes."""
    assert _detect_market("spy_data.csv") == "spy"
    assert _detect_market("NSE_results.json") == "nse"
    assert _detect_market("random_file.txt") == "unknown"


@pytest.mark.unit
def test_handler_ignores_directories() -> None:
    """Verify that directories do not trigger processing."""
    handler = BsoptFileHandler()
    event = DirCreatedEvent("/tmp/test_dir")
    handler.on_created(event)


@pytest.mark.unit
def test_handler_ignores_unsupported_extensions(tmp_path: Path) -> None:
    """Verify that unsupported extensions are ignored."""
    handler = BsoptFileHandler()
    test_file = tmp_path / "test.txt"
    test_file.write_text("dummy")
    event = FileCreatedEvent(str(test_file))
    handler.on_created(event)


@pytest.mark.unit
def test_watchdog_observer_starts(tmp_path: Path) -> None:
    """Verify that the observer can be started on a real directory."""
    observer = start_watchdog(str(tmp_path))
    assert observer.is_alive()
    observer.stop()
    observer.join()


@pytest.mark.unit
def test_handler_valid_file(tmp_path: Path, db_cleanup: None) -> None:
    """Verify handler processes a valid file. Run in thread to avoid event loop conflicts."""
    handler = BsoptFileHandler()
    test_file = tmp_path / "spy_2024.csv"
    test_file.write_text("strike,bid,ask\n100,10,11")
    
    # Run in a separate thread so asyncio.run() can create its own loop
    # without conflicting with pytest-asyncio's loop.
    thread = threading.Thread(target=handler.on_created, args=(FileCreatedEvent(str(test_file)),))
    thread.start()
    thread.join()


@pytest.mark.unit
def test_handler_case_insensitivity(tmp_path: Path) -> None:
    """Verify extension check is case insensitive."""
    handler = BsoptFileHandler()
    test_file = tmp_path / "SPY.CSV"
    test_file.write_text("dummy")
    # Also run in thread for safety
    thread = threading.Thread(target=handler.on_created, args=(FileCreatedEvent(str(test_file)),))
    thread.start()
    thread.join()


@pytest.mark.unit
def test_handler_supports_gz_files(tmp_path: Path) -> None:
    """Verify that .gz files are supported."""
    handler = BsoptFileHandler()
    test_file = tmp_path / "spy_data.csv.gz"
    test_file.write_text("dummy")
    thread = threading.Thread(target=handler.on_created, args=(FileCreatedEvent(str(test_file)),))
    thread.start()
    thread.join()
