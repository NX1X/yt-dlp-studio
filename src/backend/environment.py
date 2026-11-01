"""
Runtime environment details for YT-DLP Studio.

Two users:

* The About tab shows the FFmpeg version.
* The startup log gets one ``Environment: ...`` line, so a bug report shows
  the app, engine, FFmpeg, Deno, Python and Qt versions and the install kind.

The FFmpeg version comes from the same FFmpeg the downloader uses
(``YtDlpWrapper._get_ffmpeg_location``), started without a console window on
Windows. The result is cached, so FFmpeg starts at most once per run. Deno is
never started: its version is only known for the copy bundled in the EXE.

Nothing in this module raises. Every lookup falls back to a safe value.
"""

from __future__ import annotations

import os
import platform
import re
import subprocess
import sys
import threading

from ..utils.constants import APP_VERSION, YTDLP_VERSION
from ..utils.deno_installer import DENO_VERSION, get_app_data_deno_dir
from ..utils.logger import get_logger
from ..utils.process import hidden_window_kwargs
from ..utils.translations import tr
from .yt_dlp_wrapper import YtDlpWrapper, _project_root

logger = get_logger()

# FFmpeg answers "-version" in well under a second. The timeout only guards
# against a broken or hung binary.
FFMPEG_TIMEOUT_S = 5

# Status values for an FFmpeg probe.
FFMPEG_OK = "ok"
FFMPEG_NOT_FOUND = "not_found"
FFMPEG_UNKNOWN = "unknown"
FFMPEG_ERROR = "error"

_UNKNOWN = "unknown"

_ffmpeg_lock = threading.Lock()
_ffmpeg_result: tuple[str, str | None] | None = None

_FFMPEG_VERSION_RE = re.compile(r"^\s*ffmpeg\s+version\s+(\S+)", re.IGNORECASE)


# ---------------------------------------------------------------- FFmpeg


def _bundle_dir() -> str | None:
    """Return the PyInstaller extraction folder, or None when not frozen."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", None)
    return None


def _same_dir(a: str, b: str) -> bool:
    try:
        return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))
    except (TypeError, ValueError):
        return False


def find_ffmpeg() -> str | None:
    """Return the path of the FFmpeg executable the downloader uses, or None.

    ``YtDlpWrapper._get_ffmpeg_location`` returns a folder (or, in theory, a
    file path). For a folder, the executable inside it is ``ffmpeg.exe`` on
    Windows and ``ffmpeg`` elsewhere.
    """
    try:
        location = YtDlpWrapper()._get_ffmpeg_location()
        if not location:
            return None
        if os.path.isdir(location):
            binary = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
            location = os.path.join(location, binary)
        return location if os.path.isfile(location) else None
    except Exception as e:  # noqa: BLE001 - never raise from a lookup
        logger.debug(f"FFmpeg lookup failed: {e}")
        return None


def parse_ffmpeg_version(output: str) -> str | None:
    """Return the version token from ``ffmpeg -version`` output, or None.

    The first line looks like ``ffmpeg version 7.1.1 Copyright (c) ...``.
    Builds put many things in the token (``n7.1``, ``7.1.1-1ubuntu1``,
    ``2025-01-01-git-abc-full_build-www.gyan.dev``), so it is returned as is.
    """
    if not output:
        return None
    for line in output.splitlines():
        if line.strip():
            match = _FFMPEG_VERSION_RE.match(line)
            return match.group(1) if match else None
    return None


def probe_ffmpeg_version(timeout: float = FFMPEG_TIMEOUT_S) -> tuple[str, str | None]:
    """Run ``ffmpeg -version`` once and return ``(status, version)``.

    ``status`` is one of FFMPEG_OK, FFMPEG_NOT_FOUND, FFMPEG_UNKNOWN or
    FFMPEG_ERROR. ``version`` is set only for FFMPEG_OK. Not cached: use
    :func:`get_ffmpeg_version_info` instead. Never raises.
    """
    try:
        path = find_ffmpeg()
        if path is None:
            return FFMPEG_NOT_FOUND, None
        result = subprocess.run(  # noqa: S603 - resolved FFmpeg path, fixed argument list, no shell
            [path, "-version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            stdin=subprocess.DEVNULL,
            check=False,
            **hidden_window_kwargs(),
        )
    except FileNotFoundError:
        return FFMPEG_NOT_FOUND, None
    except Exception as e:  # noqa: BLE001 - never raise from a probe
        logger.debug(f"FFmpeg version probe failed: {e}")
        return FFMPEG_ERROR, None

    if result.returncode != 0:
        return FFMPEG_UNKNOWN, None
    version = parse_ffmpeg_version(result.stdout)
    if version is None:
        return FFMPEG_UNKNOWN, None
    return FFMPEG_OK, version


def get_ffmpeg_version_info() -> tuple[str, str | None]:
    """Return ``(status, version)`` for FFmpeg, probing at most once per run.

    Blocks for the probe on the first call, so call it off the GUI thread.
    Later calls return the cached result. Never raises.
    """
    global _ffmpeg_result
    with _ffmpeg_lock:
        if _ffmpeg_result is None:
            _ffmpeg_result = probe_ffmpeg_version()
        return _ffmpeg_result


def cached_ffmpeg_version_info() -> tuple[str, str | None] | None:
    """Return the cached FFmpeg result, or None when no probe has finished yet.

    Never blocks, so the GUI thread can call it.
    """
    return _ffmpeg_result


def reset_ffmpeg_cache() -> None:
    """Forget the cached FFmpeg result (used by tests)."""
    global _ffmpeg_result
    with _ffmpeg_lock:
        _ffmpeg_result = None


def ffmpeg_version_text(info: tuple[str, str | None] | None = None) -> str:
    """Return the FFmpeg version for the UI, or a translated fallback.

    Args:
        info: A ``(status, version)`` pair. When None, this calls
            :func:`get_ffmpeg_version_info`, which can block on the first call.
    """
    try:
        status, version = info if info is not None else get_ffmpeg_version_info()
    except Exception:  # noqa: BLE001
        status, version = FFMPEG_ERROR, None
    if status == FFMPEG_OK and version:
        return version
    if status == FFMPEG_NOT_FOUND:
        return tr("text_ffmpeg_not_found")
    if status == FFMPEG_UNKNOWN:
        return tr("text_ffmpeg_unknown")
    return tr("text_ffmpeg_error")


def ffmpeg_source() -> str:
    """Return "bundled" when FFmpeg comes from inside the EXE, else "system"."""
    path = find_ffmpeg()
    bundle = _bundle_dir()
    if path and bundle and _same_dir(os.path.dirname(path), bundle):
        return "bundled"
    return "system"


# ---------------------------------------------------------- Startup line


def _engine_version() -> str:
    version = YtDlpWrapper.get_ytdlp_version()
    if not version or version == "Unknown":
        return YTDLP_VERSION
    return version


def _ffmpeg_part() -> str:
    status, version = get_ffmpeg_version_info()
    if status == FFMPEG_NOT_FOUND:
        return "FFmpeg not found"
    if status == FFMPEG_ERROR:
        return "FFmpeg error"
    source = ffmpeg_source()
    if status == FFMPEG_OK and version:
        return f"FFmpeg {version} ({source})"
    return f"FFmpeg unknown version ({source})"


def _deno_part() -> str:
    """Describe Deno from its path only. Deno is never started here."""
    path = YtDlpWrapper()._get_deno_location()
    if not path:
        return "Deno not found"
    folder = os.path.dirname(path)
    bundle = _bundle_dir()
    if bundle and _same_dir(folder, bundle):
        return f"Deno {DENO_VERSION} (bundled)"
    if _same_dir(folder, str(_project_root / "deno")):
        # Placed by the auto-installer. It may be from an older release, so
        # the version is not stated.
        return "Deno (local)"
    if _same_dir(folder, str(get_app_data_deno_dir())):
        # Downloaded to the versioned app data folder, so the version is known.
        return f"Deno {DENO_VERSION} (downloaded)"
    return "Deno (system)"


def _python_version() -> str:
    return platform.python_version()


def _qt_version() -> str:
    from PySide6.QtCore import qVersion

    return qVersion()


def install_kind() -> str:
    """Return how this copy runs.

    From source: "source". Windows: "installer" or "portable". Linux:
    "appimage", "deb", "rpm" or "archive". Anything else: "unknown".
    """
    if not getattr(sys, "frozen", False):
        return "source"
    from .update_checker import is_installed_copy, linux_install_kind

    if os.name == "nt":
        return "installer" if is_installed_copy() else "portable"
    if sys.platform.startswith("linux"):
        return linux_install_kind() or "archive"
    return _UNKNOWN


def _safe(func, fallback: str = _UNKNOWN) -> str:
    try:
        value = func()
    except Exception as e:  # noqa: BLE001 - one bad lookup must not drop the line
        logger.debug(f"Environment lookup {getattr(func, '__name__', func)} failed: {e}")
        return fallback
    return value if value else fallback


def environment_line() -> str:
    """Return the one-line environment summary for the startup log.

    Example: ``Environment: app 0.3.1, engine 2026.10.26, FFmpeg 7.1.1
    (system), Deno (system), Python 3.12.3, Qt 6.11.2, install kind: source``.
    Blocks for the FFmpeg probe on the first call. Never raises.
    """
    return (
        f"Environment: app {_safe(lambda: APP_VERSION)}"
        f", engine {_safe(_engine_version)}"
        f", {_safe(_ffmpeg_part, 'FFmpeg unknown')}"
        f", {_safe(_deno_part, 'Deno unknown')}"
        f", Python {_safe(_python_version)}"
        f", Qt {_safe(_qt_version)}"
        f", install kind: {_safe(install_kind)}"
    )


def log_environment() -> None:
    """Log the environment line at INFO. Logs a warning instead of raising."""
    try:
        logger.info(environment_line())
    except Exception as e:  # noqa: BLE001 - must never break startup
        logger.warning(f"Could not log the environment: {e}")


def start_environment_log() -> threading.Thread | None:
    """Log the environment line from a background thread.

    The FFmpeg probe starts a process, so it stays off the GUI thread. The
    probe also fills the cache that the About tab reads. Never raises.
    """
    try:
        thread = threading.Thread(target=log_environment, name="environment-log", daemon=True)
        thread.start()
        return thread
    except Exception as e:  # noqa: BLE001 - must never break startup
        logger.warning(f"Could not log the environment: {e}")
        return None
