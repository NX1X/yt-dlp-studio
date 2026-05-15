"""
Update Dialog for YT-DLP Studio.

Shows available updates and allows users to download/install them.
"""

import os
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from ..backend.update_checker import UpdateChecker
from ..utils.logger import get_logger
from ..utils.translations import tr

logger = get_logger()


class DownloadThread(QThread):
    """Thread for downloading updates in the background."""

    progress = Signal(int, int)  # downloaded, total
    finished = Signal(bool, str)  # success, file_path

    def __init__(self, download_url: str, output_path: str):
        super().__init__()
        self.download_url = download_url
        self.output_path = output_path
        self.checker = UpdateChecker()

    def run(self):
        """Download the update file."""

        def progress_callback(downloaded, total):
            self.progress.emit(downloaded, total)

        success = self.checker.download_update(self.download_url, self.output_path, progress_callback)

        self.finished.emit(success, self.output_path if success else "")


class UpdateDialog(QDialog):
    """
    Dialog for showing and installing updates.

    Displays update information and allows downloading/installing new versions.
    """

    def __init__(self, release_info: dict, parent=None):
        """
        Initialize UpdateDialog.

        Args:
            release_info: Release information from UpdateChecker
            parent: Parent widget
        """
        super().__init__(parent)
        self.release_info = release_info
        self.download_thread = None
        self._setup_ui()
        logger.debug(f"UpdateDialog initialized for version {release_info['version']}")

    def _setup_ui(self):
        """Setup the dialog UI."""
        self.setWindowTitle(tr("dialog_update_available"))
        self.setMinimumWidth(550)
        self.setMinimumHeight(450)

        layout = QVBoxLayout()

        # Title (clean, professional - no emojis)
        version_label = QLabel(f"<h2>{tr('text_version_available', version=self.release_info['version'])}</h2>")
        layout.addWidget(version_label)

        # Current version info
        checker = UpdateChecker()
        current_label = QLabel(f"<b>{tr('label_current_version')}</b> {checker.get_current_version()}")
        layout.addWidget(current_label)

        new_label = QLabel(f"<b>{tr('label_new_version')}</b> {self.release_info['version']}")
        layout.addWidget(new_label)

        # Website link (v1.7.0)
        website_label = QLabel('<b>Website:</b> <a href="https://studio.nx1xlab.dev">studio.nx1xlab.dev</a>')
        website_label.setOpenExternalLinks(True)
        website_label.setTextFormat(Qt.RichText)
        layout.addWidget(website_label)

        # Release notes
        notes_label = QLabel(f"<b>{tr('label_release_notes')}</b>")
        layout.addWidget(notes_label)

        self.notes_text = QTextEdit()
        self.notes_text.setReadOnly(True)
        self.notes_text.setMaximumHeight(200)
        formatted_notes = UpdateChecker.format_release_notes(
            self.release_info.get("body", tr("text_no_release_notes")), max_length=1000
        )
        self.notes_text.setPlainText(formatted_notes)
        layout.addWidget(self.notes_text)

        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Buttons (clean, professional - no emojis, consistent sizing)
        button_layout = QHBoxLayout()

        self.view_online_btn = QPushButton(tr("button_view_on_github"))
        self.view_online_btn.setMinimumWidth(140)
        self.view_online_btn.clicked.connect(self._view_online)
        button_layout.addWidget(self.view_online_btn)

        self.website_btn = QPushButton(tr("button_visit_website"))
        self.website_btn.setMinimumWidth(140)
        self.website_btn.clicked.connect(self._open_website)
        button_layout.addWidget(self.website_btn)

        button_layout.addStretch()

        self.download_btn = QPushButton(tr("button_download_update"))
        self.download_btn.setMinimumWidth(160)
        self.download_btn.clicked.connect(self._download_update)
        self.download_btn.setDefault(True)
        button_layout.addWidget(self.download_btn)

        self.later_btn = QPushButton(tr("button_remind_me_later"))
        self.later_btn.setMinimumWidth(140)
        self.later_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.later_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _view_online(self):
        """Open the release page in browser."""
        import webbrowser

        url = self.release_info.get("html_url", "")
        if url:
            webbrowser.open(url)
            logger.info(f"Opened release page: {url}")

    def _open_website(self):
        """Open the project website in browser (v1.7.0)."""
        import webbrowser

        website_url = "https://studio.nx1xlab.dev"
        webbrowser.open(website_url)
        logger.info(f"Opened website: {website_url}")

    def _download_update(self):
        """Start downloading the update (v1.7.0 - user confirmation required)."""
        download_url = self.release_info.get("download_url")

        if not download_url:
            QMessageBox.warning(self, tr("dialog_download_error"), tr("msg_no_download_url"))
            return

        # Determine output path
        output_dir = Path.home() / "Downloads"
        output_dir.mkdir(exist_ok=True)

        filename = f"YT-DLP-Studio-{self.release_info['version']}.exe"
        output_path = output_dir / filename

        # Ask user for confirmation before downloading
        size_str = (
            f"{self.release_info.get('size', 0) / (1024 * 1024):.1f} MB"
            if "size" in self.release_info
            else "Unknown size"
        )
        reply = QMessageBox.question(
            self,
            tr("dialog_confirm_download"),
            tr("msg_confirm_download_text", filename=str(output_path), size=size_str),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,  # Default to No for safety
        )

        if reply != QMessageBox.Yes:
            logger.info("User cancelled update download")
            return

        # Disable buttons during download
        self.download_btn.setEnabled(False)
        self.view_online_btn.setEnabled(False)
        self.website_btn.setEnabled(False)
        self.later_btn.setEnabled(False)

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setVisible(True)
        self.status_label.setText(tr("text_downloading_update"))

        # Start download thread
        self.download_thread = DownloadThread(download_url, str(output_path))
        self.download_thread.progress.connect(self._on_progress)
        self.download_thread.finished.connect(self._on_download_finished)
        self.download_thread.start()

        logger.info(f"Started downloading update to: {output_path}")

    def _on_progress(self, downloaded: int, total: int):
        """
        Update progress bar.

        Args:
            downloaded: Bytes downloaded
            total: Total bytes
        """
        if total > 0:
            progress = int((downloaded / total) * 100)
            self.progress_bar.setValue(progress)

            # Update status label
            downloaded_mb = downloaded / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            self.status_label.setText(f"Downloading: {downloaded_mb:.1f} MB / {total_mb:.1f} MB ({progress}%)")

    def _on_download_finished(self, success: bool, file_path: str):
        """
        Handle download completion.

        Args:
            success: Whether download was successful
            file_path: Path to downloaded file
        """
        # Re-enable buttons
        self.download_btn.setEnabled(True)
        self.view_online_btn.setEnabled(True)
        self.website_btn.setEnabled(True)
        self.later_btn.setEnabled(True)

        if success:
            self.status_label.setText(tr("text_download_complete"))
            logger.info(f"Update downloaded successfully: {file_path}")

            # Ask if user wants to install now
            reply = QMessageBox.question(
                self,
                tr("dialog_download_complete_update"),
                f"Update downloaded successfully!\n\n"
                f"File: {file_path}\n\n"
                f"Would you like to run the installer now?\n"
                f"(This will close the application)",
                QMessageBox.Yes | QMessageBox.No,
            )

            if reply == QMessageBox.Yes:
                self._run_installer(file_path)
            else:
                QMessageBox.information(
                    self,
                    "Update Ready",
                    f"The installer has been saved to:\n{file_path}\n\n"
                    f"You can run it later to update the application.",
                )
                self.accept()
        else:
            self.status_label.setText(tr("text_download_failed"))
            logger.error("Update download failed")

            QMessageBox.critical(
                self,
                tr("dialog_download_error"),
                "Failed to download the update.\n\n" "Please try again or download manually from GitHub.",
            )

    def _run_installer(self, file_path: str):
        """
        Run the installer and close the application.

        Args:
            file_path: Path to installer file
        """
        try:
            # Launch installer
            if os.name == "nt":  # Windows
                os.startfile(file_path)
            else:
                subprocess.Popen([file_path])

            logger.info(f"Launched installer: {file_path}")

            # Close the application
            QMessageBox.information(
                self, tr("dialog_installing_update"), tr("msg_installer_confirmation", path=file_path)
            )

            # Signal to close the entire application
            from PySide6.QtWidgets import QApplication

            QApplication.instance().quit()

        except Exception as e:
            logger.error(f"Failed to run installer: {e}")
            QMessageBox.critical(
                self,
                tr("dialog_installer_error"),
                f"Failed to run the installer:\n{e}\n\n" f"Please run it manually:\n{file_path}",
            )
