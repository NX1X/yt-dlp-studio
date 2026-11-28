"""
Format selection handler for YT-DLP Studio.

This module handles conversion between user-friendly quality names
and yt-dlp format strings.
"""

from ..utils.constants import AUDIO_QUALITY_MAP, QUALITY_NAMES, QUALITY_OPTIONS
from ..utils.logger import get_logger
from ..utils.translations import tr

logger = get_logger()

# Quality display names (defined once to avoid duplicated literals below).
_Q_BEST = "Best Quality"
_Q_8K = "8K (4320p)"
_Q_4K = "4K (2160p)"
_Q_2K = "2K (1440p)"
_Q_1080P = "1080p (Full HD)"
_Q_720P = "720p (HD)"
_Q_480P = "480p (SD)"


class FormatHandler:
    """
    Handles format/quality selection for downloads.

    Converts user-friendly quality names to yt-dlp format strings.
    """

    @staticmethod
    def _get_english_quality_name(translated_name: str) -> str:
        """
        Convert translated quality name back to English key.

        Args:
            translated_name: Translated quality name from UI

        Returns:
            English quality key for QUALITY_OPTIONS lookup
        """
        # Reverse mapping from translated to English
        reverse_map = {
            tr("quality_best"): _Q_BEST,
            tr("quality_1080p"): _Q_1080P,
            tr("quality_720p"): _Q_720P,
            tr("quality_480p"): _Q_480P,
        }

        # Check exact matches first
        if translated_name in reverse_map:
            return reverse_map[translated_name]

        # Check audio quality options
        audio_only = tr("quality_audio_only")
        if translated_name.startswith(audio_only):
            # Extract bitrate (e.g., "320kbps")
            bitrate = translated_name.replace(audio_only, "").strip()
            return f"Audio {bitrate}"

        # If no translation match, assume it's already English or keep as-is
        # (for resolution-based like "8K (4320p)", "4K (2160p)", "360p")
        return translated_name

    @staticmethod
    def get_format_string(quality_name: str) -> str:
        """
        Get yt-dlp format string from quality name (translated or English).

        Args:
            quality_name: User-friendly quality name (e.g., "Best Quality", "720p", or Hebrew equivalent)

        Returns:
            yt-dlp format string

        Example:
            >>> format_str = FormatHandler.get_format_string("720p")
            >>> print(format_str)  # "bestvideo[height<=720]+bestaudio/best[height<=720]"
        """
        # Convert translated name to English key
        english_name = FormatHandler._get_english_quality_name(quality_name)
        format_string = QUALITY_OPTIONS.get(english_name, QUALITY_OPTIONS[_Q_BEST])
        logger.debug(f"Quality '{quality_name}' (English: '{english_name}') -> Format '{format_string}'")
        return format_string

    @staticmethod
    def is_audio_only(quality_name: str) -> bool:
        """
        Check if quality selection is audio-only.

        Args:
            quality_name: Quality name

        Returns:
            True if audio only, False otherwise

        Example:
            >>> is_audio = FormatHandler.is_audio_only("Audio 192kbps")
            >>> print(is_audio)  # True
        """
        return "Audio" in quality_name and "kbps" in quality_name

    @staticmethod
    def get_audio_quality(quality_name: str) -> str:
        """
        Get audio quality (kbps) from quality name.

        Args:
            quality_name: Quality name (e.g., "Audio 320kbps")

        Returns:
            Audio quality in kbps (e.g., "320")

        Example:
            >>> quality = FormatHandler.get_audio_quality("Audio 320kbps")
            >>> print(quality)  # "320"
        """
        return AUDIO_QUALITY_MAP.get(quality_name, "192")

    @staticmethod
    def get_available_qualities() -> list:
        """
        Get list of available quality options (translated).

        Returns:
            List of quality names

        Example:
            >>> qualities = FormatHandler.get_available_qualities()
            >>> for q in qualities:
            >>>     print(q)
        """
        # Map English quality names to translation keys
        quality_map = {
            _Q_BEST: tr("quality_best"),
            _Q_8K: _Q_8K,
            _Q_4K: _Q_4K,
            _Q_2K: _Q_2K,
            _Q_1080P: tr("quality_1080p"),
            _Q_720P: tr("quality_720p"),
            _Q_480P: tr("quality_480p"),
            "360p": "360p",
            "Audio 320kbps": tr("quality_audio_only") + " 320kbps",
            "Audio 256kbps": tr("quality_audio_only") + " 256kbps",
            "Audio 192kbps": tr("quality_audio_only") + " 192kbps",
            "Audio 128kbps": tr("quality_audio_only") + " 128kbps",
        }
        return [quality_map.get(name, name) for name in QUALITY_NAMES]

    @staticmethod
    def validate_quality(quality_name: str) -> tuple[bool, str]:
        """
        Validate quality name.

        Args:
            quality_name: Quality name to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if quality_name in QUALITY_NAMES:
            return True, ""
        else:
            return False, f"Invalid quality. Choose from: {', '.join(QUALITY_NAMES)}"

    @staticmethod
    def get_default_quality() -> str:
        """
        Get default quality option.

        Returns:
            Default quality name
        """
        return _Q_BEST

    @staticmethod
    def get_quality_description(quality_name: str) -> str:
        """
        Get description of quality option.

        Args:
            quality_name: Quality name

        Returns:
            Human-readable description

        Example:
            >>> desc = FormatHandler.get_quality_description("1080p (Full HD)")
            >>> print(desc)  # "Full HD quality (1920x1080) - Recommended for most devices"
        """
        # Texts live in src/utils/translations.py under quality_desc_*.
        description_keys = {
            _Q_BEST: "quality_desc_best",
            _Q_8K: "quality_desc_8k",
            _Q_4K: "quality_desc_4k",
            _Q_2K: "quality_desc_2k",
            _Q_1080P: "quality_desc_1080p",
            _Q_720P: "quality_desc_720p",
            _Q_480P: "quality_desc_480p",
            "360p": "quality_desc_360p",
            "Audio 320kbps": "quality_desc_audio_320",
            "Audio 256kbps": "quality_desc_audio_256",
            "Audio 192kbps": "quality_desc_audio_192",
            "Audio 128kbps": "quality_desc_audio_128",
        }

        key = description_keys.get(quality_name)
        return tr(key) if key else tr("quality_desc_none")
