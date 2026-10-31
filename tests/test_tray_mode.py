"""
Tests for tray mode ("Keep running in the tray when I close the window").

With the setting on and a system tray available, closing the main window
hides it and downloads keep running. Quit in the tray menu and Ctrl+Q still
run the normal shutdown. Without the setting, or without a tray, closing
quits as before.

Runs headless with QT_QPA_PLATFORM=offscreen, where Qt reports no system
tray. Tests that need a tray patch QSystemTrayIcon.isSystemTrayAvailable.
QApplication.quit, QueueManager.shutdown and the tray message are replaced
with mocks so the tests can check that they ran.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QMessageBox, QSystemTrayIcon

import src.backend.history_manager as hm_module
import src.ui.main_window as mw_module
from src.backend.config_manager import ConfigManager
from src.models.app_config import AppConfig
from src.ui.settings_tab import SettingsTab
from src.utils.constants import APP_NAME
from src.utils.translations import get_translation_manager


@pytest.fixture(autouse=True)
def force_english_ui():
    """Keep the language fixed so a save never reports a language change."""
    tm = get_translation_manager()
    tm.set_language("en")
    yield
    tm.set_language("en")


@pytest.fixture
def tray_available(monkeypatch):
    """Pretend the desktop has a system tray."""
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", staticmethod(lambda: True))


@pytest.fixture
def no_tray(monkeypatch):
    """Pretend the desktop has no system tray (also the offscreen default)."""
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", staticmethod(lambda: False))


@pytest.fixture
def config_manager(tmp_path):
    out_dir = tmp_path / "downloads"
    out_dir.mkdir()
    manager = ConfigManager(config_path=tmp_path / "config.json")
    manager.load_config()
    manager.update_config(output_directory=str(out_dir))
    return manager


@pytest.fixture
def quit_mock(monkeypatch):
    """Replace QApplication.quit so the tests can see an explicit quit."""
    mock = MagicMock()
    monkeypatch.setattr(mw_module.QApplication, "quit", mock)
    return mock


@pytest.fixture
def make_window(qtbot, tmp_path, monkeypatch):
    """Build a MainWindow that keeps its queue and history in tmp_path."""
    monkeypatch.setattr(mw_module, "APP_DATA_DIR", tmp_path)
    monkeypatch.setattr(hm_module, "APP_DATA_DIR", tmp_path)
    windows = []

    def _make(config_manager):
        window = mw_module.MainWindow(config_manager)
        qtbot.addWidget(window)
        window.queue_manager.shutdown = MagicMock(wraps=window.queue_manager.shutdown)
        window.notification_manager.show_tray_message = MagicMock(return_value=True)
        windows.append(window)
        return window

    yield _make
    for window in windows:
        window.notification_manager.hide_tray_icon()


def _saved_value(config_manager: ConfigManager) -> bool:
    with open(config_manager.config_path, encoding="utf-8") as f:
        return json.load(f)["close_to_tray"]


class TestConfigField:
    def test_default_is_off(self):
        assert AppConfig(output_directory="/tmp").close_to_tray is False

    def test_old_config_without_field_loads_off(self, tmp_path):
        """A config written by 0.3.1 has no close_to_tray key."""
        path = tmp_path / "config.json"
        data = AppConfig(output_directory=str(tmp_path)).to_dict()
        del data["close_to_tray"]
        path.write_text(json.dumps(data), encoding="utf-8")
        assert ConfigManager(config_path=path).load_config().close_to_tray is False

    def test_value_survives_save_and_load(self, config_manager):
        config_manager.update_config(close_to_tray=True)
        reloaded = ConfigManager(config_path=config_manager.config_path).load_config()
        assert reloaded.close_to_tray is True


class TestSettingsCheckbox:
    @pytest.fixture
    def settings_tab(self, qtbot, config_manager, tray_available):
        tab = SettingsTab(config_manager)
        qtbot.addWidget(tab)
        return tab

    def test_checkbox_starts_off_and_enabled(self, settings_tab):
        assert settings_tab.close_to_tray_checkbox.isChecked() is False
        assert settings_tab.close_to_tray_checkbox.isEnabled() is True

    def test_checkbox_loads_saved_value(self, qtbot, config_manager, tray_available):
        config_manager.update_config(close_to_tray=True)
        tab = SettingsTab(config_manager)
        qtbot.addWidget(tab)
        assert tab.close_to_tray_checkbox.isChecked() is True

    def test_no_tray_disables_checkbox_with_tooltip(self, qtbot, config_manager, no_tray):
        tab = SettingsTab(config_manager)
        qtbot.addWidget(tab)
        assert tab.close_to_tray_checkbox.isEnabled() is False
        assert "no system tray" in tab.close_to_tray_checkbox.toolTip()

    @pytest.mark.parametrize("enabled", [False, True])
    def test_save_persists_and_emits(self, qtbot, settings_tab, config_manager, enabled):
        settings_tab.close_to_tray_checkbox.setChecked(enabled)
        with (
            patch.object(QMessageBox, "information"),
            qtbot.waitSignal(settings_tab.close_to_tray_changed, timeout=1000) as blocker,
        ):
            settings_tab._save_settings()
        assert blocker.args == [enabled]
        assert config_manager.get_config().close_to_tray is enabled
        assert _saved_value(config_manager) is enabled

    def test_reset_restores_off_and_emits(self, qtbot, settings_tab, config_manager):
        config_manager.update_config(close_to_tray=True)
        settings_tab._load_settings()
        assert settings_tab.close_to_tray_checkbox.isChecked() is True
        with (
            patch.object(QMessageBox, "question", return_value=QMessageBox.Yes),
            patch.object(QMessageBox, "information"),
            qtbot.waitSignal(settings_tab.close_to_tray_changed, timeout=1000) as blocker,
        ):
            settings_tab._reset_defaults()
        assert blocker.args == [False]
        assert settings_tab.close_to_tray_checkbox.isChecked() is False
        assert config_manager.get_config().close_to_tray is False


class TestCloseBehaviour:
    def test_default_off_quits_on_close(self, make_window, config_manager, tray_available, quit_mock):
        window = make_window(config_manager)
        assert window.notification_manager.has_visible_tray_icon() is True

        assert window.close() is True

        window.queue_manager.shutdown.assert_called_once()
        quit_mock.assert_called_once()
        window.notification_manager.show_tray_message.assert_not_called()

    def test_on_with_tray_hides_instead_of_quitting(self, make_window, config_manager, tray_available, quit_mock):
        config_manager.update_config(close_to_tray=True)
        window = make_window(config_manager)
        assert window.isVisible()

        assert window.close() is False

        assert window.isVisible() is False
        window.queue_manager.shutdown.assert_not_called()
        quit_mock.assert_not_called()
        # The tray icon stays, so the user can bring the window back.
        assert window.notification_manager.has_visible_tray_icon() is True

    def test_tray_message_shown_once_per_session(self, make_window, config_manager, tray_available, quit_mock):
        config_manager.update_config(close_to_tray=True)
        window = make_window(config_manager)

        window.close()
        window.notification_manager.show_window_requested.emit()
        assert window.isVisible() is True
        window.close()

        window.notification_manager.show_tray_message.assert_called_once()
        message = window.notification_manager.show_tray_message.call_args.args[0]
        assert "tray" in message

    def test_tray_quit_shuts_down_and_quits(self, make_window, config_manager, tray_available, quit_mock):
        config_manager.update_config(close_to_tray=True)
        window = make_window(config_manager)
        window.close()
        window.queue_manager.shutdown.assert_not_called()

        window.notification_manager.quit_requested.emit()

        window.queue_manager.shutdown.assert_called_once()
        quit_mock.assert_called_once()
        assert window.notification_manager.has_visible_tray_icon() is False

    def test_quits_even_if_shutdown_fails(self, make_window, config_manager, tray_available, quit_mock):
        # Quit-on-last-window-closed is off, so a cleanup error must not leave
        # a hidden process running.
        window = make_window(config_manager)
        window.queue_manager.shutdown.side_effect = RuntimeError("boom")

        assert window.close() is True

        quit_mock.assert_called_once()

    def test_ctrl_q_quits_in_tray_mode(self, make_window, config_manager, tray_available, quit_mock):
        config_manager.update_config(close_to_tray=True)
        window = make_window(config_manager)
        assert window.quit_shortcut.key().toString() == "Ctrl+Q"

        window.quit_shortcut.activated.emit()

        window.queue_manager.shutdown.assert_called_once()
        quit_mock.assert_called_once()

    def test_no_tray_falls_back_to_quitting(self, make_window, config_manager, no_tray, quit_mock):
        config_manager.update_config(close_to_tray=True)
        window = make_window(config_manager)
        assert window.notification_manager.has_visible_tray_icon() is False

        assert window.close() is True

        window.queue_manager.shutdown.assert_called_once()
        quit_mock.assert_called_once()

    def test_cancelled_quit_keeps_tray_mode(self, make_window, config_manager, tray_available, quit_mock):
        """Answering No to the download-in-progress question cancels the quit."""
        config_manager.update_config(close_to_tray=True)
        window = make_window(config_manager)
        worker = MagicMock()
        worker.is_running.return_value = True
        window.download_tab.current_worker = worker

        with patch.object(QMessageBox, "question", return_value=QMessageBox.No):
            window.quit_application()

        window.queue_manager.shutdown.assert_not_called()
        quit_mock.assert_not_called()
        worker.cancel.assert_not_called()
        # The next close hides to the tray again.
        window.download_tab.current_worker = None
        assert window.close() is False
        window.queue_manager.shutdown.assert_not_called()

    def test_setting_saved_at_runtime_applies(self, make_window, config_manager, tray_available, quit_mock):
        window = make_window(config_manager)
        window.settings_tab.close_to_tray_checkbox.setChecked(True)
        with patch.object(QMessageBox, "information"):
            window.settings_tab._save_settings()

        assert window.close() is False
        window.queue_manager.shutdown.assert_not_called()


class TestTrayTooltip:
    @pytest.fixture
    def window(self, make_window, config_manager, tray_available):
        return make_window(config_manager)

    @staticmethod
    def _set_counts(window, active, pending):
        stats = {"total": active + pending, "pending": pending, "active": active, "completed": 0, "failed": 0}
        window.queue_manager.get_queue_statistics = MagicMock(return_value=stats)

    def test_idle_shows_app_name(self, window):
        assert window.tray_tooltip_text() == APP_NAME
        assert window.notification_manager.tray_icon.toolTip() == APP_NAME

    def test_busy_shows_counts(self, window):
        self._set_counts(window, active=2, pending=3)
        assert window.tray_tooltip_text() == f"{APP_NAME} - 2 downloading, 3 waiting"

    def test_waiting_only_is_not_idle(self, window):
        self._set_counts(window, active=0, pending=1)
        assert window.tray_tooltip_text() == f"{APP_NAME} - 0 downloading, 1 waiting"

    def test_hebrew_text(self, window):
        self._set_counts(window, active=2, pending=3)
        get_translation_manager().set_language("he")
        text = window.tray_tooltip_text()
        assert text.startswith(f"{APP_NAME} - 2 ")
        assert "3" in text
        assert chr(0x2013) not in text and chr(0x2014) not in text

    def test_queue_signal_updates_tray_icon(self, window):
        self._set_counts(window, active=1, pending=4)
        window.queue_manager.queue_updated.emit()
        assert window.notification_manager.tray_icon.toolTip() == f"{APP_NAME} - 1 downloading, 4 waiting"

        self._set_counts(window, active=0, pending=0)
        window.queue_manager.queue_updated.emit()
        assert window.notification_manager.tray_icon.toolTip() == APP_NAME
