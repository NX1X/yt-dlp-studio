"""
Playlist information fetcher for YT-DLP Studio.

Extracts information about all videos in a playlist using yt-dlp.
"""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..utils.logger import get_logger

logger = get_logger()

# Add vendored yt_dlp_engine to Python path.
# In a PyInstaller bundle the engine is extracted to <_MEIPASS>/yt_dlp_engine
# (see packaging/build.spec datas); running from source it lives at
# <project_root>/vendor/yt_dlp_engine.
if getattr(sys, "frozen", False):
    _bundle_dir = getattr(sys, "_MEIPASS", None)
    _engine_path = Path(_bundle_dir) / "yt_dlp_engine" if _bundle_dir else None
else:
    _current_dir = Path(__file__).resolve().parent
    _project_root = _current_dir.parent.parent
    _engine_path = _project_root / "vendor" / "yt_dlp_engine"

if _engine_path is not None and str(_engine_path) not in sys.path:
    sys.path.insert(0, str(_engine_path))

try:
    from yt_dlp import YoutubeDL

    logger.debug("yt-dlp imported successfully for playlist fetching")
except ImportError as e:
    logger.error(f"Failed to import yt-dlp: {e}")
    raise


@dataclass
class PlaylistVideoInfo:
    """Information about a single video in a playlist."""

    title: str
    url: str
    duration: int = 0  # seconds
    thumbnail: str | None = None
    uploader: str = ""
    view_count: int = 0
    index: int = 0  # position in playlist

    def get_duration_formatted(self) -> str:
        """Get formatted duration string."""
        if self.duration <= 0:
            return "Unknown"

        hours = self.duration // 3600
        minutes = (self.duration % 3600) // 60
        seconds = self.duration % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"


@dataclass
class PlaylistInfo:
    """Information about a playlist."""

    title: str
    url: str
    video_count: int
    uploader: str = ""
    description: str = ""
    videos: list[PlaylistVideoInfo] = None

    def __post_init__(self):
        """Initialize mutable default values."""
        if self.videos is None:
            self.videos = []


class PlaylistFetcher:
    """
    Fetches playlist information using yt-dlp.

    Extracts metadata about playlists and their videos.
    """

    @staticmethod
    def fetch_playlist_info(url: str) -> PlaylistInfo | None:
        """
        Fetch complete playlist information.

        Args:
            url: Playlist URL

        Returns:
            PlaylistInfo object or None on error
        """
        logger.info(f"Fetching playlist info: {url}")

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",  # Don't download, just extract info
            "skip_download": True,
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=False)

                if info_dict is None:
                    logger.error("No playlist information extracted")
                    return None

                # Check if it's actually a playlist
                if info_dict.get("_type") != "playlist":
                    logger.warning("URL is not a playlist")
                    return None

                # Extract playlist info
                playlist_info = PlaylistInfo(
                    title=info_dict.get("title", "Unknown Playlist"),
                    url=url,
                    video_count=info_dict.get("playlist_count", 0),
                    uploader=info_dict.get("uploader", info_dict.get("channel", "")),
                    description=info_dict.get("description", ""),
                )

                # Extract videos
                entries = info_dict.get("entries", [])
                videos = []

                for idx, entry in enumerate(entries):
                    if entry is None:
                        continue

                    video = PlaylistVideoInfo(
                        title=entry.get("title", "Unknown Title"),
                        url=entry.get("url", entry.get("webpage_url", "")),
                        duration=entry.get("duration", 0),
                        thumbnail=entry.get("thumbnail"),
                        uploader=entry.get("uploader", entry.get("channel", "")),
                        view_count=entry.get("view_count", 0),
                        index=idx + 1,
                    )
                    videos.append(video)

                playlist_info.videos = videos
                playlist_info.video_count = len(videos)

                logger.info(f"Playlist info fetched: {playlist_info.title} ({len(videos)} videos)")
                return playlist_info

        except Exception as e:
            logger.error(f"Error fetching playlist info: {e}")
            return None

    @staticmethod
    def fetch_playlist_quick(url: str) -> dict[str, Any] | None:
        """
        Fetch basic playlist info quickly (without full video details).

        Args:
            url: Playlist URL

        Returns:
            Dictionary with basic playlist info or None on error
        """
        logger.info(f"Quick fetching playlist info: {url}")

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,  # Very fast, minimal info
            "skip_download": True,
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=False)

                if info_dict is None or info_dict.get("_type") != "playlist":
                    return None

                return {
                    "title": info_dict.get("title", "Unknown Playlist"),
                    "video_count": info_dict.get("playlist_count", len(info_dict.get("entries", []))),
                    "uploader": info_dict.get("uploader", info_dict.get("channel", "")),
                }

        except Exception as e:
            logger.error(f"Error in quick playlist fetch: {e}")
            return None
