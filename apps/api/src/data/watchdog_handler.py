"""Watchdog file system monitor — Section 8 Implementation."""

from __future__ import annotations

import asyncio
from pathlib import Path

import structlog
from watchdog.events import FileCreatedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from src.metrics import WATCHDOG_FILES_DETECTED
from src.queue.publisher import publish_watchdog_task

logger = structlog.get_logger(__name__)
SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".csv", ".json"})


class BsoptFileHandler(FileSystemEventHandler):
    """Observer + FileSystemEventHandler pattern."""

    def on_created(self, event: FileCreatedEvent) -> None:  # type: ignore[override]
        if event.is_directory:
            return
        path = Path(str(event.src_path))
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return
        market = _detect_market(path.name)
        WATCHDOG_FILES_DETECTED.labels(market=market, extension=path.suffix).inc()
        logger.info(
            "watchdog_file_detected", path=str(path), market=market, step="watchdog", rows=0
        )
        asyncio.run(publish_watchdog_task(file_path=str(path), market=market))


def _detect_market(filename: str) -> str:
    lower = filename.lower()
    if lower.startswith("spy_"):
        return "spy"
    if lower.startswith("nse_"):
        return "nse"
    return "unknown"


def start_watchdog(watch_directory: str) -> Observer:
    """Initialize and start the watchdog observer."""
    observer = Observer()
    observer.schedule(BsoptFileHandler(), watch_directory, recursive=False)
    observer.start()
    logger.info("watchdog_started", watch_dir=watch_directory, step="init", rows=0)
    return observer
