"""
Download history model for YT-DLP Studio.

Tracks all downloads with timestamp and statistics.
"""

import json
from dataclasses import dataclass
from datetime import datetime


@dataclass
class HistoryEntry:
    """Represents a single download history entry."""

    url: str
    title: str
    quality: str
    output_directory: str
    filename: str
    status: str  # "completed", "failed", "cancelled"
    timestamp: datetime
    file_size: int = 0  # bytes
    download_speed: float = 0.0  # bytes per second
    duration: float = 0.0  # seconds
    error_message: str = ""
    platform: str = ""  # "youtube", "vimeo", etc.

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "url": self.url,
            "title": self.title,
            "quality": self.quality,
            "output_directory": self.output_directory,
            "filename": self.filename,
            "status": self.status,
            "timestamp": self.timestamp.isoformat(),
            "file_size": self.file_size,
            "download_speed": self.download_speed,
            "duration": self.duration,
            "error_message": self.error_message,
            "platform": self.platform,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HistoryEntry":
        """Create from dictionary (JSON deserialization)."""
        data_copy = data.copy()
        data_copy["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data_copy)


class DownloadHistory:
    """Manages download history storage and retrieval."""

    def __init__(self, max_entries: int = 1000):
        """
        Initialize download history.

        Args:
            max_entries: Maximum number of history entries to keep
        """
        self.max_entries = max_entries
        self.entries: list[HistoryEntry] = []

    def add_entry(self, entry: HistoryEntry) -> None:
        """
        Add entry to history.

        Args:
            entry: HistoryEntry to add
        """
        self.entries.insert(0, entry)  # Add to beginning (most recent first)

        # Trim if exceeds max
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[: self.max_entries]

    def get_entries(
        self,
        limit: int | None = None,
        status: str | None = None,
        platform: str | None = None,
    ) -> list[HistoryEntry]:
        """
        Get history entries with optional filtering.

        Args:
            limit: Maximum number of entries to return
            status: Filter by status (e.g., "completed", "failed")
            platform: Filter by platform (e.g., "youtube", "vimeo")

        Returns:
            List of HistoryEntry objects
        """
        entries = self.entries

        # Apply filters
        if status:
            entries = [e for e in entries if e.status == status]
        if platform:
            entries = [e for e in entries if e.platform.lower() == platform.lower()]

        # Apply limit
        if limit:
            entries = entries[:limit]

        return entries

    def search(self, query: str) -> list[HistoryEntry]:
        """
        Search history by title or URL.

        Args:
            query: Search query

        Returns:
            List of matching HistoryEntry objects
        """
        query_lower = query.lower()
        return [e for e in self.entries if query_lower in e.title.lower() or query_lower in e.url.lower()]

    def get_statistics(self) -> dict:
        """
        Get download statistics.

        Returns:
            Dictionary with statistics
        """
        total = len(self.entries)
        completed = len([e for e in self.entries if e.status == "completed"])
        failed = len([e for e in self.entries if e.status == "failed"])
        cancelled = len([e for e in self.entries if e.status == "cancelled"])

        total_size = sum(e.file_size for e in self.entries if e.status == "completed")
        total_duration = sum(e.duration for e in self.entries if e.status == "completed")

        # Calculate average speed
        speed_entries = [e.download_speed for e in self.entries if e.status == "completed" and e.download_speed > 0]
        avg_speed = sum(speed_entries) / len(speed_entries) if speed_entries else 0

        # Most downloaded platforms
        platforms = {}
        for entry in self.entries:
            if entry.platform:
                platforms[entry.platform] = platforms.get(entry.platform, 0) + 1

        return {
            "total_downloads": total,
            "completed": completed,
            "failed": failed,
            "cancelled": cancelled,
            "success_rate": (completed / total * 100) if total > 0 else 0,
            "total_size_bytes": total_size,
            "total_duration_seconds": total_duration,
            "average_speed_bps": avg_speed,
            "platforms": platforms,
        }

    def clear(self, status: str | None = None) -> int:
        """
        Clear history entries.

        Args:
            status: Optional status filter (e.g., "completed", "failed")
                   If None, clears all entries

        Returns:
            Number of entries removed
        """
        if status:
            original_count = len(self.entries)
            self.entries = [e for e in self.entries if e.status != status]
            return original_count - len(self.entries)
        else:
            count = len(self.entries)
            self.entries = []
            return count

    def to_json(self) -> str:
        """
        Export history to JSON string.

        Returns:
            JSON string
        """
        data = {
            "max_entries": self.max_entries,
            "entries": [e.to_dict() for e in self.entries],
        }
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "DownloadHistory":
        """
        Import history from JSON string.

        Args:
            json_str: JSON string

        Returns:
            DownloadHistory object
        """
        data = json.loads(json_str)
        history = cls(max_entries=data.get("max_entries", 1000))
        history.entries = [HistoryEntry.from_dict(e) for e in data.get("entries", [])]
        return history

    def export_to_csv(self) -> str:
        """
        Export history to CSV format.

        Returns:
            CSV string
        """
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "Timestamp",
                "Title",
                "URL",
                "Quality",
                "Status",
                "File Size (MB)",
                "Speed (MB/s)",
                "Duration (s)",
                "Platform",
                "Error",
            ]
        )

        # Write data
        for entry in self.entries:
            writer.writerow(
                [
                    entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    entry.title,
                    entry.url,
                    entry.quality,
                    entry.status,
                    f"{entry.file_size / 1024 / 1024:.2f}",
                    f"{entry.download_speed / 1024 / 1024:.2f}",
                    f"{entry.duration:.1f}",
                    entry.platform,
                    entry.error_message,
                ]
            )

        return output.getvalue()
