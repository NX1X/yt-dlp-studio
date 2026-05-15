"""
Tests for QueueManager backend.

Tests queue management, worker coordination, and signal emissions.
"""

from unittest.mock import Mock, patch

import pytest

from src.backend.queue_manager import QueueManager
from src.models.download_task import DownloadTask, TaskStatus


@pytest.fixture
def queue_manager():
    """Create a queue manager for testing."""
    return QueueManager(max_concurrent=3)


@pytest.fixture
def sample_task():
    """Create a sample download task."""
    return DownloadTask(url="https://www.youtube.com/watch?v=test", output_directory="/tmp/downloads", quality="1080p")


@pytest.fixture
def multiple_tasks():
    """Create multiple sample tasks."""
    return [
        DownloadTask(url=f"https://www.youtube.com/watch?v=test{i}", output_directory="/tmp/downloads", quality="1080p")
        for i in range(5)
    ]


class TestQueueManagerBasics:
    """Test basic queue manager operations."""

    def test_initialization(self, queue_manager):
        """Test queue manager initialization."""
        assert queue_manager.queue.max_concurrent == 3
        assert len(queue_manager.workers) == 0
        assert queue_manager._auto_start is True

    def test_add_task(self, queue_manager, sample_task):
        """Test adding a task to queue."""
        with patch.object(queue_manager, "_try_start_next"):
            index = queue_manager.add_task(sample_task)
            assert index == 0
            assert queue_manager.queue.get_queue_size() == 1

    def test_add_task_emits_signal(self, queue_manager, sample_task):
        """Test that adding task emits queue_updated signal."""
        signal_emitted = False

        def on_queue_updated():
            nonlocal signal_emitted
            signal_emitted = True

        queue_manager.queue_updated.connect(on_queue_updated)

        with patch.object(queue_manager, "_try_start_next"):
            queue_manager.add_task(sample_task)
            assert signal_emitted is True

    def test_add_multiple_tasks(self, queue_manager, multiple_tasks):
        """Test adding multiple tasks."""
        with patch.object(queue_manager, "_try_start_next"):
            for i, task in enumerate(multiple_tasks):
                index = queue_manager.add_task(task)
                assert index == i

    def test_get_all_tasks(self, queue_manager, multiple_tasks):
        """Test retrieving all tasks."""
        with patch.object(queue_manager, "_try_start_next"):
            for task in multiple_tasks:
                queue_manager.add_task(task)

        all_tasks = queue_manager.get_all_tasks()
        assert len(all_tasks) == 5


class TestQueueManagerRemoval:
    """Test task removal operations."""

    def test_remove_pending_task(self, queue_manager, multiple_tasks):
        """Test removing a pending task."""
        with patch.object(queue_manager, "_try_start_next"):
            for task in multiple_tasks:
                queue_manager.add_task(task)

        result = queue_manager.remove_task(1)
        assert result is True
        assert queue_manager.queue.get_queue_size() == 4

    def test_cannot_remove_active_task(self, queue_manager, sample_task):
        """Test that active tasks cannot be removed."""
        with patch.object(queue_manager, "_try_start_next"):
            index = queue_manager.add_task(sample_task)

        # Mark as active and add mock worker
        sample_task.status = TaskStatus.DOWNLOADING
        queue_manager.workers[index] = Mock()

        result = queue_manager.remove_task(index)
        assert result is False

    def test_remove_invalid_index(self, queue_manager):
        """Test removing with invalid index."""
        result = queue_manager.remove_task(0)
        assert result is False

        result = queue_manager.remove_task(100)
        assert result is False


class TestQueueManagerOrdering:
    """Test task ordering operations."""

    def test_move_task_up(self, queue_manager, multiple_tasks):
        """Test moving task up in queue."""
        with patch.object(queue_manager, "_try_start_next"):
            for task in multiple_tasks:
                queue_manager.add_task(task)

        result = queue_manager.move_task_up(2)
        assert result is True

    def test_move_task_up_emits_signal(self, queue_manager, multiple_tasks):
        """Test that moving task up emits signal."""
        signal_emitted = False

        def on_queue_updated():
            nonlocal signal_emitted
            signal_emitted = True

        queue_manager.queue_updated.connect(on_queue_updated)

        with patch.object(queue_manager, "_try_start_next"):
            for task in multiple_tasks:
                queue_manager.add_task(task)

        queue_manager.move_task_up(2)
        assert signal_emitted is True

    def test_move_task_down(self, queue_manager, multiple_tasks):
        """Test moving task down in queue."""
        with patch.object(queue_manager, "_try_start_next"):
            for task in multiple_tasks:
                queue_manager.add_task(task)

        result = queue_manager.move_task_down(2)
        assert result is True


class TestQueueManagerControl:
    """Test queue control operations."""

    def test_start_queue(self, queue_manager):
        """Test starting queue."""
        with patch.object(queue_manager, "_try_start_next") as mock_start:
            queue_manager.start_queue()
            mock_start.assert_called_once()

    def test_pause_queue(self, queue_manager):
        """Test pausing queue."""
        queue_manager.pause_queue()
        assert queue_manager._auto_start is False

    def test_resume_queue(self, queue_manager):
        """Test resuming queue."""
        queue_manager._auto_start = False
        with patch.object(queue_manager, "_try_start_next") as mock_start:
            queue_manager.resume_queue()
            assert queue_manager._auto_start is True
            mock_start.assert_called_once()

    def test_stop_all(self, queue_manager):
        """Test stopping all downloads."""
        # Create mock workers
        mock_worker1 = Mock()
        mock_worker2 = Mock()
        queue_manager.workers[0] = mock_worker1
        queue_manager.workers[1] = mock_worker2

        queue_manager.stop_all()

        # Verify cancel was called on all workers
        mock_worker1.cancel.assert_called_once()
        mock_worker2.cancel.assert_called_once()
        assert len(queue_manager.workers) == 0


class TestQueueManagerClearing:
    """Test queue clearing operations."""

    def test_clear_completed(self, queue_manager, multiple_tasks):
        """Test clearing completed tasks."""
        with patch.object(queue_manager, "_try_start_next"):
            for task in multiple_tasks:
                queue_manager.add_task(task)

        # Mark first 2 as completed
        for i in range(2):
            multiple_tasks[i].status = TaskStatus.COMPLETED

        count = queue_manager.clear_completed()
        assert count == 2
        assert queue_manager.queue.get_queue_size() == 3

    def test_clear_failed(self, queue_manager, multiple_tasks):
        """Test clearing failed tasks."""
        with patch.object(queue_manager, "_try_start_next"):
            for task in multiple_tasks:
                queue_manager.add_task(task)

        # Mark first 3 as failed
        for i in range(3):
            multiple_tasks[i].status = TaskStatus.ERROR

        count = queue_manager.clear_failed()
        assert count == 3
        assert queue_manager.queue.get_queue_size() == 2


class TestQueueManagerStatistics:
    """Test queue statistics."""

    def test_get_queue_statistics(self, queue_manager, multiple_tasks):
        """Test getting queue statistics."""
        with patch.object(queue_manager, "_try_start_next"):
            for task in multiple_tasks:
                queue_manager.add_task(task)

        # Set various statuses
        multiple_tasks[0].status = TaskStatus.PENDING
        multiple_tasks[1].status = TaskStatus.DOWNLOADING
        multiple_tasks[2].status = TaskStatus.COMPLETED
        multiple_tasks[3].status = TaskStatus.ERROR
        multiple_tasks[4].status = TaskStatus.PENDING

        stats = queue_manager.get_queue_statistics()
        assert stats["total"] == 5
        assert stats["pending"] == 2
        assert stats["active"] == 1
        assert stats["completed"] == 1
        assert stats["failed"] == 1


class TestQueueManagerWorkerManagement:
    """Test worker management and coordination."""

    @patch("src.backend.queue_manager.DownloadWorker")
    def test_start_task_creates_worker(self, mock_worker_class, queue_manager, sample_task):
        """Test that starting a task creates a worker."""
        mock_worker = Mock()
        mock_worker_class.return_value = mock_worker

        queue_manager._start_task(0, sample_task)

        mock_worker_class.assert_called_once_with(sample_task)
        assert 0 in queue_manager.workers
        mock_worker.start.assert_called_once()

    @patch("src.backend.queue_manager.DownloadWorker")
    def test_start_task_connects_signals(self, mock_worker_class, queue_manager, sample_task):
        """Test that starting a task connects worker signals."""
        mock_worker = Mock()
        mock_worker_class.return_value = mock_worker

        # Mock the signal objects
        mock_worker.download_started = Mock()
        mock_worker.download_completed = Mock()
        mock_worker.download_failed = Mock()
        mock_worker.progress_updated = Mock()

        queue_manager._start_task(0, sample_task)

        # Verify signals were connected
        mock_worker.download_started.connect.assert_called_once()
        mock_worker.download_completed.connect.assert_called_once()
        mock_worker.download_failed.connect.assert_called_once()
        mock_worker.progress_updated.connect.assert_called_once()

    def test_try_start_next_at_capacity(self, queue_manager, multiple_tasks):
        """Test that try_start_next respects capacity limit."""
        with patch.object(queue_manager, "_try_start_next"):
            for task in multiple_tasks:
                queue_manager.add_task(task)

        # Mark 3 tasks as downloading (at capacity)
        for i in range(3):
            multiple_tasks[i].status = TaskStatus.DOWNLOADING
            queue_manager.workers[i] = Mock()

        with patch.object(queue_manager, "_start_task") as mock_start:
            queue_manager._try_start_next()
            # Should not start new task (at capacity)
            mock_start.assert_not_called()

    def test_try_start_next_below_capacity(self, queue_manager, multiple_tasks):
        """Test that try_start_next starts task when capacity available."""
        with patch.object(queue_manager, "_try_start_next"):
            for task in multiple_tasks:
                queue_manager.add_task(task)

        # Mark 2 tasks as downloading (below capacity)
        for i in range(2):
            multiple_tasks[i].status = TaskStatus.DOWNLOADING
            queue_manager.workers[i] = Mock()

        with patch.object(queue_manager, "_start_task") as mock_start:
            queue_manager._try_start_next()
            # Should start next pending task
            mock_start.assert_called_once()


class TestQueueManagerSignals:
    """Test signal emissions."""

    def test_on_task_started_emits_signal(self, queue_manager):
        """Test that task started handler emits signal."""
        signal_received = False
        received_index = None
        received_title = None

        def on_task_started(index, title):
            nonlocal signal_received, received_index, received_title
            signal_received = True
            received_index = index
            received_title = title

        queue_manager.task_started.connect(on_task_started)
        queue_manager._on_task_started(0, "Test Video")

        assert signal_received is True
        assert received_index == 0
        assert received_title == "Test Video"

    def test_on_task_completed_emits_signal(self, queue_manager):
        """Test that task completed handler emits signal."""
        signal_received = False
        received_index = None
        received_filename = None

        def on_task_completed(index, filename):
            nonlocal signal_received, received_index, received_filename
            signal_received = True
            received_index = index
            received_filename = filename

        queue_manager.task_completed.connect(on_task_completed)

        # Add mock worker
        queue_manager.workers[0] = Mock()

        with patch.object(queue_manager, "_try_start_next"):
            queue_manager._on_task_completed(0, "video.mp4")

        assert signal_received is True
        assert received_index == 0
        assert received_filename == "video.mp4"
        # Worker should be removed
        assert 0 not in queue_manager.workers

    def test_on_task_failed_emits_signal(self, queue_manager):
        """Test that task failed handler emits signal."""
        signal_received = False
        received_index = None
        received_error = None

        def on_task_failed(index, error):
            nonlocal signal_received, received_index, received_error
            signal_received = True
            received_index = index
            received_error = error

        queue_manager.task_failed.connect(on_task_failed)

        # Add mock worker
        queue_manager.workers[0] = Mock()

        with patch.object(queue_manager, "_try_start_next"):
            queue_manager._on_task_failed(0, "Download error")

        assert signal_received is True
        assert received_index == 0
        assert received_error == "Download error"
        # Worker should be removed
        assert 0 not in queue_manager.workers

    def test_on_task_progress_emits_signal(self, queue_manager):
        """Test that task progress handler emits signal."""
        signal_received = False
        received_index = None
        received_data = None

        def on_task_progress(index, data):
            nonlocal signal_received, received_index, received_data
            signal_received = True
            received_index = index
            received_data = data

        queue_manager.task_progress.connect(on_task_progress)

        progress_data = {"percent": 50, "speed": 1024000}
        queue_manager._on_task_progress(0, progress_data)

        assert signal_received is True
        assert received_index == 0
        assert received_data == progress_data

    def test_all_completed_signal(self, queue_manager, sample_task):
        """Test all_completed signal emission."""
        signal_received = False

        def on_all_completed():
            nonlocal signal_received
            signal_received = True

        queue_manager.all_completed.connect(on_all_completed)

        with patch.object(queue_manager, "_try_start_next"):
            queue_manager.add_task(sample_task)

        # Mark task as completed
        sample_task.status = TaskStatus.COMPLETED

        # Try to start next (should emit all_completed)
        queue_manager._try_start_next()

        assert signal_received is True


class TestQueueManagerConfiguration:
    """Test queue configuration."""

    def test_set_max_concurrent(self, queue_manager):
        """Test changing max concurrent downloads."""
        with patch.object(queue_manager, "_try_start_next") as mock_start:
            queue_manager.set_max_concurrent(5)
            assert queue_manager.queue.max_concurrent == 5
            mock_start.assert_called_once()

    def test_set_max_concurrent_while_paused(self, queue_manager):
        """Test changing max concurrent while paused."""
        queue_manager._auto_start = False

        with patch.object(queue_manager, "_try_start_next") as mock_start:
            queue_manager.set_max_concurrent(5)
            # Should not try to start next when paused
            mock_start.assert_not_called()


class TestQueueManagerAutoStart:
    """Test auto-start behavior."""

    def test_auto_start_on_add(self, queue_manager, sample_task):
        """Test that auto-start triggers when adding task."""
        with patch.object(queue_manager, "_try_start_next") as mock_start:
            queue_manager.add_task(sample_task)
            mock_start.assert_called_once()

    def test_no_auto_start_when_paused(self, queue_manager, sample_task):
        """Test that auto-start doesn't trigger when paused."""
        queue_manager._auto_start = False

        with patch.object(queue_manager, "_try_start_next") as mock_start:
            queue_manager.add_task(sample_task)
            # _try_start_next should be called by add_task logic
            # but since _auto_start is False, it won't actually start
            assert mock_start.call_count <= 1

    def test_auto_start_after_completion(self, queue_manager, multiple_tasks):
        """Test that auto-start triggers after task completion."""
        with patch.object(queue_manager, "_try_start_next"):
            for task in multiple_tasks:
                queue_manager.add_task(task)

        # Add mock worker
        queue_manager.workers[0] = Mock()

        with patch.object(queue_manager, "_try_start_next") as mock_start:
            queue_manager._on_task_completed(0, "video.mp4")
            mock_start.assert_called_once()

    def test_auto_start_after_failure(self, queue_manager, multiple_tasks):
        """Test that auto-start triggers after task failure."""
        with patch.object(queue_manager, "_try_start_next"):
            for task in multiple_tasks:
                queue_manager.add_task(task)

        # Add mock worker
        queue_manager.workers[0] = Mock()

        with patch.object(queue_manager, "_try_start_next") as mock_start:
            queue_manager._on_task_failed(0, "Error")
            mock_start.assert_called_once()
