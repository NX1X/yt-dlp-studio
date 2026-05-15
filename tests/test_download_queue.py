"""
Tests for DownloadQueue model.

Tests queue operations, task management, and statistics.
"""

import pytest

from src.models.download_queue import DownloadQueue
from src.models.download_task import DownloadTask, TaskStatus


@pytest.fixture
def queue():
    """Create a download queue for testing."""
    return DownloadQueue(max_concurrent=3)


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


class TestDownloadQueueBasics:
    """Test basic queue operations."""

    def test_initialization(self, queue):
        """Test queue initialization."""
        assert queue.max_concurrent == 3
        assert queue.get_queue_size() == 0

    def test_add_task(self, queue, sample_task):
        """Test adding a task to queue."""
        queue.add_task(sample_task)
        assert queue.get_queue_size() == 1
        assert sample_task.status == TaskStatus.PENDING

    def test_add_multiple_tasks(self, queue, multiple_tasks):
        """Test adding multiple tasks."""
        for task in multiple_tasks:
            queue.add_task(task)
        assert queue.get_queue_size() == 5

    def test_get_all_tasks(self, queue, multiple_tasks):
        """Test retrieving all tasks."""
        for task in multiple_tasks:
            queue.add_task(task)
        all_tasks = queue.get_all_tasks()
        assert len(all_tasks) == 5
        assert all_tasks == multiple_tasks

    def test_get_task_by_index(self, queue, multiple_tasks):
        """Test getting task by index."""
        for task in multiple_tasks:
            queue.add_task(task)
        task = queue.get_task(2)
        assert task == multiple_tasks[2]

    def test_get_task_invalid_index(self, queue):
        """Test getting task with invalid index."""
        assert queue.get_task(0) is None
        assert queue.get_task(-1) is None
        assert queue.get_task(100) is None


class TestDownloadQueueRemoval:
    """Test task removal operations."""

    def test_remove_task(self, queue, sample_task):
        """Test removing a task."""
        queue.add_task(sample_task)
        assert queue.remove_task(sample_task) is True
        assert queue.get_queue_size() == 0

    def test_remove_task_not_in_queue(self, queue, sample_task):
        """Test removing a task not in queue."""
        other_task = DownloadTask(url="https://example.com/video", output_directory="/tmp", quality="720p")
        queue.add_task(sample_task)
        assert queue.remove_task(other_task) is False
        assert queue.get_queue_size() == 1

    def test_remove_task_by_index(self, queue, multiple_tasks):
        """Test removing task by index."""
        for task in multiple_tasks:
            queue.add_task(task)
        assert queue.remove_task_by_index(2) is True
        assert queue.get_queue_size() == 4
        assert multiple_tasks[2] not in queue.get_all_tasks()

    def test_remove_task_invalid_index(self, queue):
        """Test removing task with invalid index."""
        assert queue.remove_task_by_index(0) is False
        assert queue.remove_task_by_index(-1) is False
        assert queue.remove_task_by_index(100) is False

    def test_remove_active_task(self, queue, sample_task):
        """Test that active tasks can be removed from queue."""
        queue.add_task(sample_task)
        sample_task.status = TaskStatus.DOWNLOADING
        assert queue.remove_task(sample_task) is True
        assert queue.get_queue_size() == 0


class TestDownloadQueueOrdering:
    """Test task ordering and reordering."""

    def test_move_task_up(self, queue, multiple_tasks):
        """Test moving task up in queue."""
        for task in multiple_tasks:
            queue.add_task(task)

        # Move task at index 2 up
        assert queue.move_task_up(2) is True
        all_tasks = queue.get_all_tasks()
        assert all_tasks[1] == multiple_tasks[2]
        assert all_tasks[2] == multiple_tasks[1]

    def test_move_task_up_first(self, queue, multiple_tasks):
        """Test moving first task up (should fail)."""
        for task in multiple_tasks:
            queue.add_task(task)
        assert queue.move_task_up(0) is False

    def test_move_task_up_invalid_index(self, queue):
        """Test moving task up with invalid index."""
        assert queue.move_task_up(-1) is False
        assert queue.move_task_up(100) is False

    def test_move_task_down(self, queue, multiple_tasks):
        """Test moving task down in queue."""
        for task in multiple_tasks:
            queue.add_task(task)

        # Move task at index 2 down
        assert queue.move_task_down(2) is True
        all_tasks = queue.get_all_tasks()
        assert all_tasks[2] == multiple_tasks[3]
        assert all_tasks[3] == multiple_tasks[2]

    def test_move_task_down_last(self, queue, multiple_tasks):
        """Test moving last task down (should fail)."""
        for task in multiple_tasks:
            queue.add_task(task)
        assert queue.move_task_down(4) is False

    def test_move_task_down_invalid_index(self, queue):
        """Test moving task down with invalid index."""
        assert queue.move_task_down(-1) is False
        assert queue.move_task_down(100) is False

    def test_move_active_task(self, queue, multiple_tasks):
        """Test that active tasks can be moved in queue."""
        for task in multiple_tasks:
            queue.add_task(task)

        # Mark task as active
        multiple_tasks[2].status = TaskStatus.DOWNLOADING

        assert queue.move_task_up(2) is True
        assert queue.move_task_down(1) is True


class TestDownloadQueuePending:
    """Test pending task operations."""

    def test_get_next_pending(self, queue, multiple_tasks):
        """Test getting next pending task."""
        for task in multiple_tasks:
            queue.add_task(task)

        next_task = queue.get_next_pending()
        assert next_task == multiple_tasks[0]
        assert next_task.status == TaskStatus.PENDING

    def test_get_next_pending_skips_active(self, queue, multiple_tasks):
        """Test that next pending skips active tasks."""
        for task in multiple_tasks:
            queue.add_task(task)

        # Mark first two as active
        multiple_tasks[0].status = TaskStatus.DOWNLOADING
        multiple_tasks[1].status = TaskStatus.DOWNLOADING

        next_task = queue.get_next_pending()
        assert next_task == multiple_tasks[2]

    def test_get_next_pending_empty(self, queue):
        """Test getting next pending from empty queue."""
        assert queue.get_next_pending() is None

    def test_get_next_pending_all_active(self, queue, multiple_tasks):
        """Test getting next pending when all are active."""
        for task in multiple_tasks:
            task.status = TaskStatus.DOWNLOADING
            queue.add_task(task)

        assert queue.get_next_pending() is None


class TestDownloadQueueCapacity:
    """Test queue capacity and concurrent limits."""

    def test_can_start_new_download(self, queue):
        """Test checking if new download can start."""
        assert queue.can_start_new_download() is True

    def test_can_start_at_max_concurrent(self, queue, multiple_tasks):
        """Test capacity check at max concurrent limit."""
        # Add 3 tasks and mark them as downloading
        for i in range(3):
            task = multiple_tasks[i]
            task.status = TaskStatus.DOWNLOADING
            queue.add_task(task)

        # Should be at capacity
        assert queue.can_start_new_download() is False

    def test_can_start_below_max_concurrent(self, queue, multiple_tasks):
        """Test capacity check below max concurrent limit."""
        # Add 2 tasks and mark them as downloading
        for i in range(2):
            task = multiple_tasks[i]
            task.status = TaskStatus.DOWNLOADING
            queue.add_task(task)

        # Should have capacity
        assert queue.can_start_new_download() is True


class TestDownloadQueueClearing:
    """Test queue clearing operations."""

    def test_clear_completed(self, queue, multiple_tasks):
        """Test clearing completed tasks."""
        for i, task in enumerate(multiple_tasks):
            if i < 2:
                task.status = TaskStatus.COMPLETED
            queue.add_task(task)

        count = queue.clear_completed()
        assert count == 2
        assert queue.get_queue_size() == 3

    def test_clear_completed_none(self, queue, multiple_tasks):
        """Test clearing completed when none exist."""
        for task in multiple_tasks:
            queue.add_task(task)

        count = queue.clear_completed()
        assert count == 0
        assert queue.get_queue_size() == 5

    def test_clear_failed(self, queue, multiple_tasks):
        """Test clearing failed tasks."""
        for i, task in enumerate(multiple_tasks):
            if i < 3:
                task.status = TaskStatus.ERROR
            queue.add_task(task)

        count = queue.clear_failed()
        assert count == 3
        assert queue.get_queue_size() == 2

    def test_clear_failed_none(self, queue, multiple_tasks):
        """Test clearing failed when none exist."""
        for task in multiple_tasks:
            queue.add_task(task)

        count = queue.clear_failed()
        assert count == 0
        assert queue.get_queue_size() == 5


class TestDownloadQueueStatistics:
    """Test queue statistics."""

    def test_statistics_empty(self, queue):
        """Test statistics for empty queue."""
        stats = queue.get_statistics()
        assert stats["total"] == 0
        assert stats["pending"] == 0
        assert stats["active"] == 0
        assert stats["completed"] == 0
        assert stats["failed"] == 0

    def test_statistics_mixed(self, queue, multiple_tasks):
        """Test statistics with mixed task states."""
        # Task 0: pending
        queue.add_task(multiple_tasks[0])

        # Task 1-2: downloading
        multiple_tasks[1].status = TaskStatus.DOWNLOADING
        queue.add_task(multiple_tasks[1])
        multiple_tasks[2].status = TaskStatus.DOWNLOADING
        queue.add_task(multiple_tasks[2])

        # Task 3: completed
        multiple_tasks[3].status = TaskStatus.COMPLETED
        queue.add_task(multiple_tasks[3])

        # Task 4: failed
        multiple_tasks[4].status = TaskStatus.ERROR
        queue.add_task(multiple_tasks[4])

        stats = queue.get_statistics()
        assert stats["total"] == 5
        assert stats["pending"] == 1
        assert stats["active"] == 2
        assert stats["completed"] == 1
        assert stats["failed"] == 1

    def test_get_active_tasks_count(self, queue, multiple_tasks):
        """Test getting active download count via get_active_tasks."""
        # Mark 2 as downloading
        multiple_tasks[0].status = TaskStatus.DOWNLOADING
        multiple_tasks[1].status = TaskStatus.DOWNLOADING

        for task in multiple_tasks:
            queue.add_task(task)

        assert len(queue.get_active_tasks()) == 2


class TestDownloadQueueEdgeCases:
    """Test edge cases and error conditions."""

    def test_max_concurrent_zero(self):
        """Test queue with max_concurrent=0."""
        queue = DownloadQueue(max_concurrent=0)
        assert queue.can_start_new_download() is False

    def test_max_concurrent_negative(self):
        """Test queue with negative max_concurrent."""
        queue = DownloadQueue(max_concurrent=-1)
        # Should treat as 0
        assert queue.can_start_new_download() is False

    def test_add_duplicate_task(self, queue, sample_task):
        """Test adding same task twice."""
        queue.add_task(sample_task)
        queue.add_task(sample_task)
        # Should allow duplicates (same URL might be downloaded multiple times)
        assert queue.get_queue_size() == 2

    def test_operations_on_empty_queue(self, queue):
        """Test various operations on empty queue."""
        assert queue.get_next_pending() is None
        assert queue.get_task(0) is None
        assert queue.remove_task_by_index(0) is False
        assert queue.move_task_up(0) is False
        assert queue.move_task_down(0) is False
        assert queue.clear_completed() == 0
        assert queue.clear_failed() == 0
