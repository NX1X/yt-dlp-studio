"""
Subtitle-list worker for fetching available subtitle languages off the UI thread.

The Download tab's "Select Subtitles" button used to call
``YtDlpWrapper().get_available_subtitles(url)`` synchronously from the main
thread, freezing the entire Qt event loop for the 2-10 seconds the request
takes. This worker moves the call to a ``QThread`` and reports the result
back via signals, so the UI stays responsive.
"""

from PySide6.QtCore import QThread, Signal

from ..utils.logger import get_logger
from .yt_dlp_wrapper import YtDlpWrapper

logger = get_logger()


class SubtitleListWorker(QThread):
    """
    Background worker that enumerates subtitle languages for a video.

    Signals:
        subtitles_fetched: ``dict[str, dict]`` mapping ISO code to
            ``{"name": <display_name>, "auto": <bool>}``. Emitted on success
            even when the dict is empty (no subtitles available).
        fetch_failed: ``str`` human-readable error message. Emitted on
            unexpected exceptions.
    """

    subtitles_fetched = Signal(dict)
    fetch_failed = Signal(str)

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url
        logger.debug(f"SubtitleListWorker created for URL: {url}")

    def run(self) -> None:
        logger.info(f"Fetching available subtitles for: {self.url}")
        try:
            wrapper = YtDlpWrapper()
            available = wrapper.get_available_subtitles(self.url) or {}
            logger.info(f"Subtitle fetch complete; {len(available)} languages")
            self.subtitles_fetched.emit(available)
        except Exception as e:
            error_msg = f"Error fetching subtitles: {e}"
            logger.error(error_msg)
            self.fetch_failed.emit(error_msg)
