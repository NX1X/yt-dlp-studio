"""
Download worker with threading for YT-DLP Studio.

This module provides a threaded worker for non-blocking downloads.
Uses Qt's QThread for safe GUI updates via signals.
"""

import time
from typing import Any

from PySide6.QtCore import QThread, Signal

from ..models.download_task import DownloadTask
from ..utils.constants import PROGRESS_UPDATE_INTERVAL
from ..utils.logger import get_logger
from .format_handler import FormatHandler
from .progress_handler import ProgressHandler
from .yt_dlp_wrapper import YtDlpWrapper

logger = get_logger()


class DownloadWorker(QThread):
    """
    Worker thread for handling downloads without blocking the GUI.

    Uses Qt signals to communicate progress back to the main GUI thread.
    This ensures the UI remains responsive during downloads.

    Signals:
        progress_updated: Emitted when download progress changes
            Args: (dict) Cleaned progress data from ProgressHandler
        download_started: Emitted when download begins
            Args: (str) Video title
        download_completed: Emitted when download finishes successfully
            Args: (str) Output filename
        download_failed: Emitted when download fails
            Args: (str) Error message
        log_message: Emitted for log messages
            Args: (str) Log message text

    Example:
        >>> worker = DownloadWorker(task)
        >>> worker.progress_updated.connect(update_progress_bar)
        >>> worker.download_completed.connect(on_complete)
        >>> worker.download_failed.connect(on_error)
        >>> worker.start()  # Runs in background
    """

    # Define signals for communication with GUI
    progress_updated = Signal(dict)  # Progress data
    download_started = Signal(str)  # Video title
    download_completed = Signal(str)  # Filename
    download_failed = Signal(str)  # Error message
    log_message = Signal(str)  # Log messages

    def __init__(self, task: DownloadTask):
        """
        Initialize download worker.

        Args:
            task: DownloadTask to process
        """
        super().__init__()
        self.task = task
        self.wrapper: YtDlpWrapper | None = None
        self._is_cancelled = False
        self._last_progress_time = 0.0  # For throttling progress updates
        logger.debug(f"DownloadWorker created for: {task.url}")

    def run(self) -> None:
        """
        Run the download in background thread.

        This method is called automatically when worker.start() is invoked.
        It should NOT be called directly.
        """
        logger.info(f"Download worker started for: {self.task.url}")

        try:
            # Mark task as started
            self.task.start()

            # Create wrapper with progress callback
            self.wrapper = YtDlpWrapper(progress_callback=self._on_progress)

            # Emit log message
            self.log_message.emit(f"Starting download: {self.task.url}")

            # Get video info first (optional, for better UX)
            try:
                video_info = self.wrapper.get_video_info(self.task.url)
                if video_info:
                    self.download_started.emit(video_info.title)
                    self.log_message.emit(f"Downloading: {video_info.title}")
                else:
                    self.download_started.emit("Video")
                    self.log_message.emit("Starting download...")
            except Exception as e:
                logger.warning(f"Could not extract video info: {e}")
                self.download_started.emit("Video")

            # Determine if audio only - use task flag (task.audio_only is set by the UI)
            # Do NOT re-derive from quality name: "Best Quality" in audio mode has no "kbps"
            is_audio = self.task.audio_only

            # Get format string
            format_string = FormatHandler.get_format_string(self.task.quality)

            # Get audio quality if audio only
            audio_quality = "192"  # default
            if is_audio:
                audio_quality = FormatHandler.get_audio_quality(self.task.quality)

            # Check if cancelled before downloading
            if self._is_cancelled:
                self._handle_cancellation()
                return

            # Start download with all v2.1.0 parameters
            success = self.wrapper.download(
                url=self.task.url,
                output_dir=self.task.output_directory,
                format_string=format_string,
                audio_only=is_audio,
                audio_quality=audio_quality,
                download_thumbnail=self.task.download_thumbnail,
                download_subtitles=self.task.download_subtitles,
                subtitle_languages=self.task.subtitle_languages,
                speed_limit=self.task.speed_limit,
                video_container=self.task.video_container,
                audio_format=self.task.audio_format,
                selected_subtitles=getattr(self.task, "selected_subtitles", None),
                download_metadata=getattr(self.task, "download_metadata", False),
                download_comments=getattr(self.task, "download_comments", False),
                auto_number_duplicates=getattr(self.task, "auto_number_duplicates", True),
            )

            # Check result
            if self._is_cancelled:
                self._handle_cancellation()
            elif success:
                self._handle_success()
            else:
                self._handle_failure("Download failed")

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Download worker error: {e}", exc_info=True)
            self._handle_failure(error_msg)

    def cancel(self) -> None:
        """
        Request download cancellation.

        Note: Cancellation may not be immediate due to yt-dlp limitations.
        """
        logger.info("Download cancellation requested")
        self._is_cancelled = True

        if self.wrapper:
            self.wrapper.cancel_download()

        self.log_message.emit("Cancelling download...")

    def _on_progress(self, raw_data: dict[str, Any]) -> None:
        """
        Handle progress updates from yt-dlp.

        Throttled to PROGRESS_UPDATE_INTERVAL to avoid excessive UI updates.

        Args:
            raw_data: Raw progress data from yt-dlp
        """
        # Check if cancelled
        if self._is_cancelled:
            return

        # Throttle progress updates to avoid UI lag
        current_time = time.time()
        status = raw_data.get("status", "")
        if status == "downloading" and (current_time - self._last_progress_time) < PROGRESS_UPDATE_INTERVAL:
            return  # Skip this update
        self._last_progress_time = current_time

        # Parse progress data
        clean_data = ProgressHandler.parse_progress(raw_data)

        # Update task
        self.task.update_progress(
            progress_percent=clean_data["percent"],
            download_speed=clean_data["speed"],
            eta_seconds=clean_data["eta"],
            downloaded_bytes=clean_data["downloaded"],
            file_size=clean_data["total"],
        )

        # Emit signal to GUI
        self.progress_updated.emit(clean_data)

        # Create and emit log message
        if clean_data["status"] == "downloading":
            log_msg = ProgressHandler.create_progress_message(clean_data)
            self.log_message.emit(log_msg)

    def _handle_success(self) -> None:
        """Handle successful download completion (v3.0.0 - added success alert)."""
        logger.info("Download completed successfully")
        filename = self.task.filename or "video file"
        self.task.complete(filename)
        self.log_message.emit(f"Download completed: {filename}")

        # Play system success sound (v3.0.0, cross-platform v3.2.0)
        try:
            import winsound

            winsound.MessageBeep(winsound.MB_OK)
        except ImportError:
            try:
                from PySide6.QtWidgets import QApplication

                app = QApplication.instance()
                if app:
                    app.beep()
            except Exception as beep_error:
                logger.debug(f"Completion beep failed (non-fatal): {beep_error}")

        self.download_completed.emit(filename)

    def _handle_failure(self, error_message: str) -> None:
        """
        Handle download failure (v3.0.0 - added error alert).

        Args:
            error_message: Error description
        """
        logger.error(f"Download failed: {error_message}")
        self.task.fail(error_message)
        self.log_message.emit(f"Download failed: {error_message}")

        # Play system error sound (v3.0.0, cross-platform v3.2.0)
        try:
            import winsound

            winsound.MessageBeep(winsound.MB_ICONHAND)
        except ImportError:
            try:
                from PySide6.QtWidgets import QApplication

                app = QApplication.instance()
                if app:
                    app.beep()
            except Exception as beep_error:
                logger.debug(f"Failure beep failed (non-fatal): {beep_error}")

        self.download_failed.emit(error_message)

    def _handle_cancellation(self) -> None:
        """Handle download cancellation."""
        logger.info("Download cancelled")
        self.task.cancel()
        self.log_message.emit("Download cancelled by user")
        self.download_failed.emit("Download cancelled")

    def is_running(self) -> bool:
        """
        Check if worker is currently running.

        Returns:
            True if running, False otherwise
        """
        return self.isRunning()
