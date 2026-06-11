"""
Global crash handler for YT-DLP Studio.

Installs hooks on the main thread, worker threads, and Qt's message handler so
any unhandled exception writes a structured crash report to disk. Crash reports
go in `APP_DATA_DIR/crashes/` as JSON files keyed by timestamp.

A crash report contains:
- Timestamp (UTC ISO-8601)
- App version, yt-dlp engine version
- Python version, platform, architecture
- Frozen/source flag
- Exception type, message, full traceback
- Last 200 lines of the rolling log file (best effort)

Call `install_crash_handler()` exactly once, as early as possible in startup.

Why a separate handler instead of relying on the logger:
- The logger only records `logger.critical(..., exc_info=True)` if the caller
  remembers to wrap things. Unhandled exceptions in QThreads, the Qt event
  loop, or background workers don't get logged at all unless an excepthook
  is installed.
- A structured JSON file is easier to attach to a bug report than digging
  through a multi-megabyte rotating log.
"""

from __future__ import annotations

import json
import platform
import sys
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType
from typing import Any

from .constants import APP_DATA_DIR, APP_VERSION, YTDLP_VERSION
from .logger import get_logger

logger = get_logger()

CRASH_DIR = APP_DATA_DIR / "crashes"
LOG_TAIL_LINES = 200
MAX_CRASH_FILES = 20

_installed = False


def _build_report(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb: TracebackType | None,
    *,
    origin: str,
    thread_name: str | None = None,
) -> dict[str, Any]:
    """Assemble a JSON-serializable crash record."""
    report: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "origin": origin,
        "thread": thread_name or threading.current_thread().name,
        "app_version": APP_VERSION,
        "yt_dlp_version": YTDLP_VERSION,
        "python_version": sys.version.split()[0],
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "frozen": bool(getattr(sys, "frozen", False)),
        "exception_type": f"{exc_type.__module__}.{exc_type.__name__}",
        "exception_message": str(exc_value),
        "traceback": "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
    }

    report["log_tail"] = _read_log_tail()
    return report


def _read_log_tail() -> list[str]:
    """Best-effort read of the last N lines of the active log file."""
    try:
        from .constants import LOG_PATH

        log_path = Path(LOG_PATH)
        if not log_path.exists():
            return []
        # Read full file then tail — log is rotated at 5MB so this is bounded.
        text = log_path.read_text(encoding="utf-8", errors="replace")
        return text.splitlines()[-LOG_TAIL_LINES:]
    except Exception:
        return []


def _prune_old_crashes() -> None:
    """Keep at most MAX_CRASH_FILES crash reports; delete the oldest."""
    try:
        files = sorted(CRASH_DIR.glob("crash-*.json"), key=lambda p: p.stat().st_mtime)
        for old in files[:-MAX_CRASH_FILES]:
            try:
                old.unlink()
            except OSError:
                pass
    except Exception:
        pass


def _write_report(report: dict[str, Any]) -> Path | None:
    """Persist the crash record. Returns the file path or None on failure."""
    try:
        CRASH_DIR.mkdir(parents=True, exist_ok=True)
        ts = report["timestamp"].replace(":", "").replace("-", "").replace(".", "")
        path = CRASH_DIR / f"crash-{ts}.json"
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        _prune_old_crashes()
        return path
    except Exception as e:
        logger.error(f"Could not write crash report: {e}")
        return None


def _handle(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb: TracebackType | None,
    *,
    origin: str,
    thread_name: str | None = None,
) -> None:
    """Common path for sys.excepthook and threading.excepthook."""
    # Let KeyboardInterrupt fall through to the default handler so Ctrl+C
    # still kills the process cleanly during dev runs.
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return

    report = _build_report(exc_type, exc_value, exc_tb, origin=origin, thread_name=thread_name)
    path = _write_report(report)

    logger.critical(
        "Unhandled %s in %s (%s): %s",
        report["exception_type"],
        origin,
        report["thread"],
        report["exception_message"],
        exc_info=(exc_type, exc_value, exc_tb),
    )
    if path is not None:
        logger.critical("Crash report written to %s", path)


def _sys_excepthook(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb: TracebackType | None,
) -> None:
    _handle(exc_type, exc_value, exc_tb, origin="sys.excepthook")


def _threading_excepthook(args: threading.ExceptHookArgs) -> None:
    _handle(
        args.exc_type,
        args.exc_value if args.exc_value is not None else args.exc_type(),
        args.exc_traceback,
        origin="threading.excepthook",
        thread_name=args.thread.name if args.thread is not None else None,
    )


def install_crash_handler() -> None:
    """Install global excepthooks. Safe to call multiple times."""
    global _installed
    if _installed:
        return

    sys.excepthook = _sys_excepthook
    threading.excepthook = _threading_excepthook

    _installed = True
    logger.info(f"Crash handler installed. Reports will be written to {CRASH_DIR}")


def get_crash_dir() -> Path:
    """Return the directory where crash reports are written."""
    return CRASH_DIR
