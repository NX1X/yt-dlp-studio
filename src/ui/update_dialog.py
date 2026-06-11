"""
Update Dialog for YT-DLP Studio.

Shows available updates and allows users to download/install them.
Network work (the GitHub check and the installer download) runs on
background QThreads so the UI never freezes.
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

from ..backend.update_checker import DownloadResult, UpdateCheckResult, UpdateChecker
from ..utils.logger import get_logger
from ..utils.translations import tr

logger = get_logger()


class UpdateCheckThread(QThread):
    """Runs the GitHub update check off the UI thread."""

    # Custom name (not 'finished') to avoid shadowing QThread.finished.
    check_complete = Signal(object)  # UpdateCheckResult

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        try:
            result = UpdateChecker().check_for_updates()
        except Exception as e:  # defensive: never let the thread crash silently
            logger.error(f"Update check thread error: {e}")
            result = UpdateCheckResult(error="unknown")
        self.check_complete.emit(result)


class DownloadThread(QThread):
    """Thread for downloading + verifying updates in the background."""

    progress = Signal(int, int)  # downloaded, total
    # Custom name (not 'finished') to avoid shadowing QThread.finished.
    download_complete = Signal(object)  # DownloadResult

    def __init__(self, download_url: str, output_path: str, expected_digest: str = ""):
        super().__init__()
        self.download_url = download_url
        self.output_path = output_path
        self.expected_digest = expected_digest
        self.checker = UpdateChecker()

    def run(self):
        """Download the update file and verify its integrity."""

        def progress_callback(downloaded, total):
            self.progress.emit(downloaded, total)

        result = self.checker.download_update(
            self.download_url,
            self.output_path,
            expected_digest=self.expected_digest,
            progress_callback=progress_callback,
        )
        self.download_complete.emit(result)


class UpdateDialog(QDialog):
    """
    Dialog for showing and installing updates.

    Displays update information and allows downloading/installing new versions.
    The installer is launched only after its SHA-256 digest has been verified
    against the digest GitHub publishes for the release asset.
    """

    def __init__(self, release_info: dict, parent=None, config_manager=None):
        """
        Initialize UpdateDialog.

        Args:
            release_info: Release information from UpdateChecker
            parent: Parent widget
            config_manager: Optional ConfigManager, used to persist a
                "skip this version" choice.
        """
        super().__init__(parent)
        self.release_info = release_info
        self.config_manager = config_manager
        self.download_thread = None
        self._setup_ui()
        logger.debug(f"UpdateDialog initialized for version {release_info['version']}")

    def _setup_ui(self):
        """Setup the dialog UI."""
        self.setWindowTitle(tr("dialog_update_available"))
        self.setMinimumWidth(550)
        self.setMinimumHeight(450)

        layout = QVBoxLayout()

        version_label = QLabel(f"<h2>{tr('text_version_available', version=self.release_info['version'])}</h2>")
        layout.addWidget(version_label)

        checker = UpdateChecker()
        current_label = QLabel(f"<b>{tr('label_current_version')}</b> {checker.get_current_version()}")
        layout.addWidget(current_label)

        new_label = QLabel(f"<b>{tr('label_new_version')}</b> {self.release_info['version']}")
        layout.addWidget(new_label)

        website_label = QLabel('<b>Website:</b> <a href="https://studio.nx1xlab.dev">studio.nx1xlab.dev</a>')
        website_label.setOpenExternalLinks(True)
        website_label.setTextFormat(Qt.RichText)
        layout.addWidget(website_label)

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

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        layout.addStretch()

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

        self.skip_btn = QPushButton(tr("button_skip_version"))
        self.skip_btn.setMinimumWidth(140)
        self.skip_btn.clicked.connect(self._skip_version)
        button_layout.addWidget(self.skip_btn)

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
        """Open the project website in browser."""
        import webbrowser

        website_url = "https://studio.nx1xlab.dev"
        webbrowser.open(website_url)
        logger.info(f"Opened website: {website_url}")

    def _skip_version(self):
        """Persist a 'skip this version' choice so startup checks stay quiet."""
        skipped = self.release_info.get("version", "")
        if self.config_manager is not None and skipped:
            self.config_manager.update_config(skipped_update_version=skipped)
            logger.info(f"User chose to skip version {skipped}")
        self.reject()

    def _download_update(self):
        """Start downloading the update (user confirmation required)."""
        download_url = self.release_info.get("download_url")

        if not download_url:
            QMessageBox.warning(self, tr("dialog_download_error"), tr("msg_no_download_url"))
            return

        output_dir = Path.home() / "Downloads"
        output_dir.mkdir(exist_ok=True)

        filename = f"YT-DLP-Studio-{self.release_info['version']}.exe"
        output_path = output_dir / filename

        size_bytes = self.release_info.get("size", 0)
        size_str = f"{size_bytes / (1024 * 1024):.1f} MB" if size_bytes else tr("text_unknown_size")
        reply = QMessageBox.question(
            self,
            tr("dialog_confirm_download"),
            tr("msg_confirm_download_text", filename=str(output_path), size=size_str),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply != QMessageBox.Yes:
            logger.info("User cancelled update download")
            return

        self.download_btn.setEnabled(False)
        self.view_online_btn.setEnabled(False)
        self.website_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)
        self.later_btn.setEnabled(False)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setVisible(True)
        self.status_label.setText(tr("text_downloading_update"))

        self.download_thread = DownloadThread(
            download_url,
            str(output_path),
            expected_digest=self.release_info.get("digest", ""),
        )
        self.download_thread.progress.connect(self._on_progress)
        self.download_thread.download_complete.connect(self._on_download_finished)
        self.download_thread.start()

        logger.info(f"Started downloading update to: {output_path}")

    def _on_progress(self, downloaded: int, total: int):
        """Update progress bar."""
        if total > 0:
            progress = int((downloaded / total) * 100)
            self.progress_bar.setValue(progress)

            downloaded_mb = downloaded / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            self.status_label.setText(f"Downloading: {downloaded_mb:.1f} MB / {total_mb:.1f} MB ({progress}%)")

    def _on_download_finished(self, result: DownloadResult):
        """
        Handle download completion.

        Args:
            result: DownloadResult from the download thread.
        """
        self.download_btn.setEnabled(True)
        self.view_online_btn.setEnabled(True)
        self.website_btn.setEnabled(True)
        self.skip_btn.setEnabled(True)
        self.later_btn.setEnabled(True)

        if result.success:
            self.status_label.setText(tr("text_download_verified"))
            logger.info(f"Update downloaded and verified: {result.file_path}")

            reply = QMessageBox.question(
                self,
                tr("dialog_download_complete_update"),
                tr("msg_download_verified_install", path=result.file_path),
                QMessageBox.Yes | QMessageBox.No,
            )

            if reply == QMessageBox.Yes:
                self._run_installer(result.file_path)
            else:
                QMessageBox.information(
                    self,
                    tr("dialog_download_complete_update"),
                    tr("msg_installer_saved", path=result.file_path),
                )
                self.accept()
            return

        # Failure paths.
        self.status_label.setText(tr("text_download_failed"))

        if result.error == "verify_failed":
            logger.error("Update integrity verification failed")
            QMessageBox.critical(
                self,
                tr("dialog_verify_failed"),
                tr(
                    "msg_verify_failed",
                    expected=result.expected_digest,
                    actual=result.actual_digest,
                ),
            )
        elif result.error == "no_digest":
            logger.warning("Update downloaded but could not be verified (no published digest)")
            QMessageBox.warning(
                self,
                tr("dialog_unverified_download"),
                tr("msg_unverified_download", path=result.file_path),
            )
        else:
            logger.error("Update download failed")
            QMessageBox.critical(
                self,
                tr("dialog_download_error"),
                tr("msg_download_failed_retry"),
            )

    def _run_installer(self, file_path: str):
        """
        Run the (already verified) installer and close the application.

        Args:
            file_path: Path to installer file
        """
        try:
            if os.name == "nt":  # Windows
                os.startfile(file_path)
            else:
                subprocess.Popen([file_path])

            logger.info(f"Launched installer: {file_path}")

            QMessageBox.information(
                self, tr("dialog_installing_update"), tr("msg_installer_confirmation", path=file_path)
            )

            from PySide6.QtWidgets import QApplication

            QApplication.instance().quit()

        except Exception as e:
            logger.error(f"Failed to run installer: {e}")
            QMessageBox.critical(
                self,
                tr("dialog_installer_error"),
                tr("msg_installer_launch_failed", error=str(e), path=file_path),
            )
