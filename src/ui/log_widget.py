"""
Log widget for YT-DLP Studio.

Displays log messages and download progress in a text area. Colors come
from the current theme; after a theme change the log is drawn again in the
new colors.
"""

import html
from collections import deque

from PySide6.QtCore import QDateTime
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QTextEdit

from ..utils.logger import get_logger
from ..utils.translations import tr
from .theme import get_theme_manager, theme_color

logger = get_logger()

# Level -> (theme color token, translation key of the prefix). None = plain text.
_LEVELS: dict[str | None, tuple[str | None, str | None]] = {
    None: (None, None),
    "error": ("error", "log_level_error"),
    "success": ("success", "log_level_success"),
    "info": ("log_info", "log_level_info"),
    "warning": ("warning", "log_level_warning"),
}

# Lines kept for redrawing after a theme change.
MAX_LOG_LINES = 2000


class LogWidget(QTextEdit):
    """
    Text widget for displaying log messages.

    Shows timestamped log messages with automatic scrolling.
    Read-only for users but can be programmatically updated.

    Example:
        >>> log = LogWidget()
        >>> log.append_log("Download started")
        >>> log.append_log("Progress: 50%")
    """

    def __init__(self, parent=None):
        """
        Initialize log widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        # (level, timestamp or None, message) for each line, oldest first
        self._entries: deque[tuple[str | None, str | None, str]] = deque(maxlen=MAX_LOG_LINES)
        self._setup_ui()
        get_theme_manager().theme_changed.connect(self._redraw)

    def _setup_ui(self) -> None:
        """Set up the widget UI."""
        self.setReadOnly(True)
        # The theme gives #activityLog a monospace font; colors come from the theme.
        self.setObjectName("activityLog")
        self.setPlaceholderText(tr("placeholder_log_messages"))
        logger.debug("LogWidget initialized")

    @staticmethod
    def _timestamp() -> str:
        return QDateTime.currentDateTime().toString("hh:mm:ss")

    @staticmethod
    def _line_html(level: str | None, stamp: str | None, message: str) -> str:
        token, prefix_key = _LEVELS[level]
        prefix = f"{tr(prefix_key)}: " if prefix_key else ""
        line = html.escape(f"[{stamp}] {prefix}{message}" if stamp else f"{prefix}{message}")
        if token is None:
            # A span keeps the escaped text rich text, so "&lt;" shows as "<".
            return f"<span>{line}</span>"
        return f'<span style="color: {theme_color(token)};">{line}</span>'

    def _add(self, level: str | None, message: str, with_stamp: bool = True) -> None:
        entry = (level, self._timestamp() if with_stamp else None, message)
        try:
            self._entries.append(entry)
            self.append(self._line_html(*entry))
            self.moveCursor(QTextCursor.End)
            self.ensureCursorVisible()
        except RuntimeError:
            # The widget was deleted (app closing) while a signal was queued.
            pass

    def _redraw(self, _mode: str = "") -> None:
        """Draw all kept lines again in the colors of the current theme."""
        try:
            super().clear()
            for entry in self._entries:
                self.append(self._line_html(*entry))
            self.moveCursor(QTextCursor.End)
        except RuntimeError:
            pass

    def append_log(self, message: str, include_timestamp: bool = True) -> None:
        """
        Append a log message to the widget.

        Args:
            message: Log message text
            include_timestamp: If True, prepend timestamp

        Example:
            >>> log.append_log("Download complete")
        """
        self._add(None, message, with_stamp=include_timestamp)

    def clear(self) -> None:
        """Clear the text and the kept lines."""
        self._entries.clear()
        super().clear()

    def clear_log(self) -> None:
        """Clear all log messages."""
        self.clear()
        logger.debug("Log widget cleared")

    def append_error(self, message: str) -> None:
        """
        Append an error message in the theme's error color.

        Args:
            message: Error message

        Example:
            >>> log.append_error("Download failed")
        """
        self._add("error", message)

    def append_success(self, message: str) -> None:
        """
        Append a success message in the theme's success color.

        Args:
            message: Success message

        Example:
            >>> log.append_success("Download completed!")
        """
        self._add("success", message)

    def append_info(self, message: str) -> None:
        """
        Append an info message in the theme's info color.

        Args:
            message: Info message
        """
        self._add("info", message)

    def append_warning(self, message: str) -> None:
        """
        Append a warning message in the theme's warning color.

        Args:
            message: Warning message

        Example:
            >>> log.append_warning("No subtitles available")
        """
        self._add("warning", message)
