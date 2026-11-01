"""
Tests for the "Enable Desktop Notifications" setting.

The checkbox on the Settings tab is saved in the config, sent to the
NotificationManager on save and reset, and applied again at startup.
Runs headless with QT_QPA_PLATFORM=offscreen. Message boxes are patched.
"""

import json
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QMessageBox

import src.backend.history_manager as hm_module
import src.ui.main_window as mw_module
from src.backend.config_manager import ConfigManager
from src.models.app_config import AppConfig
from src.ui.settings_tab import SettingsTab
from src.utils.translations import get_translation_manager


@pytest.fixture(autouse=True)
def force_english_ui():
    """Keep the language fixed so a save never reports a language change."""
    get_translation_manager().set_language("en")


@pytest.fixture
def config_manager(tmp_path):
    out_dir = tmp_path / "downloads"
    out_dir.mkdir()
    manager = ConfigManager(config_path=tmp_path / "config.json")
    manager.load_config()
    manager.update_config(output_directory=str(out_dir))
    return manager


@pytest.fixture
def settings_tab(qtbot, config_manager):
    tab = SettingsTab(config_manager)
    qtbot.addWidget(tab)
    return tab


def _saved_value(config_manager: ConfigManager) -> bool:
    with open(config_manager.config_path, encoding="utf-8") as f:
        return json.load(f)["notifications_enabled"]


class TestConfigField:
    def test_default_is_enabled(self):
        assert AppConfig(output_directory="/tmp").notifications_enabled is True

    def test_old_config_without_field_loads_enabled(self, tmp_path):
        """A config written by 0.3.0 has no notifications_enabled key."""
        path = tmp_path / "config.json"
        data = AppConfig(output_directory=str(tmp_path)).to_dict()
        del data["notifications_enabled"]
        path.write_text(json.dumps(data), encoding="utf-8")
        assert ConfigManager(config_path=path).load_config().notifications_enabled is True


class TestSettingsCheckbox:
    def test_checkbox_starts_enabled(self, settings_tab):
        assert settings_tab.notifications_checkbox.isChecked() is True

    def test_checkbox_loads_saved_value(self, qtbot, config_manager):
        config_manager.update_config(notifications_enabled=False)
        tab = SettingsTab(config_manager)
        qtbot.addWidget(tab)
        assert tab.notifications_checkbox.isChecked() is False

    @pytest.mark.parametrize("enabled", [False, True])
    def test_save_persists_and_emits(self, qtbot, settings_tab, config_manager, enabled):
        settings_tab.notifications_checkbox.setChecked(not enabled)
        settings_tab.notifications_checkbox.setChecked(enabled)
        with (
            patch.object(QMessageBox, "information"),
            qtbot.waitSignal(settings_tab.notifications_enabled_changed, timeout=1000) as blocker,
        ):
            settings_tab._save_settings()
        assert blocker.args == [enabled]
        assert config_manager.get_config().notifications_enabled is enabled
        assert _saved_value(config_manager) is enabled

    def test_toggle_without_save_does_not_persist(self, settings_tab, config_manager):
        settings_tab.notifications_checkbox.setChecked(False)
        assert config_manager.get_config().notifications_enabled is True
        assert _saved_value(config_manager) is True

    def test_reset_restores_enabled_and_emits(self, qtbot, settings_tab, config_manager):
        config_manager.update_config(notifications_enabled=False)
        settings_tab._load_settings()
        assert settings_tab.notifications_checkbox.isChecked() is False
        with (
            patch.object(QMessageBox, "question", return_value=QMessageBox.Yes),
            patch.object(QMessageBox, "information"),
            qtbot.waitSignal(settings_tab.notifications_enabled_changed, timeout=1000) as blocker,
        ):
            settings_tab._reset_defaults()
        assert blocker.args == [True]
        assert settings_tab.notifications_checkbox.isChecked() is True
        assert config_manager.get_config().notifications_enabled is True


class TestMainWindowWiring:
    @pytest.fixture
    def make_window(self, qtbot, tmp_path, monkeypatch):
        """Build a MainWindow that keeps its queue and history in tmp_path."""
        monkeypatch.setattr(mw_module, "APP_DATA_DIR", tmp_path)
        monkeypatch.setattr(hm_module, "APP_DATA_DIR", tmp_path)

        def _make(config_manager):
            window = mw_module.MainWindow(config_manager)
            qtbot.addWidget(window)
            return window

        yield _make

    @pytest.mark.parametrize("enabled", [False, True])
    def test_startup_applies_saved_value(self, make_window, config_manager, enabled):
        config_manager.update_config(notifications_enabled=enabled)
        window = make_window(config_manager)
        try:
            assert window.notification_manager.is_enabled() is enabled
            assert window.settings_tab.notifications_checkbox.isChecked() is enabled
        finally:
            window.notification_manager.hide_tray_icon()

    def test_save_in_settings_updates_manager(self, make_window, config_manager):
        window = make_window(config_manager)
        try:
            assert window.notification_manager.is_enabled() is True
            window.settings_tab.notifications_checkbox.setChecked(False)
            with patch.object(QMessageBox, "information"):
                window.settings_tab._save_settings()
            assert window.notification_manager.is_enabled() is False
            assert window.notification_manager.notify_custom("t", "m") is False
        finally:
            window.notification_manager.hide_tray_icon()
