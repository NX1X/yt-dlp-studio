"""
Download queue data model.

This module manages a queue of download tasks.
"""

from .download_task import DownloadTask, TaskStatus


class DownloadQueue:
    """
    Manages a queue of download tasks.

    Provides methods to add, remove, reorder, and manage download tasks.

    Example:
        >>> queue = DownloadQueue()
        >>> task = DownloadTask(url="...", output_directory="...", quality="Best Quality")
        >>> queue.add_task(task)
        >>> queue.get_next_pending()
    """

    def __init__(self, max_concurrent: int = 3):
        """
        Initialize download queue.

        Args:
            max_concurrent: Maximum number of concurrent downloads (default: 3)
        """
        self._tasks: list[DownloadTask] = []
        self.max_concurrent = max_concurrent

    def add_task(self, task: DownloadTask) -> None:
        """
        Add a task to the queue.

        Args:
            task: DownloadTask to add

        Example:
            >>> queue.add_task(task)
        """
        self._tasks.append(task)

    def remove_task(self, task: DownloadTask) -> bool:
        """
        Remove a task from the queue.

        Args:
            task: DownloadTask to remove

        Returns:
            True if removed, False if not found
        """
        try:
            self._tasks.remove(task)
            return True
        except ValueError:
            return False

    def remove_task_by_index(self, index: int) -> bool:
        """
        Remove a task by index.

        Args:
            index: Index of task to remove

        Returns:
            True if removed, False if index invalid
        """
        if 0 <= index < len(self._tasks):
            del self._tasks[index]
            return True
        return False

    def get_task(self, index: int) -> DownloadTask | None:
        """
        Get task by index.

        Args:
            index: Task index

        Returns:
            DownloadTask or None if invalid index
        """
        if 0 <= index < len(self._tasks):
            return self._tasks[index]
        return None

    def get_all_tasks(self) -> list[DownloadTask]:
        """
        Get all tasks in queue.

        Returns:
            List of all tasks
        """
        return self._tasks.copy()

    def get_next_pending(self) -> DownloadTask | None:
        """
        Get next pending task.

        Returns:
            Next pending task or None if none available
        """
        for task in self._tasks:
            if task.status == TaskStatus.PENDING:
                return task
        return None

    def get_active_tasks(self) -> list[DownloadTask]:
        """
        Get all currently downloading tasks.

        Returns:
            List of active tasks
        """
        return [task for task in self._tasks if task.status == TaskStatus.DOWNLOADING]

    def get_pending_tasks(self) -> list[DownloadTask]:
        """
        Get all pending tasks.

        Returns:
            List of pending tasks
        """
        return [task for task in self._tasks if task.status == TaskStatus.PENDING]

    def get_completed_tasks(self) -> list[DownloadTask]:
        """
        Get all completed tasks.

        Returns:
            List of completed tasks
        """
        return [task for task in self._tasks if task.status == TaskStatus.COMPLETED]

    def get_failed_tasks(self) -> list[DownloadTask]:
        """
        Get all failed tasks.

        Returns:
            List of failed tasks
        """
        return [task for task in self._tasks if task.status == TaskStatus.ERROR]

    def can_start_new_download(self) -> bool:
        """
        Check if a new download can be started.

        Returns:
            True if can start new download (under max_concurrent limit)
        """
        active_count = len(self.get_active_tasks())
        return active_count < self.max_concurrent

    def move_task_up(self, index: int) -> bool:
        """
        Move task up in queue (decrease index).

        Args:
            index: Current task index

        Returns:
            True if moved, False if already at top or invalid index
        """
        if index > 0 and index < len(self._tasks):
            self._tasks[index], self._tasks[index - 1] = self._tasks[index - 1], self._tasks[index]
            return True
        return False

    def move_task_down(self, index: int) -> bool:
        """
        Move task down in queue (increase index).

        Args:
            index: Current task index

        Returns:
            True if moved, False if already at bottom or invalid index
        """
        if index >= 0 and index < len(self._tasks) - 1:
            self._tasks[index], self._tasks[index + 1] = self._tasks[index + 1], self._tasks[index]
            return True
        return False

    def clear_completed(self) -> int:
        """
        Remove all completed tasks from queue.

        Returns:
            Number of tasks removed
        """
        completed = self.get_completed_tasks()
        for task in completed:
            self._tasks.remove(task)
        return len(completed)

    def clear_failed(self) -> int:
        """
        Remove all failed tasks from queue.

        Returns:
            Number of tasks removed
        """
        failed = self.get_failed_tasks()
        for task in failed:
            self._tasks.remove(task)
        return len(failed)

    def clear_all(self) -> None:
        """Clear all tasks from queue."""
        self._tasks.clear()

    def get_queue_size(self) -> int:
        """
        Get total number of tasks in queue.

        Returns:
            Total task count
        """
        return len(self._tasks)

    def get_statistics(self) -> dict:
        """
        Get queue statistics.

        Returns:
            Dictionary with queue stats:
                - total: Total tasks
                - pending: Pending count
                - active: Active count
                - completed: Completed count
                - failed: Failed count
        """
        return {
            "total": len(self._tasks),
            "pending": len(self.get_pending_tasks()),
            "active": len(self.get_active_tasks()),
            "completed": len(self.get_completed_tasks()),
            "failed": len(self.get_failed_tasks()),
        }

    def __len__(self) -> int:
        """Get queue size."""
        return len(self._tasks)

    def __repr__(self) -> str:
        """String representation for debugging."""
        stats = self.get_statistics()
        return (
            f"DownloadQueue(total={stats['total']}, "
            f"pending={stats['pending']}, "
            f"active={stats['active']}, "
            f"completed={stats['completed']}, "
            f"failed={stats['failed']})"
        )
