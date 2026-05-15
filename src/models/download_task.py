"""
Download task data model.

This module defines the structure for a download task.
"""

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
        filename: Output filename (set after extraction)
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
    error_message: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    # v1.7.0 features
    download_thumbnail: bool = True
    download_subtitles: bool = False
    subtitle_languages: str = "en"
    speed_limit: int = 0  # KB/s, 0 = unlimited
    # v2.0.0 features
    video_container: str | None = None
    audio_format: str = "mp3"
    audio_only: bool = False  # Track if this is audio-only download for duplicate detection
    # v2.1.0 features - Advanced options
    selected_subtitles: list | None = None  # List of selected subtitle language codes
    download_metadata: bool = False  # Download metadata (comments, description, etc.)
    download_comments: bool = False  # Download comments to separate .txt file (v2.0.0)
    auto_number_duplicates: bool = True  # Automatically number duplicate files

    def start(self) -> None:
        """Mark task as started."""
        self.status = TaskStatus.DOWNLOADING
        self.started_at = datetime.now()

    def complete(self, filename: str) -> None:
        """
        Mark task as completed.

        Args:
            filename: Final output filename
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
            f"DownloadTask(url={self.url[:50]}..., "
            f"status={self.status.value}, "
            f"progress={self.progress_percent:.1f}%)"
        )
