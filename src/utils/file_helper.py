"""
File system helper utilities for YT-DLP Studio.

This module provides helper functions for file and directory operations.
"""

import os
from pathlib import Path

from .constants import SIZE_UNITS
from .logger import get_logger

logger = get_logger()


class FileHelper:
    """Collection of file system utility functions."""

    @staticmethod
    def ensure_directory_exists(path: str) -> bool:
        """
        Create directory if it doesn't exist.

        Args:
            path: Directory path to create

        Returns:
            True if directory exists or was created, False on error

        Example:
            >>> FileHelper.ensure_directory_exists("/path/to/downloads")
        """
        try:
            dir_path = Path(path)
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Directory ensured: {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {path}: {e}")
            return False

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        Format file size in human-readable format.

        Args:
            size_bytes: Size in bytes

        Returns:
            Formatted string (e.g., "1.5 MB")

        Example:
            >>> FileHelper.format_file_size(1536000)
            '1.46 MB'
        """
        if size_bytes == 0:
            return "0 B"

        size = float(size_bytes)
        unit_index = 0

        while size >= 1024.0 and unit_index < len(SIZE_UNITS) - 1:
            size /= 1024.0
            unit_index += 1

        # Format with 2 decimal places, but remove trailing zeros
        formatted = f"{size:.2f}".rstrip("0").rstrip(".")
        return f"{formatted} {SIZE_UNITS[unit_index]}"

    @staticmethod
    def get_file_size(file_path: str) -> int | None:
        """
        Get file size in bytes.

        Args:
            file_path: Path to file

        Returns:
            File size in bytes, or None if file doesn't exist

        Example:
            >>> size = FileHelper.get_file_size("/path/to/video.mp4")
        """
        try:
            return os.path.getsize(file_path)
        except Exception as e:
            logger.error(f"Failed to get file size for {file_path}: {e}")
            return None

    @staticmethod
    def file_exists(file_path: str) -> bool:
        """
        Check if file exists.

        Args:
            file_path: Path to file

        Returns:
            True if file exists, False otherwise
        """
        return Path(file_path).is_file()

    @staticmethod
    def directory_exists(dir_path: str) -> bool:
        """
        Check if directory exists.

        Args:
            dir_path: Path to directory

        Returns:
            True if directory exists, False otherwise
        """
        return Path(dir_path).is_dir()

    @staticmethod
    def get_safe_path(base_dir: str, filename: str) -> str:
        """
        Combine directory and filename safely.

        Args:
            base_dir: Base directory path
            filename: Filename to append

        Returns:
            Full file path

        Example:
            >>> path = FileHelper.get_safe_path("/downloads", "video.mp4")
            >>> print(path)  # "/downloads/video.mp4"
        """
        return str(Path(base_dir) / filename)

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """
        Alias for format_file_size for convenience.

        Args:
            size_bytes: Size in bytes

        Returns:
            Formatted string (e.g., "1.5 MB")

        Example:
            >>> FileHelper.format_size(1536000)
            '1.46 MB'
        """
        return FileHelper.format_file_size(size_bytes)

    @staticmethod
    def format_speed(bytes_per_second: float) -> str:
        """
        Format download speed in human-readable format.

        Args:
            bytes_per_second: Speed in bytes per second

        Returns:
            Formatted string (e.g., "1.5 MB/s")

        Example:
            >>> FileHelper.format_speed(1536000)
            '1.46 MB/s'
        """
        if bytes_per_second == 0:
            return "0 B/s"

        return f"{FileHelper.format_file_size(int(bytes_per_second))}/s"

    @staticmethod
    def format_time(seconds: int) -> str:
        """
        Format time in human-readable format.

        Args:
            seconds: Time in seconds

        Returns:
            Formatted string (e.g., "1h 23m 45s" or "5m 30s")

        Example:
            >>> FileHelper.format_time(90)
            '1m 30s'
        """
        if seconds < 0:
            return "Unknown"

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"
