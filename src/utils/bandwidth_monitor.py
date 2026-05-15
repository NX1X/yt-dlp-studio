"""
Bandwidth Monitor for YT-DLP Studio.

Tracks download speeds and provides statistics for visualization.
"""

import time
from collections import deque

from PySide6.QtCore import QObject, Signal

from ..utils.logger import get_logger

logger = get_logger()


class BandwidthMonitor(QObject):
    """
    Monitors bandwidth usage during downloads.

    Tracks:
    - Current download speed
    - Average download speed
    - Peak download speed
    - Total bytes downloaded
    - Speed history for graphing
    """

    # Signals
    speed_updated = Signal(float)  # Current speed in bytes/sec
    stats_updated = Signal(dict)  # Full statistics dict

    def __init__(self, history_size: int = 60):
        """
        Initialize BandwidthMonitor.

        Args:
            history_size: Number of speed samples to keep (default 60 for 1 minute at 1 sec intervals)
        """
        super().__init__()
        self.history_size = history_size

        # Speed tracking
        self.speed_history = deque(maxlen=history_size)
        self.current_speed = 0.0
        self.peak_speed = 0.0
        self.average_speed = 0.0

        # Download tracking
        self.total_downloaded = 0
        self.last_downloaded = 0
        self.last_update_time = None

        # Active download tracking
        self.is_active = False

        logger.debug(f"BandwidthMonitor initialized with history_size={history_size}")

    def start_monitoring(self):
        """Start monitoring bandwidth."""
        self.is_active = True
        self.last_update_time = time.time()
        logger.debug("Bandwidth monitoring started")

    def stop_monitoring(self):
        """Stop monitoring bandwidth."""
        self.is_active = False
        logger.debug("Bandwidth monitoring stopped")

    def reset(self):
        """Reset all statistics."""
        self.speed_history.clear()
        self.current_speed = 0.0
        self.peak_speed = 0.0
        self.average_speed = 0.0
        self.total_downloaded = 0
        self.last_downloaded = 0
        self.last_update_time = None
        logger.debug("Bandwidth statistics reset")

    def update(self, downloaded_bytes: int, total_bytes: int | None = None):
        """
        Update bandwidth statistics with new download progress.

        Args:
            downloaded_bytes: Total bytes downloaded so far
            total_bytes: Total file size (optional)
        """
        if not self.is_active:
            return

        current_time = time.time()

        # Calculate speed
        if self.last_update_time is not None:
            time_delta = current_time - self.last_update_time

            if time_delta > 0:
                bytes_delta = downloaded_bytes - self.last_downloaded
                speed = bytes_delta / time_delta  # bytes per second

                # Update current speed
                self.current_speed = speed

                # Update speed history
                self.speed_history.append(speed)

                # Update peak speed
                if speed > self.peak_speed:
                    self.peak_speed = speed

                # Calculate average speed from history
                if self.speed_history:
                    self.average_speed = sum(self.speed_history) / len(self.speed_history)

                # Emit signals
                self.speed_updated.emit(speed)
                self.stats_updated.emit(self.get_stats())

        # Update tracking variables
        self.last_downloaded = downloaded_bytes
        self.last_update_time = current_time
        self.total_downloaded = downloaded_bytes

    def get_current_speed(self) -> float:
        """
        Get current download speed.

        Returns:
            Speed in bytes per second
        """
        return self.current_speed

    def get_current_speed_str(self) -> str:
        """
        Get current speed as formatted string.

        Returns:
            Speed string (e.g., "1.5 MB/s")
        """
        return self._format_speed(self.current_speed)

    def get_average_speed(self) -> float:
        """
        Get average download speed.

        Returns:
            Speed in bytes per second
        """
        return self.average_speed

    def get_average_speed_str(self) -> str:
        """
        Get average speed as formatted string.

        Returns:
            Speed string
        """
        return self._format_speed(self.average_speed)

    def get_peak_speed(self) -> float:
        """
        Get peak download speed.

        Returns:
            Speed in bytes per second
        """
        return self.peak_speed

    def get_peak_speed_str(self) -> str:
        """
        Get peak speed as formatted string.

        Returns:
            Speed string
        """
        return self._format_speed(self.peak_speed)

    def get_total_downloaded(self) -> int:
        """
        Get total bytes downloaded.

        Returns:
            Total bytes
        """
        return self.total_downloaded

    def get_total_downloaded_str(self) -> str:
        """
        Get total downloaded as formatted string.

        Returns:
            Size string (e.g., "45.3 MB")
        """
        return self._format_size(self.total_downloaded)

    def get_speed_history(self) -> list[float]:
        """
        Get speed history for graphing.

        Returns:
            List of speed values (bytes/sec)
        """
        return list(self.speed_history)

    def get_speed_history_formatted(self) -> list[tuple[int, float]]:
        """
        Get speed history with timestamps for graphing.

        Returns:
            List of (timestamp, speed) tuples
        """
        history = []
        current_time = time.time()

        for i, speed in enumerate(self.speed_history):
            # Calculate timestamp (going backwards from current time)
            timestamp = current_time - (len(self.speed_history) - i - 1)
            history.append((int(timestamp), speed))

        return history

    def get_stats(self) -> dict:
        """
        Get all statistics as dictionary.

        Returns:
            Dictionary with all stats
        """
        return {
            "current_speed": self.current_speed,
            "current_speed_str": self.get_current_speed_str(),
            "average_speed": self.average_speed,
            "average_speed_str": self.get_average_speed_str(),
            "peak_speed": self.peak_speed,
            "peak_speed_str": self.get_peak_speed_str(),
            "total_downloaded": self.total_downloaded,
            "total_downloaded_str": self.get_total_downloaded_str(),
            "speed_history": self.get_speed_history(),
        }

    def _format_speed(self, bytes_per_sec: float) -> str:
        """
        Format speed for display.

        Args:
            bytes_per_sec: Speed in bytes per second

        Returns:
            Formatted string (e.g., "1.5 MB/s")
        """
        if bytes_per_sec < 1024:
            return f"{bytes_per_sec:.1f} B/s"
        elif bytes_per_sec < 1024 * 1024:
            return f"{bytes_per_sec / 1024:.1f} KB/s"
        elif bytes_per_sec < 1024 * 1024 * 1024:
            return f"{bytes_per_sec / (1024 * 1024):.2f} MB/s"
        else:
            return f"{bytes_per_sec / (1024 * 1024 * 1024):.2f} GB/s"

    def _format_size(self, bytes_value: int) -> str:
        """
        Format file size for display.

        Args:
            bytes_value: Size in bytes

        Returns:
            Formatted string (e.g., "45.3 MB")
        """
        if bytes_value < 1024:
            return f"{bytes_value} B"
        elif bytes_value < 1024 * 1024:
            return f"{bytes_value / 1024:.1f} KB"
        elif bytes_value < 1024 * 1024 * 1024:
            return f"{bytes_value / (1024 * 1024):.1f} MB"
        else:
            return f"{bytes_value / (1024 * 1024 * 1024):.2f} GB"

    def is_monitoring(self) -> bool:
        """
        Check if monitoring is active.

        Returns:
            True if monitoring
        """
        return self.is_active
