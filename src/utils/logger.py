"""
Logging configuration for YT-DLP Studio.

This module sets up logging for the entire application.
Logs are written to both file and console for debugging purposes.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler

from .constants import (
    APP_NAME,
    LOG_BACKUP_COUNT,
    LOG_FORMAT,
    LOG_LEVEL,
    LOG_MAX_SIZE,
    LOG_PATH,
)


class Logger:
    """
    Application logger singleton.

    Provides centralized logging with file rotation and console output.
    """

    _instance: logging.Logger | None = None

    @classmethod
    def get_logger(cls, name: str = APP_NAME) -> logging.Logger:
        """
        Get or create the application logger.

        Args:
            name: Logger name (default: APP_NAME)

        Returns:
            Configured logger instance
        """
        if cls._instance is None:
            cls._instance = cls._setup_logger(name)
        return cls._instance

    @staticmethod
    def _setup_logger(name: str) -> logging.Logger:
        """
        Set up logger with file and console handlers.

        Args:
            name: Logger name

        Returns:
            Configured logger
        """
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

        # Avoid duplicate handlers if logger already exists
        if logger.handlers:
            return logger

        # Create formatters
        formatter = logging.Formatter(LOG_FORMAT)

        # File handler with rotation
        try:
            file_handler = RotatingFileHandler(
                LOG_PATH,
                maxBytes=LOG_MAX_SIZE,
                backupCount=LOG_BACKUP_COUNT,
                encoding="utf-8",
            )
            file_handler.setLevel(logging.DEBUG)  # Log everything to file
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not create log file: {e}", file=sys.stderr)

        # Console handler (only INFO and above)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Log initial setup
        logger.info(f"Logger initialized. Log file: {LOG_PATH}")

        return logger


# Convenience function
def get_logger(name: str = APP_NAME) -> logging.Logger:
    """
    Get the application logger.

    Args:
        name: Logger name (default: APP_NAME)

    Returns:
        Logger instance

    Example:
        >>> from utils.logger import get_logger
        >>> logger = get_logger()
        >>> logger.info("Application started")
    """
    return Logger.get_logger(name)
