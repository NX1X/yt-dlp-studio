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
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from ..models.download_queue import DownloadQueue
from ..models.download_task import DownloadTask, TaskStatus
from ..utils.error_handler import ErrorCategory, ErrorHandler
from ..utils.logger import get_logger
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

    Persistence:
        Pass ``persist_path`` to keep the queue across restarts. Nothing is
        written until ``load_queue()`` has run, so an empty queue at startup
        can never overwrite a saved one. Without ``persist_path`` the queue
        lives in memory only (this is what the tests use by default).
    """

    # Signals
    queue_updated = Signal()
    task_started = Signal(int, str)  # index, title
    task_completed = Signal(int, str)  # index, filename
    task_failed = Signal(int, str)  # index, error
    task_progress = Signal(int, dict)  # index, progress_data
    all_completed = Signal()

    # Queue file name inside APP_DATA_DIR (same folder as the history file)
    QUEUE_FILE = "download_queue.json"
    # Format version of the queue file. Bump it and add a migration when
    # the format changes; an unknown version is never loaded.
    QUEUE_FILE_VERSION = 1
    # Automatic retries allowed per task (network errors only)
    MAX_AUTO_RETRIES = 1
    # Delay before an automatic retry starts, in milliseconds
    AUTO_RETRY_DELAY_MS = 5000

    def __init__(self, max_concurrent: int = 3, notification_manager=None, persist_path: Path | None = None):
        """
        Initialize queue manager.

        Args:
            max_concurrent: Maximum concurrent downloads
            notification_manager: Optional NotificationManager for desktop notifications (v1.7.0)
            persist_path: Optional path of the queue file. None keeps the queue in memory only.
        """
        super().__init__()
        self.queue = DownloadQueue(max_concurrent=max_concurrent)
        self.workers: dict[int, DownloadWorker] = {}  # task_index -> worker
        self._auto_start = True  # Auto-start next task when one completes
        self.notification_manager = notification_manager  # v1.7.0
        self.persist_path = Path(persist_path) if persist_path is not None else None
        self._persistence_enabled = False  # set by load_queue(), cleared by shutdown()
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
        """Stop all active downloads."""
        logger.info("Stopping all active downloads")
        for _index, worker in self.workers.items():
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

    def _fill_slots(self) -> None:
        """
        Start pending tasks until every free download slot is used.

        ``_try_start_next`` starts at most one task per call. Restoring a
        queue or retrying several failed tasks can free more than one slot
        at once, so call it until it stops starting new workers.
        """
        while True:
            before = len(self.workers)
            self._try_start_next()
            after = len(self.workers)
            if after <= before or after >= self.queue.max_concurrent:
                break

    def _try_start_next(self) -> None:
        """Try to start next pending task if capacity available."""
        # A worker sets its task to DOWNLOADING from its own thread, a moment
        # after start(). Count the workers too, so that several calls in a
        # row cannot start more than max_concurrent downloads.
        if len(self.workers) >= self.queue.max_concurrent:
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
        # Pass the task object too: the index can point at another task after
        # a reorder, and auto-retry must act on the task that really failed.
        worker.download_failed.connect(lambda error: self._on_task_failed(index, error, task))
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

    def _on_task_failed(self, index: int, error: str, task: DownloadTask | None = None) -> None:
        """
        Handle task failed (also called for a cancelled task).

        Args:
            index: Task index when the task started
            error: Error message from the worker
            task: The task that failed. If None, the task at ``index`` is used.
        """
        logger.error(f"Task {index} failed: {error}")

        # Remove worker (keep it here to read the detailed error below)
        worker = self.workers.pop(index, None)

        if task is None:
            task = self.queue.get_task(index)

        # The worker reports a short "Download failed"; the yt-dlp reason is
        # kept on its wrapper. Use both to decide on an automatic retry.
        detail = getattr(getattr(worker, "wrapper", None), "_last_error", None)
        will_retry = task is not None and self._should_auto_retry(task, error, detail)

        # Send desktop notification (v1.7.0). Skip it when an automatic retry
        # follows; the user hears about the final result instead.
        if self.notification_manager and task and not will_retry:
            title = task.url[:50] + "..." if len(task.url) > 50 else task.url
            self.notification_manager.notify_download_error(title, error)

        if will_retry:
            self._schedule_auto_retry(task)

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

    def shutdown(self) -> None:
        """
        Save the queue one last time and stop saving.

        Call on clean shutdown. Running downloads are not cancelled here;
        they are saved as in-progress and continue as pending on the next
        start. Later signals from those workers do not overwrite the file.
        """
        if self._persistence_enabled:
            self.save_queue()
        self._persistence_enabled = False

    def _on_queue_changed(self) -> None:
        """Save after every queue change (not on progress ticks)."""
        self._autosave()

    def _autosave(self) -> None:
        """Save if persistence is on."""
        if self._persistence_enabled:
            self.save_queue()

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
