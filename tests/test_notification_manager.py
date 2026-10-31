"""
Tests for NotificationManager.

Every backend is mocked: no test shows a real tray message or runs a real
notify-send. Runs headless with QT_QPA_PLATFORM=offscreen.
"""

import logging
import subprocess
import threading
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QSystemTrayIcon

import src.utils.notification_manager as nm_module
from src.utils.notification_manager import NotificationManager
from src.utils.translations import TRANSLATIONS, get_translation_manager

NOTIFY_SEND = "/usr/bin/notify-send"
SENT = "Notification sent"


@pytest.fixture
def manager(qapp):
    """A manager with no tray and no notify-send by default."""
    mgr = NotificationManager()
    with (
        patch.object(nm_module, "_is_linux_like", return_value=True),
        patch.object(nm_module.shutil, "which", return_value=None),
        patch.object(nm_module.subprocess, "run") as run,
    ):
        mgr.run_mock = run
        yield mgr


def _fake_tray(visible: bool = True) -> MagicMock:
    tray = MagicMock()
    tray.isVisible.return_value = visible
    return tray


def _completed(returncode: int = 0, stderr: bytes = b"") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=None, stderr=stderr)


def _sent_records(caplog) -> list[logging.LogRecord]:
    return [r for r in caplog.records if SENT in r.getMessage()]


def _warnings(caplog) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.levelno == logging.WARNING]


class TestSystemTraySetup:
    def test_no_tray_available_returns_false(self, manager):
        with patch.object(QSystemTrayIcon, "isSystemTrayAvailable", return_value=False):
            assert manager.setup_system_tray() is False
        assert manager.tray_icon is None
        assert manager.use_system_tray is False

    def test_tray_created_and_kept_referenced(self, manager):
        with patch.object(QSystemTrayIcon, "isSystemTrayAvailable", return_value=True):
            assert manager.setup_system_tray() is True
            tray = manager.tray_icon
            assert isinstance(tray, QSystemTrayIcon)
            assert tray.parent() is manager
            # The context menu must stay referenced (setContextMenu does not own it).
            assert manager._tray_menu is not None
            assert tray.contextMenu() is manager._tray_menu
            assert not tray.icon().isNull()

            # A second call does not create a second icon.
            assert manager.setup_system_tray() is True
            assert manager.tray_icon is tray
        manager.hide_tray_icon()


class TestTrayBackend:
    def test_tray_used_when_visible_and_supported(self, manager, caplog):
        manager.tray_icon = _fake_tray()
        manager.use_system_tray = True
        caplog.set_level(logging.DEBUG, logger="YT-DLP Studio")

        with patch.object(QSystemTrayIcon, "supportsMessages", return_value=True):
            assert manager.notify_download_complete("My Video", "10 MB") is True

        manager.tray_icon.showMessage.assert_called_once()
        title, message, icon, timeout = manager.tray_icon.showMessage.call_args.args
        assert title == "Download Complete"
        assert "My Video" in message and "10 MB" in message
        assert icon == QSystemTrayIcon.MessageIcon.Information
        assert timeout > 0
        manager.run_mock.assert_not_called()
        assert len(_sent_records(caplog)) == 1
        assert _warnings(caplog) == []

    def test_invisible_tray_falls_through(self, manager):
        manager.tray_icon = _fake_tray(visible=False)
        manager.use_system_tray = True
        with patch.object(QSystemTrayIcon, "supportsMessages", return_value=True):
            assert manager.notify_custom("t", "m") is False
        manager.tray_icon.showMessage.assert_not_called()

    def test_messages_unsupported_falls_back_to_notify_send(self, manager):
        manager.tray_icon = _fake_tray()
        manager.use_system_tray = True
        manager.run_mock.return_value = _completed(0)
        with (
            patch.object(QSystemTrayIcon, "supportsMessages", return_value=False),
            patch.object(nm_module.shutil, "which", return_value=NOTIFY_SEND),
        ):
            assert manager.notify_custom("t", "m") is True
        manager.tray_icon.showMessage.assert_not_called()
        manager.run_mock.assert_called_once()

    def test_tray_skipped_off_gui_thread(self, manager):
        manager.tray_icon = _fake_tray()
        manager.use_system_tray = True
        result = {}

        def worker():
            result["value"] = manager._send_via_tray("t", "m", QSystemTrayIcon.MessageIcon.Information, 1000)

        with patch.object(QSystemTrayIcon, "supportsMessages", return_value=True):
            thread = threading.Thread(target=worker)
            thread.start()
            thread.join()

        assert result["value"] == (False, "not on the GUI thread")
        manager.tray_icon.showMessage.assert_not_called()


class TestNotifySendBackend:
    def test_called_with_argument_list_and_no_shell(self, manager, caplog):
        manager.run_mock.return_value = _completed(0)
        title = '-x"; rm -rf ~ $(id) `whoami` | tee /tmp/p'
        caplog.set_level(logging.INFO, logger="YT-DLP Studio")

        with patch.object(nm_module.shutil, "which", return_value=NOTIFY_SEND):
            assert manager.notify_download_error(title, "boom") is True

        manager.run_mock.assert_called_once()
        args = manager.run_mock.call_args.args[0]
        kwargs = manager.run_mock.call_args.kwargs
        assert isinstance(args, list)
        assert args[0] == NOTIFY_SEND
        assert "--urgency=critical" in args
        # Untrusted text comes after "--" and stays one argument each.
        sep = args.index("--")
        assert args[sep + 1] == "Download Error"
        assert args[sep + 2].startswith(title + "\n")
        assert len(args) == sep + 3
        assert kwargs.get("shell", False) is False
        assert kwargs["check"] is False
        assert kwargs["timeout"] == nm_module.NOTIFY_SEND_TIMEOUT_S
        assert len(_sent_records(caplog)) == 1

    def test_not_tried_when_absent(self, manager, caplog):
        caplog.set_level(logging.INFO, logger="YT-DLP Studio")
        assert manager.notify_download_complete("Video") is False
        manager.run_mock.assert_not_called()
        warnings = _warnings(caplog)
        assert len(warnings) == 1
        text = warnings[0].getMessage()
        assert "tray: no tray icon" in text
        assert "notify-send: not available" in text
        assert "plyer" not in text
        assert _sent_records(caplog) == []

    def test_not_tried_off_linux(self, manager):
        with (
            patch.object(nm_module, "_is_linux_like", return_value=False),
            patch.object(nm_module.shutil, "which", return_value=NOTIFY_SEND),
        ):
            assert manager.notify_custom("t", "m") is False
        manager.run_mock.assert_not_called()

    def test_nonzero_exit_is_failure(self, manager, caplog):
        manager.run_mock.return_value = _completed(1, b"Cannot connect to D-Bus")
        caplog.set_level(logging.INFO, logger="YT-DLP Studio")
        with patch.object(nm_module.shutil, "which", return_value=NOTIFY_SEND):
            assert manager.notify_download_complete("Video") is False
        warnings = _warnings(caplog)
        assert len(warnings) == 1
        assert "notify-send: exit code 1 (Cannot connect to D-Bus)" in warnings[0].getMessage()
        assert _sent_records(caplog) == []

    @pytest.mark.parametrize(
        "exc, reason",
        [
            (subprocess.TimeoutExpired(cmd="notify-send", timeout=3), "timed out"),
            (FileNotFoundError("gone"), "error: gone"),
            (PermissionError("denied"), "error: denied"),
        ],
    )
    def test_subprocess_exceptions_are_failures(self, manager, caplog, exc, reason):
        manager.run_mock.side_effect = exc
        caplog.set_level(logging.INFO, logger="YT-DLP Studio")
        with patch.object(nm_module.shutil, "which", return_value=NOTIFY_SEND):
            assert manager.notify_download_complete("Video") is False
        warnings = _warnings(caplog)
        assert len(warnings) == 1
        assert reason in warnings[0].getMessage()
        assert _sent_records(caplog) == []


class TestNoPlyer:
    """plyer was removed: the tray and notify-send are the only backends."""

    def test_module_does_not_reference_plyer(self):
        assert not hasattr(nm_module, "_plyer_notification")
        assert not hasattr(NotificationManager, "_send_via_plyer")

    def test_failure_names_only_tray_and_notify_send(self, manager, caplog):
        caplog.set_level(logging.INFO, logger="YT-DLP Studio")
        assert manager.notify_custom("t", "m") is False
        warnings = _warnings(caplog)
        assert len(warnings) == 1
        backends = warnings[0].getMessage().split("Backends tried: ", 1)[1]
        assert [part.split(":", 1)[0] for part in backends.split("; ")] == ["tray", "notify-send"]


class TestTrayMenuTranslations:
    """The tray menu texts come from the translation tables."""

    @staticmethod
    def _menu_texts(manager) -> list[str]:
        return [a.text() for a in manager._tray_menu.actions() if not a.isSeparator()]

    @pytest.mark.parametrize("language", ["en", "he"])
    def test_menu_uses_translations(self, manager, language):
        tm = get_translation_manager()
        previous = tm.get_language()
        tm.set_language(language)
        try:
            with patch.object(QSystemTrayIcon, "isSystemTrayAvailable", return_value=True):
                assert manager.setup_system_tray() is True
            expected = [TRANSLATIONS[language]["tray_show_window"], TRANSLATIONS[language]["tray_quit"]]
            assert self._menu_texts(manager) == expected
        finally:
            manager.hide_tray_icon()
            tm.set_language(previous)

    def test_hebrew_tray_texts(self):
        assert TRANSLATIONS["he"]["tray_show_window"] == "הצג חלון"
        assert TRANSLATIONS["he"]["tray_quit"] == "יציאה"

    def test_menu_actions_still_emit_signals(self, manager):
        with patch.object(QSystemTrayIcon, "isSystemTrayAvailable", return_value=True):
            manager.setup_system_tray()
        show, quit_ = (a for a in manager._tray_menu.actions() if not a.isSeparator())
        shown, quit_seen = [], []
        manager.show_window_requested.connect(lambda: shown.append(True))
        manager.quit_requested.connect(lambda: quit_seen.append(True))
        show.trigger()
        quit_.trigger()
        manager.hide_tray_icon()
        assert shown == [True]
        assert quit_seen == [True]


class TestNoFalseSuccessLog:
    @pytest.mark.parametrize(
        "call",
        [
            lambda m: m.notify_download_complete("Video", "1 MB"),
            lambda m: m.notify_download_error("Video", "err"),
            lambda m: m.notify_batch_complete(3, 2, 1),
            lambda m: m.notify_update_available("9.9.9"),
            lambda m: m.notify_custom("t", "m", "warning"),
        ],
    )
    def test_every_notify_method_returns_false_without_success_log(self, manager, caplog, call):
        caplog.set_level(logging.DEBUG, logger="YT-DLP Studio")
        assert call(manager) is False
        assert _sent_records(caplog) == []
        assert len(_warnings(caplog)) == 1

    def test_disabled_sends_nothing(self, manager, caplog):
        manager.set_enabled(False)
        caplog.set_level(logging.DEBUG, logger="YT-DLP Studio")
        with patch.object(nm_module.shutil, "which", return_value=NOTIFY_SEND):
            assert manager.notify_download_complete("Video") is False
        manager.run_mock.assert_not_called()
        assert _sent_records(caplog) == []
        assert _warnings(caplog) == []


class TestSubprocessEnv:
    def test_frozen_restores_original_library_path(self, monkeypatch):
        monkeypatch.setattr(nm_module.sys, "frozen", True, raising=False)
        monkeypatch.setenv("LD_LIBRARY_PATH", "/bundle")
        monkeypatch.setenv("LD_LIBRARY_PATH_ORIG", "/usr/lib")
        assert nm_module._subprocess_env()["LD_LIBRARY_PATH"] == "/usr/lib"

    def test_frozen_without_original_drops_library_path(self, monkeypatch):
        monkeypatch.setattr(nm_module.sys, "frozen", True, raising=False)
        monkeypatch.setenv("LD_LIBRARY_PATH", "/bundle")
        monkeypatch.delenv("LD_LIBRARY_PATH_ORIG", raising=False)
        assert "LD_LIBRARY_PATH" not in nm_module._subprocess_env()

    def test_source_run_keeps_environment(self, monkeypatch):
        monkeypatch.delattr(nm_module.sys, "frozen", raising=False)
        monkeypatch.setenv("LD_LIBRARY_PATH", "/custom")
        assert nm_module._subprocess_env()["LD_LIBRARY_PATH"] == "/custom"
