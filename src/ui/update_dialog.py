"""
Update Dialog for YT-DLP Studio.

Shows available updates and allows users to download/install them.
Network work (the GitHub check and the installer download) runs on
background QThreads so the UI never freezes.
"""

import hmac
import html
import os
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QTextDocument
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from ..backend.update_checker import (
    DownloadResult,
    UpdateChecker,
    UpdateCheckResult,
    is_installed_copy,
    safe_asset_filename,
    sha256_of_file,
)
from ..utils.logger import get_logger
from ..utils.translations import tr
from .bidi import ltr

logger = get_logger()

WEBSITE_URL = "https://studio.nx1xlab.dev"

# Release notes are scrollable, so show most of them.
RELEASE_NOTES_MAX_LENGTH = 6000

# GitHub flavored Markdown without raw HTML: the notes come from the network.
MARKDOWN_FEATURES = QTextDocument.MarkdownFeature.MarkdownDialectGitHub | QTextDocument.MarkdownFeature.MarkdownNoHTML


def is_web_url(url: str) -> bool:
    """True for an http(s) link; other schemes (file:, javascript:) never open."""
    return QUrl(url).scheme().lower() in ("http", "https")


def open_web_link(url: str) -> None:
    """Open an http(s) link from the release notes in the browser; ignore anything else."""
    if is_web_url(url):
        QDesktopServices.openUrl(QUrl(url))
        logger.info(f"Opened link: {url}")
    else:
        logger.warning(f"Ignored a non-web link in the update dialog: {url!r}")


def _link(url: str, text: str) -> str:
    return f'<a href="{html.escape(url, quote=True)}">{html.escape(text)}</a>'


def child_process_env() -> dict[str, str]:
    """Return the environment for a process this app starts and then quits.

    A PyInstaller one-file app passes ``_PYI_*`` variables to its child
    processes. They point at the app's temporary folder (``_MEI...``), which
    is deleted when the app quits. The installer inherits them and passes
    them to the new app it starts, and that app then fails with "Failed to
    load Python DLL" from the deleted folder. ``PYINSTALLER_RESET_ENVIRONMENT``
    tells a PyInstaller app to ignore them.
    """
    env = {k: v for k, v in os.environ.items() if not k.startswith("_PYI_") and k != "_MEIPASS2"}
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env


class UpdateCheckThread(QThread):
    """Runs the GitHub update check off the UI thread."""

    # Custom name (not 'finished') to avoid shadowing QThread.finished.
    check_complete = Signal(object)  # UpdateCheckResult

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        try:
            result = UpdateChecker().check_for_updates()
        except Exception:  # noqa: BLE001 - defensive: never let the thread crash silently
            logger.exception("Update check thread error")
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
        self.setMinimumWidth(560)
        self.setMinimumHeight(460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        version = self.release_info["version"]
        version_label = QLabel(tr("text_version_available", version=ltr(version)))
        version_label.setProperty("labelStyle", "title")
        version_label.setWordWrap(True)
        layout.addWidget(version_label)

        checker = UpdateChecker()
        versions = QFormLayout()
        versions.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)
        versions.setHorizontalSpacing(12)
        versions.addRow(self._secondary(tr("label_current_version")), QLabel(ltr(checker.get_current_version())))
        versions.addRow(self._secondary(tr("label_new_version")), QLabel(ltr(version)))
        layout.addLayout(versions)

        # Links in the text, not as buttons (GitHub release page, website)
        links = []
        release_url = self.release_info.get("html_url", "")
        if is_web_url(release_url):
            links.append(_link(release_url, tr("button_view_on_github")))
        links.append(f"{html.escape(tr('label_website'))} {_link(WEBSITE_URL, 'studio.nx1xlab.dev')}")
        self.links_label = QLabel(" &nbsp;&nbsp;|&nbsp;&nbsp; ".join(links))
        self.links_label.setTextFormat(Qt.RichText)
        self.links_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.links_label.setOpenExternalLinks(False)
        self.links_label.linkActivated.connect(open_web_link)
        layout.addWidget(self.links_label)

        layout.addSpacing(4)
        notes_label = QLabel(tr("label_release_notes"))
        notes_label.setProperty("labelStyle", "subtitle")
        layout.addWidget(notes_label)

        # Release notes are Markdown on GitHub. Raw HTML is not rendered and
        # only http(s) links open (in the browser).
        self.notes_text = QTextBrowser()
        self.notes_text.setOpenLinks(False)
        self.notes_text.anchorClicked.connect(lambda url: open_web_link(url.toString()))
        body = self.release_info.get("body") or tr("text_no_release_notes")
        self.notes_text.document().setMarkdown(
            UpdateChecker.format_release_notes(body, max_length=RELEASE_NOTES_MAX_LENGTH), MARKDOWN_FEATURES
        )
        layout.addWidget(self.notes_text, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setVisible(False)
        self.status_label.setProperty("labelStyle", "secondary")
        layout.addWidget(self.status_label)

        # Buttons: the platform decides the order. One primary button.
        self.button_box = QDialogButtonBox()
        self.download_btn = QPushButton(tr("button_download_update"))
        self.download_btn.setProperty("buttonStyle", "primary")
        self.download_btn.setDefault(True)
        self.download_btn.clicked.connect(self._download_update)
        self.button_box.addButton(self.download_btn, QDialogButtonBox.ButtonRole.AcceptRole)

        self.skip_btn = QPushButton(tr("button_skip_version"))
        self.skip_btn.clicked.connect(self._skip_version)
        self.button_box.addButton(self.skip_btn, QDialogButtonBox.ButtonRole.ActionRole)

        self.later_btn = QPushButton(tr("button_remind_me_later"))
        self.later_btn.clicked.connect(self.reject)
        self.button_box.addButton(self.later_btn, QDialogButtonBox.ButtonRole.RejectRole)
        layout.addWidget(self.button_box)

    @staticmethod
    def _secondary(text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty("labelStyle", "secondary")
        return label

    def _set_buttons_enabled(self, enabled: bool) -> None:
        for button in (self.download_btn, self.skip_btn, self.later_btn):
            button.setEnabled(enabled)
        self.links_label.setEnabled(enabled)

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

        # Prefer the real asset filename published on the release (keeps the
        # correct extension - .exe on Windows, .tar.gz on Linux). Fall back to
        # a platform-appropriate default only if the release omitted it.
        asset_name = safe_asset_filename(self.release_info.get("asset_name"))
        if asset_name:
            filename = asset_name
        elif os.name == "nt":
            filename = f"YT-DLP-Studio-{self.release_info['version']}.exe"
        else:
            filename = f"yt-dlp-studio-{self.release_info['version']}-Linux.tar.gz"
        output_path = output_dir / filename
        # Defence in depth: the file must land directly in the Downloads folder.
        if output_path.resolve().parent != output_dir.resolve():
            logger.error(f"Refusing update path outside the Downloads folder: {output_path}")
            QMessageBox.warning(self, tr("dialog_download_error"), tr("msg_no_download_url"))
            return

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

        self._set_buttons_enabled(False)

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
            self.status_label.setText(
                tr(
                    "text_update_download_progress",
                    done=ltr(f"{downloaded_mb:.1f} MB"),
                    total=ltr(f"{total_mb:.1f} MB"),
                    percent=ltr(f"{progress}%"),
                )
            )

    def _on_download_finished(self, result: DownloadResult):
        """
        Handle download completion.

        Args:
            result: DownloadResult from the download thread.
        """
        self._set_buttons_enabled(True)

        if result.success:
            self.status_label.setText(tr("text_download_verified"))
            logger.info(f"Update downloaded and verified: {result.file_path}")
            self._handle_verified_download(result.file_path)
            return

        # Failure paths.
        self.status_label.setText(tr("text_download_failed"))
        self._show_download_error(result)

    def _show_file_saved(self, file_path: str, message_key: str = "msg_installer_saved"):
        """Tell the user where the downloaded update was saved."""
        QMessageBox.information(
            self,
            tr("dialog_download_complete_update"),
            tr(message_key, path=file_path),
        )

    def _ask_yes_no(self, message: str) -> bool:
        """Ask a Yes/No question in the "download complete" dialog."""
        reply = QMessageBox.question(
            self,
            tr("dialog_download_complete_update"),
            message,
            QMessageBox.Yes | QMessageBox.No,
        )
        return reply == QMessageBox.Yes

    def _handle_verified_download(self, file_path: str):
        """Offer the next step for a verified update file."""
        kind = self.release_info.get("update_kind")

        if os.name != "nt":
            # Linux: nothing is run from here. Reveal the file in the file
            # manager with the next step for its kind (extract the archive,
            # open the package, or start the new AppImage); the running app
            # is left open.
            reveal_key = {
                "appimage": "msg_download_verified_reveal_appimage",
                "package": "msg_download_verified_reveal_package",
            }.get(kind, "msg_download_verified_reveal")
            if self._ask_yes_no(tr(reveal_key, path=file_path)):
                self._reveal_in_file_manager(file_path)
            else:
                self._show_file_saved(file_path)
            self.accept()
            return

        is_exe = file_path.lower().endswith(".exe")
        if kind not in ("installer", "portable") or not is_exe:
            # A ZIP or an unknown asset: never execute it. Show it instead.
            self._reveal_in_file_manager(file_path)
            self.accept()
            return

        if kind == "installer":
            self._offer_installer_update(file_path)
        else:
            self._offer_portable_update(file_path)

    def _offer_installer_update(self, file_path: str):
        """Run the verified installer on an installed copy, if the user agrees."""
        if not is_installed_copy():
            # A portable copy must not run the installer silently; that
            # would create a second, installed copy behind the user's back.
            logger.warning("Installer update offered to a portable copy; not running it")
            self._show_file_saved(file_path)
            self.accept()
            return

        # Installed copy: the installer replaces this copy in place
        # and starts the app again (/LAUNCH=yes).
        if self._ask_yes_no(tr("msg_update_install_restart", version=self.release_info.get("version", ""))):
            self._run_installer_silent(file_path)
        else:
            self._show_file_saved(file_path)
            self.accept()

    def _offer_portable_update(self, file_path: str):
        """Start the new portable EXE, if the user agrees."""
        # Portable copy: the download is a second, separate copy. Say so.
        if self._ask_yes_no(tr("msg_portable_update_ready", path=file_path)):
            self._launch_and_quit([file_path])
        else:
            self._show_file_saved(file_path, "msg_portable_update_saved")
            self.accept()

    def _show_download_error(self, result: DownloadResult):
        """Show why the update download failed."""
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

    # Arguments for the Inno Setup installer during an in-place update:
    # /SILENT shows only a progress window, /SUPPRESSMSGBOXES and /NORESTART
    # keep it unattended, and /LAUNCH=yes makes it start the app again when it
    # is done (see the [Run] section of packaging/installer.iss).
    SILENT_INSTALL_ARGS = ("/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/LAUNCH=yes")

    def _run_installer_silent(self, file_path: str):
        """Run the verified installer to update this installed copy in place, then quit.

        The installer closes any copy still running (CloseApplications=force),
        replaces the EXE and starts the new version.
        """
        self._launch_and_quit([file_path, *self.SILENT_INSTALL_ARGS])

    def _launch_and_quit(self, argv: list[str]):
        """Start a verified, downloaded program detached from this app, then quit.

        Only called after the download's SHA-256 matched the published digest.
        argv is passed as a list, never through a shell.
        """
        expected = self.release_info.get("digest", "")
        try:
            actual = sha256_of_file(argv[0])
        except OSError as e:
            actual = f"unreadable ({e})"
        if not expected or not hmac.compare_digest(actual, expected):
            logger.error(f"Update changed after verification; not starting it ({argv[0]})")
            QMessageBox.critical(
                self,
                tr("dialog_verify_failed"),
                tr("msg_verify_failed", expected=expected or "-", actual=actual),
            )
            return
        try:
            flags = 0
            if os.name == "nt":
                flags = getattr(subprocess, "DETACHED_PROCESS", 0x00000008) | getattr(
                    subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200
                )
            # S603: the file was verified and argv is a list (no shell).
            subprocess.Popen(argv, close_fds=True, creationflags=flags, env=child_process_env())  # noqa: S603
            logger.info(f"Launched update: {argv[0]} (args: {' '.join(argv[1:]) or 'none'})")

            from PySide6.QtWidgets import QApplication

            QApplication.instance().quit()

        except Exception as e:
            logger.exception("Failed to start the downloaded update")
            QMessageBox.critical(
                self,
                tr("dialog_installer_error"),
                tr("msg_installer_launch_failed", error=str(e), path=argv[0]),
            )

    def _reveal_in_file_manager(self, file_path: str):
        """
        Open the folder containing the downloaded file.

        Explorer on Windows, ``xdg-open`` elsewhere. Used for archives (and any
        asset that is not a verified installer or portable EXE), so the user
        can extract and run it themselves. The app is NOT closed - unlike the
        Windows installer flow, there is no executable to hand off to.

        Args:
            file_path: Path to the downloaded archive.
        """
        folder = str(Path(file_path).parent)
        try:
            if os.name == "nt":
                # S606: this opens a folder in Explorer and starts no program.
                os.startfile(folder)  # noqa: S606
            else:
                subprocess.Popen(["xdg-open", folder])
            logger.info(f"Opened download folder: {folder}")
            QMessageBox.information(
                self,
                tr("dialog_download_complete_update"),
                tr("msg_installer_saved", path=file_path),
            )
        except Exception:
            logger.exception("Failed to open download folder")
            QMessageBox.information(
                self,
                tr("dialog_download_complete_update"),
                tr("msg_installer_saved", path=file_path),
            )
