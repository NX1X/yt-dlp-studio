"""
Tests for translated status labels and notification texts.

Statuses are translated only at display time. The queue file and the history
file keep the English values, so files stay compatible across languages.
Runs headless with QT_QPA_PLATFORM=offscreen.
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
from PySide6.QtWidgets import QSystemTrayIcon

import src.utils.notification_manager as nm_module
from src.backend.queue_manager import QueueManager
from src.models.download_history import HistoryEntry
from src.models.download_task import DownloadTask, TaskStatus
from src.utils.notification_manager import NotificationManager
from src.utils.status_labels import (
    HISTORY_STATUS_KEYS,
    TASK_STATUS_KEYS,
    history_status_text,
    task_status_text,
)
from src.utils.translations import TRANSLATIONS, get_translation_manager

# A title with format-like characters. It must pass through
# every notification unchanged.
VIDEO_TITLE = "Mein Video {title} - part 1/2"


@pytest.fixture
def language():
    """Switch the UI language for one test and restore it afterwards."""
    tm = get_translation_manager()
    previous = tm.get_language()

    def _set(code: str) -> None:
        tm.set_language(code)

    yield _set
    tm.set_language(previous)


@pytest.fixture(autouse=True)
def mock_worker_class():
    """Replace DownloadWorker so no test runs a real download."""
    with patch("src.backend.queue_manager.DownloadWorker") as worker_class:
        worker_class.side_effect = lambda task: MagicMock(task=task)
        yield worker_class


def make_task(n: int = 0) -> DownloadTask:
    return DownloadTask(url=f"https://www.youtube.com/watch?v=test{n}", output_directory="/tmp/dl", quality="1080p")


class TestStatusKeys:
    def test_every_task_status_has_a_key(self):
        assert set(TASK_STATUS_KEYS) == set(TaskStatus)

    @pytest.mark.parametrize("lang", ["en", "he"])
    def test_every_status_key_exists_in_both_languages(self, lang):
        keys = set(TASK_STATUS_KEYS.values()) | set(HISTORY_STATUS_KEYS.values())
        missing = {k for k in keys if not TRANSLATIONS[lang].get(k)}
        assert missing == set()

    @pytest.mark.parametrize("status", list(TaskStatus))
    def test_hebrew_label_differs_from_english(self, language, status):
        language("he")
        hebrew = task_status_text(status)
        language("en")
        assert hebrew != task_status_text(status)

    def test_history_values_match_what_queue_manager_records(self):
        assert set(HISTORY_STATUS_KEYS) == {"completed", "failed", "cancelled"}

    def test_unknown_history_status_is_shown_as_stored(self):
        assert history_status_text("paused") == "paused"


class TestQueueTabStatus:
    @pytest.fixture
    def queue_manager(self, qapp):
        return QueueManager(max_concurrent=3)

    def _make_tab(self, qtbot, queue_manager):
        from src.ui.queue_tab import QueueTab

        tab = QueueTab(queue_manager)
        qtbot.addWidget(tab)
        return tab

    @pytest.mark.parametrize("status", list(TaskStatus))
    def test_hebrew_status_cell(self, qtbot, language, queue_manager, status):
        language("he")
        tab = self._make_tab(qtbot, queue_manager)
        queue_manager.pause_queue()
        task = make_task()
        queue_manager.add_task(task)
        task.status = status
        queue_manager.queue_updated.emit()

        cell = tab.queue_table.item(0, 3).text()
        assert cell == TRANSLATIONS["he"][TASK_STATUS_KEYS[status]]
        assert task.status is status  # the model value is unchanged

    def test_english_status_cell(self, qtbot, language, queue_manager):
        language("en")
        tab = self._make_tab(qtbot, queue_manager)
        queue_manager.pause_queue()
        queue_manager.add_task(make_task())

        assert tab.queue_table.item(0, 3).text() == "Pending"


class TestStoredValuesStayEnglish:
    @pytest.mark.parametrize("status", list(TaskStatus))
    def test_task_dict_keeps_enum_value(self, language, status):
        language("he")
        task = make_task()
        task.status = status
        assert task.to_dict()["status"] == status.value

    # The queue file holds only the statuses that are restored on start.
    @pytest.mark.parametrize("status", [TaskStatus.PENDING, TaskStatus.DOWNLOADING, TaskStatus.ERROR])
    def test_queue_file_keeps_enum_value(self, qapp, tmp_path, language, status):
        language("he")
        path = tmp_path / "download_queue.json"
        manager = QueueManager(max_concurrent=3, persist_path=path)
        manager.pause_queue()
        task = make_task()
        manager.add_task(task)
        task.status = status
        manager.save_queue()

        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["tasks"][0]["status"] == status.value

    def test_history_file_keeps_english_status(self, tmp_path, language):
        language("he")
        with patch("src.backend.history_manager.APP_DATA_DIR", tmp_path):
            from src.backend.history_manager import HistoryManager

            mgr = HistoryManager()
            task = make_task()
            task.filename = "video.mp4"
            for status in ("completed", "failed", "cancelled"):
                mgr.add_download(task, status)

        data = json.loads((tmp_path / "download_history.json").read_text(encoding="utf-8"))
        assert sorted(e["status"] for e in data["entries"]) == ["cancelled", "completed", "failed"]


class TestHistoryTabStatus:
    def test_hebrew_status_cell(self, qtbot, language):
        language("he")
        history_manager = Mock()
        history_manager.get_statistics.return_value = {
            "total_downloads": 1,
            "completed": 0,
            "failed": 1,
            "cancelled": 0,
            "success_rate": 0.0,
            "total_size_bytes": 0,
            "average_speed_bps": 0,
        }
        history_manager.get_history.return_value = [
            HistoryEntry(
                url="https://example.com",
                title=VIDEO_TITLE,
                quality="Best",
                output_directory="/dl",
                filename="v.mp4",
                status="failed",
                timestamp=datetime(2026, 10, 31, 12, 0),
                platform="youtube",
            )
        ]
        from src.ui.history_tab import HistoryTab

        tab = HistoryTab(history_manager)
        qtbot.addWidget(tab)

        assert tab.history_table.item(0, 3).text() == TRANSLATIONS["he"]["status_failed"]
        assert tab.history_table.item(0, 1).text() == VIDEO_TITLE


@pytest.fixture
def notifier(qapp):
    """A manager whose tray accepts every message."""
    mgr = NotificationManager()
    mgr.tray_icon = MagicMock()
    mgr.tray_icon.isVisible.return_value = True
    mgr.use_system_tray = True
    with (
        patch.object(QSystemTrayIcon, "supportsMessages", return_value=True),
        patch.object(nm_module.shutil, "which", return_value=None),
    ):
        yield mgr


def _shown(mgr) -> tuple[str, str]:
    title, message, _icon, _timeout = mgr.tray_icon.showMessage.call_args.args
    return title, message


class TestNotificationTexts:
    @pytest.mark.parametrize("lang", ["en", "he"])
    def test_download_complete(self, notifier, language, lang):
        language(lang)
        assert notifier.notify_download_complete(VIDEO_TITLE, "10 MB") is True
        title, message = _shown(notifier)
        t = TRANSLATIONS[lang]
        assert title == t["notif_download_complete"]
        assert message == f"{VIDEO_TITLE}\n" + t["notif_download_complete_msg_size"].format(size="10 MB")

    @pytest.mark.parametrize("lang", ["en", "he"])
    def test_download_complete_without_size(self, notifier, language, lang):
        language(lang)
        notifier.notify_download_complete(VIDEO_TITLE)
        assert _shown(notifier)[1] == f"{VIDEO_TITLE}\n{TRANSLATIONS[lang]['notif_download_complete_msg']}"

    @pytest.mark.parametrize("lang", ["en", "he"])
    def test_download_error(self, notifier, language, lang):
        language(lang)
        notifier.notify_download_error(VIDEO_TITLE, "HTTP Error 403")
        title, message = _shown(notifier)
        t = TRANSLATIONS[lang]
        assert title == t["notif_download_error"]
        assert message == f"{VIDEO_TITLE}\n" + t["notif_download_error_msg_reason"].format(error="HTTP Error 403")

    def test_download_error_without_reason(self, notifier, language):
        language("he")
        notifier.notify_download_error(VIDEO_TITLE)
        assert _shown(notifier)[1] == f"{VIDEO_TITLE}\n{TRANSLATIONS['he']['notif_download_error_msg']}"

    def test_error_reason_with_braces_is_not_formatted_twice(self, notifier, language):
        language("en")
        notifier.notify_download_error(VIDEO_TITLE, "bad {key}")
        assert _shown(notifier)[1].endswith("Download failed: bad {key}")

    @pytest.mark.parametrize("lang", ["en", "he"])
    def test_batch_complete(self, notifier, language, lang):
        language(lang)
        notifier.notify_batch_complete(3, 2, 1)
        title, message = _shown(notifier)
        t = TRANSLATIONS[lang]
        assert title == t["notif_batch_complete"]
        expected = t["notif_batch_completed_count"].format(successful=2, total=3)
        expected += "\n" + t["notif_batch_failed_count"].format(failed=1)
        assert message == expected

    @pytest.mark.parametrize("lang", ["en", "he"])
    def test_update_available(self, notifier, language, lang):
        language(lang)
        notifier.notify_update_available("9.9.9")
        title, message = _shown(notifier)
        t = TRANSLATIONS[lang]
        assert title == t["notif_update_available"]
        assert message == t["notif_update_available_msg"].format(version="9.9.9")

    def test_placeholders_match_in_both_languages(self):
        import string

        def fields(text: str) -> set[str]:
            return {f for _, f, _, _ in string.Formatter().parse(text) if f}

        for key, en_text in TRANSLATIONS["en"].items():
            if key.startswith("notif_") or key.startswith("status_") or key == "msg_clear_status_confirm":
                assert fields(en_text) == fields(TRANSLATIONS["he"][key]), key


class TestQueueManagerErrorReason:
    def _fail(self, manager, task, error, detail):
        worker = Mock(task=task)
        worker.wrapper.last_error = detail
        manager.workers[id(task)] = worker
        manager._on_worker_failed(worker, error)

    def test_worker_english_text_is_not_passed(self, qapp):
        notifier = Mock()
        manager = QueueManager(max_concurrent=3, notification_manager=notifier)
        manager.pause_queue()
        task = make_task()
        manager.add_task(task)
        task.fail("Download failed")
        with patch.object(manager, "_should_auto_retry", return_value=False):
            self._fail(manager, task, "Download failed", None)
        notifier.notify_download_error.assert_called_once_with(task.url, "")

    def test_ytdlp_reason_is_passed_unchanged(self, qapp):
        notifier = Mock()
        manager = QueueManager(max_concurrent=3, notification_manager=notifier)
        manager.pause_queue()
        task = make_task()
        manager.add_task(task)
        task.fail("Download failed")
        with patch.object(manager, "_should_auto_retry", return_value=False):
            self._fail(manager, task, "Download failed", "HTTP Error 403: Forbidden")
        notifier.notify_download_error.assert_called_once_with(task.url, "HTTP Error 403: Forbidden")

    def test_cancel_reason_is_translated(self, qapp, language):
        language("he")
        notifier = Mock()
        manager = QueueManager(max_concurrent=3, notification_manager=notifier)
        manager.pause_queue()
        task = make_task()
        manager.add_task(task)
        task.cancel()
        self._fail(manager, task, "Download cancelled", None)
        notifier.notify_download_error.assert_called_once_with(task.url, TRANSLATIONS["he"]["status_cancelled"])
