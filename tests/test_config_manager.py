"""
Tests for ConfigManager.

Run with: pytest tests/test_config_manager.py -v
"""

import tempfile
from pathlib import Path

import pytest

from src.backend.config_manager import ConfigManager
from src.models.app_config import AppConfig


class TestConfigManager:
    """Test suite for ConfigManager class."""

    @pytest.fixture
    def temp_config_file(self):
        """Create temporary config file for testing (with valid empty JSON)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = Path(f.name)
        # Remove the empty file so ConfigManager creates defaults
        temp_path.unlink()
        yield temp_path
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    def test_create_default_config(self, temp_config_file):
        """Test creating default configuration."""
        manager = ConfigManager(temp_config_file)
        config = manager.load_config()

        assert config is not None
        assert isinstance(config, AppConfig)
        assert config.default_quality == "Best Quality"
        assert config.window_width == 900
        assert config.window_height == 700

    def test_save_and_load_config(self, temp_config_file):
        """Test saving and loading configuration."""
        manager = ConfigManager(temp_config_file)
        manager.load_config()

        # Update config with valid quality name and save
        manager.config.default_quality = "720p (HD)"
        manager.config.window_width = 1024
        manager.config.window_height = 768
        manager.save_config(manager.config)

        # Load and verify
        manager2 = ConfigManager(temp_config_file)
        loaded_config = manager2.load_config()

        assert loaded_config.default_quality == "720p (HD)"
        assert loaded_config.window_width == 1024
        assert loaded_config.window_height == 768

    def test_update_config(self, temp_config_file):
        """Test updating specific config values."""
        manager = ConfigManager(temp_config_file)
        manager.load_config()

        # Update with valid quality name from QUALITY_NAMES
        success = manager.update_config(default_quality="1080p (Full HD)", window_width=1920)

        assert success is True

        # Verify changes
        config = manager.get_config()
        assert config.default_quality == "1080p (Full HD)"
        assert config.window_width == 1920
