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
        notifications_enabled: Show desktop notifications for download events
        close_to_tray: Hide the window to the system tray on close, instead of quitting
        theme: UI theme, "dark" (default) or "light"
        cookies_browser: Browser to read cookies from for downloads ("" = none)
        cookies_profile: Browser profile name or folder ("" = default profile)
        proxy_url: Proxy for downloads and info look-ups ("" = no proxy).
            May hold a user name and password; never log it unmasked.
        filename_template_preset: File name preset (see download_options.FILENAME_PRESETS)
        custom_filename_template: yt-dlp template for the "custom" preset
        video_codec_preference: Preferred video codec ("any", "h264", "h265", "vp9", "av1")
        audio_codec_preference: Preferred audio codec for videos ("any", "aac", "opus", "vorbis")
        custom_format: yt-dlp format string that replaces quality and codecs ("" = not used)

    The advanced download fields are checked when they are used (see
    backend/download_preferences.py), not in ``validate()``: a bad value
    there falls back to its default instead of resetting the whole config.
    """

    output_directory: str
    default_quality: str = "Best Quality"
    window_width: int = 900
    window_height: int = 700
    last_url: str = ""
    check_updates_on_startup: bool = False
    skipped_update_version: str = ""
    last_update_check: str = ""
    notifications_enabled: bool = True
    close_to_tray: bool = False
    # UI theme, "dark" or "light". Unknown values start in dark (see ThemeMode.from_value).
    theme: str = "dark"
    # Advanced download options (0.5.0)
    cookies_browser: str = ""
    cookies_profile: str = ""
    proxy_url: str = ""
    filename_template_preset: str = "title_quality"
    custom_filename_template: str = ""
    video_codec_preference: str = "any"
    audio_codec_preference: str = "any"
    custom_format: str = ""

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
