"""
Progress data handler for YT-DLP Studio.

This module processes raw progress data from yt-dlp into a clean format for the UI.
"""

from typing import Any

from ..utils.logger import get_logger

logger = get_logger()


class ProgressHandler:
    """
    Handles and processes progress data from yt-dlp.

    yt-dlp provides progress data in a raw format with various fields.
    This class normalizes it into a clean, consistent structure for the UI.
    """

    @staticmethod
    def parse_progress(raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        Parse raw progress data from yt-dlp into UI-friendly format.

        Args:
            raw_data: Progress dictionary from yt-dlp progress hook

        Returns:
            Cleaned progress dictionary with keys:
                - status: 'downloading', 'finished', 'error'
                - percent: Progress percentage (0-100)
                - speed: Download speed in bytes/sec
                - eta: Estimated time remaining in seconds
                - downloaded: Bytes downloaded
                - total: Total file size in bytes
                - filename: Output filename

        Example:
            >>> raw = {...}  # From yt-dlp
            >>> clean = ProgressHandler.parse_progress(raw)
            >>> print(f"Progress: {clean['percent']}%")
        """
        logger.debug(f"Parsing progress data: {raw_data.get('status', 'unknown')}")

        # Initialize clean data structure
        clean_data = {
            "status": "unknown",
            "percent": 0.0,
            "speed": 0.0,
            "eta": 0,
            "downloaded": 0,
            "total": 0,
            "filename": "",
        }

        try:
            # Get status
            status = raw_data.get("status", "unknown")
            clean_data["status"] = status

            # Get filename
            clean_data["filename"] = raw_data.get("filename", "")

            # Handle different statuses
            if status == "downloading":
                clean_data.update(ProgressHandler._parse_downloading(raw_data))

            elif status == "finished":
                clean_data["percent"] = 100.0
                clean_data["total"] = raw_data.get("total_bytes") or raw_data.get("total_bytes_estimate", 0)
                clean_data["downloaded"] = clean_data["total"]

            elif status == "error":
                logger.error(f"Download error status: {raw_data}")

        except Exception as e:
            logger.error(f"Error parsing progress data: {e}")

        return clean_data

    @staticmethod
    def _parse_downloading(raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        Parse downloading status data.

        Args:
            raw_data: Raw progress data

        Returns:
            Dictionary with downloading-specific data
        """
        data = {}

        # Get downloaded bytes
        downloaded = raw_data.get("downloaded_bytes", 0)
        data["downloaded"] = downloaded

        # Get total bytes (may be estimate)
        total = raw_data.get("total_bytes") or raw_data.get("total_bytes_estimate", 0)
        data["total"] = total

        # Calculate percentage
        if total > 0:
            percent = (downloaded / total) * 100
            data["percent"] = min(percent, 100.0)
        else:
            # If total unknown, use percent string from yt-dlp if available
            percent_str = raw_data.get("_percent_str", "0%")
            try:
                data["percent"] = float(percent_str.strip("%"))
            except:
                data["percent"] = 0.0

        # Get download speed
        speed = raw_data.get("speed")
        if speed is not None:
            data["speed"] = float(speed)
        else:
            data["speed"] = 0.0

        # Get ETA
        eta = raw_data.get("eta")
        if eta is not None:
            data["eta"] = int(eta)
        else:
            data["eta"] = 0

        return data

    @staticmethod
    def create_progress_message(progress_data: dict[str, Any]) -> str:
        """
        Create human-readable progress message.

        Args:
            progress_data: Cleaned progress data from parse_progress()

        Returns:
            Progress message string

        Example:
            >>> data = ProgressHandler.parse_progress(raw)
            >>> msg = ProgressHandler.create_progress_message(data)
            >>> print(msg)  # "Downloading: 45.3% at 1.2 MB/s (ETA: 30s)"
        """
        status = progress_data.get("status", "unknown")

        if status == "downloading":
            percent = progress_data.get("percent", 0)
            from ..utils.file_helper import FileHelper

            speed = progress_data.get("speed", 0)
            speed_str = FileHelper.format_speed(speed) if speed > 0 else "Unknown"

            eta = progress_data.get("eta", 0)
            eta_str = FileHelper.format_time(eta) if eta > 0 else "Unknown"

            return f"Downloading: {percent:.1f}% at {speed_str} (ETA: {eta_str})"

        elif status == "finished":
            return "Download finished, processing..."

        elif status == "error":
            return "Download error occurred"

        else:
            return f"Status: {status}"
