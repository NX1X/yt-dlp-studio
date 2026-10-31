"""
Application initialization for YT-DLP Studio.

This module creates and configures the QApplication and main window.
"""

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from .backend.config_manager import ConfigManager
from .backend.environment import start_environment_log
from .ui.main_window import MainWindow
from .utils.constants import APP_NAME, APP_USER_MODEL_ID, APP_VERSION
from .utils.deno_installer import ensure_deno_installed
from .utils.logger import get_logger

logger = get_logger()


class App:
    """
    Main application class.

    Handles initialization of Qt application and main window.

    Example:
        >>> app = App()
        >>> sys.exit(app.run())
    """

    def __init__(self):
        """Initialize the application."""
        logger.info(f"Initializing {APP_NAME} v{APP_VERSION}")

        ensure_deno_installed()

        # Windows: claim the same AppUserModelID the installer puts on the
        # shortcuts, before any window opens. Without it the taskbar shows a
        # second, ungrouped button next to the pinned shortcut.
        if sys.platform == "win32":
            try:
                import ctypes

                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
            except (AttributeError, OSError) as e:
                logger.debug(f"Could not set AppUserModelID: {e}")

        # Create QApplication
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setApplicationName(APP_NAME)
        self.qt_app.setApplicationVersion(APP_VERSION)

        # The app quits only through MainWindow.closeEvent, which calls
        # QApplication.quit() after the clean shutdown. With the Qt default
        # (quit when the last window closes), hiding the window to the tray
        # and then closing any dialog would end the app without that
        # shutdown.
        self.qt_app.setQuitOnLastWindowClosed(False)

        # On Linux, tie the window to its .desktop entry so GNOME/Wayland shows
        # the installed icon in the dock and groups windows correctly. Must
        # match the installed file name (yt-dlp-studio.desktop) and the
        # StartupWMClass declared there.
        if sys.platform.startswith("linux"):
            self.qt_app.setDesktopFileName("yt-dlp-studio")

        # Enable high DPI scaling
        if hasattr(Qt, "AA_EnableHighDpiScaling"):
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        if hasattr(Qt, "AA_UseHighDpiPixmaps"):
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        # Initialize config manager
        self.config_manager = ConfigManager()
        self.config_manager.load_config()

        # Create main window
        self.main_window = MainWindow(self.config_manager)

        logger.info("Application initialized successfully")

    def run(self) -> int:
        """
        Run the application.

        Shows the main window and starts the Qt event loop.

        Returns:
            Exit code from Qt application
        """
        logger.info("Starting application")

        # Show main window
        self.main_window.show()

        # Log startup complete
        logger.info(f"{APP_NAME} started successfully")

        # One line with the versions and install kind, for bug reports. It
        # runs in a background thread because it starts FFmpeg once.
        start_environment_log()

        # Start event loop
        return self.qt_app.exec()
