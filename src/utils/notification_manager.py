"""
Notification Manager for YT-DLP Studio.

Handles desktop notifications for download events (completed, error, etc.).
Uses plyer for cross-platform notification support.
"""

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from ..utils.logger import get_logger

logger = get_logger()


class NotificationManager(QObject):
    """
    Manages desktop notifications and system tray integration.

    Provides notifications for:
    - Download completed
    - Download error
    - Batch download completed
    - Application updates available
    """

    # Signals
    show_window_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent=None):
        """
        Initialize NotificationManager.

        Args:
            parent: Parent QObject
        """
        super().__init__(parent)
        self.enabled = True
        self.tray_icon = None
        self.use_system_tray = False
        logger.debug("NotificationManager initialized")

    def setup_system_tray(self, app_icon: QIcon | None = None):
        """
        Setup system tray icon with menu.

        Args:
            app_icon: Application icon to use for tray
        """
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray not available on this platform")
            return

        self.tray_icon = QSystemTrayIcon(self)

        # Set icon
        if app_icon:
            self.tray_icon.setIcon(app_icon)

        # Create tray menu
        tray_menu = QMenu()

        show_action = QAction("Show Window", self)
        show_action.triggered.connect(self.show_window_requested.emit)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_requested.emit)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)

        # Connect double-click to show window
        self.tray_icon.activated.connect(self._on_tray_activated)

        self.tray_icon.show()
        self.use_system_tray = True
        logger.info("System tray icon setup complete")

    def _on_tray_activated(self, reason):
        """
        Handle system tray icon activation.

        Args:
            reason: Activation reason
        """
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_window_requested.emit()

    def set_enabled(self, enabled: bool):
        """
        Enable or disable notifications.

        Args:
            enabled: True to enable, False to disable
        """
        self.enabled = enabled
        logger.debug(f"Notifications {'enabled' if enabled else 'disabled'}")

    def is_enabled(self) -> bool:
        """
        Check if notifications are enabled.

        Returns:
            True if enabled
        """
        return self.enabled

    def notify_download_complete(self, title: str, file_size: str = ""):
        """
        Send notification for completed download.

        Args:
            title: Video title
            file_size: File size string (optional)
        """
        if not self.enabled:
            return

        message = "Download completed"
        if file_size:
            message += f" ({file_size})"

        self._send_notification("Download Complete", f"{title}\n{message}", QSystemTrayIcon.Information)
        logger.info(f"Notification sent: Download complete - {title}")

    def notify_download_error(self, title: str, error: str = ""):
        """
        Send notification for download error.

        Args:
            title: Video title or URL
            error: Error message (optional)
        """
        if not self.enabled:
            return

        message = "Download failed"
        if error:
            message += f": {error[:50]}"  # Truncate long errors

        self._send_notification("Download Error", f"{title}\n{message}", QSystemTrayIcon.Critical)
        logger.info(f"Notification sent: Download error - {title}")

    def notify_batch_complete(self, total: int, successful: int, failed: int):
        """
        Send notification for batch download completion.

        Args:
            total: Total number of downloads
            successful: Number of successful downloads
            failed: Number of failed downloads
        """
        if not self.enabled:
            return

        message = f"Completed: {successful}/{total}"
        if failed > 0:
            message += f"\nFailed: {failed}"

        icon = QSystemTrayIcon.Information if failed == 0 else QSystemTrayIcon.Warning

        self._send_notification("Batch Download Complete", message, icon)
        logger.info(f"Notification sent: Batch complete - {successful}/{total}")

    def notify_update_available(self, version: str):
        """
        Send notification for available update.

        Args:
            version: New version string
        """
        if not self.enabled:
            return

        self._send_notification(
            "Update Available", f"Version {version} is available!\nClick to update.", QSystemTrayIcon.Information
        )
        logger.info(f"Notification sent: Update available - {version}")

    def notify_custom(self, title: str, message: str, icon_type: str = "info"):
        """
        Send custom notification.

        Args:
            title: Notification title
            message: Notification message
            icon_type: Icon type ("info", "warning", "error")
        """
        if not self.enabled:
            return

        icon_map = {
            "info": QSystemTrayIcon.Information,
            "warning": QSystemTrayIcon.Warning,
            "error": QSystemTrayIcon.Critical,
        }

        icon = icon_map.get(icon_type, QSystemTrayIcon.Information)

        self._send_notification(title, message, icon)
        logger.info(f"Notification sent: {title}")

    def _send_notification(self, title: str, message: str, icon: QSystemTrayIcon.MessageIcon):
        """
        Internal method to send notification.

        Args:
            title: Notification title
            message: Notification message
            icon: Icon type
        """
        if self.tray_icon and self.use_system_tray:
            # Use system tray for notification
            self.tray_icon.showMessage(title, message, icon, 3000)  # 3 seconds
        else:
            # Fallback: Try using plyer for cross-platform notifications
            try:
                from plyer import notification

                notification.notify(title=title, message=message, app_name="YT-DLP Studio", timeout=3)
                logger.debug("Sent notification via plyer")
            except Exception as e:
                logger.warning(f"Could not send notification: {e}")

    def show_tray_message(self, message: str):
        """
        Show a quick message in the system tray.

        Args:
            message: Message to display
        """
        if self.tray_icon and self.use_system_tray:
            self.tray_icon.showMessage("YT-DLP Studio", message, QSystemTrayIcon.Information, 2000)  # 2 seconds

    def hide_tray_icon(self):
        """Hide the system tray icon."""
        if self.tray_icon:
            self.tray_icon.hide()
            logger.debug("System tray icon hidden")

    def show_tray_icon(self):
        """Show the system tray icon."""
        if self.tray_icon:
            self.tray_icon.show()
            logger.debug("System tray icon shown")
