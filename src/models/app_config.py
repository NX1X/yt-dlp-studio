"""
Application configuration data model.

This module defines the configuration structure for YT-DLP Studio.
"""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class AppConfig:
    """
    Application configuration settings.

    This class holds all user-configurable settings for the application.
    Settings are persisted to a JSON file using ConfigManager.

    Attributes:
        output_directory: Default directory for downloaded files
        default_quality: Default quality selection
        window_width: Last window width (for saving window size)
        window_height: Last window height
        last_url: Last URL entered (for convenience)
        check_updates_on_startup: Run a silent update check at launch
        skipped_update_version: Release version the user chose to skip
        last_update_check: ISO timestamp of the last successful update check
    """

    output_directory: str
    default_quality: str = "Best Quality"
    window_width: int = 900
    window_height: int = 700
    last_url: str = ""
    check_updates_on_startup: bool = False
    skipped_update_version: str = ""
    last_update_check: str = ""

    def to_dict(self) -> dict[str, Any]:
        """
        Convert config to dictionary for JSON serialization.

        Returns:
            Dictionary representation of config
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        """
        Create AppConfig from dictionary.

        Args:
            data: Dictionary with config values

        Returns:
            AppConfig instance
        """
        return cls(**data)

    def validate(self) -> bool:
        """
        Validate configuration values.

        Returns:
            True if valid, False otherwise
        """
        # Check output directory is not empty
        if not self.output_directory:
            return False

        # Check window dimensions are reasonable
        if self.window_width < 600 or self.window_height < 400:
            return False

        # Check quality is valid
        from ..utils.constants import QUALITY_NAMES

        if self.default_quality not in QUALITY_NAMES:
            return False

        return True

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"AppConfig(output_directory={self.output_directory}, "
            f"default_quality={self.default_quality}, "
            f"window={self.window_width}x{self.window_height})"
        )
