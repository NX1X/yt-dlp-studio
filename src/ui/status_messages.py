"""
Short confirmations in the main window status bar.

Routine feedback ("Added to the queue", "Path copied") goes to the status
bar for a few seconds instead of a blocking message box. Real errors stay
dialogs.

Usage:
    from .status_messages import show_status

    show_status(self, tr("status_added_to_queue"))
"""

from PySide6.QtWidgets import QMainWindow, QStatusBar, QWidget

from ..utils.logger import get_logger

logger = get_logger()

DEFAULT_TIMEOUT_MS = 4000


def find_status_bar(widget: QWidget | None) -> QStatusBar | None:
    """
    Find the status bar of the main window that holds ``widget``.

    A dialog is not a main window, so the search goes on through the
    dialog's parent until it reaches a ``QMainWindow``.

    Returns:
        The status bar, or None if the widget is not inside a main window
    """
    current = widget
    while current is not None:
        window = current.window()
        if isinstance(window, QMainWindow):
            return window.statusBar()
        current = window.parentWidget()
    return None


def show_status(widget: QWidget | None, text: str, timeout_ms: int = DEFAULT_TIMEOUT_MS) -> bool:
    """
    Show ``text`` in the main window status bar for ``timeout_ms``.

    Call it on the GUI thread only.

    Returns:
        True if a status bar showed the text. Without a main window (for
        example in a test that builds a tab on its own) the text goes to the
        log and the result is False.
    """
    bar = find_status_bar(widget)
    if bar is None:
        logger.info(f"Status: {text}")
        return False
    bar.showMessage(text, timeout_ms)
    return True
