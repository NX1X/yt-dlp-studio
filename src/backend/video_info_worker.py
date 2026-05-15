"""
Video info worker for fetching metadata in background.

This module provides a QThread worker to fetch video information
without blocking the UI.
"""

from PySide6.QtCore import QThread, Signal

from ..models.video_info import VideoInfo
from ..utils.logger import get_logger
from .yt_dlp_wrapper import YtDlpWrapper

logger = get_logger()


class VideoInfoWorker(QThread):
    """
    Background worker to fetch video information.

    Fetches video metadata using yt-dlp without blocking the UI.

    Signals:
        info_fetched: Emitted when info is successfully fetched (VideoInfo)
        fetch_failed: Emitted when fetching fails (error_message)
    """

    # Signals
    info_fetched = Signal(VideoInfo)
    fetch_failed = Signal(str)

    def __init__(self, url: str, parent=None):
        """
        Initialize video info worker.

        Args:
            url: Video URL to fetch info for
            parent: Parent QObject
        """
        super().__init__(parent)
        self.url = url
        logger.debug(f"VideoInfoWorker created for URL: {url}")

    def run(self) -> None:
        """
        Fetch video information in background thread.

        Emits info_fetched on success or fetch_failed on error.
        """
        logger.info(f"Fetching video info for: {self.url}")

        try:
            wrapper = YtDlpWrapper()
            video_info = wrapper.get_video_info(self.url)

            if video_info is None:
                error_msg = (
                    "Could not extract video information. The URL may be invalid or the video may be unavailable."
                )
                logger.error(error_msg)
                self.fetch_failed.emit(error_msg)
                return

            logger.info(f"Video info fetched successfully: {video_info.title}")
            self.info_fetched.emit(video_info)

        except Exception as e:
            error_msg = f"Error fetching video info: {str(e)}"
            logger.error(error_msg)
            self.fetch_failed.emit(error_msg)
