"""
Download error dialog for YT-DLP Studio.

Shows the friendly explanation from ``ErrorHandler`` and a "Copy details"
button that puts the technical text on the clipboard, for a bug report.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from ..utils.error_handler import ErrorHandler
from ..utils.logger import get_logger
from ..utils.translations import tr
from .help_links import ANCHOR_DOWNLOAD_FAILED, open_guide
from .theme import get_theme_manager

logger = get_logger()


def build_download_error_dialog(parent: QWidget | None, error_message: str, title: str | None = None) -> QMessageBox:
    """
    Build (not show) the "download failed" dialog.

    Args:
        parent: Parent widget
        error_message: The raw error from yt-dlp
        title: Window title; default is the "Download failed" text

    Returns:
        The message box; call ``exec()`` to show it
    """
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Critical)
    box.setWindowTitle(title or tr("dialog_download_failed"))
    box.setTextFormat(Qt.TextFormat.RichText)
    box.setText(ErrorHandler.format_error_dialog_text(error_message, get_theme_manager().colors()))

    copy_button = box.addButton(tr("button_copy_details"), QMessageBox.ButtonRole.ActionRole)
    help_button = box.addButton(tr("button_help"), QMessageBox.ButtonRole.HelpRole)
    help_button.setToolTip(tr("tooltip_help_guide"))
    ok_button = box.addButton(QMessageBox.StandardButton.Ok)
    box.setDefaultButton(ok_button)

    # A message box closes on any button. Disconnect the copy button from it,
    # so copying keeps the dialog open.
    copy_button.clicked.disconnect()
    help_button.clicked.disconnect()

    def copy_details() -> None:
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(error_message)
            copy_button.setText(tr("text_copied"))
            logger.debug("Copied download error details to the clipboard")

    copy_button.clicked.connect(copy_details)
    help_button.clicked.connect(lambda: open_guide(ANCHOR_DOWNLOAD_FAILED))
    return box


def show_download_error(parent: QWidget | None, error_message: str, title: str | None = None) -> None:
    """Show the "download failed" dialog and wait until the user closes it."""
    build_download_error_dialog(parent, error_message, title).exec()
