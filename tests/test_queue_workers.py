"""
Tests for worker bookkeeping, threading and shutdown in QueueManager.

Covers:
- workers keyed by task identity, so index shifts (remove, clear,
  reorder) never orphan or overwrite a running worker
- worker references kept until QThread.finished, also after stop_all
- worker slots running on the GUI thread (real QThreads)
- the explicit double-start guard
- the debounced save (many changes, one write)
- shutdown(): immediate save, cancel and bounded wait, no new starts

FakeWorker is a real QThread with the same signals as DownloadWorker. It
never touches the network.
"""

import threading
import time
from unittest.mock import MagicMock, Mock, patch

import pytest
import shiboken6
from PySide6.QtCore import QCoreApplication, Qt, QThread, Signal

from src.backend import queue_manager as qm_module
from src.backend.queue_manager import QueueManager
from src.models.download_task import DownloadTask, TaskStatus


def make_task(n=0):
    return DownloadTask(url=f"https://www.youtube.com/watch?v=w{n}", output_directory="/tmp", quality="1080p")


class FakeWorker(QThread):
    """A real QThread with DownloadWorker's signals and cancel()."""

    progress_updated = Signal(dict)
    download_started = Signal(str)
    download_completed = Signal(str)
    download_failed = Signal(str)
    log_message = Signal(str)

    # Set per test
    block_until_cancel = False
    ignore_cancel = False
    linger_after_cancel_s = 0.0

    lock = threading.Lock()
    running = 0
    peak = 0
    instances: list["FakeWorker"] = []

    def __init__(self, task):
        super().__init__()
        self.task = task
        self.wrapper = None
        self._cancel = threading.Event()
        self._release = threading.Event()
        FakeWorker.instances.append(self)

    @classmethod
    def reset(cls):
        cls.block_until_cancel = False
        cls.ignore_cancel = False
        cls.linger_after_cancel_s = 0.0
        cls.running = 0
        cls.peak = 0
        cls.instances = []

    def cancel(self):
        self._cancel.set()

    def release(self):
        self._release.set()

    def run(self):
        with FakeWorker.lock:
            FakeWorker.running += 1
            FakeWorker.peak = max(FakeWorker.peak, FakeWorker.running)
        try:
            self.task.start()
            self.download_started.emit("Title")
            self.progress_updated.emit({"percent": 50.0, "speed": 1.0})
            if self.ignore_cancel:
                self._release.wait(10)
            elif self.block_until_cancel:
                self._cancel.wait(10)
            if self._cancel.is_set():
                self.task.cancel()
                self.download_failed.emit("Download cancelled")
                # Like yt-dlp cleanup: the thread runs on after reporting.
                time.sleep(self.linger_after_cancel_s)
            else:
                self.task.complete("video.mp4")
                self.download_completed.emit("video.mp4")
        finally:
            with FakeWorker.lock:
                FakeWorker.running -= 1


@pytest.fixture
def fake_workers(qapp):
    """Use FakeWorker for every task. Stop all threads after the test."""
    FakeWorker.reset()
    with patch.object(qm_module, "DownloadWorker", FakeWorker):
        yield FakeWorker
    for worker in FakeWorker.instances:
        if not shiboken6.isValid(worker):
            continue  # finished and deleted by the queue manager
        worker.cancel()
        worker.release()
        worker.wait(5000)
    QCoreApplication.processEvents()
    FakeWorker.reset()


@pytest.fixture
def mock_workers():
    """Use MagicMock workers (no threads)."""
    with patch.object(qm_module, "DownloadWorker") as worker_class:
        worker_class.side_effect = lambda task: MagicMock(task=task)
        yield worker_class


def spy_finished(manager):
    """Record, for each finished slot call, where the worker was kept and if its thread still ran."""
    events = []
    real = manager._on_worker_finished

    def spy(worker):
        if worker in manager._stopping.values():
            place = "stopping"
        elif worker in manager._finishing.values():
            place = "finishing"
        else:
            place = "unreferenced"
        events.append((place, worker.isRunning()))
        real(worker)

    # _start_task binds the slot when it connects, so set the spy first.
    manager._on_worker_finished = spy
    return events


# ----------------------------------------------------------------------
# 1. Workers keyed by task identity
# ----------------------------------------------------------------------


class TestWorkersKeyedByTask:
    def test_remove_before_running_task_does_not_overwrite_its_worker(self, mock_workers):
        manager = QueueManager(max_concurrent=3)
        manager.pause_queue()
        p0, running, p2 = make_task(0), make_task(1), make_task(2)
        for task in (p0, running, p2):
            manager.add_task(task)
        manager._start_task(1, running)
        running_worker = manager.get_worker(running)

        assert manager.remove_task(0) is True  # running task moves to index 0
        manager.resume_queue()  # starts p2, now at index 1

        assert manager.get_worker(running) is running_worker
        assert manager.get_worker(p2) is not None
        assert manager.get_worker(p2) is not running_worker
        assert len(manager.workers) == 2

    def test_completion_after_reorder_frees_the_right_worker(self, mock_workers):
        manager = QueueManager(max_concurrent=3)
        manager.pause_queue()
        a, b = make_task(0), make_task(1)
        manager.add_task(a)
        manager.add_task(b)
        manager._start_task(0, a)
        manager._start_task(1, b)
        worker_a = manager.get_worker(a)
        indexes = []
        manager.task_completed.connect(lambda index, _name: indexes.append(index))

        manager.move_task_down(0)  # a is now at index 1
        a.complete("a.mp4")
        manager._on_worker_completed(worker_a, "a.mp4")

        assert manager.get_worker(a) is None
        assert manager.get_worker(b) is not None
        assert indexes == [1]  # the current index, not the start index

    def test_clear_completed_does_not_orphan_running_worker(self, mock_workers):
        manager = QueueManager(max_concurrent=2)
        manager.pause_queue()
        done, running, waiting = make_task(0), make_task(1), make_task(2)
        for task in (done, running, waiting):
            manager.add_task(task)
        done.complete("x.mp4")
        manager._start_task(1, running)

        manager.clear_completed()  # running moves from index 1 to 0
        manager.resume_queue()

        assert len(manager.workers) == 2
        assert manager.get_worker(running) is not None
        assert manager.get_worker(waiting) is not None

    def test_stop_all_cancels_every_worker_after_reorder(self, mock_workers):
        manager = QueueManager(max_concurrent=3)
        manager.pause_queue()
        tasks = [make_task(n) for n in range(3)]
        for task in tasks:
            manager.add_task(task)
        manager.resume_queue()
        workers = [manager.get_worker(t) for t in tasks]
        manager.move_task_up(2)
        manager.remove_task(0)  # refused: active

        manager.stop_all()

        for worker in workers:
            worker.cancel.assert_called_once()
        assert manager.workers == {}
        assert len(manager._stopping) == 3

    def test_cancel_task_uses_current_row(self, mock_workers):
        manager = QueueManager(max_concurrent=3)
        manager.pause_queue()
        a, b = make_task(0), make_task(1)
        manager.add_task(a)
        manager.add_task(b)
        manager._start_task(1, b)
        worker_b = manager.get_worker(b)
        manager.move_task_up(1)  # b is now row 0

        assert manager.cancel_task(0) is True

        worker_b.cancel.assert_called_once()
        assert a in manager.get_all_tasks()  # the pending task was not removed

    def test_cancel_task_removes_pending_task_without_worker(self):
        manager = QueueManager(max_concurrent=3)
        manager.pause_queue()
        manager.add_task(make_task(0))
        assert manager.cancel_task(0) is True
        assert manager.get_all_tasks() == []

    def test_cancel_task_ignores_finished_task(self):
        manager = QueueManager(max_concurrent=3)
        manager.pause_queue()
        manager.add_task(make_task(0))
        manager.get_all_tasks()[0].complete("x.mp4")
        assert manager.cancel_task(0) is False
        assert manager.cancel_task(5) is False

    def test_progress_for_removed_task_is_not_emitted(self):
        manager = QueueManager(max_concurrent=3)
        received = []
        manager.task_progress.connect(lambda index, data: received.append(index))
        manager._on_worker_progress(Mock(task=make_task(9)), {"percent": 1.0})
        assert received == []


# ----------------------------------------------------------------------
# 6. Explicit double-start guard
# ----------------------------------------------------------------------


class TestDoubleStartGuard:
    def test_pending_task_with_worker_is_not_started_again(self, mock_workers):
        manager = QueueManager(max_concurrent=3)
        manager.pause_queue()
        task = make_task(0)
        manager.add_task(task)
        manager._start_task(0, task)
        assert task.status == TaskStatus.PENDING  # the thread has not run yet

        with patch.object(manager, "_has_conflicting_download", return_value=False):
            manager._try_start_next()
            manager._fill_slots()

        assert mock_workers.call_count == 1

    def test_stopping_workers_use_slots(self, mock_workers):
        manager = QueueManager(max_concurrent=1)
        manager.pause_queue()
        a, b = make_task(0), make_task(1)
        manager.add_task(a)
        manager.add_task(b)
        manager._start_task(0, a)

        manager.stop_all()
        manager.resume_queue()

        assert mock_workers.call_count == 1  # b waits for a's thread to end


# ----------------------------------------------------------------------
# 2 and 3. Real threads: GUI-thread slots and references until finished
# ----------------------------------------------------------------------


class TestRealThreads:
    def test_worker_slots_run_on_gui_thread(self, qtbot, fake_workers):
        app_thread = QCoreApplication.instance().thread()
        seen = {}
        manager = QueueManager(max_concurrent=3)
        # DirectConnection: these run in whatever thread the manager's slot
        # runs in, so they show where the worker signals were delivered.
        manager.task_started.connect(
            lambda i, t: seen.__setitem__("started", QThread.currentThread() is app_thread),
            Qt.ConnectionType.DirectConnection,
        )
        manager.task_progress.connect(
            lambda i, d: seen.__setitem__("progress", QThread.currentThread() is app_thread),
            Qt.ConnectionType.DirectConnection,
        )
        manager.task_completed.connect(
            lambda i, f: seen.__setitem__("completed", QThread.currentThread() is app_thread),
            Qt.ConnectionType.DirectConnection,
        )

        task = make_task(0)
        manager.add_task(task)

        qtbot.waitUntil(lambda: "completed" in seen, timeout=5000)
        assert seen == {"started": True, "progress": True, "completed": True}

    def test_failed_slot_runs_on_gui_thread(self, qtbot, fake_workers):
        fake_workers.block_until_cancel = True
        app_thread = QCoreApplication.instance().thread()
        seen = []
        manager = QueueManager(max_concurrent=3)
        manager.task_failed.connect(
            lambda i, e: seen.append(QThread.currentThread() is app_thread),
            Qt.ConnectionType.DirectConnection,
        )
        task = make_task(0)
        manager.add_task(task)
        qtbot.waitUntil(lambda: task.status == TaskStatus.DOWNLOADING, timeout=5000)

        manager.cancel_task(0)

        qtbot.waitUntil(lambda: bool(seen), timeout=5000)
        assert seen == [True]

    def test_completed_worker_is_kept_until_finished(self, qtbot, fake_workers):
        manager = QueueManager(max_concurrent=3)
        events = spy_finished(manager)
        task = make_task(0)
        manager.add_task(task)

        qtbot.waitUntil(lambda: bool(events), timeout=5000)

        # When the finished slot ran, the worker was still referenced and
        # its thread had ended. Afterwards nothing references it.
        assert events == [("finishing", False)]
        assert task.status == TaskStatus.COMPLETED
        assert manager.workers == {}
        assert manager._finishing == {}

    def test_stop_all_keeps_reference_and_slot_until_finished(self, qtbot, fake_workers):
        fake_workers.block_until_cancel = True
        fake_workers.linger_after_cancel_s = 0.3
        manager = QueueManager(max_concurrent=1)
        events = spy_finished(manager)
        first, second = make_task(0), make_task(1)
        manager.add_task(first)
        manager.add_task(second)
        qtbot.waitUntil(lambda: first.status == TaskStatus.DOWNLOADING, timeout=5000)
        first_worker = fake_workers.instances[0]

        manager.stop_all()

        assert manager.workers == {}
        assert first_worker in manager._stopping.values()
        # The cancel is reported while the thread still runs; the second
        # task must wait for the thread to end.
        qtbot.waitUntil(lambda: first.status == TaskStatus.CANCELLED, timeout=5000)
        qtbot.wait(50)
        assert len(fake_workers.instances) == 1

        qtbot.waitUntil(lambda: len(fake_workers.instances) == 2, timeout=5000)
        assert events[0] == ("stopping", False)
        assert manager._stopping == {}
        assert fake_workers.peak == 1  # never two download threads at once

        manager.shutdown(wait_ms=3000)


# ----------------------------------------------------------------------
# 4. Debounced save
# ----------------------------------------------------------------------


class TestDebouncedSave:
    @pytest.fixture
    def manager(self, qapp, tmp_path, mock_workers):
        manager = QueueManager(max_concurrent=3, persist_path=tmp_path / "download_queue.json")
        manager.load_queue()
        manager.pause_queue()
        return manager

    def test_many_rapid_changes_write_once(self, qtbot, manager):
        with patch.object(qm_module, "_write_atomic", wraps=qm_module._write_atomic) as write:
            for n in range(25):
                manager.add_task(make_task(n))
            assert write.call_count == 0  # nothing written yet

            qtbot.waitUntil(lambda: write.call_count == 1, timeout=3000)
            qtbot.wait(manager.SAVE_DELAY_MS + 100)

        assert write.call_count == 1
        assert len(manager.to_dict()["tasks"]) == 25
        assert manager.persist_path.read_text(encoding="utf-8").count('"url"') == 25

    def test_pause_saves_at_once(self, manager):
        manager.add_task(make_task(0))
        with patch.object(qm_module, "_write_atomic", wraps=qm_module._write_atomic) as write:
            manager.resume_queue()
            assert write.call_count == 1
        assert '"url"' in manager.persist_path.read_text(encoding="utf-8")

    def test_shutdown_writes_pending_change_at_once(self, manager):
        manager.add_task(make_task(0))
        with patch.object(qm_module, "_write_atomic", wraps=qm_module._write_atomic) as write:
            manager.shutdown(wait_ms=100)
            assert write.call_count == 1
        assert '"url"' in manager.persist_path.read_text(encoding="utf-8")

    def test_flush_without_change_does_not_write(self, manager):
        manager.flush_save()
        with patch.object(qm_module, "_write_atomic") as write:
            assert manager.flush_save() is False
            write.assert_not_called()


# ----------------------------------------------------------------------
# 5. Shutdown
# ----------------------------------------------------------------------


class TestShutdown:
    def test_shutdown_saves_then_cancels_and_waits(self, qtbot, tmp_path, fake_workers):
        fake_workers.block_until_cancel = True
        path = tmp_path / "download_queue.json"
        manager = QueueManager(max_concurrent=2, persist_path=path)
        manager.load_queue()
        tasks = [make_task(n) for n in range(2)]
        for task in tasks:
            manager.add_task(task)
        qtbot.waitUntil(lambda: all(t.status == TaskStatus.DOWNLOADING for t in tasks), timeout=5000)

        manager.shutdown(wait_ms=3000)

        assert all(w.isFinished() for w in fake_workers.instances)
        assert all(t.status == TaskStatus.CANCELLED for t in tasks)
        # The file was written before the cancel and is not changed after it.
        assert path.read_text(encoding="utf-8").count('"status": "downloading"') == 2
        qtbot.wait(50)
        assert path.read_text(encoding="utf-8").count('"status": "downloading"') == 2

    def test_shutdown_wait_is_bounded(self, qtbot, fake_workers):
        fake_workers.ignore_cancel = True
        manager = QueueManager(max_concurrent=1)
        task = make_task(0)
        manager.add_task(task)
        qtbot.waitUntil(lambda: task.status == TaskStatus.DOWNLOADING, timeout=5000)

        started = time.monotonic()
        manager.shutdown(wait_ms=200)
        elapsed = time.monotonic() - started

        assert elapsed < 2.0
        assert fake_workers.instances[0].isRunning()  # released by the fixture

    def test_no_start_after_shutdown(self, mock_workers):
        manager = QueueManager(max_concurrent=3)
        manager.pause_queue()
        manager.shutdown(wait_ms=100)

        manager.add_task(make_task(0))
        manager.resume_queue()
        manager.start_queue()

        mock_workers.assert_not_called()

    def test_pending_auto_retry_does_not_start_after_shutdown(self, qtbot, mock_workers):
        manager = QueueManager(max_concurrent=3)
        manager.auto_retry_delay_ms = 30
        manager.pause_queue()
        task = make_task(0)
        manager.add_task(task)
        manager.resume_queue()
        worker = manager.get_worker(task)
        worker.wrapper._last_error = "Unable to download webpage: <urlopen error timed out>"
        task.fail("Download failed")
        manager._on_worker_failed(worker, "Download failed")
        assert task.retry_count == 1  # retry scheduled

        manager.shutdown(wait_ms=100)
        qtbot.wait(150)

        assert task.status == TaskStatus.ERROR
        assert mock_workers.call_count == 1

    def test_failure_during_shutdown_does_not_notify_or_retry(self, mock_workers):
        notifier = Mock()
        manager = QueueManager(max_concurrent=3, notification_manager=notifier)
        task = make_task(0)
        manager.add_task(task)
        worker = manager.get_worker(task)
        worker.wrapper._last_error = "Unable to download webpage: <urlopen error timed out>"

        manager.shutdown(wait_ms=100)
        task.fail("Download failed")
        manager._on_worker_failed(worker, "Download failed")

        notifier.notify_download_error.assert_not_called()
        assert task.retry_count == 0
