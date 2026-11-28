"""
Short confirmations in the main window's status bar.

Routine events (settings saved, path copied, added to the queue) show a
status bar message for a few seconds instead of a blocking message box.
"""

from PySide6.QtWidgets import QApplication, QMainWindow, QStatusBar, QWidget

from ..utils.logger import get_logger

logger = get_logger()


def _find_main_window(widget: QWidget | None) -> QMainWindow | None:
    """Return the main window that holds ``widget``, or any open main window."""
    current = widget
    while current is not None:
        window = current.window()
        if isinstance(window, QMainWindow):
            return window
        # A dialog is its own window; continue with the widget it belongs to.
        current = window.parentWidget()
    app = QApplication.instance()
    if app is None:
        return None
    for top_level in app.topLevelWidgets():
        if isinstance(top_level, QMainWindow):
            return top_level
    return None


def find_status_bar(widget: QWidget | None) -> QStatusBar | None:
    """Return the status bar of the main window that holds ``widget``, or None."""
    window = _find_main_window(widget)
    return window.statusBar() if window is not None else None


def show_status(widget: QWidget | None, text: str, timeout_ms: int = 4000) -> bool:
    """
    Show ``text`` in the status bar of the main window for ``timeout_ms``.

    Args:
        widget: Any widget inside the main window (a tab, or a dialog whose
            parent is in the main window)
        text: The translated message
        timeout_ms: How long the message stays; 0 keeps it until replaced

    Returns:
        True if a status bar showed the message. Without a main window (for
        example a tab under test on its own) the message is only logged.
    """
    window = _find_main_window(widget)
    if window is None:
        logger.debug(f"No main window for status message: {text}")
        return False
    window.statusBar().showMessage(text, timeout_ms)
    return True
