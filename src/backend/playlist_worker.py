"""
Playlist worker for fetching playlist info in background.

This module provides a QThread worker to fetch playlist information
without blocking the UI.
"""

from PySide6.QtCore import QThread, Signal

from ..utils.logger import get_logger
from .playlist_fetcher import PlaylistFetcher, PlaylistInfo

logger = get_logger()


class PlaylistWorker(QThread):
    """
    Background worker to fetch playlist information.

    Fetches playlist metadata using yt-dlp without blocking the UI.

    Signals:
        playlist_fetched: Emitted when playlist is successfully fetched (PlaylistInfo)
        fetch_failed: Emitted when fetching fails (error_message)
    """

    # Signals
    playlist_fetched = Signal(PlaylistInfo)
    fetch_failed = Signal(str)

    def __init__(self, url: str, parent=None):
        """
        Initialize playlist worker.

        Args:
            url: Playlist URL to fetch info for
            parent: Parent QObject
        """
        super().__init__(parent)
        self.url = url
        logger.debug(f"PlaylistWorker created for URL: {url}")

    def run(self) -> None:
        """
        Fetch playlist information in background thread.

        Emits playlist_fetched on success or fetch_failed on error.
        """
        logger.info(f"Fetching playlist info for: {self.url}")

        try:
            playlist_info = PlaylistFetcher.fetch_playlist_info(self.url)

            if playlist_info is None:
                error_msg = (
                    "Could not extract playlist information. The URL may be invalid or the playlist may be unavailable."
                )
                logger.error(error_msg)
                self.fetch_failed.emit(error_msg)
                return

            logger.info(
                f"Playlist info fetched successfully: {playlist_info.title} ({len(playlist_info.videos)} videos)"
            )
            self.playlist_fetched.emit(playlist_info)

        except Exception as e:
            error_msg = f"Error fetching playlist info: {str(e)}"
            logger.error(error_msg)
            self.fetch_failed.emit(error_msg)
