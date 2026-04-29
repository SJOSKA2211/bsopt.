"""Watchdog file system monitor — Phase 3."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import structlog
from watchdog.events import FileCreatedEvent, FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from src.metrics import WATCHDOG_FILES_DETECTED
from src.queue.publisher import publish_watchdog_task

logger = structlog.get_logger(__name__)
SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".csv", ".json"})

_active_tasks: set[asyncio.Task[Any]] = set()


class BsoptFileHandler(FileSystemEventHandler):
    """Handles file creation events in the watch directory."""

    def on_created(self, event: FileSystemEvent) -> None:
        if not isinstance(event, FileCreatedEvent) or event.is_directory:
            return
        path = Path(str(event.src_path))
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return
        market = _detect_market(path.name)
        WATCHDOG_FILES_DETECTED.labels(market=market, extension=path.suffix).inc()
        logger.info(
            "watchdog_file_detected", path=str(path), market=market, step="watchdog", rows=0
        )

        # publish_watchdog_task is async, we use asyncio.run or similar
        # but in a long-running app, we should probably use a dedicated loop or queue
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(publish_watchdog_task(file_path=str(path), market=market))
            _active_tasks.add(task)
            task.add_done_callback(_active_tasks.discard)
        except RuntimeError:
            asyncio.run(publish_watchdog_task(file_path=str(path), market=market))


def _detect_market(filename: str) -> str:
    """Detect market from filename prefix."""
    lower = filename.lower()
    if lower.startswith("spy_"):
        return "spy"
    if lower.startswith("nse_"):
        return "nse"
    return "unknown"


def start_watchdog(watch_directory: str) -> Any:
    """Initialize and start the watchdog observer."""
    observer = Observer()
    observer.schedule(BsoptFileHandler(), watch_directory, recursive=False)
    observer.start()
    logger.info("watchdog_started", watch_dir=watch_directory, step="init", rows=0)
    return observer
