"""
Queue manager for handling multiple downloads.

This module manages the download queue and coordinates multiple download workers.

It also keeps the queue across restarts (a small JSON file next to the
history file) and retries failed tasks: on request from the user, and once
automatically for network errors.
"""

import contextlib
import json
import os
import shutil
import tempfile
import time
from functools import partial
from pathlib import Path
from urllib.parse import urlparse

from PySide6.QtCore import QObject, Qt, QTimer, Signal

from ..models.download_queue import DownloadQueue
from ..models.download_task import DownloadTask, TaskStatus
from ..utils.error_handler import ErrorCategory, ErrorHandler
from ..utils.logger import get_logger
from ..utils.translations import tr
from .download_worker import DownloadWorker
from .format_handler import FormatHandler

logger = get_logger()

# Statuses written to the queue file. Completed and cancelled tasks are done
# and are not restored.
_PERSISTED_STATUSES = (TaskStatus.PENDING, TaskStatus.DOWNLOADING, TaskStatus.ERROR)

# ErrorHandler.categorize_error checks the network keywords first, so a
# message such as "Unable to download webpage: ... not available in your
# country" is categorized as NETWORK. A retry cannot fix these reasons, so
# any of these phrases blocks the automatic retry.
_NON_RETRYABLE_HINTS = (
    # Geo-blocked
    "geo restrict",
    "geo-restrict",
    "geo block",
    "geo-block",
    "not available in your",
    "not available from your location",
    "blocked in your country",
    # Private or login required
    "private video",
    "video is private",
    "sign in",
    "login required",
    "members only",
    "members-only",
    # Copyright
    "copyright",
    "dmca",
    "removed due to",
    # Invalid or unsupported URL
    "unsupported url",
    "invalid url",
    "not a valid url",
    # Removed video
    "video unavailable",
    "this video is unavailable",
    "video has been removed",
)


def _platform_of(url: str) -> str:
    """Site name for history, from the URL host ("youtube.com" for www.youtube.com)."""
    try:
        host = (urlparse(url or "").hostname or "").lower()
    except ValueError:
        return ""
    for prefix in ("www.", "m."):
        if host.startswith(prefix):
            host = host[len(prefix) :]
    return host


def is_auto_retryable(*messages: str | None) -> bool:
    """
    Decide if a failure may get one automatic retry.

    Only network errors qualify (``ErrorCategory.NETWORK``). A message that
    also names a geo-block, private video, copyright claim or invalid URL
    never qualifies.

    Args:
        messages: Error texts for the same failure (for example the short
            worker message and the detailed yt-dlp message). None is skipped.

    Returns:
        True if at least one message is a network error and none names a
        reason that a retry cannot fix
    """
    texts = [m for m in messages if isinstance(m, str) and m.strip()]
    if not texts:
        return False
    for text in texts:
        lowered = text.lower()
        if any(hint in lowered for hint in _NON_RETRYABLE_HINTS):
            return False
    return any(ErrorHandler.categorize_error(text) == ErrorCategory.NETWORK for text in texts)


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

    The int in these signals is the task's index at the moment of the
    signal. It is -1 if the task is no longer in the queue.

    Workers:
        Workers are keyed by task identity (``id(task)``), never by queue
        index, because indexes shift on remove, clear and reorder. A worker
        stays referenced until its QThread ``finished`` signal, so a running
        thread is never garbage collected:

        - ``workers``: running downloads. They use a download slot.
        - ``_stopping``: cancelled by ``stop_all`` and still winding down.
          They keep their slot until ``finished``, so a stop cannot push
          the number of running threads over ``max_concurrent``.
        - ``_finishing``: reported their result and are returning from
          ``run()``. They no longer use a slot.

        All worker signals use explicit ``Qt.QueuedConnection`` to bound
        methods of this object, so every slot runs on the GUI thread.

    Persistence:
        Pass ``persist_path`` to keep the queue across restarts. Nothing is
        written until ``load_queue()`` has run, so an empty queue at startup
        can never overwrite a saved one. Without ``persist_path`` the queue
        lives in memory only (this is what the tests use by default).
        Changes are saved after a short delay (``SAVE_DELAY_MS``), so a
        burst of changes, such as adding a playlist, writes the file once.
    """

    # Signals
    queue_updated = Signal()
    task_started = Signal(int, str)  # index, title
    task_completed = Signal(int, str)  # index, filename
    task_failed = Signal(int, str)  # index, error
    task_progress = Signal(int, dict)  # index, progress_data
    all_completed = Signal()
    history_recorded = Signal()  # a finished download was added to history

    # Queue file name inside APP_DATA_DIR (same folder as the history file)
    QUEUE_FILE = "download_queue.json"
    # Format version of the queue file. Bump it and add a migration when
    # the format changes; an unknown version is never loaded.
    QUEUE_FILE_VERSION = 1
    # Automatic retries allowed per task (network errors only)
    MAX_AUTO_RETRIES = 1
    # Delay before an automatic retry starts, in milliseconds
    AUTO_RETRY_DELAY_MS = 5000
    # Delay between a queue change and the save, in milliseconds. Changes
    # inside this window are written together.
    SAVE_DELAY_MS = 250
    # Total time shutdown() waits for running workers to stop, in milliseconds
    SHUTDOWN_WAIT_MS = 4000

    def __init__(
        self,
        max_concurrent: int = 3,
        notification_manager=None,
        persist_path: Path | None = None,
        history_manager=None,
    ):
        """
        Initialize queue manager.

        Args:
            max_concurrent: Maximum concurrent downloads
            notification_manager: Optional NotificationManager for desktop notifications (v1.7.0)
            persist_path: Optional path of the queue file. None keeps the queue in memory only.
            history_manager: Optional HistoryManager; finished downloads are recorded there.
        """
        super().__init__()
        self.queue = DownloadQueue(max_concurrent=max_concurrent)
        # id(task) -> worker for running downloads. The worker holds the
        # task, so the id cannot be reused while the entry exists.
        self.workers: dict[int, DownloadWorker] = {}
        # id(worker) -> worker, kept until QThread.finished (see class doc)
        self._stopping: dict[int, DownloadWorker] = {}
        self._finishing: dict[int, DownloadWorker] = {}
        self._shutting_down = False
        self._auto_start = True  # Auto-start next task when one completes
        self.notification_manager = notification_manager  # v1.7.0
        self.history_manager = history_manager
        self.persist_path = Path(persist_path) if persist_path is not None else None
        self._persistence_enabled = False  # set by load_queue(), cleared by shutdown()
        self._save_pending = False
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(self.SAVE_DELAY_MS)
        self._save_timer.timeout.connect(self.flush_save)
        self.auto_retry_delay_ms = self.AUTO_RETRY_DELAY_MS
        # Tasks waiting for their automatic retry, keyed by id(). The value
        # keeps a reference so the id cannot be reused while it waits.
        self._pending_auto_retries: dict[int, DownloadTask] = {}
        # Every change to the queue emits queue_updated, so one connection
        # covers add, remove, reorder, clear, retry and status changes.
        self.queue_updated.connect(self._on_queue_changed)
        logger.info(f"QueueManager initialized with max_concurrent={max_concurrent}")

    @property
    def is_paused(self) -> bool:
        """True if the queue does not start tasks on its own."""
        return not self._auto_start

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
        if task.is_active() and self.get_worker(task) is not None:
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
        self._fill_slots()

    def pause_queue(self) -> None:
        """Pause queue processing (disable auto-start)."""
        logger.info("Queue paused (auto-start disabled)")
        self._auto_start = False
        self._autosave()

    def resume_queue(self) -> None:
        """Resume queue processing (enable auto-start)."""
        logger.info("Queue resumed (auto-start enabled)")
        self._auto_start = True
        self._autosave()
        self._fill_slots()

    def stop_all(self) -> None:
        """
        Stop all active downloads.

        Each worker is cancelled and moved to ``_stopping``. It stays
        referenced, and keeps its download slot, until its thread emits
        ``finished``. Pending tasks then start as before, unless paused.
        """
        logger.info("Stopping all active downloads")
        for worker in list(self.workers.values()):
            worker.cancel()
            self._stopping[id(worker)] = worker
        self.workers.clear()

    def get_worker(self, task: DownloadTask) -> DownloadWorker | None:
        """
        Get the running worker of a task.

        Args:
            task: Task in the queue

        Returns:
            The worker, or None if the task is not downloading
        """
        return self.workers.get(id(task))

    def cancel_task(self, index: int) -> bool:
        """
        Cancel one task (user action).

        A downloading task is cancelled through its worker; the worker then
        reports the cancel and frees its slot. A pending task is removed.

        Args:
            index: Task index

        Returns:
            True if a cancel was requested or the task was removed
        """
        task = self.queue.get_task(index)
        if task is None:
            return False
        worker = self.get_worker(task)
        if worker is not None:
            worker.cancel()
            logger.info(f"Cancel requested for downloading task at index {index}")
            return True
        if task.status == TaskStatus.PENDING:
            return self.remove_task(index)
        return False

    def _slots_in_use(self) -> int:
        """Running downloads plus cancelled ones that are still winding down."""
        return len(self.workers) + len(self._stopping)

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
        The task is deferred: it will auto-start once the conflicting
        download finishes.

        Args:
            pending_task: Task to check against running workers

        Returns:
            True if a running task would produce conflicting temp files
        """
        pending_format = FormatHandler.get_format_string(pending_task.quality)
        pending_audio_only = getattr(pending_task, "audio_only", False)

        # Cancelled workers still winding down may still write their temp
        # files, so they count as running here too.
        for worker in [*self.workers.values(), *self._stopping.values()]:
            running_task = worker.task
            if running_task.url != pending_task.url:
                continue
            running_format = FormatHandler.get_format_string(running_task.quality)
            running_audio_only = getattr(running_task, "audio_only", False)
            if running_format == pending_format and running_audio_only == pending_audio_only:
                return True

        return False

    def _fill_slots(self) -> None:
        """
        Start pending tasks until every free download slot is used.

        ``_try_start_next`` starts at most one task per call. Restoring a
        queue or retrying several failed tasks can free more than one slot
        at once, so call it until it stops starting new workers.
        """
        while not self._shutting_down:
            before = len(self.workers)
            self._try_start_next()
            if len(self.workers) <= before or self._slots_in_use() >= self.queue.max_concurrent:
                break

    def _try_start_next(self) -> None:
        """Try to start next pending task if capacity available."""
        if self._shutting_down:
            return
        # A worker sets its task to DOWNLOADING from its own thread, a moment
        # after start(). Count the workers too, so that several calls in a
        # row cannot start more than max_concurrent downloads.
        if self._slots_in_use() >= self.queue.max_concurrent:
            logger.debug("Max concurrent downloads reached, waiting...")
            return
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
            # A task stays PENDING until its worker thread runs. Never
            # start a second worker for a task that already has one.
            if self.get_worker(task) is not None:
                continue
            if self._has_conflicting_download(task):
                logger.info(
                    f"Deferring task {i} ({task.url[:60]}) - "
                    f"same URL+format already downloading, will auto-start when ready"
                )
                continue
            next_task = task
            task_index = i
            break

        if next_task is None:
            if not self.workers and not self._stopping:
                logger.info("All tasks completed")
                self.all_completed.emit()
            return

        self._start_task(task_index, next_task)

    def _start_task(self, index: int, task: DownloadTask) -> None:
        """
        Start downloading a task.

        Args:
            index: Task index in queue (for the log only)
            task: DownloadTask to download
        """
        logger.info(f"Starting task {index}: {task.url}")

        # Create worker
        worker = DownloadWorker(task)

        # Bound methods of this QObject with an explicit queued connection:
        # the worker emits from its own thread, and every slot must run on
        # the GUI thread. The worker is passed along, not the queue index,
        # because the index can change while the download runs.
        queued = Qt.ConnectionType.QueuedConnection
        worker.download_started.connect(partial(self._on_worker_started, worker), queued)
        worker.download_completed.connect(partial(self._on_worker_completed, worker), queued)
        worker.download_failed.connect(partial(self._on_worker_failed, worker), queued)
        worker.progress_updated.connect(partial(self._on_worker_progress, worker), queued)
        worker.finished.connect(partial(self._on_worker_finished, worker), queued)

        # Store worker and start
        self.workers[id(task)] = worker
        worker.start()

    def _index_of(self, task: DownloadTask | None) -> int:
        """Current queue index of a task, or -1 if it is not in the queue."""
        if task is None:
            return -1
        index = self.queue.index_of(task)
        return -1 if index is None else index

    def _release_worker(self, worker: DownloadWorker) -> None:
        """
        Free the download slot of a worker that reported its result.

        The worker stays referenced in ``_finishing`` until its thread
        emits ``finished``. A worker in ``_stopping`` stays there.
        """
        key = id(worker.task)
        if self.workers.get(key) is worker:
            del self.workers[key]
            self._finishing[id(worker)] = worker

    def _on_worker_started(self, worker: DownloadWorker, title: str) -> None:
        """Handle task started."""
        index = self._index_of(worker.task)
        logger.info(f"Task {index} started: {title}")
        self.task_started.emit(index, title)
        self.queue_updated.emit()

    def record_history(self, task: DownloadTask, status: str, error_message: str = "") -> None:
        """Add a finished download to the download history (GUI thread only).

        Called for queue downloads here, and for single downloads by the
        Download tab, so both end up in the History tab. A failure that is
        about to be retried automatically is not recorded; its final result
        is. Never raises: history is a convenience, not part of the download.
        """
        if self.history_manager is None:
            return
        try:
            self.history_manager.add_download(
                task, status, error_message=error_message, platform=_platform_of(task.url)
            )
        except Exception:
            logger.exception("Could not record the download in history")
            return
        self.history_recorded.emit()

    def _on_worker_completed(self, worker: DownloadWorker, filename: str) -> None:
        """Handle task completed."""
        task = worker.task
        index = self._index_of(task)
        logger.info(f"Task {index} completed: {filename}")

        # Send desktop notification (v1.7.0)
        if self.notification_manager:
            file_size = task.get_file_size_str() if hasattr(task, "get_file_size_str") else ""
            self.notification_manager.notify_download_complete(filename, file_size)

        self.record_history(task, "completed")
        self._release_worker(worker)

        self.task_completed.emit(index, filename)
        self.queue_updated.emit()

        # Try to start next task
        if self._auto_start:
            self._try_start_next()

    def _on_worker_failed(self, worker: DownloadWorker, error: str) -> None:
        """
        Handle task failed (also called for a cancelled task).

        Args:
            worker: The worker that failed
            error: Error message from the worker
        """
        task = worker.task
        index = self._index_of(task)
        logger.error(f"Task {index} failed: {error}")

        self._release_worker(worker)

        # The worker reports a short "Download failed"; the yt-dlp reason is
        # kept on its wrapper. Use both to decide on an automatic retry.
        detail = getattr(getattr(worker, "wrapper", None), "last_error", None)
        will_retry = not self._shutting_down and self._should_auto_retry(task, error, detail)

        # Send desktop notification (v1.7.0). Skip it when an automatic retry
        # follows; the user hears about the final result instead. Also skip
        # it for the cancels that shutdown() causes.
        if self.notification_manager and not will_retry and not self._shutting_down:
            title = task.url[:50] + "..." if len(task.url) > 50 else task.url
            # The worker's own "Download failed" and "Download cancelled" are
            # English: send a translated reason or the yt-dlp reason instead.
            if task.status == TaskStatus.CANCELLED:
                reason = tr("status_cancelled")
            else:
                reason = detail or ""
            self.notification_manager.notify_download_error(title, reason)

        if not will_retry and not self._shutting_down:
            status = "cancelled" if task.status == TaskStatus.CANCELLED else "failed"
            self.record_history(task, status, error_message="" if status == "cancelled" else (detail or error))

        if will_retry:
            self._schedule_auto_retry(task)

        self.task_failed.emit(index, error)
        self.queue_updated.emit()

        # Try to start next task
        if self._auto_start:
            self._try_start_next()

    def _on_worker_progress(self, worker: DownloadWorker, progress_data: dict) -> None:
        """Handle task progress update."""
        index = self._index_of(worker.task)
        if index >= 0:
            self.task_progress.emit(index, progress_data)

    def _on_worker_finished(self, worker: DownloadWorker) -> None:
        """
        Drop the last reference to a worker whose thread has ended.

        A cancelled worker from ``stop_all`` frees its download slot only
        here, so pending tasks may start now.
        """
        freed_slot = self._stopping.pop(id(worker), None) is not None
        self._finishing.pop(id(worker), None)

        task = worker.task
        if self.workers.get(id(task)) is worker:
            # The thread ended without reporting a result. Should not
            # happen (run() catches every exception), but never leave a
            # task stuck in DOWNLOADING with a dead worker.
            logger.warning(f"Worker ended without a result: {task.url[:60]}")
            del self.workers[id(task)]
            freed_slot = True
            if task.status in (TaskStatus.PENDING, TaskStatus.DOWNLOADING):
                task.fail("Download stopped unexpectedly")
                self.queue_updated.emit()

        worker.deleteLater()

        if freed_slot and self._auto_start:
            self._fill_slots()

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

    # ------------------------------------------------------------------
    # Retry
    # ------------------------------------------------------------------

    def retry_task(self, index: int) -> bool:
        """
        Retry one failed task (user action).

        The task goes back to PENDING and the queue picks it up. A paused
        queue keeps it PENDING until the user resumes. A manual retry also
        resets the automatic retry count, so the new attempt gets its own
        single network retry.

        Args:
            index: Task index

        Returns:
            True if the task was failed and is now pending
        """
        task = self.queue.get_task(index)
        if task is None or task.status != TaskStatus.ERROR:
            return False

        self._reset_for_manual_retry(task)
        logger.info(f"Retrying failed task at index {index}")
        self.queue_updated.emit()
        if self._auto_start:
            self._fill_slots()
        return True

    def retry_all_failed(self) -> int:
        """
        Retry every failed task (user action).

        Returns:
            Number of tasks set back to pending
        """
        failed = self.queue.get_failed_tasks()
        for task in failed:
            self._reset_for_manual_retry(task)

        if failed:
            logger.info(f"Retrying {len(failed)} failed tasks")
            self.queue_updated.emit()
            if self._auto_start:
                self._fill_slots()
        return len(failed)

    def _reset_for_manual_retry(self, task: DownloadTask) -> None:
        """Reset a failed task for a manual retry and cancel any pending auto-retry."""
        self._pending_auto_retries.pop(id(task), None)
        task.reset_for_retry()
        task.retry_count = 0

    def _should_auto_retry(self, task: DownloadTask, error: str, detail: str | None = None) -> bool:
        """
        Decide if a failed task gets an automatic retry.

        Args:
            task: The failed task
            error: Error message from the worker
            detail: Detailed yt-dlp error, if known

        Returns:
            True only for a real failure (not a cancel), a network-type
            error, and a task that has not used its automatic retry yet
        """
        if task.status != TaskStatus.ERROR:
            return False  # cancelled by the user, or already reset
        if task.retry_count >= self.MAX_AUTO_RETRIES:
            return False
        return is_auto_retryable(error, detail, task.error_message)

    def _schedule_auto_retry(self, task: DownloadTask) -> None:
        """Count the retry on the task and run it after a short delay."""
        task.retry_count += 1
        self._pending_auto_retries[id(task)] = task
        logger.info(
            f"Network error, automatic retry {task.retry_count}/{self.MAX_AUTO_RETRIES} "
            f"in {self.auto_retry_delay_ms} ms: {task.url[:60]}"
        )
        QTimer.singleShot(self.auto_retry_delay_ms, self, lambda: self._run_auto_retry(task))

    def _run_auto_retry(self, task: DownloadTask) -> None:
        """Set a task back to pending for its automatic retry, if still wanted."""
        if self._pending_auto_retries.pop(id(task), None) is None:
            return  # retried by hand meanwhile
        if self._shutting_down:
            return  # the app is closing; never start a download now
        if self.queue.index_of(task) is None or task.status != TaskStatus.ERROR:
            return  # removed or changed meanwhile

        task.reset_for_retry()
        self.queue_updated.emit()
        if self._auto_start:
            self._fill_slots()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """
        Build the queue file content.

        Returns:
            Dictionary with the format version, the paused state and the
            pending, in-progress and failed tasks in queue order
        """
        return {
            "version": self.QUEUE_FILE_VERSION,
            "paused": self.is_paused,
            "tasks": [task.to_dict() for task in self.queue.get_all_tasks() if task.status in _PERSISTED_STATUSES],
        }

    def save_queue(self) -> bool:
        """
        Write the queue file atomically.

        Writes a temp file in the same folder, then renames it over the
        old file with ``os.replace``. A crash during the write leaves the
        old file intact. Errors are logged, never raised.

        Returns:
            True if the file was written
        """
        if self.persist_path is None:
            return False
        try:
            text = json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
            _write_atomic(self.persist_path, text)
            logger.debug(f"Queue saved to {self.persist_path}")
            return True
        except (OSError, TypeError, ValueError):
            logger.exception("Failed to save queue")
            return False

    def load_queue(self) -> int:
        """
        Restore the queue from the queue file and turn on saving.

        - In-progress tasks become PENDING; yt-dlp continues them from
          their ``.part`` files.
        - A missing file means an empty queue.
        - An empty, unreadable, corrupt or unknown-version file never
          raises: it logs a warning, starts with an empty queue and keeps
          a copy as ``<name>.bad`` (if it had content).
        - The paused state is restored when at least one task is restored.
          A queue that was running starts its pending tasks now; a paused
          queue waits for the user.

        Returns:
            Number of tasks restored
        """
        try:
            restored, paused = self._read_queue_file()
        finally:
            # Saving starts only now, so the empty startup queue can never
            # overwrite the file before it was read.
            self._persistence_enabled = self.persist_path is not None

        if not restored:
            return 0

        for task in restored:
            self.queue.add_task(task)
        self._auto_start = not paused

        state = "paused" if paused else "running"
        logger.info(f"Queue restored: {len(restored)} tasks, queue {state}")
        self.queue_updated.emit()

        if self._auto_start and self.queue.get_pending_tasks():
            self._fill_slots()
        return len(restored)

    def shutdown(self, wait_ms: int | None = None) -> None:
        """
        Save the queue, then stop every download and wait for the threads.

        Call once on clean shutdown, on the GUI thread.

        1. No new download starts after this call (also not from a pending
           auto-retry timer).
        2. The queue is saved at once. Running downloads are saved as
           in-progress and continue as pending on the next start.
        3. Saving stops, so the cancels below cannot change the file.
        4. Every worker is cancelled, then waited for. The total wait is at
           most ``wait_ms`` (default ``SHUTDOWN_WAIT_MS``) for all workers
           together. A worker still running after that is logged.

        Args:
            wait_ms: Total time to wait for the workers, in milliseconds
        """
        self._shutting_down = True
        self._pending_auto_retries.clear()

        self.flush_save()
        self._persistence_enabled = False

        running = [*self.workers.values(), *self._stopping.values(), *self._finishing.values()]
        for worker in running:
            worker.cancel()

        budget_ms = self.SHUTDOWN_WAIT_MS if wait_ms is None else wait_ms
        deadline = time.monotonic() + budget_ms / 1000
        for worker in running:
            remaining_ms = max(0, int((deadline - time.monotonic()) * 1000))
            if not worker.wait(remaining_ms):
                logger.warning(f"Download worker did not stop within {budget_ms} ms: {worker.task.url[:60]}")

    def flush_save(self) -> bool:
        """
        Write a pending save now.

        Returns:
            True if the file was written
        """
        self._save_timer.stop()
        if not self._save_pending:
            return False
        self._save_pending = False
        if not self._persistence_enabled:
            return False
        return self.save_queue()

    def _on_queue_changed(self) -> None:
        """
        Schedule a save after a queue change (not on progress ticks).

        The single-shot timer restarts on every change, so a burst of
        changes (for example a playlist of many items) writes the file once.
        """
        if not self._persistence_enabled:
            return
        self._save_pending = True
        self._save_timer.start()

    def _autosave(self) -> None:
        """Save now, including any pending change (used for pause and resume)."""
        if not self._persistence_enabled:
            return
        self._save_pending = True
        self.flush_save()

    def _read_queue_file(self) -> tuple[list[DownloadTask], bool]:
        """
        Read and check the queue file.

        Returns:
            (restored tasks, paused). Empty list on any problem.
        """
        path = self.persist_path
        if path is None:
            return [], False

        try:
            raw = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.debug("No queue file found, starting with an empty queue")
            return [], False
        except (OSError, UnicodeDecodeError):
            logger.warning(f"Could not read queue file {path}, starting with an empty queue", exc_info=True)
            self._backup_bad_file()
            return [], False

        if not raw.strip():
            logger.warning(f"Queue file {path} is empty, starting with an empty queue")
            return [], False

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(f"Queue file {path} is not valid JSON, starting with an empty queue")
            self._backup_bad_file()
            return [], False

        if not isinstance(data, dict):
            logger.warning(f"Queue file {path} has an unexpected layout, starting with an empty queue")
            self._backup_bad_file()
            return [], False

        version = data.get("version")
        # type() check: True == 1 in Python, but a bool is not a version.
        if type(version) is not int or version != self.QUEUE_FILE_VERSION:
            logger.warning(
                f"Queue file {path} has unknown version {version!r} "
                f"(expected {self.QUEUE_FILE_VERSION}), starting with an empty queue"
            )
            self._backup_bad_file()
            return [], False

        entries = data.get("tasks", [])
        if not isinstance(entries, list):
            logger.warning(f"Queue file {path} has no valid task list, starting with an empty queue")
            self._backup_bad_file()
            return [], False

        paused = data.get("paused", False)
        if not isinstance(paused, bool):
            # Do not start downloads on our own when the file is unclear.
            logger.warning(f"Queue file {path} has an invalid paused value, treating the queue as paused")
            paused = True

        restored: list[DownloadTask] = []
        skipped = 0
        for entry in entries:
            try:
                task = DownloadTask.from_dict(entry)
            except (ValueError, TypeError):
                skipped += 1
                continue
            if task.status == TaskStatus.DOWNLOADING:
                # Interrupted by the shutdown: run it again. yt-dlp
                # continues from the .part file.
                task.reset_for_retry()
            elif task.status not in _PERSISTED_STATUSES:
                continue  # completed or cancelled: nothing to restore
            restored.append(task)

        if skipped:
            logger.warning(f"Skipped {skipped} invalid task entries in queue file {path}")
            self._backup_bad_file()

        return restored, paused

    def _backup_bad_file(self) -> None:
        """Keep a copy of a bad queue file as <name>.bad so no data is lost silently."""
        if self.persist_path is None:
            return
        bad_path = self.persist_path.with_name(self.persist_path.name + ".bad")
        try:
            shutil.copyfile(self.persist_path, bad_path)
            logger.warning(f"Kept a copy of the bad queue file at {bad_path}")
        except OSError:
            logger.warning(f"Could not keep a copy of the bad queue file at {bad_path}", exc_info=True)


def _write_atomic(path: Path, text: str) -> None:
    """
    Write text to path atomically.

    The temp file is in the same folder, so ``os.replace`` is a rename on
    the same file system and is atomic on Windows and Linux.

    Raises:
        OSError: If the write or the rename fails. The temp file is removed.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise
