"""Finished downloads are recorded in the download history.

Before this, nothing called HistoryManager.add_download(), so the History
tab never got new entries. Queue downloads are recorded by QueueManager;
single downloads by the Download tab through QueueManager.record_history().
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.backend.queue_manager import QueueManager, _platform_of
from src.models.download_task import DownloadTask, TaskStatus


def make_task(url="https://www.youtube.com/watch?v=abc"):
    task = DownloadTask(url=url, output_directory="/tmp", quality="1080p")
    task.title = "A video"
    task.filename = "A video_1080p.mp4"
    return task


@pytest.fixture
def qm(qapp):
    history = MagicMock()
    manager = QueueManager(max_concurrent=3, history_manager=history)
    manager._auto_start = False  # never start real downloads here
    recorded = []
    manager.history_recorded.connect(lambda: recorded.append(1))
    manager.recorded = recorded
    return manager


def fake_worker(task, last_error=None):
    return SimpleNamespace(task=task, wrapper=SimpleNamespace(last_error=last_error))


def test_completed_queue_download_is_recorded(qm):
    task = make_task()
    qm._on_worker_completed(fake_worker(task), task.filename)
    qm.history_manager.add_download.assert_called_once_with(task, "completed", error_message="", platform="youtube.com")
    assert qm.recorded == [1], "the History tab must be told to refresh"


def test_final_failure_is_recorded_with_the_real_reason(qm):
    task = make_task()
    task.status = TaskStatus.ERROR
    qm._on_worker_failed(fake_worker(task, last_error="ERROR: Private video"), "Download failed")
    args, kwargs = qm.history_manager.add_download.call_args
    assert args == (task, "failed")
    assert kwargs["error_message"] == "ERROR: Private video"


def test_failure_that_will_be_retried_is_not_recorded_yet(qm, monkeypatch):
    task = make_task()
    task.status = TaskStatus.ERROR
    monkeypatch.setattr(qm, "_should_auto_retry", lambda *a, **k: True)
    monkeypatch.setattr(qm, "_schedule_auto_retry", lambda t: None)
    qm._on_worker_failed(fake_worker(task, last_error="Connection reset"), "Download failed")
    qm.history_manager.add_download.assert_not_called()


def test_cancel_is_recorded_as_cancelled_without_an_error(qm):
    task = make_task()
    task.status = TaskStatus.CANCELLED
    qm._on_worker_failed(fake_worker(task), "Download cancelled")
    args, kwargs = qm.history_manager.add_download.call_args
    assert args == (task, "cancelled")
    assert kwargs["error_message"] == ""


def test_shutdown_cancels_are_not_recorded(qm):
    task = make_task()
    task.status = TaskStatus.CANCELLED
    qm._shutting_down = True
    qm._on_worker_failed(fake_worker(task), "Download cancelled")
    qm.history_manager.add_download.assert_not_called()


def test_history_errors_never_break_the_download_flow(qm):
    qm.history_manager.add_download.side_effect = OSError("disk full")
    task = make_task()
    qm.record_history(task, "completed")  # must not raise
    assert qm.recorded == [], "no refresh signal when nothing was written"


def test_without_a_history_manager_nothing_happens(qapp):
    manager = QueueManager(max_concurrent=3)
    manager.record_history(make_task(), "completed")  # must not raise


@pytest.mark.parametrize(
    ("url", "platform"),
    [
        ("https://www.youtube.com/watch?v=x", "youtube.com"),
        ("https://m.youtube.com/watch?v=x", "youtube.com"),
        ("https://youtu.be/x", "youtu.be"),
        ("https://vimeo.com/1", "vimeo.com"),
        ("not a url", ""),
        ("", ""),
    ],
)
def test_platform_from_url(url, platform):
    assert _platform_of(url) == platform


def test_history_entry_uses_the_real_title(tmp_path, monkeypatch):
    """End to end through the real HistoryManager (stored under tmp_path)."""
    from src.backend import history_manager as hm_module

    monkeypatch.setattr(hm_module, "APP_DATA_DIR", tmp_path)
    manager = hm_module.HistoryManager()
    task = make_task()
    manager.add_download(task, "completed", platform="youtube.com")
    entries = manager.get_history()
    assert entries and entries[0].title == "A video"
    assert entries[0].filename == "A video_1080p.mp4"
