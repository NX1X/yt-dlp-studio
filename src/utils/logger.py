"""
Logging configuration for YT-DLP Studio.

This module sets up logging for the entire application.
Logs are written to both file and console for debugging purposes.

Every log record passes through :class:`SecretScrubbingFormatter` before
reaching a handler, so URL userinfo (``https://user:pass@host``), Bearer
or Basic tokens, ``api_key=`` / ``password=`` / ``token=`` / ``cookie=``
patterns, and AWS-style access key IDs are replaced with ``[REDACTED]``
before they hit the rolling log file or the console. That defends the
rolling log file under ``%APPDATA%\\YT-DLP Studio\\yt-dlp-studio.log``
against credential leakage from ``logger.exception()`` / ``exc_info=``
traceback content, which is what a user shares when they copy the log
path from Settings -> Storage and attach it to a GitHub issue.
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
from .secret_scrub import scrub_secrets


class SecretScrubbingFormatter(logging.Formatter):
    """A ``logging.Formatter`` that runs every output line through ``scrub_secrets``.

    Subclassing ``Formatter`` (rather than installing a ``Filter``) catches
    *everything* the formatter would emit: the message after ``%``-args
    interpolation, exception tracebacks rendered from ``exc_info=``, and any
    stack info. A filter, by contrast, only sees ``record.msg`` and
    ``record.args`` before formatting, so tracebacks would slip through.
    """

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        formatted = super().format(record)
        return scrub_secrets(formatted)


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

        # Create formatters. Both handlers use the scrubbing formatter so
        # the rolling log file AND any console output are stripped of
        # credentials before any line is emitted.
        formatter = SecretScrubbingFormatter(LOG_FORMAT)

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
