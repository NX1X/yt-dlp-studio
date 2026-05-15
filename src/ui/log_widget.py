"""
Log widget for YT-DLP Studio.

Displays log messages and download progress in a text area.
"""

from PySide6.QtCore import QDateTime
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QTextEdit

from ..utils.logger import get_logger
from ..utils.translations import tr

logger = get_logger()


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
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the widget UI."""
        # Make read-only
        self.setReadOnly(True)

        # Set styling
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
                border: 1px solid #3e3e3e;
                padding: 5px;
            }
        """)

        # Set placeholder
        self.setPlaceholderText(tr("placeholder_log_messages"))

        logger.debug("LogWidget initialized")

    def append_log(self, message: str, include_timestamp: bool = True) -> None:
        """
        Append a log message to the widget.

        Args:
            message: Log message text
            include_timestamp: If True, prepend timestamp

        Example:
            >>> log.append_log("Download complete")
        """
        if include_timestamp:
            timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")
            formatted_message = f"[{timestamp}] {message}"
        else:
            formatted_message = message

        self.append(formatted_message)

        # Auto-scroll to bottom
        self.moveCursor(QTextCursor.End)
        self.ensureCursorVisible()

    def clear_log(self) -> None:
        """Clear all log messages."""
        self.clear()
        logger.debug("Log widget cleared")

    def append_error(self, message: str) -> None:
        """
        Append an error message with red color.

        Args:
            message: Error message

        Example:
            >>> log.append_error("Download failed")
        """
        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")
        html = f'<span style="color: #f48771;">[{timestamp}] ERROR: {message}</span>'
        self.append(html)
        self.moveCursor(QTextCursor.End)

    def append_success(self, message: str) -> None:
        """
        Append a success message with green color.

        Args:
            message: Success message

        Example:
            >>> log.append_success("Download completed!")
        """
        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")
        html = f'<span style="color: #4ec9b0;">[{timestamp}] SUCCESS: {message}</span>'
        self.append(html)
        self.moveCursor(QTextCursor.End)

    def append_info(self, message: str) -> None:
        """
        Append an info message with blue color.

        Args:
            message: Info message
        """
        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")
        html = f'<span style="color: #569cd6;">[{timestamp}] INFO: {message}</span>'
        self.append(html)
        self.moveCursor(QTextCursor.End)

    def append_warning(self, message: str) -> None:
        """
        Append a warning message with yellow color.

        Args:
            message: Warning message

        Example:
            >>> log.append_warning("No subtitles available")
        """
        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")
        html = f'<span style="color: #dcdcaa;">[{timestamp}] WARNING: {message}</span>'
        self.append(html)
        self.moveCursor(QTextCursor.End)
