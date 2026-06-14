"""
Error handler utility for YT-DLP Studio.

Categorizes errors and provides helpful suggestions to users.
"""

from enum import Enum

from .logger import get_logger

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

        if category == ErrorCategory.NETWORK:
            return (
                "Network Error",
                "Unable to connect to the internet or the video server.",
                "• Check your internet connection\n"
                "• Verify the URL is accessible in your browser\n"
                "• Try again in a few moments\n"
                "• Check if a firewall or VPN is blocking access",
            )

        elif category == ErrorCategory.URL_INVALID:
            return (
                "Invalid URL",
                "The URL you entered is not valid or not supported.",
                "• Make sure you copied the complete URL\n"
                "• Check if the URL starts with http:// or https://\n"
                "• Verify the site is supported by yt-dlp\n"
                "• Try clicking 'Show Info' to test the URL first",
            )

        elif category == ErrorCategory.VIDEO_UNAVAILABLE:
            return (
                "Video Unavailable",
                "The video is no longer available or doesn't exist.",
                "• The video may have been deleted by the uploader\n"
                "• The URL might be incorrect or expired\n"
                "• Try refreshing the page in your browser\n"
                "• Check if the video is still accessible online",
            )

        elif category == ErrorCategory.GEO_BLOCKED:
            return (
                "Geo-Restricted Content",
                "This video is not available in your region.",
                "• The video may be restricted to certain countries\n"
                "• You might need a VPN to access this content\n"
                "• Check if the video is available in your browser\n"
                "• Try a different video or source",
            )

        elif category == ErrorCategory.COPYRIGHT:
            return (
                "Copyright Restriction",
                "This video has been removed due to copyright claims.",
                "• The video violated copyright or terms of service\n"
                "• It has been removed by the platform or uploader\n"
                "• This content cannot be downloaded\n"
                "• Look for alternative sources",
            )

        elif category == ErrorCategory.PRIVATE:
            return (
                "Private or Login Required",
                "This video is private or requires authentication.",
                "• The video may be set to private\n"
                "• You might need to be logged in to access it\n"
                "• Check if you can view it in your browser when logged in\n"
                "• Contact the video owner for access",
            )

        elif category == ErrorCategory.FORMAT:
            return (
                "Format Error",
                "There was an issue with the video or audio format.",
                "• Try a different quality setting\n"
                "• The video format may not be compatible\n"
                "• Check if 'Best Quality' works better\n"
                "• Try downloading audio only first",
            )

        elif category == ErrorCategory.DISK_SPACE:
            return (
                "Insufficient Disk Space",
                "There is not enough space to download this file.",
                "• Free up disk space on your drive\n"
                "• Choose a different download location\n"
                "• Delete unnecessary files\n"
                "• Try downloading a lower quality version",
            )

        elif category == ErrorCategory.PERMISSION:
            return (
                "Permission Denied",
                "Cannot write to the selected download directory.",
                "• Choose a different download folder\n"
                "• Check folder permissions\n"
                "• Try saving to your Downloads folder\n"
                "• Run the application as administrator (Windows)",
            )

        else:  # UNKNOWN
            return (
                "Download Failed",
                f"An error occurred during download:\n\n{error_message[:200]}",
                "• Try downloading again\n"
                "• Check the log for more details\n"
                "• Try a different quality setting\n"
                "• Verify the URL is still valid",
            )

    @staticmethod
    def format_error_dialog_text(error_message: str) -> str:
        """
        Format error message for display in dialog.

        Args:
            error_message: Raw error message

        Returns:
            Formatted HTML text for dialog
        """
        title, message, suggestions = ErrorHandler.get_error_info(error_message)

        html = f"""
<h3 style="color: #f48771;">{title}</h3>

<p><b>{message}</b></p>

<h4>Suggestions:</h4>
<p style="color: #cccccc;">{suggestions.replace(chr(10), "<br>")}</p>

<hr>

<p style="color: #858585; font-size: small;">
<b>Technical Details:</b><br>
{error_message[:300]}
</p>
"""
        return html
