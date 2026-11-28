"""
Progress bar widget for YT-DLP Studio.

Displays download progress with percentage, speed, and ETA. All colors come
from the theme (``progressState`` and ``labelStyle`` properties), so the
widget reads correctly in the dark and the light theme.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from ..utils.file_helper import FileHelper
from ..utils.logger import get_logger
from ..utils.translations import tr
from .display_format import ltr
from .theme import repolish

logger = get_logger()


class DownloadProgressWidget(QWidget):
    """
    Widget for displaying download progress.

    Shows progress bar, percentage, download speed, and ETA.

    Example:
        >>> progress = DownloadProgressWidget()
        >>> progress.update_progress(50.5, 1536000, 30)  # 50.5%, 1.5MB/s, 30s ETA
    """

    def __init__(self, parent=None):
        """
        Initialize progress widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._setup_ui()
        logger.debug("DownloadProgressWidget initialized")

    def _setup_ui(self) -> None:
        """Set up the widget UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        main_layout.addWidget(self.progress_bar)

        # Row 1: file size and downloaded amount
        file_info_layout = QHBoxLayout()
        self.file_size_label = QLabel()
        self.downloaded_label = QLabel()
        file_info_layout.addWidget(self.file_size_label)
        file_info_layout.addStretch()
        file_info_layout.addWidget(self.downloaded_label)
        main_layout.addLayout(file_info_layout)

        # Row 2: speed and time left
        info_layout = QHBoxLayout()
        self.speed_label = QLabel()
        self.eta_label = QLabel()
        info_layout.addWidget(self.speed_label)
        info_layout.addStretch()
        info_layout.addWidget(self.eta_label)
        main_layout.addLayout(info_layout)

        for label in (self.file_size_label, self.downloaded_label, self.speed_label, self.eta_label):
            label.setProperty("labelStyle", "secondary")

        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)

        self.reset()

    @staticmethod
    def _value_text(label_key: str, value: str | None) -> str:
        """``"Size: 12.3 MB"`` with the value kept left-to-right in Hebrew."""
        return f"{tr(label_key)} {ltr(value) if value else tr('text_unknown')}"

    def _set_state(self, state: str, label_style: str) -> None:
        """Set the theme state of the bar ("", "error", "success") and the status label."""
        self.progress_bar.setProperty("progressState", state)
        self.status_label.setProperty("labelStyle", label_style)
        repolish(self.progress_bar)
        repolish(self.status_label)

    def update_progress(
        self,
        percent: float,
        speed: float = 0,
        eta: int = 0,
        total_bytes: int = 0,
        downloaded_bytes: int = 0,
    ) -> None:
        """
        Update progress display.

        Args:
            percent: Progress percentage (0-100)
            speed: Download speed in bytes/sec
            eta: Estimated time remaining in seconds
            total_bytes: Total file size in bytes
            downloaded_bytes: Downloaded amount in bytes

        Example:
            >>> progress.update_progress(75.5, 2048000, 15, 104857600, 78643200)
        """
        self.progress_bar.setValue(int(percent))
        self.file_size_label.setText(
            self._value_text("label_size", FileHelper.format_size(total_bytes) if total_bytes > 0 else None)
        )
        self.downloaded_label.setText(
            self._value_text(
                "label_downloaded", FileHelper.format_size(downloaded_bytes) if downloaded_bytes > 0 else None
            )
        )
        self.speed_label.setText(self._value_text("label_speed", FileHelper.format_speed(speed) if speed > 0 else None))
        self.eta_label.setText(self._value_text("label_eta", FileHelper.format_time(eta) if eta > 0 else None))

        if percent >= 100:
            self.set_status(tr("status_complete"))
        elif percent > 0:
            self.set_status(tr("status_downloading"))

    def set_status(self, status: str) -> None:
        """
        Set status text.

        Args:
            status: Status message

        Example:
            >>> progress.set_status("Download starting...")
        """
        self.status_label.setText(status)

    def set_preparing_state(self) -> None:
        """Set preparing state (v1.9.0)."""
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(tr("status_preparing"))
        self.status_label.setText(tr("status_preparing"))
        self._set_state("", "secondary")
        logger.debug("Progress widget in preparing state")

    def reset(self) -> None:
        """Reset progress to initial state."""
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        for label, key in (
            (self.file_size_label, "label_size"),
            (self.downloaded_label, "label_downloaded"),
            (self.speed_label, "label_speed"),
            (self.eta_label, "label_eta"),
        ):
            label.setText(self._value_text(key, None))
        self.status_label.setText(tr("status_ready"))
        self._set_state("", "secondary")
        logger.debug("Progress widget reset")

    def set_error_state(self, error_message: str) -> None:
        """
        Set error state.

        Args:
            error_message: Error message to display
        """
        self.status_label.setText(f"{tr('text_error_prefix')} {error_message}")
        self._set_state("error", "error")

    def set_success_state(self) -> None:
        """Set success state."""
        self.progress_bar.setFormat("%p%")
        self.status_label.setText(tr("status_success"))
        self._set_state("success", "success")
