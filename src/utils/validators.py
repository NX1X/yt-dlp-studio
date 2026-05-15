"""
Input validation utilities for YT-DLP Studio.

This module provides functions to validate user input such as URLs and file paths.
"""

import re
from pathlib import Path

from .constants import URL_PATTERN
from .logger import get_logger

logger = get_logger()


class Validators:
    """Collection of validation functions for user input."""

    @staticmethod
    def is_valid_url(url: str) -> tuple[bool, str]:
        """
        Validate if a string is a valid URL.

        Args:
            url: URL string to validate

        Returns:
            Tuple of (is_valid, error_message)
            - (True, "") if valid
            - (False, error_message) if invalid

        Example:
            >>> is_valid, error = Validators.is_valid_url("https://youtube.com/watch?v=123")
            >>> if is_valid:
            >>>     print("Valid URL")
        """
        if not url or not url.strip():
            return False, "URL cannot be empty"

        url = url.strip()

        # Check basic URL pattern
        if not re.match(URL_PATTERN, url):
            return False, "Invalid URL format. Must start with http:// or https://"

        # Check minimum length
        if len(url) < 10:
            return False, "URL is too short"

        # Check for common issues
        if " " in url:
            return False, "URL contains spaces"

        logger.debug(f"URL validation passed: {url}")
        return True, ""

    @staticmethod
    def is_valid_directory(path: str) -> tuple[bool, str]:
        """
        Validate if a path is a valid directory.

        Args:
            path: Directory path to validate

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> is_valid, error = Validators.is_valid_directory("/home/user/Downloads")
        """
        if not path or not path.strip():
            return False, "Directory path cannot be empty"

        path = path.strip()

        try:
            dir_path = Path(path)

            # Check if path exists
            if not dir_path.exists():
                return False, f"Directory does not exist: {path}"

            # Check if it's actually a directory
            if not dir_path.is_dir():
                return False, f"Path is not a directory: {path}"

            # Check if we can write to it
            if not os.access(dir_path, os.W_OK):
                return False, f"Directory is not writable: {path}"

            logger.debug(f"Directory validation passed: {path}")
            return True, ""

        except Exception as e:
            logger.error(f"Directory validation error: {e}")
            return False, f"Invalid directory path: {str(e)}"

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Remove invalid characters from filename.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename safe for filesystem

        Example:
            >>> safe_name = Validators.sanitize_filename("My Video: Cool!")
            >>> print(safe_name)  # "My Video Cool"
        """
        if not filename:
            return "download"

        # Remove invalid characters for Windows and Linux
        invalid_chars = r'<>:"/\\|?*'
        sanitized = filename

        for char in invalid_chars:
            sanitized = sanitized.replace(char, "")

        # Remove leading/trailing spaces and dots
        sanitized = sanitized.strip(". ")

        # Replace multiple spaces with single space
        sanitized = re.sub(r"\s+", " ", sanitized)

        # If filename is empty after sanitization
        if not sanitized:
            sanitized = "download"

        # Limit length (Windows has 255 char limit)
        max_length = 200  # Leave room for extension
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        logger.debug(f"Filename sanitized: '{filename}' -> '{sanitized}'")
        return sanitized

    @staticmethod
    def validate_quality_choice(quality: str) -> tuple[bool, str]:
        """
        Validate if quality choice is valid.

        Args:
            quality: Quality string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        from .constants import QUALITY_NAMES

        if quality not in QUALITY_NAMES:
            return False, f"Invalid quality choice. Must be one of: {', '.join(QUALITY_NAMES)}"

        return True, ""


# Need to import os for directory validation
import os
