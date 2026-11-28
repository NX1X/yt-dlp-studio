"""
Display helpers for the Download, Queue and History tabs.

Numbers with units ("3.24 MB/s"), times and links are left-to-right text.
In a Hebrew (right-to-left) layout the bidi algorithm can reorder them, for
example "MB/s 3.24". Every helper here wraps its result in a left-to-right
isolate (LRI ... PDI, U+2066 / U+2069), so the value reads the same in both
layout directions.

The module also maps the stable quality keys that the queue and history
files store ("Best Quality", "1080p (Full HD)") to translated labels, and
gives the theme colors for statuses.
"""

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

from ..utils.file_helper import FileHelper
from ..utils.logger import get_logger
from ..utils.translations import tr
from .theme import ModernTheme, ThemeMode, get_theme_manager

logger = get_logger()

# Left-to-right isolate and pop directional isolate
LRI = "⁦"
PDI = "⁩"

# Stored quality key -> translation key. Keys without an entry are shown as
# stored (resolutions such as "4K (2160p)" read the same in every language).
_QUALITY_KEYS = {
    "Best Quality": "quality_best",
    "1080p (Full HD)": "quality_1080p",
    "720p (HD)": "quality_720p",
    "480p (SD)": "quality_480p",
    "Audio 320kbps": "quality_audio_320",
    "Audio 256kbps": "quality_audio_256",
    "Audio 192kbps": "quality_audio_192",
    "Audio 128kbps": "quality_audio_128",
    "Audio Only": "quality_audio_only",
}


def ltr(text: str) -> str:
    """Wrap ``text`` in a left-to-right isolate. Empty text stays empty."""
    if not text:
        return text
    return f"{LRI}{text}{PDI}"


def strip_isolates(text: str) -> str:
    """Remove the isolate marks again (for copying and for tests)."""
    return text.replace(LRI, "").replace(PDI, "")


def size_text(size_bytes: int | float) -> str:
    """File size, for example "410.5 MB". Empty for an unknown size."""
    if not size_bytes or size_bytes <= 0:
        return ""
    return ltr(FileHelper.format_size(int(size_bytes)))


def speed_text(bytes_per_second: float) -> str:
    """Download speed, for example "3.24 MB/s". Empty when there is none."""
    if not bytes_per_second or bytes_per_second <= 0:
        return ""
    return ltr(FileHelper.format_speed(bytes_per_second))


def duration_text(seconds: int | float) -> str:
    """Time as "m:ss" or "h:mm:ss". Empty for an unknown or zero time."""
    if not seconds or seconds <= 0:
        return ""
    total = int(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return ltr(f"{hours}:{minutes:02d}:{secs:02d}")
    return ltr(f"{minutes}:{secs:02d}")


def percent_text(percent: float) -> str:
    """Progress, for example "47%"."""
    return ltr(f"{max(0.0, min(percent, 100.0)):.0f}%")


def link_text(url: str) -> str:
    """A link as left-to-right text."""
    return ltr(url)


def quality_label(quality: str) -> str:
    """Translated label for a stored quality key."""
    key = _QUALITY_KEYS.get(quality)
    return tr(key) if key else quality


def theme_colors() -> dict:
    """Colors of the theme that is active now."""
    mode = get_theme_manager().get_current_mode()
    name = "light" if mode == ThemeMode.LIGHT else "dark"
    return ModernTheme.COLORS[name]


def status_color(kind: str) -> str:
    """
    Text color for a status kind.

    Args:
        kind: "running", "done", "failed", "waiting" or "cancelled"

    Returns:
        A hex color from the active theme
    """
    colors = theme_colors()
    light = get_theme_manager().get_current_mode() == ThemeMode.LIGHT
    running = colors.get("status_running") or (colors["accent_primary"] if light else colors["accent_light"])
    return {
        "running": running,
        "done": colors["success"],
        "failed": colors["error"],
    }.get(kind, colors["text_secondary"])


def open_local_path(path: str) -> bool:
    """
    Open a file or folder with the program the desktop uses for it.

    Returns:
        True if the desktop accepted the request
    """
    if not path:
        return False
    opened = QDesktopServices.openUrl(QUrl.fromLocalFile(path))
    if opened:
        logger.info(f"Opened: {path}")
    else:
        logger.warning(f"Could not open: {path}")
    return bool(opened)
