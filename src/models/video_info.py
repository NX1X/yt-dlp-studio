"""
Video information data model.

This module defines the structure for video metadata extracted from URLs.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class VideoInfo:
    """
    Video metadata extracted from URL.

    This class holds information about a video extracted using yt-dlp,
    such as title, duration, formats, etc.

    Attributes:
        title: Video title
        url: Original URL
        duration: Video duration in seconds
        thumbnail: Thumbnail URL
        description: Video description
        uploader: Channel/uploader name
        upload_date: Upload date string (YYYYMMDD)
        view_count: Number of views
        like_count: Number of likes
        formats: List of available formats
        extractor: Extractor name (e.g., 'youtube')
        subtitles: Dict of available subtitles {lang: [subtitle_dicts]}
        automatic_captions: Dict of available auto-generated captions
    """

    title: str
    url: str
    duration: int = 0
    thumbnail: str | None = None
    description: str = ""
    uploader: str = ""
    upload_date: str = ""
    view_count: int = 0
    like_count: int = 0
    formats: list[dict[str, Any]] = None
    extractor: str = ""
    subtitles: dict[str, list[dict[str, Any]]] = None
    automatic_captions: dict[str, list[dict[str, Any]]] = None

    def __post_init__(self):
        """Initialize mutable default values."""
        if self.formats is None:
            self.formats = []
        if self.subtitles is None:
            self.subtitles = {}
        if self.automatic_captions is None:
            self.automatic_captions = {}

    @classmethod
    def from_yt_dlp_dict(cls, info_dict: dict[str, Any]) -> "VideoInfo":
        """
        Create VideoInfo from yt-dlp info dictionary.

        Args:
            info_dict: Dictionary returned by yt-dlp extract_info

        Returns:
            VideoInfo instance
        """
        return cls(
            title=info_dict.get("title", "Unknown Title"),
            url=info_dict.get("webpage_url", info_dict.get("url", "")),
            duration=info_dict.get("duration", 0),
            thumbnail=info_dict.get("thumbnail"),
            description=info_dict.get("description", ""),
            uploader=info_dict.get("uploader", ""),
            upload_date=info_dict.get("upload_date", ""),
            view_count=info_dict.get("view_count", 0),
            like_count=info_dict.get("like_count", 0),
            formats=info_dict.get("formats", []),
            extractor=info_dict.get("extractor", ""),
            subtitles=info_dict.get("subtitles", {}),
            automatic_captions=info_dict.get("automatic_captions", {}),
        )

    def get_available_subtitle_languages(self) -> list[str]:
        """
        Get list of all available subtitle language codes.

        Returns:
            List of language codes (e.g., ['en', 'es', 'fr'])
        """
        manual_subs = set(self.subtitles.keys()) if self.subtitles else set()
        auto_subs = set(self.automatic_captions.keys()) if self.automatic_captions else set()
        return sorted(manual_subs | auto_subs)

    def get_duration_formatted(self) -> str:
        """
        Get formatted duration string.

        Returns:
            Duration in format "HH:MM:SS" or "MM:SS"
        """
        if self.duration <= 0:
            return "Unknown"

        hours = self.duration // 3600
        minutes = (self.duration % 3600) // 60
        seconds = self.duration % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    def get_short_title(self, max_length: int = 50) -> str:
        """
        Get truncated title.

        Args:
            max_length: Maximum title length

        Returns:
            Truncated title with ellipsis if needed
        """
        if len(self.title) <= max_length:
            return self.title
        return self.title[: max_length - 3] + "..."

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"VideoInfo(title='{self.title}', duration={self.duration}s, uploader='{self.uploader}')"
