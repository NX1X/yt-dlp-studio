"""
Main window for YT-DLP Studio.

The main application window with tabs for Download and Settings.
"""

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow, QMessageBox, QStatusBar, QTabWidget

from ..backend.config_manager import ConfigManager
from ..backend.history_manager import HistoryManager
from ..backend.queue_manager import QueueManager
from ..utils.constants import APP_NAME, WINDOW_MIN_HEIGHT, WINDOW_MIN_WIDTH
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

        # Create queue manager with notification support (v1.7.0)
        self.queue_manager = QueueManager(max_concurrent=3, notification_manager=self.notification_manager)

        # Create history manager (v2.0.0)
        self.history_manager = HistoryManager()

        self._setup_ui()
        self._apply_theme()
        self._apply_rtl_layout()
        self._restore_window_state()
        logger.info("MainWindow initialized")

    def _setup_ui(self) -> None:
        """Set up the main window UI."""
        # Set window title
        self.setWindowTitle(APP_NAME)

        # Set minimum size
        self.setMinimumSize(QSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT))

        # Set application icon
        import os

        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icons", "favicon.svg")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Create central tab widget
        self.tabs = QTabWidget()

        # Create tabs
        self.download_tab = DownloadTab(self.config_manager, self.queue_manager)
        self.queue_tab = QueueTab(self.queue_manager)
        self.history_tab = HistoryTab(self.history_manager)
        self.settings_tab = SettingsTab(self.config_manager)
        self.about_tab = AboutTab()

        # Connect settings to download tab (v1.9.0 smart folder logic)
        self.settings_tab.default_folder_changed.connect(self.download_tab.update_output_directory)

        # Add tabs with translations (v2.0.0 - added History and About tabs)
        self.tabs.addTab(self.download_tab, tr("tab_download"))
        self.tabs.addTab(self.queue_tab, tr("tab_queue"))
        self.tabs.addTab(self.history_tab, tr("tab_history"))
        self.tabs.addTab(self.settings_tab, tr("tab_settings"))
        self.tabs.addTab(self.about_tab, tr("tab_about"))

        # Set as central widget
        self.setCentralWidget(self.tabs)

        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(tr("status_bar_ready"))

        logger.debug("Main window UI setup complete")

    def _restore_window_state(self) -> None:
        """Restore window size from config."""
        self.showMaximized()
        logger.debug("Window opened maximized")

    def closeEvent(self, event) -> None:
        """
        Handle window close event.

        Saves window size to config before closing.

        Args:
            event: Close event
        """
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
                event.ignore()
                return
            else:
                # Cancel download
                self.download_tab.current_worker.cancel()

        event.accept()

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
