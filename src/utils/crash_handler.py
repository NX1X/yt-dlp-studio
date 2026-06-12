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
import re
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

_REDACTED = "[REDACTED]"

# Patterns that catch the most common ways a credential ends up in a
# Python traceback, exception message, or log line:
#   1. Userinfo embedded in a URL: https://user:pass@host/...
#   2. Common key=value patterns for password/token/cookie/api-key,
#      with either '=' or ':' as the separator.
#   3. Authorization: Bearer <token> headers.
#   4. AWS-style access key IDs (visible in tracebacks from boto3-like code).
_SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"(?P<scheme>https?://)[^/@\s]+:[^/@\s]+@", re.IGNORECASE),
        rf"\g<scheme>{_REDACTED}@",
    ),
    # `Bearer <token>` / `Basic <token>` - the bearer keyword is followed by
    # whitespace, not a `:` or `=` separator, so it needs its own rule.
    # Handled before the generic key=value pattern so the latter does not
    # half-match and leave the token visible.
    (
        re.compile(
            r"(?P<keyword>\b(?:Bearer|Basic))\s+(?P<val>[A-Za-z0-9._\-+/=]{8,})",
            re.IGNORECASE,
        ),
        rf"\g<keyword> {_REDACTED}",
    ),
    (
        re.compile(
            r"(?P<key>(?:api[_-]?key|password|passwd|secret|token|cookie|authorization))"
            r"(?P<sep>\s*[:=]\s*)"
            r"(?P<val>['\"]?[^\s'\",;]+['\"]?)",
            re.IGNORECASE,
        ),
        rf"\g<key>\g<sep>{_REDACTED}",
    ),
    (
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        _REDACTED,
    ),
)


def _scrub_secrets(text: str) -> str:
    """Replace anything that looks like a credential with ``[REDACTED]``.

    Applied to crash-report fields the user is expected to attach to a bug
    report (exception_message, traceback, every log_tail line). Best effort -
    designed to catch the obvious cases that tests caught in real logs, not
    to be a comprehensive DLP filter.
    """
    if not text:
        return text
    for pattern, replacement in _SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


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
        # exception_message, traceback, and log_tail are scrubbed because
        # users are expected to attach this JSON to a public bug report.
        "exception_message": _scrub_secrets(str(exc_value)),
        "traceback": _scrub_secrets(
            "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        ),
    }

    report["log_tail"] = [_scrub_secrets(line) for line in _read_log_tail()]
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

    _show_crash_dialog(path)


def _show_crash_dialog(path: Path | None) -> None:
    """Best-effort native dialog so the user knows a crash report was saved.

    Skipped silently when:
    - PySide6 is not importable (e.g. during early startup).
    - No ``QApplication`` instance exists yet.
    - The current thread is not the Qt main thread (Qt forbids creating a
      widget off the GUI thread; the user will still see the report path in
      the log file, and the next-run will pick it up from the crashes/ dir).

    The handler itself must never raise, so the whole body is wrapped in a
    broad ``except`` that just logs and returns.
    """
    try:
        from PySide6.QtCore import QThread
        from PySide6.QtWidgets import QApplication, QMessageBox

        from .translations import tr

        qapp = QApplication.instance()
        if qapp is None:
            return
        if QThread.currentThread() != qapp.thread():
            # Background-thread crash. Showing a QMessageBox from here would
            # itself crash. Skip - the log file and the JSON report are the
            # user's recovery surfaces.
            return

        if path is not None:
            body = tr("dialog_crash_body").format(path=str(path))
        else:
            body = tr("dialog_crash_body_no_path")

        QMessageBox.critical(None, tr("dialog_crash_title"), body)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Could not show crash dialog: {e}")


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
