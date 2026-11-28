"""
Error handler utility for YT-DLP Studio.

Categorizes errors and provides helpful suggestions to users.
"""

from enum import Enum

from .logger import get_logger
from .translations import tr

logger = get_logger()


class ErrorCategory(Enum):
    """Error categories for better user feedback."""

    NETWORK = "network"
    URL_INVALID = "url_invalid"
    VIDEO_UNAVAILABLE = "video_unavailable"
    GEO_BLOCKED = "geo_blocked"
    COPYRIGHT = "copyright"
    PRIVATE = "private"
    FORMAT = "format"
    DISK_SPACE = "disk_space"
    PERMISSION = "permission"
    UNKNOWN = "unknown"


class ErrorHandler:
    """
    Handles and categorizes errors with helpful suggestions.

    Provides user-friendly error messages and suggestions for common issues.
    """

    @staticmethod
    def categorize_error(error_message: str) -> ErrorCategory:
        """
        Categorize error based on error message.

        Args:
            error_message: Error message string

        Returns:
            ErrorCategory enum value
        """
        error_lower = error_message.lower()

        # Network errors
        if any(
            keyword in error_lower
            for keyword in [
                "network",
                "connection",
                "timeout",
                "timed out",
                "unable to download",
                "urlopen error",
                "socket",
                "no internet",
                "dns",
                "resolve",
            ]
        ):
            return ErrorCategory.NETWORK

        # URL invalid
        if any(
            keyword in error_lower
            for keyword in [
                "unsupported url",
                "invalid url",
                "unable to extract",
                "no video formats found",
                "not a valid url",
            ]
        ):
            return ErrorCategory.URL_INVALID

        # Video unavailable
        if any(
            keyword in error_lower
            for keyword in [
                "video unavailable",
                "this video is unavailable",
                "video has been removed",
                "video does not exist",
                "404",
                "not found",
            ]
        ):
            return ErrorCategory.VIDEO_UNAVAILABLE

        # Geo-blocked
        if any(
            keyword in error_lower
            for keyword in ["geo", "region", "country", "location", "not available in your", "blocked in your country"]
        ):
            return ErrorCategory.GEO_BLOCKED

        # Copyright/DMCA
        if any(
            keyword in error_lower for keyword in ["copyright", "dmca", "terms of service", "violat", "removed due to"]
        ):
            return ErrorCategory.COPYRIGHT

        # Private video
        if any(
            keyword in error_lower
            for keyword in ["private", "sign in", "login required", "members only", "authentication"]
        ):
            return ErrorCategory.PRIVATE

        # Format errors
        if any(keyword in error_lower for keyword in ["format", "codec", "audio", "video stream"]):
            return ErrorCategory.FORMAT

        # Disk space
        if any(
            keyword in error_lower for keyword in ["disk", "space", "no space left", "out of space", "quota exceeded"]
        ):
            return ErrorCategory.DISK_SPACE

        # Permission errors
        if any(
            keyword in error_lower for keyword in ["permission denied", "access denied", "cannot write", "read-only"]
        ):
            return ErrorCategory.PERMISSION

        return ErrorCategory.UNKNOWN

    @staticmethod
    def get_error_info(error_message: str) -> tuple[str, str, str]:
        """
        Get detailed error information with title, message, and suggestions.

        Args:
            error_message: Raw error message

        Returns:
            Tuple of (title, user_friendly_message, suggestions)
        """
        category = ErrorHandler.categorize_error(error_message)
        logger.info(f"Error categorized as: {category.value}")

        # Texts live in src/utils/translations.py under errcat_<category>_*.
        prefix = f"errcat_{category.value}"
        return (
            tr(f"{prefix}_title"),
            tr(f"{prefix}_message", detail=error_message[:200]),
            tr(f"{prefix}_suggestions"),
        )

    @staticmethod
    def format_error_dialog_text(error_message: str, colors: dict[str, str] | None = None) -> str:
        """
        Format error message for display in dialog.

        Args:
            error_message: Raw error message
            colors: Optional theme colors ("error", "text_secondary"). Without
                them the text uses the dialog's own colors, which read in
                both themes.

        Returns:
            Formatted HTML text for dialog
        """
        import html

        title, message, suggestions = ErrorHandler.get_error_info(error_message)
        colors = colors or {}
        title_style = f' style="color: {colors["error"]};"' if "error" in colors else ""
        detail_color = f"color: {colors['text_secondary']}; " if "text_secondary" in colors else ""
        suggestions_html = html.escape(suggestions).replace(chr(10), "<br>")

        return f"""
<h3{title_style}>{html.escape(title)}</h3>

<p><b>{html.escape(message)}</b></p>

<h4>{html.escape(tr("header_error_suggestions"))}</h4>
<p>{suggestions_html}</p>

<hr>

<p style="{detail_color}font-size: small;"><b>{html.escape(tr("header_error_technical_details"))}</b></p>
<p dir="ltr" align="left" style="{detail_color}font-size: small;">{html.escape(error_message[:300])}</p>
"""
