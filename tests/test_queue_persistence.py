"""
Tests for download queue persistence and retry.

Covers the queue file (save/load round trip, atomic write, bad files, the
paused state) and retry (manual retry, one automatic retry for network
errors only). Every test uses ``tmp_path``; none touches the real user data
directory. DownloadWorker is replaced with a mock so no thread or network
request ever starts.
"""

import json
import os
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.backend.queue_manager import QueueManager, is_auto_retryable
from src.models.download_task import DownloadTask, TaskStatus

NETWORK_ERROR = "ERROR: [youtube] abc: Unable to download webpage: <urlopen error timed out>"


@pytest.fixture(autouse=True)
def _app(qapp):
    """The debounced save uses a QTimer, which needs a Qt application."""
    return qapp


@pytest.fixture(autouse=True)
def mock_worker_class():
    """Replace DownloadWorker so starting a task never runs a real download."""
    with patch("src.backend.queue_manager.DownloadWorker") as worker_class:
        worker_class.side_effect = lambda task: MagicMock(task=task)
        yield worker_class


@pytest.fixture
def queue_path(tmp_path):
    """Path of the queue file inside a temp folder."""
    return tmp_path / "download_queue.json"


def make_manager(path, max_concurrent=3, **kwargs):
    """Create a queue manager that saves to path."""
    return QueueManager(max_concurrent=max_concurrent, persist_path=path, **kwargs)


def make_task(n=0, status=TaskStatus.PENDING, **kwargs):
    """Create a task with a unique URL."""
    task = DownloadTask(
        url=f"https://www.youtube.com/watch?v=test{n}",
        output_directory="/tmp/downloads",
        quality="1080p",
        **kwargs,
    )
    task.status = status
    return task


def write_queue_file(path, tasks, paused=False, version=1):
    """Write a queue file the way QueueManager does."""
    data = {"version": version, "paused": paused, "tasks": [t.to_dict() for t in tasks]}
    path.write_text(json.dumps(data), encoding="utf-8")


def read_queue_file(path):
    return json.loads(path.read_text(encoding="utf-8"))


def saved(manager):
    """Write any debounced save now and return the file content."""
    manager.flush_save()
    return read_queue_file(manager.persist_path)


def fail_task(manager, index, error, detail=None):
    """Simulate a worker that failed task `index` with `error`."""
    task = manager.queue.get_task(index)
    task.fail(error)
    worker = Mock(task=task)
    worker.wrapper.last_error = detail
    manager.workers[id(task)] = worker
    manager._on_worker_failed(worker, error)
    return task


# ----------------------------------------------------------------------
# DownloadTask serialization
# ----------------------------------------------------------------------


class TestTaskSerialization:
    def test_round_trip_keeps_settings(self):
        task = make_task(
            audio_only=True,
            download_subtitles=True,
            subtitle_languages="he,en",
            speed_limit=500,
            video_container="mkv",
            audio_format="opus",
            selected_subtitles=["he", "en"],
            download_metadata=True,
            download_comments=True,
            auto_number_duplicates=False,
            retry_count=1,
        )
        task.status = TaskStatus.ERROR
        task.error_message = "boom"
        task.filename = "video.mp4"
        task.title = "A video"

        restored = DownloadTask.from_dict(json.loads(json.dumps(task.to_dict())))

        for name in (
            "url",
            "output_directory",
            "quality",
            "audio_only",
            "download_subtitles",
            "subtitle_languages",
            "speed_limit",
            "video_container",
            "audio_format",
            "selected_subtitles",
            "download_metadata",
            "download_comments",
            "auto_number_duplicates",
            "retry_count",
            "status",
            "error_message",
            "filename",
            "title",
            "created_at",
        ):
            assert getattr(restored, name) == getattr(task, name), name

    def test_progress_is_not_stored(self):
        task = make_task(status=TaskStatus.DOWNLOADING)
        task.update_progress(55.0, download_speed=1000.0, eta_seconds=9, downloaded_bytes=10, file_size=20)
        data = task.to_dict()
        for name in ("progress_percent", "download_speed", "eta_seconds", "downloaded_bytes"):
            assert name not in data

    def test_unknown_keys_are_ignored(self):
        data = make_task().to_dict()
        data["from_a_newer_version"] = 42
        assert DownloadTask.from_dict(data).url == make_task().url

    def test_missing_optional_keys_take_defaults(self):
        task = DownloadTask.from_dict({"url": "https://example.com/v", "output_directory": "/tmp", "quality": "Best"})
        assert task.status == TaskStatus.PENDING
        assert task.retry_count == 0
        assert task.download_thumbnail is True

    @pytest.mark.parametrize(
        "change",
        [
            {"url": None},
            {"url": ""},
            {"quality": 5},
            {"audio_only": "yes"},
            {"speed_limit": "100"},
            {"speed_limit": True},
            {"retry_count": -1},
            {"selected_subtitles": "en"},
            {"selected_subtitles": ["en", 3]},
            {"status": "exploded"},
            {"created_at": "not a date"},
            {"created_at": 123},
        ],
    )
    def test_invalid_values_raise_value_error(self, change):
        data = make_task().to_dict()
        data.update(change)
        with pytest.raises(ValueError):
            DownloadTask.from_dict(data)

    def test_missing_required_key_raises(self):
        data = make_task().to_dict()
        del data["output_directory"]
        with pytest.raises(ValueError):
            DownloadTask.from_dict(data)

    def test_non_dict_raises(self):
        with pytest.raises(ValueError):
            DownloadTask.from_dict(["not", "a", "dict"])

    def test_reset_for_retry(self):
        task = make_task(status=TaskStatus.DOWNLOADING, retry_count=1)
        task.started_at = datetime.now()
        task.update_progress(40.0, download_speed=5.0, eta_seconds=3, downloaded_bytes=7)
        task.fail("network down")

        task.reset_for_retry()

        assert task.status == TaskStatus.PENDING
        assert task.error_message == ""
        assert task.progress_percent == 0.0
        assert task.download_speed == 0.0
        assert task.eta_seconds == 0
        assert task.downloaded_bytes == 0
        assert task.started_at is None
        assert task.completed_at is None
        assert task.retry_count == 1  # the caller decides how a retry counts


# ----------------------------------------------------------------------
# Save and load
# ----------------------------------------------------------------------


class TestSaveLoadRoundTrip:
    def test_round_trip_keeps_order_and_skips_finished_tasks(self, queue_path):
        manager = make_manager(queue_path)
        manager.pause_queue()
        tasks = [
            make_task(0, TaskStatus.PENDING),
            make_task(1, TaskStatus.COMPLETED),
            make_task(2, TaskStatus.ERROR),
            make_task(3, TaskStatus.CANCELLED),
            make_task(4, TaskStatus.PENDING, subtitle_languages="עברית"),
        ]
        for task in tasks:
            manager.queue.add_task(task)
        assert manager.save_queue() is True

        restored = make_manager(queue_path)
        count = restored.load_queue()

        assert count == 3
        urls = [t.url for t in restored.get_all_tasks()]
        assert urls == [tasks[0].url, tasks[2].url, tasks[4].url]
        assert [t.status for t in restored.get_all_tasks()] == [
            TaskStatus.PENDING,
            TaskStatus.ERROR,
            TaskStatus.PENDING,
        ]
        assert restored.get_all_tasks()[2].subtitle_languages == "עברית"

    def test_file_has_version_paused_and_tasks(self, queue_path):
        manager = make_manager(queue_path)
        manager.queue.add_task(make_task())
        manager.save_queue()

        data = read_queue_file(queue_path)
        assert data["version"] == 1
        assert data["paused"] is False
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["status"] == "pending"

    def test_in_progress_becomes_pending_on_load(self, queue_path):
        task = make_task(0, TaskStatus.DOWNLOADING)
        task.started_at = datetime.now()
        write_queue_file(queue_path, [task], paused=True)

        manager = make_manager(queue_path)
        manager.load_queue()

        restored = manager.get_all_tasks()[0]
        assert restored.status == TaskStatus.PENDING
        assert restored.progress_percent == 0.0
        assert restored.started_at is None

    def test_failed_task_keeps_error_and_retry_count(self, queue_path):
        task = make_task(0, TaskStatus.ERROR, retry_count=1)
        task.error_message = "Download failed"
        write_queue_file(queue_path, [task])

        manager = make_manager(queue_path)
        manager.load_queue()

        restored = manager.get_all_tasks()[0]
        assert restored.status == TaskStatus.ERROR
        assert restored.error_message == "Download failed"
        assert restored.retry_count == 1

    def test_no_persist_path_means_memory_only(self, tmp_path):
        manager = QueueManager(max_concurrent=3)
        assert manager.load_queue() == 0
        manager.add_task(make_task())
        assert manager.save_queue() is False
        assert list(tmp_path.iterdir()) == []


class TestAtomicWrite:
    def test_no_temp_files_left_after_save(self, queue_path):
        manager = make_manager(queue_path)
        manager.queue.add_task(make_task())
        manager.save_queue()
        assert [p.name for p in queue_path.parent.iterdir()] == [queue_path.name]

    def test_writes_temp_file_in_same_folder_then_replaces(self, queue_path):
        manager = make_manager(queue_path)
        manager.queue.add_task(make_task())
        calls = []
        real_replace = os.replace

        def spy(src, dst):
            calls.append((src, dst))
            real_replace(src, dst)

        with patch("src.backend.queue_manager.os.replace", side_effect=spy):
            assert manager.save_queue() is True

        assert len(calls) == 1
        src, dst = calls[0]
        assert os.path.dirname(src) == str(queue_path.parent)
        assert src != str(queue_path)
        assert str(dst) == str(queue_path)

    def test_failed_replace_keeps_old_file_and_removes_temp(self, queue_path):
        queue_path.write_text('{"version": 1, "paused": false, "tasks": []}', encoding="utf-8")
        before = queue_path.read_text(encoding="utf-8")
        manager = make_manager(queue_path)
        manager.queue.add_task(make_task())

        with patch("src.backend.queue_manager.os.replace", side_effect=OSError("disk full")):
            assert manager.save_queue() is False  # logged, not raised

        assert queue_path.read_text(encoding="utf-8") == before
        assert [p.name for p in queue_path.parent.iterdir()] == [queue_path.name]

    def test_creates_missing_folder(self, tmp_path):
        path = tmp_path / "new" / "download_queue.json"
        manager = make_manager(path)
        manager.queue.add_task(make_task())
        assert manager.save_queue() is True
        assert path.exists()


class TestBadFiles:
    def test_missing_file_starts_empty(self, queue_path):
        manager = make_manager(queue_path)
        assert manager.load_queue() == 0
        assert manager.get_all_tasks() == []
        assert not queue_path.with_name(queue_path.name + ".bad").exists()

    def test_empty_file_starts_empty(self, queue_path):
        queue_path.write_text("   \n", encoding="utf-8")
        manager = make_manager(queue_path)
        assert manager.load_queue() == 0
        assert manager.get_all_tasks() == []

    def test_corrupt_file_starts_empty_and_keeps_bad_copy(self, queue_path):
        queue_path.write_text('{"version": 1, "tasks": [', encoding="utf-8")
        manager = make_manager(queue_path)

        assert manager.load_queue() == 0
        assert manager.get_all_tasks() == []
        bad = queue_path.with_name("download_queue.json.bad")
        assert bad.read_text(encoding="utf-8") == '{"version": 1, "tasks": ['

    def test_invalid_utf8_starts_empty_and_keeps_bad_copy(self, queue_path):
        queue_path.write_bytes(b"\xff\xfe\x00garbage")
        manager = make_manager(queue_path)
        assert manager.load_queue() == 0
        assert queue_path.with_name("download_queue.json.bad").exists()

    @pytest.mark.parametrize("version", [2, 0, "1", True, None])
    def test_unknown_version_starts_empty_and_keeps_bad_copy(self, queue_path, version):
        write_queue_file(queue_path, [make_task()], version=version)
        manager = make_manager(queue_path)

        assert manager.load_queue() == 0
        assert manager.get_all_tasks() == []
        assert queue_path.with_name("download_queue.json.bad").exists()

    def test_missing_version_starts_empty(self, queue_path):
        queue_path.write_text(json.dumps({"tasks": [make_task().to_dict()]}), encoding="utf-8")
        manager = make_manager(queue_path)
        assert manager.load_queue() == 0

    @pytest.mark.parametrize("content", ["[]", "42", '"text"', '{"version": 1, "tasks": {}}'])
    def test_wrong_layout_starts_empty(self, queue_path, content):
        queue_path.write_text(content, encoding="utf-8")
        manager = make_manager(queue_path)
        assert manager.load_queue() == 0
        assert queue_path.with_name("download_queue.json.bad").exists()

    def test_invalid_entry_is_skipped_and_others_restored(self, queue_path):
        good = make_task(0).to_dict()
        data = {"version": 1, "paused": True, "tasks": [good, {"url": 5}, "nonsense"]}
        queue_path.write_text(json.dumps(data), encoding="utf-8")
        manager = make_manager(queue_path)

        assert manager.load_queue() == 1
        assert manager.get_all_tasks()[0].url == good["url"]
        assert queue_path.with_name("download_queue.json.bad").exists()

    def test_unreadable_path_does_not_crash(self, queue_path):
        queue_path.mkdir()  # reading a folder raises an OSError
        manager = make_manager(queue_path)
        assert manager.load_queue() == 0

    def test_bad_file_is_replaced_on_next_save(self, queue_path):
        queue_path.write_text("garbage", encoding="utf-8")
        manager = make_manager(queue_path)
        manager.load_queue()
        manager.add_task(make_task())

        assert saved(manager)["version"] == 1
        assert queue_path.with_name("download_queue.json.bad").read_text(encoding="utf-8") == "garbage"


# ----------------------------------------------------------------------
# When the queue is saved
# ----------------------------------------------------------------------


class TestAutosave:
    def test_nothing_is_saved_before_load(self, queue_path):
        write_queue_file(queue_path, [make_task(0), make_task(1)], paused=True)
        before = queue_path.read_text(encoding="utf-8")

        manager = make_manager(queue_path)
        manager.pause_queue()
        manager.add_task(make_task(9))

        assert queue_path.read_text(encoding="utf-8") == before

    def test_add_remove_and_reorder_save(self, queue_path):
        manager = make_manager(queue_path)
        manager.load_queue()
        manager.pause_queue()

        manager.add_task(make_task(0))
        manager.add_task(make_task(1))
        assert len(saved(manager)["tasks"]) == 2

        manager.move_task_down(0)
        urls = [t["url"] for t in saved(manager)["tasks"]]
        assert urls == [make_task(1).url, make_task(0).url]

        manager.remove_task(0)
        urls = [t["url"] for t in saved(manager)["tasks"]]
        assert urls == [make_task(0).url]

    def test_clear_failed_saves(self, queue_path):
        manager = make_manager(queue_path)
        manager.load_queue()
        manager.pause_queue()
        manager.add_task(make_task(0))
        manager.get_all_tasks()[0].fail("x")
        manager.queue_updated.emit()
        assert len(saved(manager)["tasks"]) == 1

        manager.clear_failed()
        assert saved(manager)["tasks"] == []

    def test_status_change_saves(self, queue_path):
        manager = make_manager(queue_path)
        manager.load_queue()
        manager.pause_queue()
        manager.add_task(make_task(0))

        task = manager.get_all_tasks()[0]
        task.start()
        manager._on_worker_started(Mock(task=task), "Title")

        assert saved(manager)["tasks"][0]["status"] == "downloading"

    def test_completed_task_leaves_the_file(self, queue_path):
        manager = make_manager(queue_path)
        manager.load_queue()
        manager.pause_queue()
        manager.add_task(make_task(0))

        task = manager.get_all_tasks()[0]
        task.complete("video.mp4")
        manager._on_worker_completed(Mock(task=task), "video.mp4")

        assert saved(manager)["tasks"] == []

    def test_pause_and_resume_save_the_paused_state(self, queue_path):
        manager = make_manager(queue_path)
        manager.load_queue()

        manager.pause_queue()
        assert read_queue_file(queue_path)["paused"] is True

        manager.resume_queue()
        assert read_queue_file(queue_path)["paused"] is False

    def test_shutdown_saves_then_stops_saving(self, queue_path):
        manager = make_manager(queue_path)
        manager.load_queue()
        manager.pause_queue()
        manager.add_task(make_task(0))
        manager.get_all_tasks()[0].start()

        manager.shutdown()
        saved = queue_path.read_text(encoding="utf-8")
        assert read_queue_file(queue_path)["tasks"][0]["status"] == "downloading"

        # A worker that ends during teardown must not change the saved file.
        manager.get_all_tasks()[0].cancel()
        manager.queue_updated.emit()
        assert queue_path.read_text(encoding="utf-8") == saved

    def test_progress_ticks_do_not_save(self, queue_path):
        manager = make_manager(queue_path)
        manager.load_queue()
        manager.pause_queue()
        manager.add_task(make_task(0))
        manager.flush_save()

        with patch.object(manager, "save_queue") as save:
            manager._on_worker_progress(Mock(task=manager.get_all_tasks()[0]), {"percent": 10.0})
            manager.flush_save()
            save.assert_not_called()


# ----------------------------------------------------------------------
# Paused state on restore
# ----------------------------------------------------------------------


class TestRestoreStart:
    def test_paused_queue_stays_paused_and_starts_nothing(self, queue_path, mock_worker_class):
        write_queue_file(queue_path, [make_task(0), make_task(1, TaskStatus.DOWNLOADING)], paused=True)
        manager = make_manager(queue_path)

        manager.load_queue()

        assert manager.is_paused is True
        assert manager.workers == {}
        mock_worker_class.assert_not_called()
        assert all(t.status == TaskStatus.PENDING for t in manager.get_all_tasks())

    def test_running_queue_starts_up_to_max_concurrent(self, queue_path, mock_worker_class):
        write_queue_file(queue_path, [make_task(n) for n in range(5)], paused=False)
        manager = make_manager(queue_path, max_concurrent=3)

        manager.load_queue()

        assert manager.is_paused is False
        assert len(manager.workers) == 3
        assert mock_worker_class.call_count == 3

    def test_running_queue_with_only_failed_tasks_starts_nothing(self, queue_path, mock_worker_class):
        write_queue_file(queue_path, [make_task(0, TaskStatus.ERROR)], paused=False)
        manager = make_manager(queue_path)

        manager.load_queue()

        mock_worker_class.assert_not_called()
        assert manager.get_all_tasks()[0].status == TaskStatus.ERROR

    def test_paused_flag_ignored_when_nothing_restored(self, queue_path):
        write_queue_file(queue_path, [], paused=True)
        manager = make_manager(queue_path)
        manager.load_queue()
        assert manager.is_paused is False

    def test_invalid_paused_value_is_treated_as_paused(self, queue_path, mock_worker_class):
        data = {"version": 1, "paused": "no", "tasks": [make_task(0).to_dict()]}
        queue_path.write_text(json.dumps(data), encoding="utf-8")
        manager = make_manager(queue_path)

        manager.load_queue()

        assert manager.is_paused is True
        mock_worker_class.assert_not_called()

    def test_resume_after_paused_restore_starts_tasks(self, queue_path, mock_worker_class):
        write_queue_file(queue_path, [make_task(0), make_task(1)], paused=True)
        manager = make_manager(queue_path)
        manager.load_queue()

        manager.resume_queue()

        assert len(manager.workers) == 2


# ----------------------------------------------------------------------
# Manual retry
# ----------------------------------------------------------------------


class TestManualRetry:
    def test_retry_resets_failed_task_and_starts_it(self, queue_path, mock_worker_class):
        manager = make_manager(queue_path)
        manager.load_queue()
        manager.pause_queue()
        manager.add_task(make_task(0))
        task = manager.get_all_tasks()[0]
        task.fail("Download failed")
        task.retry_count = 1
        manager.resume_queue()  # nothing pending, nothing starts
        mock_worker_class.assert_not_called()

        assert manager.retry_task(0) is True

        assert task.status == TaskStatus.PENDING
        assert task.error_message == ""
        assert task.retry_count == 0
        assert manager.get_worker(task) is not None
        assert saved(manager)["tasks"][0]["status"] == "pending"

    def test_retry_when_paused_does_not_start(self, mock_worker_class):
        manager = QueueManager(max_concurrent=3)
        manager.pause_queue()
        manager.add_task(make_task(0))
        manager.get_all_tasks()[0].fail("x")

        assert manager.retry_task(0) is True
        assert manager.get_all_tasks()[0].status == TaskStatus.PENDING
        mock_worker_class.assert_not_called()

    def test_retry_emits_queue_updated(self):
        manager = QueueManager(max_concurrent=3)
        manager.pause_queue()
        manager.add_task(make_task(0))
        manager.get_all_tasks()[0].fail("x")
        updates = []
        manager.queue_updated.connect(lambda: updates.append(1))

        manager.retry_task(0)

        assert updates == [1]

    @pytest.mark.parametrize("status", [TaskStatus.PENDING, TaskStatus.DOWNLOADING, TaskStatus.COMPLETED])
    def test_retry_ignores_tasks_that_did_not_fail(self, status):
        manager = QueueManager(max_concurrent=3)
        manager.pause_queue()
        manager.add_task(make_task(0))
        manager.get_all_tasks()[0].status = status

        assert manager.retry_task(0) is False
        assert manager.get_all_tasks()[0].status == status

    def test_retry_invalid_index(self):
        manager = QueueManager(max_concurrent=3)
        assert manager.retry_task(7) is False

    def test_retry_all_failed(self, mock_worker_class):
        manager = QueueManager(max_concurrent=2)
        manager.pause_queue()
        for n in range(4):
            manager.add_task(make_task(n))
        tasks = manager.get_all_tasks()
        for task in tasks[:3]:
            task.fail("x")
        tasks[3].complete("done.mp4")
        manager.resume_queue()

        assert manager.retry_all_failed() == 3

        assert [t.status for t in tasks[:3]] == [TaskStatus.PENDING] * 3
        assert tasks[3].status == TaskStatus.COMPLETED
        assert len(manager.workers) == 2  # max_concurrent respected

    def test_retry_all_failed_with_none_failed(self):
        manager = QueueManager(max_concurrent=3)
        updates = []
        manager.queue_updated.connect(lambda: updates.append(1))
        assert manager.retry_all_failed() == 0
        assert updates == []


# ----------------------------------------------------------------------
# Automatic retry
# ----------------------------------------------------------------------


class TestIsAutoRetryable:
    @pytest.mark.parametrize(
        "message",
        [
            NETWORK_ERROR,
            "Connection reset by peer",
            "Read timed out",
            "<urlopen error [Errno -3] Temporary failure in name resolution>",
            "ERROR: unable to download video data: HTTP Error 503",
        ],
    )
    def test_network_errors_are_retryable(self, message):
        assert is_auto_retryable(message) is True

    @pytest.mark.parametrize(
        "message",
        [
            "The uploader has not made this video available in your country",
            "Video is not available from your location due to geo restriction",
            "Unable to download webpage: This video is not available in your country",
            "Private video. Sign in if you've been granted access to this video",
            "Unable to download webpage: login required",
            "This video has been removed due to a copyright claim",
            "Unsupported URL: https://example.com/page",
            "Unable to download: invalid URL",
            "Video unavailable",
            "Download failed",
            "Download cancelled",
            "No space left on device",
            "",
        ],
    )
    def test_other_errors_are_not_retryable(self, message):
        assert is_auto_retryable(message) is False

    def test_none_is_not_retryable(self):
        assert is_auto_retryable(None) is False

    def test_detail_message_is_used(self):
        assert is_auto_retryable("Download failed", NETWORK_ERROR) is True

    def test_detail_with_blocking_reason_wins(self):
        assert is_auto_retryable(NETWORK_ERROR, "Private video") is False


class TestAutoRetry:
    @pytest.fixture
    def manager(self, qtbot):
        manager = QueueManager(max_concurrent=3)
        manager.auto_retry_delay_ms = 0
        manager.pause_queue()  # control starts by hand
        manager.add_task(make_task(0))
        return manager

    def test_network_error_retries_once(self, qtbot, manager):
        task = fail_task(manager, 0, "Download failed", detail=NETWORK_ERROR)

        assert task.retry_count == 1
        qtbot.waitUntil(lambda: task.status == TaskStatus.PENDING, timeout=2000)
        assert task.error_message == ""

    def test_second_network_failure_is_not_retried(self, qtbot, manager):
        task = fail_task(manager, 0, "Download failed", detail=NETWORK_ERROR)
        qtbot.waitUntil(lambda: task.status == TaskStatus.PENDING, timeout=2000)

        fail_task(manager, 0, "Download failed", detail=NETWORK_ERROR)
        qtbot.wait(50)

        assert task.status == TaskStatus.ERROR
        assert task.retry_count == 1
        assert manager._pending_auto_retries == {}

    @pytest.mark.parametrize(
        "detail",
        [
            "The uploader has not made this video available in your country",
            "Private video. Sign in if you've been granted access to this video",
            "This video has been removed due to a copyright claim",
            "Unsupported URL: https://example.com",
            None,
        ],
    )
    def test_non_network_errors_are_not_retried(self, qtbot, manager, detail):
        task = fail_task(manager, 0, "Download failed", detail=detail)
        qtbot.wait(50)
        assert task.status == TaskStatus.ERROR
        assert task.retry_count == 0

    def test_cancelled_task_is_not_retried(self, qtbot, manager):
        task = manager.get_all_tasks()[0]
        task.cancel()
        worker = Mock(task=task)
        worker.wrapper.last_error = NETWORK_ERROR
        manager.workers[id(task)] = worker

        manager._on_worker_failed(worker, "Download cancelled")
        qtbot.wait(50)

        assert task.status == TaskStatus.CANCELLED
        assert task.retry_count == 0

    def test_auto_retry_starts_task_when_queue_runs(self, qtbot, manager, mock_worker_class):
        manager._auto_start = True
        task = fail_task(manager, 0, "Download failed", detail=NETWORK_ERROR)

        qtbot.waitUntil(lambda: manager.get_worker(task) is not None, timeout=2000)
        assert task.status == TaskStatus.PENDING
        assert mock_worker_class.call_count == 1

    def test_auto_retry_waits_while_paused(self, qtbot, manager, mock_worker_class):
        task = fail_task(manager, 0, "Download failed", detail=NETWORK_ERROR)
        qtbot.waitUntil(lambda: task.status == TaskStatus.PENDING, timeout=2000)
        mock_worker_class.assert_not_called()

    def test_auto_retry_skipped_if_task_removed_meanwhile(self, qtbot, manager):
        manager.auto_retry_delay_ms = 30
        task = fail_task(manager, 0, "Download failed", detail=NETWORK_ERROR)
        manager.clear_failed()

        qtbot.wait(100)

        assert task.status == TaskStatus.ERROR
        assert manager.get_all_tasks() == []

    def test_manual_retry_cancels_pending_auto_retry(self, qtbot, manager):
        manager.auto_retry_delay_ms = 30
        task = fail_task(manager, 0, "Download failed", detail=NETWORK_ERROR)
        manager.retry_task(0)
        task.fail("Download failed")  # fails again before the timer fires

        qtbot.wait(100)

        assert task.status == TaskStatus.ERROR  # the old timer did nothing

    def test_notification_skipped_when_retry_follows(self, qtbot):
        notifier = Mock()
        manager = QueueManager(max_concurrent=3, notification_manager=notifier)
        manager.auto_retry_delay_ms = 0
        manager.pause_queue()
        manager.add_task(make_task(0))

        fail_task(manager, 0, "Download failed", detail=NETWORK_ERROR)
        notifier.notify_download_error.assert_not_called()

        qtbot.waitUntil(lambda: manager.get_all_tasks()[0].status == TaskStatus.PENDING, timeout=2000)
        fail_task(manager, 0, "Download failed", detail=NETWORK_ERROR)
        notifier.notify_download_error.assert_called_once()

    def test_restored_task_that_used_its_retry_is_not_retried(self, qtbot, queue_path):
        write_queue_file(queue_path, [make_task(0, retry_count=1)], paused=True)
        manager = make_manager(queue_path)
        manager.auto_retry_delay_ms = 0
        manager.load_queue()

        task = fail_task(manager, 0, "Download failed", detail=NETWORK_ERROR)
        qtbot.wait(50)

        assert task.status == TaskStatus.ERROR

    def test_retry_count_is_saved(self, qtbot, queue_path):
        manager = make_manager(queue_path)
        manager.auto_retry_delay_ms = 0
        manager.load_queue()
        manager.pause_queue()
        manager.add_task(make_task(0))

        task = fail_task(manager, 0, "Download failed", detail=NETWORK_ERROR)
        qtbot.waitUntil(lambda: task.status == TaskStatus.PENDING, timeout=2000)

        assert saved(manager)["tasks"][0]["retry_count"] == 1
