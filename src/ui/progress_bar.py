"""
Progress bar widget for YT-DLP Studio.

Displays download progress with percentage, speed, and ETA.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from ..utils.file_helper import FileHelper
from ..utils.logger import get_logger
from ..utils.translations import tr

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
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3e3e3e;
                border-radius: 3px;
                text-align: center;
                background-color: #2d2d2d;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #0e639c;
                border-radius: 2px;
            }
        """)

        main_layout.addWidget(self.progress_bar)

        # Info labels layout - Row 1: File size and downloaded
        file_info_layout = QHBoxLayout()

        # File size label
        self.file_size_label = QLabel("Size: --")
        self.file_size_label.setAlignment(Qt.AlignLeft)

        # Downloaded amount label
        self.downloaded_label = QLabel("Downloaded: --")
        self.downloaded_label.setAlignment(Qt.AlignRight)

        file_info_layout.addWidget(self.file_size_label)
        file_info_layout.addStretch()
        file_info_layout.addWidget(self.downloaded_label)

        main_layout.addLayout(file_info_layout)

        # Info labels layout - Row 2: Speed and ETA
        info_layout = QHBoxLayout()

        # Speed label
        self.speed_label = QLabel("Speed: --")
        self.speed_label.setAlignment(Qt.AlignLeft)

        # ETA label
        self.eta_label = QLabel("ETA: --")
        self.eta_label.setAlignment(Qt.AlignRight)

        info_layout.addWidget(self.speed_label)
        info_layout.addStretch()
        info_layout.addWidget(self.eta_label)

        main_layout.addLayout(info_layout)

        # Status label
        self.status_label = QLabel(tr("status_ready"))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #858585; font-style: italic;")

        main_layout.addWidget(self.status_label)

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
        # Update progress bar
        self.progress_bar.setValue(int(percent))

        # Update file size label
        if total_bytes > 0:
            size_str = FileHelper.format_size(total_bytes)
            self.file_size_label.setText(f"{tr('label_size')} {size_str}")
        else:
            self.file_size_label.setText(f"{tr('label_size')} {tr('text_unknown')}")

        # Update downloaded amount label
        if downloaded_bytes > 0:
            downloaded_str = FileHelper.format_size(downloaded_bytes)
            if total_bytes > 0:
                self.downloaded_label.setText(f"{tr('label_downloaded')} {downloaded_str}")
            else:
                self.downloaded_label.setText(f"{tr('label_downloaded')} {downloaded_str}")
        else:
            self.downloaded_label.setText(f"{tr('label_downloaded')} {tr('text_unknown')}")

        # Update speed label
        if speed > 0:
            speed_str = FileHelper.format_speed(speed)
            self.speed_label.setText(f"{tr('label_speed')} {speed_str}")
        else:
            self.speed_label.setText(f"{tr('label_speed')} {tr('text_unknown')}")

        # Update ETA label
        if eta > 0:
            eta_str = FileHelper.format_time(eta)
            self.eta_label.setText(f"{tr('label_eta')} {eta_str}")
        else:
            self.eta_label.setText(f"{tr('label_eta')} {tr('text_unknown')}")

        # Update status
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
        self.status_label.setStyleSheet("color: #0e639c; font-style: italic;")
        logger.debug("Progress widget in preparing state")

    def reset(self) -> None:
        """Reset progress to initial state."""
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        self.file_size_label.setText(f"{tr('label_size')} {tr('text_unknown')}")
        self.downloaded_label.setText(f"{tr('label_downloaded')} {tr('text_unknown')}")
        self.speed_label.setText(f"{tr('label_speed')} {tr('text_unknown')}")
        self.eta_label.setText(f"{tr('label_eta')} {tr('text_unknown')}")
        self.status_label.setText(tr("status_ready"))
        self.status_label.setStyleSheet("color: #858585; font-style: italic;")
        # Reset progress bar style
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3e3e3e;
                border-radius: 3px;
                text-align: center;
                background-color: #2d2d2d;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #0e639c;
                border-radius: 2px;
            }
        """)
        logger.debug("Progress widget reset")

    def set_error_state(self, error_message: str) -> None:
        """
        Set error state.

        Args:
            error_message: Error message to display
        """
        self.status_label.setText(f"{tr('text_error_prefix')}{error_message}")
        self.status_label.setStyleSheet("color: #f48771; font-style: italic;")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3e3e3e;
                border-radius: 3px;
                text-align: center;
                background-color: #2d2d2d;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #f48771;
                border-radius: 2px;
            }
        """)

    def set_success_state(self) -> None:
        """Set success state."""
        self.progress_bar.setFormat("%p%")
        self.status_label.setText(tr("status_success"))
        self.status_label.setStyleSheet("color: #4ec9b0; font-style: italic;")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3e3e3e;
                border-radius: 3px;
                text-align: center;
                background-color: #2d2d2d;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #4ec9b0;
                border-radius: 2px;
            }
        """)
