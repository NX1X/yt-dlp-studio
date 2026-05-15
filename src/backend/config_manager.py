"""
Configuration management for YT-DLP Studio.

This module handles loading and saving application settings.
"""

import json
from pathlib import Path

from ..models.app_config import AppConfig
from ..utils.constants import CONFIG_PATH, DEFAULT_OUTPUT_DIR
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
        If config file is corrupted, logs error and returns default.

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

        # Try to load from file
        if self.config_path.exists():
            try:
                with open(self.config_path, encoding="utf-8") as f:
                    data = json.load(f)
                    self.config = AppConfig.from_dict(data)

                    # Validate loaded config
                    if not self.config.validate():
                        logger.warning("Loaded config failed validation, using defaults")
                        self.config = self._create_default_config()
                    else:
                        logger.info("Configuration loaded successfully")

            except json.JSONDecodeError as e:
                logger.error(f"Config file corrupted: {e}. Using defaults.")
                self.config = self._create_default_config()
            except Exception as e:
                logger.error(f"Error loading config: {e}. Using defaults.")
                self.config = self._create_default_config()
        else:
            logger.info("Config file not found, creating default")
            self.config = self._create_default_config()
            self.save_config(self.config)

        return self.config

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

            # Save to file
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config.to_dict(), f, indent=4)

            self.config = config
            logger.info("Configuration saved successfully")
            return True

        except Exception as e:
            logger.error(f"Error saving config: {e}")
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
