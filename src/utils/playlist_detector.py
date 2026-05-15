"""
Playlist detection utility for YT-DLP Studio.

Detects if a URL is a playlist and provides playlist information.
"""

import re

from .logger import get_logger

logger = get_logger()


class PlaylistDetector:
    """
    Utility to detect playlist URLs and extract basic information.

    Detects playlists from various platforms before downloading.
    """

    # Common playlist URL patterns
    PLAYLIST_PATTERNS = {
        "youtube": [
            r"list=([a-zA-Z0-9_-]+)",  # ?list=PLAYLIST_ID
            r"/playlist\?",  # /playlist?...
        ],
        "youtube_channel": [
            r"/@([^/]+)/videos",  # /@channel/videos
            r"/channel/([^/]+)/videos",  # /channel/ID/videos
            r"/c/([^/]+)/videos",  # /c/channel/videos
            r"/user/([^/]+)/videos",  # /user/USERNAME/videos
        ],
        "vimeo": [
            r"vimeo\.com/album/(\d+)",  # vimeo.com/album/123
            r"vimeo\.com/channels/([^/]+)",  # vimeo.com/channels/name
        ],
        "dailymotion": [
            r"dailymotion\.com/playlist/",  # dailymotion.com/playlist/...
        ],
    }

    @staticmethod
    def is_playlist_url(url: str) -> tuple[bool, str]:
        """
        Check if URL is a playlist.

        Args:
            url: Video/playlist URL

        Returns:
            Tuple of (is_playlist, platform_type)
            platform_type can be: 'youtube', 'youtube_channel', 'vimeo', 'dailymotion', 'unknown'
        """
        # Check YouTube playlists
        for pattern in PlaylistDetector.PLAYLIST_PATTERNS["youtube"]:
            if re.search(pattern, url):
                logger.info(f"Detected YouTube playlist: {url}")
                return (True, "youtube")

        # Check YouTube channels
        for pattern in PlaylistDetector.PLAYLIST_PATTERNS["youtube_channel"]:
            if re.search(pattern, url):
                logger.info(f"Detected YouTube channel: {url}")
                return (True, "youtube_channel")

        # Check Vimeo
        for pattern in PlaylistDetector.PLAYLIST_PATTERNS["vimeo"]:
            if re.search(pattern, url):
                logger.info(f"Detected Vimeo playlist/album: {url}")
                return (True, "vimeo")

        # Check Dailymotion
        for pattern in PlaylistDetector.PLAYLIST_PATTERNS["dailymotion"]:
            if re.search(pattern, url):
                logger.info(f"Detected Dailymotion playlist: {url}")
                return (True, "dailymotion")

        logger.debug(f"URL is not a playlist: {url}")
        return (False, "unknown")

    @staticmethod
    def extract_playlist_id(url: str, platform: str) -> str:
        """
        Extract playlist ID from URL.

        Args:
            url: Playlist URL
            platform: Platform type ('youtube', 'vimeo', etc.)

        Returns:
            Playlist ID or empty string if not found
        """
        if platform == "youtube":
            match = re.search(r"list=([a-zA-Z0-9_-]+)", url)
            if match:
                return match.group(1)

        elif platform == "youtube_channel":
            # Extract channel identifier
            for pattern in [r"/@([^/]+)", r"/channel/([^/]+)", r"/c/([^/]+)", r"/user/([^/]+)"]:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)

        elif platform == "vimeo":
            match = re.search(r"/album/(\d+)", url)
            if match:
                return match.group(1)
            match = re.search(r"/channels/([^/]+)", url)
            if match:
                return match.group(1)

        elif platform == "dailymotion":
            match = re.search(r"/playlist/([^/]+)", url)
            if match:
                return match.group(1)

        return ""

    @staticmethod
    def get_platform_name(platform: str) -> str:
        """
        Get friendly platform name.

        Args:
            platform: Platform identifier

        Returns:
            Friendly platform name
        """
        platform_names = {
            "youtube": "YouTube Playlist",
            "youtube_channel": "YouTube Channel",
            "vimeo": "Vimeo Album/Channel",
            "dailymotion": "Dailymotion Playlist",
            "unknown": "Unknown",
        }
        return platform_names.get(platform, "Unknown")
