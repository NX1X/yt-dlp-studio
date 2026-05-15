"""
History manager for YT-DLP Studio.

Manages persistent storage of download history.
"""

from datetime import datetime
from pathlib import Path

from ..models.download_history import DownloadHistory, HistoryEntry
from ..models.download_task import DownloadTask
from ..utils.constants import APP_DATA_DIR
from ..utils.logger import get_logger

logger = get_logger()


class HistoryManager:
    """Manages download history persistence."""

    HISTORY_FILE = "download_history.json"

    def __init__(self):
        """Initialize history manager."""
        self.history = DownloadHistory(max_entries=1000)
        self.history_path = APP_DATA_DIR / self.HISTORY_FILE
        self.load()
        logger.info(f"HistoryManager initialized. Loaded {len(self.history.entries)} entries")

    def add_download(
        self,
        task: DownloadTask,
        status: str,
        error_message: str = "",
        platform: str = "",
    ) -> None:
        """
        Add download to history.

        Args:
            task: DownloadTask that was executed
            status: Final status ("completed", "failed", "cancelled")
            error_message: Error message if failed
            platform: Platform name (e.g., "youtube", "vimeo")
        """
        entry = HistoryEntry(
            url=task.url,
            title=task.filename or "Unknown",
            quality=task.quality,
            output_directory=task.output_directory,
            filename=task.filename or "",
            status=status,
            timestamp=datetime.now(),
            file_size=task.file_size or 0,
            download_speed=task.download_speed or 0.0,
            duration=task.eta_seconds or 0.0,
            error_message=error_message,
            platform=platform,
        )

        self.history.add_entry(entry)
        self.save()
        logger.info(f"Added to history: {entry.title} ({status})")

    def get_history(
        self,
        limit: int | None = None,
        status: str | None = None,
        platform: str | None = None,
    ) -> list:
        """
        Get history entries.

        Args:
            limit: Maximum number of entries
            status: Filter by status
            platform: Filter by platform

        Returns:
            List of HistoryEntry objects
        """
        return self.history.get_entries(limit=limit, status=status, platform=platform)

    def search_history(self, query: str) -> list:
        """
        Search history.

        Args:
            query: Search query

        Returns:
            List of matching HistoryEntry objects
        """
        return self.history.search(query)

    def get_statistics(self) -> dict:
        """
        Get download statistics.

        Returns:
            Dictionary with statistics
        """
        return self.history.get_statistics()

    def clear_history(self, status: str | None = None) -> int:
        """
        Clear history.

        Args:
            status: Optional status filter

        Returns:
            Number of entries removed
        """
        count = self.history.clear(status=status)
        self.save()
        logger.info(f"Cleared {count} history entries (status={status})")
        return count

    def export_to_csv(self, filepath: Path) -> bool:
        """
        Export history to CSV file.

        Args:
            filepath: Output file path

        Returns:
            True if successful
        """
        try:
            csv_data = self.history.export_to_csv()
            filepath.write_text(csv_data, encoding="utf-8")
            logger.info(f"Exported history to CSV: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to export CSV: {e}")
            return False

    def save(self) -> bool:
        """
        Save history to file.

        Returns:
            True if successful
        """
        try:
            json_data = self.history.to_json()
            self.history_path.write_text(json_data, encoding="utf-8")
            logger.debug(f"History saved to {self.history_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save history: {e}")
            return False

    def load(self) -> bool:
        """
        Load history from file.

        Returns:
            True if successful
        """
        if not self.history_path.exists():
            logger.debug("No history file found, starting fresh")
            return False

        try:
            json_data = self.history_path.read_text(encoding="utf-8")
            self.history = DownloadHistory.from_json(json_data)
            logger.info(f"History loaded: {len(self.history.entries)} entries")
            return True
        except Exception as e:
            logger.error(f"Failed to load history: {e}")
            return False
