"""
History manager for YT-DLP Studio.

Manages persistent storage of download history.
"""

from datetime import datetime
from pathlib import Path

from ..models.download_history import DownloadHistory, HistoryEntry
from ..models.download_task import DownloadTask
from ..utils.constants import APP_DATA_DIR
from ..utils.file_formats import HISTORY_FORMAT, FileState, keep_bad_copy, load_json_file, save_json_file
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
            title=task.title or task.filename or "Unknown",
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
        except Exception:
            logger.exception("Failed to export CSV")
            return False

    def save(self) -> bool:
        """
        Save history to file, with the format version, atomically.

        Returns:
            True if successful
        """
        try:
            save_json_file(self.history_path, HISTORY_FORMAT, self.history.to_dict())
            logger.debug(f"History saved to {self.history_path}")
            return True
        except Exception:
            logger.exception("Failed to save history")
            return False

    def load(self) -> bool:
        """
        Load history from file.

        An older file format is migrated (see src/utils/file_formats.py). A
        damaged file is kept as ``<name>.bad`` and the history starts empty.
        Invalid entries are skipped (the file is kept as ``.bad`` too).

        Returns:
            True if successful
        """
        result = load_json_file(self.history_path, HISTORY_FORMAT)
        if result.data is None:
            if result.state is FileState.MISSING:
                logger.debug("No history file found, starting fresh")
            return False

        try:
            history, skipped = DownloadHistory.from_dict(result.data)
        except ValueError:
            logger.warning(f"History file {self.history_path} has no valid entry list, starting fresh")
            keep_bad_copy(self.history_path)
            return False

        if skipped:
            logger.warning(f"Skipped {skipped} invalid entries in history file {self.history_path}")
            keep_bad_copy(self.history_path)

        self.history = history
        logger.info(f"History loaded: {len(self.history.entries)} entries")
        return True
