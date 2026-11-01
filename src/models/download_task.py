"""
Download task data model.

This module defines the structure for a download task.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TaskStatus(Enum):
    """Download task status enumeration."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class DownloadTask:
    """
    Represents a single download task.

    This class holds all information about a download operation,
    including URL, status, progress, and output information.

    Attributes:
        url: Video URL to download
        output_directory: Directory to save the file
        quality: Selected quality option
        status: Current task status
        progress_percent: Download progress (0-100)
        download_speed: Current download speed in bytes/sec
        eta_seconds: Estimated time remaining in seconds
        file_size: Total file size in bytes
        downloaded_bytes: Bytes downloaded so far
        filename: Name of the downloaded file inside ``output_directory``
            (set when the download completes)
        title: Video title (set when yt-dlp reports it)
        error_message: Error message if status is ERROR
        created_at: Timestamp when task was created
        started_at: Timestamp when download started
        completed_at: Timestamp when download completed
    """

    url: str
    output_directory: str
    quality: str
    audio_only: bool = False  # Whether this is an audio-only download
    status: TaskStatus = TaskStatus.PENDING
    progress_percent: float = 0.0
    download_speed: float = 0.0
    eta_seconds: int = 0
    file_size: int = 0
    downloaded_bytes: int = 0
    filename: str = ""
    title: str = ""
    error_message: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    # v1.7.0 features
    download_thumbnail: bool = True
    download_subtitles: bool = False
    subtitle_languages: str = "en"
    speed_limit: int = 0  # KB/s (0 means unlimited)
    # v2.0.0 features
    video_container: str | None = None
    audio_format: str = "mp3"
    # v2.1.0 features - Advanced options
    selected_subtitles: list | None = None  # List of selected subtitle language codes
    download_metadata: bool = False  # Download metadata (comments, description, etc.)
    download_comments: bool = False  # Download comments to separate .txt file (v2.0.0)
    auto_number_duplicates: bool = True  # Automatically number duplicate files
    # Number of automatic retries already used. The queue manager reads this
    # so an automatic retry can never loop; a manual retry resets it.
    retry_count: int = 0

    def start(self) -> None:
        """Mark task as started."""
        self.status = TaskStatus.DOWNLOADING
        self.started_at = datetime.now()

    def complete(self, filename: str) -> None:
        """
        Mark task as completed.

        Args:
            filename: Name of the downloaded file inside ``output_directory``
        """
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.filename = filename
        self.progress_percent = 100.0

    def fail(self, error_message: str) -> None:
        """
        Mark task as failed.

        Args:
            error_message: Error description
        """
        self.status = TaskStatus.ERROR
        self.error_message = error_message
        self.completed_at = datetime.now()

    def cancel(self) -> None:
        """Mark task as cancelled."""
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.now()

    def reset_for_retry(self) -> None:
        """
        Put the task back to PENDING so the queue can run it again.

        Clears the error and all progress data. Does not touch
        ``retry_count``; the caller decides how a retry is counted.
        """
        self.status = TaskStatus.PENDING
        self.error_message = ""
        self.progress_percent = 0.0
        self.download_speed = 0.0
        self.eta_seconds = 0
        self.downloaded_bytes = 0
        self.started_at = None
        self.completed_at = None

    def to_dict(self) -> dict:
        """
        Serialize the task for the queue file.

        Only settings and state that matter after a restart are stored.
        Live progress data (speed, ETA, bytes) is not stored.

        Returns:
            JSON-safe dictionary
        """
        data = {name: getattr(self, name) for name in _PERSISTED_FIELDS}
        data["status"] = self.status.value
        data["created_at"] = self.created_at.isoformat()
        if self.selected_subtitles is not None:
            data["selected_subtitles"] = list(self.selected_subtitles)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "DownloadTask":
        """
        Build a task from a dictionary made by ``to_dict``.

        Unknown keys are ignored. Missing optional keys take their defaults.

        Args:
            data: Dictionary from the queue file

        Returns:
            New DownloadTask

        Raises:
            ValueError: If a required key is missing or a value has the wrong type
        """
        if not isinstance(data, dict):
            raise ValueError("task entry is not an object")

        kwargs = {}
        for name, expected in _PERSISTED_FIELDS.items():
            if name not in data:
                if name in _REQUIRED_FIELDS:
                    raise ValueError(f"task entry has no '{name}'")
                continue
            value = data[name]
            # bool is a subclass of int; do not accept True/False as a number.
            if expected is int and isinstance(value, bool):
                raise ValueError(f"task field '{name}' has the wrong type")
            if not isinstance(value, expected):
                raise ValueError(f"task field '{name}' has the wrong type")
            kwargs[name] = value

        for name in _REQUIRED_FIELDS:
            if not kwargs[name]:
                raise ValueError(f"task field '{name}' is empty")

        subtitles = kwargs.get("selected_subtitles")
        if subtitles is not None:
            if not all(isinstance(item, str) for item in subtitles):
                raise ValueError("task field 'selected_subtitles' must be a list of strings")
            kwargs["selected_subtitles"] = list(subtitles)

        if kwargs.get("retry_count", 0) < 0 or kwargs.get("speed_limit", 0) < 0:
            raise ValueError("task has a negative number")

        try:
            kwargs["status"] = TaskStatus(data.get("status", TaskStatus.PENDING.value))
        except ValueError as e:
            raise ValueError(f"task has an unknown status: {data.get('status')!r}") from e

        created_at = data.get("created_at")
        if created_at is not None:
            if not isinstance(created_at, str):
                raise ValueError("task field 'created_at' has the wrong type")
            kwargs["created_at"] = datetime.fromisoformat(created_at)

        return cls(**kwargs)

    def update_progress(
        self,
        progress_percent: float,
        download_speed: float = 0.0,
        eta_seconds: int = 0,
        downloaded_bytes: int = 0,
        file_size: int = 0,
    ) -> None:
        """
        Update task progress information.

        Args:
            progress_percent: Progress percentage (0-100)
            download_speed: Current speed in bytes/sec
            eta_seconds: Estimated time remaining
            downloaded_bytes: Bytes downloaded
            file_size: Total file size
        """
        self.progress_percent = min(progress_percent, 100.0)
        self.download_speed = download_speed
        self.eta_seconds = eta_seconds
        self.downloaded_bytes = downloaded_bytes
        if file_size > 0:
            self.file_size = file_size

    def output_path(self) -> str:
        """
        Full path of the downloaded file.

        Joins ``output_directory`` and ``filename``. User (``~``) and
        environment variables in the folder are expanded, the same way
        yt-dlp expands its output template.

        Returns:
            The path, or "" if the task has no filename yet
        """
        if not self.filename:
            return ""
        directory = os.path.expandvars(os.path.expanduser(self.output_directory))
        return os.path.join(directory, self.filename)

    def is_active(self) -> bool:
        """Check if task is currently active (pending or downloading)."""
        return self.status in (TaskStatus.PENDING, TaskStatus.DOWNLOADING)

    def is_finished(self) -> bool:
        """Check if task is finished (completed, error, or cancelled)."""
        return self.status in (TaskStatus.COMPLETED, TaskStatus.ERROR, TaskStatus.CANCELLED)

    def get_status_text(self) -> str:
        """Get human-readable status text."""
        status_texts = {
            TaskStatus.PENDING: "Waiting to start...",
            TaskStatus.DOWNLOADING: "Downloading...",
            TaskStatus.COMPLETED: "Completed",
            TaskStatus.ERROR: f"Error: {self.error_message}",
            TaskStatus.CANCELLED: "Cancelled",
        }
        return status_texts.get(self.status, "Unknown")

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"DownloadTask(url={self.url[:50]}..., status={self.status.value}, progress={self.progress_percent:.1f}%)"
        )


# Fields written to the queue file, with the type each one must have on load.
# "status" and "created_at" are handled separately (enum and datetime).
_PERSISTED_FIELDS: dict[str, type | tuple[type, ...]] = {
    "url": str,
    "output_directory": str,
    "quality": str,
    "audio_only": bool,
    "filename": str,
    "title": str,
    "error_message": str,
    "download_thumbnail": bool,
    "download_subtitles": bool,
    "subtitle_languages": str,
    "speed_limit": int,
    "video_container": (str, type(None)),
    "audio_format": str,
    "selected_subtitles": (list, type(None)),
    "download_metadata": bool,
    "download_comments": bool,
    "auto_number_duplicates": bool,
    "retry_count": int,
}

_REQUIRED_FIELDS = ("url", "output_directory", "quality")
