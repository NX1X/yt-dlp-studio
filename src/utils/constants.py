"""
Constants for YT-DLP Studio application.

This file contains all constant values used throughout the application.
Centralizing constants makes it easy to update values and maintain consistency.
"""

import os
from pathlib import Path

from .. import __version__

# Application Information
APP_NAME = "YT-DLP Studio"
APP_VERSION = __version__
APP_AUTHOR = "NX1X"
APP_ORGANIZATION = "NXTools"
APP_WEBSITE = "https://nx1xlab.dev"
APP_NXTOOLS_WEBSITE = "https://nx1xlab.dev/nxtools"
APP_DESCRIPTION = "A user-friendly GUI for yt-dlp video downloader"

# yt-dlp Engine Information
YTDLP_VERSION = "2026.02.04"  # Version of bundled yt-dlp
YTDLP_ENGINE_DIR = "vendor/yt_dlp_engine"

# File Names
CONFIG_FILE = "yt-dlp-studio_config.json"
LOG_FILE = "yt-dlp-studio.log"

# Default Settings
DEFAULT_OUTPUT_DIR = str(Path.home() / "Downloads")
DEFAULT_QUALITY = "best"  # best, 1080p, 720p, 480p, audio
DEFAULT_MAX_CONCURRENT_DOWNLOADS = 1  # v1.0 only supports single download

# Quality Options for v1.5.0 - Enhanced with 2K, 4K, 8K and multiple audio quality options
QUALITY_OPTIONS = {
    # Video Quality Options
    "Best Quality": "bestvideo+bestaudio/best",
    "8K (4320p)": "bestvideo[height<=4320]+bestaudio/best[height<=4320]",
    "4K (2160p)": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
    "2K (1440p)": "bestvideo[height<=1440]+bestaudio/best[height<=1440]",
    "1080p (Full HD)": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720p (HD)": "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480p (SD)": "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]",
    # Audio Quality Options
    "Audio 320kbps": "bestaudio/best",
    "Audio 256kbps": "bestaudio/best",
    "Audio 192kbps": "bestaudio/best",
    "Audio 128kbps": "bestaudio/best",
}

# Audio quality mapping (kbps for each audio option)
AUDIO_QUALITY_MAP = {
    "Best Quality": "0",  # 0 = VBR best quality (no bitrate cap)
    "Audio 320kbps": "320",
    "Audio 256kbps": "256",
    "Audio 192kbps": "192",
    "Audio 128kbps": "128",
}

# Default quality names (for dropdown)
QUALITY_NAMES = list(QUALITY_OPTIONS.keys())

# Audio extraction settings (when Audio Only is selected)
AUDIO_FORMAT = "mp3"
AUDIO_QUALITY = "192"  # kbps (default)

# v2.0.0: Video Container Format Options
VIDEO_CONTAINER_FORMATS = {
    "MP4 (Best Compatibility)": "mp4",
    "MKV (Matroska)": "mkv",
    "WebM": "webm",
    "Auto (Best Quality)": None,  # Let yt-dlp choose
}
DEFAULT_VIDEO_CONTAINER = "MP4 (Best Compatibility)"

# v2.0.0: Audio Format Options
AUDIO_FORMATS = {
    "MP3 (Most Compatible)": "mp3",
    "M4A/AAC (High Quality)": "m4a",
    "OPUS (Best Quality/Size)": "opus",
    "FLAC (Lossless)": "flac",
    "WAV (Uncompressed)": "wav",
    "Vorbis/OGG": "vorbis",
}
DEFAULT_AUDIO_FORMAT = "MP3 (Most Compatible)"

# Thumbnail settings (v1.7.0)
THUMBNAIL_DOWNLOAD = False  # Thumbnail off by default — user opts in
THUMBNAIL_FORMATS = ["jpg", "png", "webp"]  # Supported formats

# v2.0.0: Metadata Download Options
DEFAULT_SAVE_METADATA = False


# Download Status
class DownloadStatus:
    """Download task status constants."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


# UI Constants
WINDOW_MIN_WIDTH = 800
WINDOW_MIN_HEIGHT = 600
WINDOW_TITLE = APP_NAME

# Logging Configuration
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_MAX_SIZE = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT = 3

# File Size Display Units
SIZE_UNITS = ["B", "KB", "MB", "GB", "TB"]

# Timeout Settings (in seconds)
DOWNLOAD_TIMEOUT = 300  # 5 minutes for initial connection
PROGRESS_UPDATE_INTERVAL = 0.5  # Update UI every 500ms

# URL Validation Pattern (basic)
URL_PATTERN = r"https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)"

# Platform Detection
IS_WINDOWS = os.name == "nt"
IS_LINUX = os.name == "posix"


# Paths
def get_app_data_dir() -> Path:
    """Get application data directory based on platform."""
    if IS_WINDOWS:
        base = Path(os.getenv("APPDATA", str(Path.home() / "AppData" / "Roaming")))
    else:
        base = Path.home() / ".config"

    app_dir = base / APP_NAME
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


APP_DATA_DIR = get_app_data_dir()
CONFIG_PATH = APP_DATA_DIR / CONFIG_FILE
LOG_PATH = APP_DATA_DIR / LOG_FILE

# About Text
ABOUT_TEXT = f"""
{APP_NAME} v{APP_VERSION}

A user-friendly graphical interface for yt-dlp.

Bundled yt-dlp version: {YTDLP_VERSION}

{APP_DESCRIPTION}

For more information, visit the project repository.
"""

# Help Text
HELP_TEXT = """
How to use YT-DLP Studio:

1. Paste a video URL in the URL field
2. Select your desired quality
3. Choose output directory (optional)
4. Click Download
5. Monitor progress in the progress bar and log

Supported Sites:
YouTube
"""
