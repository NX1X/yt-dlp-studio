"""
Data models for YT-DLP Studio.

This package contains data classes and models used throughout the application.
"""

from .app_config import AppConfig
from .download_queue import DownloadQueue
from .download_task import DownloadTask, TaskStatus
from .video_info import VideoInfo

__all__ = [
    "AppConfig",
    "DownloadTask",
    "TaskStatus",
    "VideoInfo",
    "DownloadQueue",
]
