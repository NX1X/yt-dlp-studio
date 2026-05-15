"""
Application initialization for YT-DLP Studio.

This module creates and configures the QApplication and main window.
"""

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from .backend.config_manager import ConfigManager
from .ui.main_window import MainWindow
from .utils.constants import APP_NAME, APP_VERSION
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

        # Create QApplication
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setApplicationName(APP_NAME)
        self.qt_app.setApplicationVersion(APP_VERSION)

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

        # Start event loop
        return self.qt_app.exec()
