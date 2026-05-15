"""
Queue manager for handling multiple downloads.

This module manages the download queue and coordinates multiple download workers.
"""

from PySide6.QtCore import QObject, Signal

from ..models.download_queue import DownloadQueue
from ..models.download_task import DownloadTask, TaskStatus
from ..utils.logger import get_logger
from .download_worker import DownloadWorker
from .format_handler import FormatHandler

logger = get_logger()


class QueueManager(QObject):
    """
    Manages download queue and worker threads.

    Coordinates multiple download workers and ensures
    max_concurrent limit is respected.

    Signals:
        queue_updated: Emitted when queue changes
        task_started: Emitted when a task starts (task_index)
        task_completed: Emitted when a task completes (task_index, filename)
        task_failed: Emitted when a task fails (task_index, error)
        all_completed: Emitted when all tasks are done
    """

    # Signals
    queue_updated = Signal()
    task_started = Signal(int, str)  # index, title
    task_completed = Signal(int, str)  # index, filename
    task_failed = Signal(int, str)  # index, error
    task_progress = Signal(int, dict)  # index, progress_data
    all_completed = Signal()

    def __init__(self, max_concurrent: int = 3, notification_manager=None):
        """
        Initialize queue manager.

        Args:
            max_concurrent: Maximum concurrent downloads
            notification_manager: Optional NotificationManager for desktop notifications (v1.7.0)
        """
        super().__init__()
        self.queue = DownloadQueue(max_concurrent=max_concurrent)
        self.workers: dict[int, DownloadWorker] = {}  # task_index -> worker
        self._auto_start = True  # Auto-start next task when one completes
        self.notification_manager = notification_manager  # v1.7.0
        logger.info(f"QueueManager initialized with max_concurrent={max_concurrent}")

    def add_task(self, task: DownloadTask) -> int:
        """
        Add task to queue.

        Args:
            task: DownloadTask to add

        Returns:
            Index of added task
        """
        self.queue.add_task(task)
        index = self.queue.get_queue_size() - 1
        logger.info(f"Task added to queue at index {index}: {task.url}")
        self.queue_updated.emit()

        # Auto-start if enabled and capacity available
        if self._auto_start:
            self._try_start_next()

        return index

    def remove_task(self, index: int) -> bool:
        """
        Remove task from queue.

        Args:
            index: Task index

        Returns:
            True if removed successfully
        """
        task = self.queue.get_task(index)
        if not task:
            return False

        # Check if task is currently downloading
        if task.is_active() and index in self.workers:
            logger.warning(f"Cannot remove active task at index {index}")
            return False

        success = self.queue.remove_task_by_index(index)
        if success:
            logger.info(f"Task removed from queue at index {index}")
            self.queue_updated.emit()

        return success

    def move_task_up(self, index: int) -> bool:
        """
        Move task up in queue.

        Args:
            index: Current task index

        Returns:
            True if moved successfully
        """
        success = self.queue.move_task_up(index)
        if success:
            logger.debug(f"Task moved up: {index} -> {index - 1}")
            self.queue_updated.emit()
        return success

    def move_task_down(self, index: int) -> bool:
        """
        Move task down in queue.

        Args:
            index: Current task index

        Returns:
            True if moved successfully
        """
        success = self.queue.move_task_down(index)
        if success:
            logger.debug(f"Task moved down: {index} -> {index + 1}")
            self.queue_updated.emit()
        return success

    def start_queue(self) -> None:
        """Start processing the queue."""
        logger.info("Starting queue processing")
        self._try_start_next()

    def pause_queue(self) -> None:
        """Pause queue processing (disable auto-start)."""
        logger.info("Queue paused (auto-start disabled)")
        self._auto_start = False

    def resume_queue(self) -> None:
        """Resume queue processing (enable auto-start)."""
        logger.info("Queue resumed (auto-start enabled)")
        self._auto_start = True
        self._try_start_next()

    def stop_all(self) -> None:
        """Stop all active downloads."""
        logger.info("Stopping all active downloads")
        for _index, worker in list(self.workers.items()):
            worker.cancel()
        self.workers.clear()

    def clear_completed(self) -> int:
        """
        Remove completed tasks from queue.

        Returns:
            Number of tasks cleared
        """
        count = self.queue.clear_completed()
        if count > 0:
            logger.info(f"Cleared {count} completed tasks")
            self.queue_updated.emit()
        return count

    def clear_failed(self) -> int:
        """
        Remove failed tasks from queue.

        Returns:
            Number of tasks cleared
        """
        count = self.queue.clear_failed()
        if count > 0:
            logger.info(f"Cleared {count} failed tasks")
            self.queue_updated.emit()
        return count

    def get_queue_statistics(self) -> dict:
        """
        Get queue statistics.

        Returns:
            Dictionary with queue stats
        """
        return self.queue.get_statistics()

    def get_all_tasks(self):
        """Get all tasks in queue."""
        return self.queue.get_all_tasks()

    def is_duplicate_task(self, url: str, quality: str, audio_only: bool) -> bool:
        """
        Check if an identical task is already in queue.

        This prevents accidental duplicate downloads of the same video with
        the same settings, while still allowing:
        - Same URL with different quality (e.g., 1080p vs 720p)
        - Same URL with different format (video vs audio-only)

        Args:
            url: Video URL
            quality: Quality setting (e.g., "Best", "1080p", "720p", "Audio Only (MP3)")
            audio_only: Whether this is an audio-only download

        Returns:
            True if identical task exists in queue (pending or downloading)
        """
        for task in self.queue.get_all_tasks():
            # Only check pending and downloading tasks
            if task.status not in [TaskStatus.PENDING, TaskStatus.DOWNLOADING]:
                continue

            # Check if URL matches
            if task.url != url:
                continue

            # Check if quality matches
            task_quality = getattr(task, "quality", None)
            if task_quality != quality:
                continue

            # Check if audio_only matches
            task_audio_only = getattr(task, "audio_only", False)
            if task_audio_only != audio_only:
                continue

            # Found an identical task!
            logger.debug(f"Duplicate task found: {url} with quality={quality}, audio_only={audio_only}")
            return True

        return False

    def _has_conflicting_download(self, pending_task: DownloadTask) -> bool:
        """
        Check if a running download would conflict with this pending task.

        A conflict occurs when two tasks download the same URL with the same
        yt-dlp format string (meaning they'd write to identical temp files).
        The task is deferred — it will auto-start once the conflicting
        download finishes.

        Args:
            pending_task: Task to check against running workers

        Returns:
            True if a running task would produce conflicting temp files
        """
        pending_format = FormatHandler.get_format_string(pending_task.quality)
        pending_audio_only = getattr(pending_task, "audio_only", False)

        for worker in self.workers.values():
            running_task = worker.task
            if running_task.url != pending_task.url:
                continue
            running_format = FormatHandler.get_format_string(running_task.quality)
            running_audio_only = getattr(running_task, "audio_only", False)
            if running_format == pending_format and running_audio_only == pending_audio_only:
                return True

        return False

    def _try_start_next(self) -> None:
        """Try to start next pending task if capacity available."""
        if not self.queue.can_start_new_download():
            logger.debug("Max concurrent downloads reached, waiting...")
            return

        # Iterate pending tasks in order; skip any that conflict with a
        # running download (same URL + same format → same temp files).
        # Skipped tasks stay PENDING and will be retried automatically
        # when a worker finishes and calls _try_start_next() again.
        next_task = None
        task_index = None
        for i, task in enumerate(self.queue.get_all_tasks()):
            if task.status != TaskStatus.PENDING:
                continue
            if self._has_conflicting_download(task):
                logger.info(
                    f"Deferring task {i} ({task.url[:60]}) — "
                    f"same URL+format already downloading, will auto-start when ready"
                )
                continue
            next_task = task
            task_index = i
            break

        if next_task is None:
            if len(self.workers) == 0:
                logger.info("All tasks completed")
                self.all_completed.emit()
            return

        self._start_task(task_index, next_task)

    def _start_task(self, index: int, task: DownloadTask) -> None:
        """
        Start downloading a task.

        Args:
            index: Task index in queue
            task: DownloadTask to download
        """
        logger.info(f"Starting task {index}: {task.url}")

        # Create worker
        worker = DownloadWorker(task)

        # Connect signals
        worker.download_started.connect(lambda title: self._on_task_started(index, title))
        worker.download_completed.connect(lambda filename: self._on_task_completed(index, filename))
        worker.download_failed.connect(lambda error: self._on_task_failed(index, error))
        worker.progress_updated.connect(lambda data: self._on_task_progress(index, data))

        # Store worker and start
        self.workers[index] = worker
        worker.start()

    def _on_task_started(self, index: int, title: str) -> None:
        """Handle task started."""
        logger.info(f"Task {index} started: {title}")
        self.task_started.emit(index, title)
        self.queue_updated.emit()

    def _on_task_completed(self, index: int, filename: str) -> None:
        """Handle task completed."""
        logger.info(f"Task {index} completed: {filename}")

        # Send desktop notification (v1.7.0)
        if self.notification_manager:
            task = self.queue.get_task(index)
            if task:
                file_size = task.get_file_size_str() if hasattr(task, "get_file_size_str") else ""
                self.notification_manager.notify_download_complete(filename, file_size)

        # Remove worker
        if index in self.workers:
            del self.workers[index]

        self.task_completed.emit(index, filename)
        self.queue_updated.emit()

        # Try to start next task
        if self._auto_start:
            self._try_start_next()

    def _on_task_failed(self, index: int, error: str) -> None:
        """Handle task failed."""
        logger.error(f"Task {index} failed: {error}")

        # Send desktop notification (v1.7.0)
        if self.notification_manager:
            task = self.queue.get_task(index)
            if task:
                title = task.url[:50] + "..." if len(task.url) > 50 else task.url
                self.notification_manager.notify_download_error(title, error)

        # Remove worker
        if index in self.workers:
            del self.workers[index]

        self.task_failed.emit(index, error)
        self.queue_updated.emit()

        # Try to start next task
        if self._auto_start:
            self._try_start_next()

    def _on_task_progress(self, index: int, progress_data: dict) -> None:
        """Handle task progress update."""
        self.task_progress.emit(index, progress_data)

    def set_max_concurrent(self, max_concurrent: int) -> None:
        """
        Set maximum concurrent downloads.

        Args:
            max_concurrent: New max concurrent value
        """
        logger.info(f"Max concurrent downloads changed: {self.queue.max_concurrent} -> {max_concurrent}")
        self.queue.max_concurrent = max_concurrent

        # Try to start more tasks if limit increased
        if self._auto_start:
            self._try_start_next()
