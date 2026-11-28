"""
Configuration management for YT-DLP Studio.

This module handles loading and saving application settings.
"""

from dataclasses import fields
from pathlib import Path

from ..models.app_config import AppConfig
from ..utils.constants import CONFIG_PATH, DEFAULT_OUTPUT_DIR
from ..utils.file_formats import CONFIG_FORMAT, FileState, keep_bad_copy, load_json_file, save_json_file
from ..utils.logger import get_logger

logger = get_logger()


class ConfigManager:
    """
    Manages application configuration persistence.

    Handles loading configuration from JSON file and saving user preferences.
    Creates default configuration if none exists.
    """

    def __init__(self, config_path: Path | None = None):
        """
        Initialize ConfigManager.

        Args:
            config_path: Path to config file (default: CONFIG_PATH from constants)
        """
        self.config_path = config_path or CONFIG_PATH
        self.config: AppConfig | None = None
        logger.info(f"ConfigManager initialized with path: {self.config_path}")

    def load_config(self) -> AppConfig:
        """
        Load configuration from file.

        If config file doesn't exist, creates default configuration.
        An older file format is migrated (see src/utils/file_formats.py).
        If config file is damaged or invalid, keeps a copy as
        ``<name>.bad``, logs a warning and returns defaults.

        Returns:
            AppConfig instance

        Example:
            >>> manager = ConfigManager()
            >>> config = manager.load_config()
            >>> print(config.output_directory)
        """
        # If already loaded, return cached config
        if self.config is not None:
            return self.config

        result = load_json_file(self.config_path, CONFIG_FORMAT)
        if result.state is FileState.MISSING:
            logger.info("Config file not found, creating default")
            self.config = self._create_default_config()
            self.save_config(self.config)
            return self.config

        config = self._config_from_data(result.data) if result.data is not None else None
        if config is None:
            if result.data is not None:
                # Parsed, but the values are unusable: keep the file as .bad.
                logger.warning("Loaded config failed validation, using defaults")
                keep_bad_copy(self.config_path)
            self.config = self._create_default_config()
        else:
            self.config = config
            logger.info("Configuration loaded successfully")

        return self.config

    @staticmethod
    def _config_from_data(data: dict) -> AppConfig | None:
        """
        Build an AppConfig from the (migrated) file content.

        Keys that AppConfig does not know are ignored, so a file from a newer
        app still loads the settings this app understands.

        Returns:
            AppConfig, or None if the values are missing or invalid
        """
        known = {field.name for field in fields(AppConfig)}
        unknown = sorted(set(data) - known)
        if unknown:
            logger.info(f"Ignoring unknown config fields: {', '.join(unknown)}")
        try:
            config = AppConfig.from_dict({key: value for key, value in data.items() if key in known})
            # validate() compares values, so a wrong type raises TypeError.
            return config if config.validate() else None
        except (TypeError, ValueError):
            return None

    def save_config(self, config: AppConfig) -> bool:
        """
        Save configuration to file.

        Args:
            config: AppConfig instance to save

        Returns:
            True if saved successfully, False otherwise

        Example:
            >>> manager = ConfigManager()
            >>> config = manager.load_config()
            >>> config.default_quality = "720p"
            >>> manager.save_config(config)
        """
        try:
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            # Validate before saving
            if not config.validate():
                logger.error("Cannot save invalid configuration")
                return False

            # Save to file (with the format version, atomically)
            save_json_file(self.config_path, CONFIG_FORMAT, config.to_dict(), indent=4)

            self.config = config
            logger.info("Configuration saved successfully")
            return True

        except Exception:
            logger.exception("Error saving config")
            return False

    def update_config(self, **kwargs) -> bool:
        """
        Update specific config values.

        Args:
            **kwargs: Configuration fields to update

        Returns:
            True if saved successfully

        Example:
            >>> manager = ConfigManager()
            >>> manager.update_config(default_quality="1080p", window_width=1024)
        """
        if self.config is None:
            self.load_config()

        # Update specified fields
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.debug(f"Updated config: {key} = {value}")
            else:
                logger.warning(f"Unknown config field: {key}")

        return self.save_config(self.config)

    def reset_to_defaults(self) -> AppConfig:
        """
        Reset configuration to defaults.

        Returns:
            Default AppConfig instance
        """
        logger.info("Resetting configuration to defaults")
        self.config = self._create_default_config()
        self.save_config(self.config)
        return self.config

    def _create_default_config(self) -> AppConfig:
        """
        Create default configuration.

        Returns:
            AppConfig with default values
        """
        return AppConfig(
            output_directory=DEFAULT_OUTPUT_DIR,
            default_quality="Best Quality",
            window_width=900,
            window_height=700,
            last_url="",
        )

    def get_config(self) -> AppConfig:
        """
        Get current configuration.

        Returns:
            Current AppConfig (loads if not loaded)
        """
        if self.config is None:
            return self.load_config()
        return self.config
