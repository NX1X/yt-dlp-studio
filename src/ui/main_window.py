"""
Main window for YT-DLP Studio.

The main application window with tabs for Download and Settings.
"""

from datetime import UTC

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QStatusBar, QTabWidget

from ..backend.config_manager import ConfigManager
from ..backend.history_manager import HistoryManager
from ..backend.queue_manager import QueueManager
from ..utils.constants import APP_DATA_DIR, APP_NAME, WINDOW_MIN_HEIGHT, WINDOW_MIN_WIDTH
from ..utils.logger import get_logger
from ..utils.translations import get_translation_manager, tr
from .about_tab import AboutTab
from .download_tab import DownloadTab
from .history_tab import HistoryTab
from .queue_tab import QueueTab
from .settings_tab import SettingsTab
from .theme import ThemeMode, get_theme_manager

logger = get_logger()


class MainWindow(QMainWindow):
    """
    Main application window.

    Contains tabbed interface with:
    - Download tab
    - Settings tab

    Also provides menu bar and status bar.

    Example:
        >>> window = MainWindow(config_manager)
        >>> window.show()
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize main window.

        Args:
            config_manager: ConfigManager instance
        """
        super().__init__()
        self.config_manager = config_manager

        # Initialize translation manager (v1.8.0)
        self.translation_manager = get_translation_manager()

        # Initialize theme manager (v1.8.0)
        self.theme_manager = get_theme_manager()

        # Create notification manager (v1.7.0)
        from ..utils.notification_manager import NotificationManager

        self.notification_manager = NotificationManager(self)
        self.notification_manager.set_enabled(self.config_manager.get_config().notifications_enabled)

        # Hide-to-tray state. _quitting is set by an explicit Quit (tray
        # menu or Ctrl+Q), so the close that follows really exits.
        self._close_to_tray = self.config_manager.get_config().close_to_tray
        self._quitting = False
        self._tray_hint_shown = False

        # Create history manager (v2.0.0) first: the queue records finished
        # downloads in it.
        self.history_manager = HistoryManager()

        # Create queue manager with notification support (v1.7.0). The queue
        # file sits next to the history file in APP_DATA_DIR.
        self.queue_manager = QueueManager(
            max_concurrent=3,
            notification_manager=self.notification_manager,
            persist_path=APP_DATA_DIR / QueueManager.QUEUE_FILE,
            history_manager=self.history_manager,
        )

        self._setup_ui()
        self._apply_theme()
        self._apply_rtl_layout()
        self._restore_window_state()
        # Restore the saved queue after the Queue tab exists, so the tab
        # shows the restored tasks. Saving starts only after this call.
        self.queue_manager.load_queue()
        self._maybe_check_updates_on_startup()
        logger.info("MainWindow initialized")

    def _maybe_check_updates_on_startup(self) -> None:
        """
        Run a silent background update check at launch, if opted in.

        Skips entirely unless the user enabled it, and throttles to at most
        one check per 24h. Failures stay silent (logged only). A dialog is
        shown only for a genuinely new release the user has not skipped.
        """
        config = self.config_manager.get_config()
        if not config.check_updates_on_startup:
            return

        if config.last_update_check:
            try:
                from datetime import datetime

                last = datetime.fromisoformat(config.last_update_check)
                if (datetime.now(UTC) - last).total_seconds() < 24 * 3600:
                    logger.debug("Skipping startup update check (checked within 24h)")
                    return
            except ValueError:
                pass  # malformed timestamp -> just check again

        from .update_dialog import UpdateCheckThread

        logger.info("Running silent startup update check")
        self._startup_update_thread = UpdateCheckThread(self)
        self._startup_update_thread.check_complete.connect(self._on_startup_update_check)
        self._startup_update_thread.start()

    def _on_startup_update_check(self, result) -> None:
        """Surface the update dialog only for a new, non-skipped release."""
        from datetime import datetime

        if result.error:
            logger.info(f"Startup update check failed silently: {result.error}")
            return

        self.config_manager.update_config(last_update_check=datetime.now(UTC).isoformat())

        if not (result.update_available and result.release_info):
            return

        config = self.config_manager.get_config()
        new_version = result.release_info.get("version", "")
        if new_version and new_version == config.skipped_update_version:
            logger.info(f"Skipping prompt for user-skipped version {new_version}")
            return

        from .update_dialog import UpdateDialog

        logger.info(f"Startup check found update: {new_version}")
        UpdateDialog(result.release_info, self, self.config_manager).exec()

    def _setup_ui(self) -> None:
        """Set up the main window UI."""
        # Set window title
        self.setWindowTitle(APP_NAME)

        # Set minimum size
        self.setMinimumSize(QSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT))

        # Set application icon. Prefer the PNG (renders without the Qt SVG
        # image plugin, which a frozen Linux build may not bundle), then fall
        # back to the SVG for the crisp vector when running from source.
        import os

        icons_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icons")
        for icon_name in ("favicon.png", "favicon.svg", "favicon.ico"):
            icon_path = os.path.join(icons_dir, icon_name)
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
                break

        # Create central tab widget
        self.tabs = QTabWidget()

        # Create tabs
        self.download_tab = DownloadTab(self.config_manager, self.queue_manager)
        self.queue_tab = QueueTab(self.queue_manager)
        self.history_tab = HistoryTab(self.history_manager)
        # New history entries show up without pressing Refresh.
        self.queue_manager.history_recorded.connect(self.history_tab.refresh)
        self.settings_tab = SettingsTab(self.config_manager)
        self.about_tab = AboutTab()

        # Connect settings to download tab (v1.9.0 smart folder logic)
        self.settings_tab.default_folder_changed.connect(self.download_tab.update_output_directory)
        self.settings_tab.notifications_enabled_changed.connect(self.notification_manager.set_enabled)
        self.settings_tab.close_to_tray_changed.connect(self.set_close_to_tray)

        # Add tabs with translations (v2.0.0 - added History and About tabs)
        self.tabs.addTab(self.download_tab, tr("tab_download"))
        self.tabs.addTab(self.queue_tab, tr("tab_queue"))
        self.tabs.addTab(self.history_tab, tr("tab_history"))
        self.tabs.addTab(self.settings_tab, tr("tab_settings"))
        self.tabs.addTab(self.about_tab, tr("tab_about"))

        # Set as central widget
        self.setCentralWidget(self.tabs)

        # Tray icon for desktop notifications. It is created here, on the GUI
        # thread, and owned by the notification manager for the window's
        # lifetime. Without a tray, the manager falls back to notify-send.
        self.notification_manager.show_window_requested.connect(self._show_from_tray)
        self.notification_manager.quit_requested.connect(self.quit_application)
        self.notification_manager.setup_system_tray(self.windowIcon())

        # The tray tooltip shows queue progress. QueueManager emits its
        # signals on the GUI thread, so the slot may touch the tray icon.
        self.queue_manager.queue_updated.connect(self._update_tray_tooltip)
        self._update_tray_tooltip()

        # Ctrl+Q always quits, also when closing only hides to the tray.
        self.quit_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        self.quit_shortcut.activated.connect(self.quit_application)

        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(tr("status_bar_ready"))

        logger.debug("Main window UI setup complete")

    def _show_from_tray(self) -> None:
        """Bring the window to the front from the tray icon."""
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
        self.raise_()
        self.activateWindow()

    def set_close_to_tray(self, enabled: bool) -> None:
        """
        Turn hide-to-tray on close on or off.

        Args:
            enabled: True to hide the window on close instead of quitting
        """
        self._close_to_tray = enabled
        logger.debug(f"Close to tray {'enabled' if enabled else 'disabled'}")

    def _should_hide_to_tray(self) -> bool:
        """Return True if a close should hide the window instead of quitting."""
        return self._close_to_tray and not self._quitting and self.notification_manager.has_visible_tray_icon()

    def quit_application(self) -> None:
        """
        Really quit, also in tray mode (tray menu Quit and Ctrl+Q).

        Runs the normal close path in closeEvent. If the user cancels the
        close (download in progress), the app keeps running.
        """
        self._quitting = True
        if not self.close():
            self._quitting = False

    def _show_tray_hint_once(self) -> None:
        """Tell the user once per session that the app still runs in the tray."""
        if self._tray_hint_shown:
            return
        self._tray_hint_shown = True
        self.notification_manager.show_tray_message(tr("tray_still_running"))

    def tray_tooltip_text(self) -> str:
        """
        Build the tray tooltip from the queue counts.

        Returns:
            The app name when idle, else the app name with the number of
            running and waiting downloads
        """
        stats = self.queue_manager.get_queue_statistics()
        active = stats.get("active", 0)
        pending = stats.get("pending", 0)
        if active == 0 and pending == 0:
            return APP_NAME
        return tr("tray_tooltip_busy", app=APP_NAME, active=active, pending=pending)

    def _update_tray_tooltip(self) -> None:
        """Refresh the tray tooltip. Runs on the GUI thread (queue signals)."""
        self.notification_manager.set_tray_tooltip(self.tray_tooltip_text())

    def _restore_window_state(self) -> None:
        """Restore window size from config."""
        self.showMaximized()
        logger.debug("Window opened maximized")

    def closeEvent(self, event) -> None:
        """
        Handle window close event.

        In tray mode (setting on and a tray icon visible) the window is
        only hidden, and downloads keep running. Otherwise, or after an
        explicit Quit, saves window size to config and quits the app.

        Args:
            event: Close event
        """
        if self._should_hide_to_tray():
            event.ignore()
            self.hide()
            self._show_tray_hint_once()
            logger.info("Window hidden to the system tray")
            return

        # Save window size
        size = self.size()
        self.config_manager.update_config(window_width=size.width(), window_height=size.height())

        logger.info("Application closing, window state saved")

        # Check if download is in progress
        if (
            hasattr(self.download_tab, "current_worker")
            and self.download_tab.current_worker
            and self.download_tab.current_worker.is_running()
        ):
            reply = QMessageBox.question(
                self,
                tr("dialog_download_in_progress"),
                tr("msg_download_in_progress_exit"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )

            if reply == QMessageBox.No:
                self._quitting = False
                event.ignore()
                return
            else:
                # Cancel download
                self.download_tab.current_worker.cancel()

        # Once the close is certain: save the download queue (running
        # downloads are saved as in-progress and resume next start), then
        # cancel the queue workers and wait for them, at most 4 s in total.
        self.queue_manager.shutdown()

        # Remove the tray icon now, so no stale icon stays in the tray.
        self.notification_manager.hide_tray_icon()
        event.accept()

        # src/app.py turns off quit-on-last-window-closed, so hiding to the
        # tray, or closing a dialog while the window is hidden, does not end
        # the app. Quit the event loop here instead. Outside exec() this
        # call does nothing.
        QApplication.quit()

    def _apply_theme(self) -> None:
        """Apply modern theme to application (v1.8.0)."""
        stylesheet = self.theme_manager.set_theme(ThemeMode.DARK)
        self.setStyleSheet(stylesheet)
        logger.info("Modern theme applied")

    def _apply_rtl_layout(self) -> None:
        """Apply RTL (Right-to-Left) layout for Hebrew (v1.9.0)."""
        from PySide6.QtWidgets import QApplication

        lang = self.translation_manager.get_language()

        if lang == "he":
            # Hebrew: Right-to-Left
            QApplication.instance().setLayoutDirection(Qt.RightToLeft)
            logger.info("RTL layout applied for Hebrew")
        else:
            # English: Left-to-Right
            QApplication.instance().setLayoutDirection(Qt.LeftToRight)
            logger.info("LTR layout applied")
