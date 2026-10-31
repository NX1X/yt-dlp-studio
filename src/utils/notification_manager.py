"""
Notification Manager for YT-DLP Studio.

Handles desktop notifications for download events (completed, error, etc.).

Backends, tried in this order until one accepts the notification:

1. Qt ``QSystemTrayIcon.showMessage`` on a tray icon that lives as long as
   the main window. This is the native path on Windows 10/11 and on Linux
   desktops that have a system tray (KDE, GNOME with an AppIndicator
   extension, and so on).
2. ``notify-send`` (libnotify) on Linux when no system tray is available,
   for example stock GNOME. It is called with an argument list, never a
   shell string, because titles come from untrusted video metadata.

Every ``notify_*`` method returns ``True`` only when a backend accepted the
notification, and only then logs "Notification sent".
"""

import os
import shutil
import subprocess
import sys

from PySide6.QtCore import QCoreApplication, QObject, QThread, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon

from ..utils.constants import APP_NAME
from ..utils.logger import get_logger

logger = get_logger()

# Seconds to wait for notify-send. It normally returns in well under a
# second; the cap keeps a stuck D-Bus from freezing the GUI thread for long.
NOTIFY_SEND_TIMEOUT_S = 3

# How long a toast stays on screen, in milliseconds.
DEFAULT_TIMEOUT_MS = 5000

_NOTIFY_SEND_URGENCY = {
    QSystemTrayIcon.MessageIcon.Information: "normal",
    QSystemTrayIcon.MessageIcon.Warning: "normal",
    QSystemTrayIcon.MessageIcon.Critical: "critical",
    QSystemTrayIcon.MessageIcon.NoIcon: "low",
}


def _is_linux_like() -> bool:
    """Return True on platforms where notify-send may exist."""
    return sys.platform.startswith(("linux", "freebsd", "openbsd", "netbsd"))


def _subprocess_env() -> dict[str, str]:
    """
    Build the environment for an external system binary.

    A frozen PyInstaller build on Linux points LD_LIBRARY_PATH at the bundle,
    which can make system binaries such as notify-send load the wrong libglib.
    PyInstaller keeps the original value in LD_LIBRARY_PATH_ORIG.
    """
    env = dict(os.environ)
    if getattr(sys, "frozen", False):
        original = env.get("LD_LIBRARY_PATH_ORIG")
        if original is not None:
            env["LD_LIBRARY_PATH"] = original
        else:
            env.pop("LD_LIBRARY_PATH", None)
    return env


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
        self.tray_icon: QSystemTrayIcon | None = None
        self._tray_menu: QMenu | None = None
        self.use_system_tray = False
        logger.debug("NotificationManager initialized")

    def setup_system_tray(self, app_icon: QIcon | None = None) -> bool:
        """
        Create the system tray icon with its menu.

        Call this once, on the GUI thread. The icon is a child of this object
        and is kept referenced for the lifetime of the manager.

        Args:
            app_icon: Application icon to use for tray

        Returns:
            True if a tray icon is now visible
        """
        if self.tray_icon is not None:
            return self.use_system_tray

        if not QSystemTrayIcon.isSystemTrayAvailable():
            fallback = "notify-send" if self._find_notify_send() else "no other backend"
            logger.info(f"System tray not available; notifications will use {fallback}")
            return False

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setToolTip(APP_NAME)

        # A tray icon without an icon is invisible on Windows, and an
        # invisible tray icon cannot show messages.
        icon = app_icon if app_icon is not None and not app_icon.isNull() else None
        if icon is None:
            app = QApplication.instance()
            if app is not None and not app.windowIcon().isNull():
                icon = app.windowIcon()
            elif app is not None:
                icon = app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        if icon is not None:
            self.tray_icon.setIcon(icon)

        # Keep the menu referenced: setContextMenu does not take ownership.
        self._tray_menu = QMenu()

        show_action = QAction("Show Window", self)
        show_action.triggered.connect(self.show_window_requested.emit)
        self._tray_menu.addAction(show_action)

        self._tray_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_requested.emit)
        self._tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(self._tray_menu)

        # Connect double-click to show window
        self.tray_icon.activated.connect(self._on_tray_activated)

        self.tray_icon.show()
        self.use_system_tray = True
        logger.info("System tray icon setup complete")
        return True

    def _on_tray_activated(self, reason):
        """
        Handle system tray icon activation.

        Args:
            reason: Activation reason
        """
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
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

    def notify_download_complete(self, title: str, file_size: str = "") -> bool:
        """
        Send notification for completed download.

        Args:
            title: Video title
            file_size: File size string (optional)

        Returns:
            True if a backend accepted the notification
        """
        if not self.enabled:
            return False

        message = "Download completed"
        if file_size:
            message += f" ({file_size})"

        sent = self._send_notification(
            "Download Complete", f"{title}\n{message}", QSystemTrayIcon.MessageIcon.Information
        )
        if sent:
            logger.info(f"Notification sent: Download complete - {title}")
        return sent

    def notify_download_error(self, title: str, error: str = "") -> bool:
        """
        Send notification for download error.

        Args:
            title: Video title or URL
            error: Error message (optional)

        Returns:
            True if a backend accepted the notification
        """
        if not self.enabled:
            return False

        message = "Download failed"
        if error:
            message += f": {error[:50]}"  # Truncate long errors

        sent = self._send_notification("Download Error", f"{title}\n{message}", QSystemTrayIcon.MessageIcon.Critical)
        if sent:
            logger.info(f"Notification sent: Download error - {title}")
        return sent

    def notify_batch_complete(self, total: int, successful: int, failed: int) -> bool:
        """
        Send notification for batch download completion.

        Args:
            total: Total number of downloads
            successful: Number of successful downloads
            failed: Number of failed downloads

        Returns:
            True if a backend accepted the notification
        """
        if not self.enabled:
            return False

        message = f"Completed: {successful}/{total}"
        if failed > 0:
            message += f"\nFailed: {failed}"

        icon = QSystemTrayIcon.MessageIcon.Information if failed == 0 else QSystemTrayIcon.MessageIcon.Warning

        sent = self._send_notification("Batch Download Complete", message, icon)
        if sent:
            logger.info(f"Notification sent: Batch complete - {successful}/{total}")
        return sent

    def notify_update_available(self, version: str) -> bool:
        """
        Send notification for available update.

        Args:
            version: New version string

        Returns:
            True if a backend accepted the notification
        """
        if not self.enabled:
            return False

        sent = self._send_notification(
            "Update Available",
            f"Version {version} is available!\nClick to update.",
            QSystemTrayIcon.MessageIcon.Information,
        )
        if sent:
            logger.info(f"Notification sent: Update available - {version}")
        return sent

    def notify_custom(self, title: str, message: str, icon_type: str = "info") -> bool:
        """
        Send custom notification.

        Args:
            title: Notification title
            message: Notification message
            icon_type: Icon type ("info", "warning", "error")

        Returns:
            True if a backend accepted the notification
        """
        if not self.enabled:
            return False

        icon_map = {
            "info": QSystemTrayIcon.MessageIcon.Information,
            "warning": QSystemTrayIcon.MessageIcon.Warning,
            "error": QSystemTrayIcon.MessageIcon.Critical,
        }

        icon = icon_map.get(icon_type, QSystemTrayIcon.MessageIcon.Information)

        sent = self._send_notification(title, message, icon)
        if sent:
            logger.info(f"Notification sent: {title}")
        return sent

    def _send_notification(
        self,
        title: str,
        message: str,
        icon: QSystemTrayIcon.MessageIcon,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ) -> bool:
        """
        Send a notification through the first backend that accepts it.

        Args:
            title: Notification title
            message: Notification message
            icon: Icon type
            timeout_ms: How long the toast stays visible

        Returns:
            True if a backend accepted the notification. On False, one
            WARNING names every backend that was tried and why it failed.
        """
        attempts: list[str] = []

        for name, backend in (
            ("tray", self._send_via_tray),
            ("notify-send", self._send_via_notify_send),
        ):
            ok, reason = backend(title, message, icon, timeout_ms)
            if ok:
                logger.debug(f"Notification delivered via {name}")
                return True
            attempts.append(f"{name}: {reason}")

        logger.warning(f"Could not send notification '{title}'. Backends tried: {'; '.join(attempts)}")
        return False

    def _send_via_tray(self, title: str, message: str, icon, timeout_ms: int) -> tuple[bool, str]:
        """Show the message as a tray balloon or toast."""
        if self.tray_icon is None or not self.use_system_tray:
            return False, "no tray icon"
        if not self.tray_icon.isVisible():
            return False, "tray icon not visible"
        if not QSystemTrayIcon.supportsMessages():
            return False, "messages not supported"
        app = QCoreApplication.instance()
        if app is None or QThread.currentThread() is not app.thread():
            return False, "not on the GUI thread"
        try:
            self.tray_icon.showMessage(title, message, icon, timeout_ms)
        except Exception as e:  # pragma: no cover - Qt rarely raises here
            return False, f"error: {e}"
        return True, ""

    @staticmethod
    def _find_notify_send() -> str | None:
        """Return the path to notify-send on Linux, or None."""
        if not _is_linux_like():
            return None
        return shutil.which("notify-send")

    def _send_via_notify_send(self, title: str, message: str, icon, timeout_ms: int) -> tuple[bool, str]:
        """Call notify-send with an argument list (no shell)."""
        path = self._find_notify_send()
        if path is None:
            return False, "not available"

        args = [
            path,
            f"--app-name={APP_NAME}",
            f"--urgency={_NOTIFY_SEND_URGENCY.get(icon, 'normal')}",
            f"--expire-time={int(timeout_ms)}",
            "--",  # Everything after this is text, even if it starts with "-".
            title,
            message,
        ]
        try:
            result = subprocess.run(  # noqa: S603 - fixed binary, argument list, no shell
                args,
                check=False,
                timeout=NOTIFY_SEND_TIMEOUT_S,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                env=_subprocess_env(),
            )
        except subprocess.TimeoutExpired:
            return False, f"timed out after {NOTIFY_SEND_TIMEOUT_S}s"
        except (OSError, subprocess.SubprocessError) as e:
            return False, f"error: {e}"

        if result.returncode != 0:
            stderr = (result.stderr or b"").decode("utf-8", errors="replace").strip()
            detail = f" ({stderr[:200]})" if stderr else ""
            return False, f"exit code {result.returncode}{detail}"
        return True, ""

    def show_tray_message(self, message: str) -> bool:
        """
        Show a quick message in the system tray.

        Args:
            message: Message to display

        Returns:
            True if the tray accepted the message
        """
        ok, _ = self._send_via_tray(APP_NAME, message, QSystemTrayIcon.MessageIcon.Information, 2000)
        return ok

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
