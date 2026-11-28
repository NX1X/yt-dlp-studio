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
# Windows taskbar identity. Must match AppUserModelID in packaging/installer.iss,
# which the installer puts on the Start-menu and desktop shortcuts.
APP_USER_MODEL_ID = "NX1X.YTDLPStudio"
APP_AUTHOR = "NX1X"
APP_ORGANIZATION = "NXTools"
APP_WEBSITE = "https://nx1xlab.dev"
APP_NXTOOLS_WEBSITE = "https://nx1xlab.dev/nxtools"
APP_DESCRIPTION = "A user-friendly GUI for yt-dlp video downloader"
# Online help that F1 opens (the README on GitHub)
APP_DOCS_URL = "https://github.com/NX1X/yt-dlp-studio#readme"

# yt-dlp Engine Information
YTDLP_VERSION = "2026.11.23"  # Version of bundled yt-dlp
YTDLP_ENGINE_DIR = "vendor/yt_dlp_engine"

# File Names
CONFIG_FILE = "yt-dlp-studio_config.json"
LOG_FILE = "yt-dlp-studio.log"

# Default Settings
DEFAULT_OUTPUT_DIR = str(Path.home() / "Downloads")
DEFAULT_QUALITY = "best"  # best, 1080p, 720p, 480p, audio
DEFAULT_MAX_CONCURRENT_DOWNLOADS = 1  # v1.0 only supports single download

# yt-dlp format string for "best available audio", shared by all audio-only
# quality options (defined once to avoid a duplicated literal).
_AUDIO_BEST = "bestaudio/best"


def _height_capped(height: int) -> str:
    """Format string for the best quality up to ``height`` pixels.

    ``<=?`` also accepts a format that has no height (Facebook sd/hd,
    Instagram progressive files), which the plain ``<=`` drops. The
    ``vcodec!=?none`` filter keeps the second choice from taking an
    audio-only format. If every format is taller than the cap, the last two
    choices take the smallest one, so the download works instead of failing
    with "Requested format is not available". Where heights are known, the
    result is the same as the old ``bestvideo[height<=N]+bestaudio`` choice.
    """
    return f"bestvideo[height<=?{height}]+bestaudio/best[height<=?{height}][vcodec!=?none]/worstvideo+bestaudio/worst"


# Quality Options for v1.5.0 - Enhanced with 2K, 4K, 8K and multiple audio quality options
QUALITY_OPTIONS = {
    # Video Quality Options
    "Best Quality": "bestvideo+bestaudio/best",
    "8K (4320p)": _height_capped(4320),
    "4K (2160p)": _height_capped(2160),
    "2K (1440p)": _height_capped(1440),
    "1080p (Full HD)": _height_capped(1080),
    "720p (HD)": _height_capped(720),
    "480p (SD)": _height_capped(480),
    "360p": _height_capped(360),
    # Audio Quality Options
    "Audio 320kbps": _AUDIO_BEST,
    "Audio 256kbps": _AUDIO_BEST,
    "Audio 192kbps": _AUDIO_BEST,
    "Audio 128kbps": _AUDIO_BEST,
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
_MP4_KEY = "MP4 (Best Compatibility)"
_MP3_KEY = "MP3 (Most Compatible)"
VIDEO_CONTAINER_FORMATS = {
    _MP4_KEY: "mp4",
    "MKV (Matroska)": "mkv",
    "WebM": "webm",
    "Auto (Best Quality)": None,  # Let yt-dlp choose
}
DEFAULT_VIDEO_CONTAINER = _MP4_KEY
# The keys above are stable lookup keys (the Download tab stores them as combo
# item data). The text the user sees comes from these translation keys.
VIDEO_CONTAINER_LABEL_KEYS = {
    _MP4_KEY: "format_video_mp4",
    "MKV (Matroska)": "format_video_mkv",
    "WebM": "format_video_webm",
    "Auto (Best Quality)": "format_video_auto",
}

# v2.0.0: Audio Format Options
AUDIO_FORMATS = {
    _MP3_KEY: "mp3",
    "M4A/AAC (High Quality)": "m4a",
    "OPUS (Best Quality/Size)": "opus",
    "FLAC (Lossless)": "flac",
    "WAV (Uncompressed)": "wav",
    "Vorbis/OGG": "vorbis",
}
DEFAULT_AUDIO_FORMAT = _MP3_KEY
AUDIO_FORMAT_LABEL_KEYS = {
    _MP3_KEY: "format_audio_mp3",
    "M4A/AAC (High Quality)": "format_audio_m4a",
    "OPUS (Best Quality/Size)": "format_audio_opus",
    "FLAC (Lossless)": "format_audio_flac",
    "WAV (Uncompressed)": "format_audio_wav",
    "Vorbis/OGG": "format_audio_vorbis",
}

# Thumbnail settings (v1.7.0)
THUMBNAIL_DOWNLOAD = False  # Thumbnail off by default; the user opts in
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
