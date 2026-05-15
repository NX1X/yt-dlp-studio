"""Tests for src/utils/error_handler.py."""

from src.utils.error_handler import ErrorCategory, ErrorHandler


class TestCategorizeError:
    """Tests for ErrorHandler.categorize_error()."""

    def test_network_error(self):
        assert ErrorHandler.categorize_error("connection timeout") == ErrorCategory.NETWORK

    def test_network_dns(self):
        assert ErrorHandler.categorize_error("DNS resolution failed") == ErrorCategory.NETWORK

    def test_url_invalid(self):
        assert ErrorHandler.categorize_error("unsupported URL") == ErrorCategory.URL_INVALID

    def test_url_no_formats(self):
        assert ErrorHandler.categorize_error("no video formats found") == ErrorCategory.URL_INVALID

    def test_video_unavailable(self):
        assert ErrorHandler.categorize_error("This video is unavailable") == ErrorCategory.VIDEO_UNAVAILABLE

    def test_video_404(self):
        assert ErrorHandler.categorize_error("HTTP Error 404: Not Found") == ErrorCategory.VIDEO_UNAVAILABLE

    def test_geo_blocked(self):
        assert ErrorHandler.categorize_error("not available in your country") == ErrorCategory.GEO_BLOCKED

    def test_copyright(self):
        assert ErrorHandler.categorize_error("removed due to copyright") == ErrorCategory.COPYRIGHT

    def test_private(self):
        assert ErrorHandler.categorize_error("Sign in to confirm your age") == ErrorCategory.PRIVATE

    def test_format_error(self):
        assert ErrorHandler.categorize_error("requested format not available") == ErrorCategory.FORMAT

    def test_disk_space(self):
        assert ErrorHandler.categorize_error("no space left on device") == ErrorCategory.DISK_SPACE

    def test_permission(self):
        assert ErrorHandler.categorize_error("permission denied") == ErrorCategory.PERMISSION

    def test_unknown(self):
        assert ErrorHandler.categorize_error("some random error xyz") == ErrorCategory.UNKNOWN


class TestGetErrorInfo:
    """Tests for ErrorHandler.get_error_info()."""

    def test_returns_tuple_of_three(self):
        result = ErrorHandler.get_error_info("connection timeout")
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_network_error_title(self):
        title, message, suggestions = ErrorHandler.get_error_info("connection timeout")
        assert title == "Network Error"
        assert "internet" in message.lower()

    def test_all_categories_return_valid_info(self):
        test_messages = {
            ErrorCategory.NETWORK: "connection timeout",
            ErrorCategory.URL_INVALID: "unsupported URL",
            ErrorCategory.VIDEO_UNAVAILABLE: "video unavailable",
            ErrorCategory.GEO_BLOCKED: "not available in your country",
            ErrorCategory.COPYRIGHT: "copyright claim",
            ErrorCategory.PRIVATE: "private video",
            ErrorCategory.FORMAT: "format not available",
            ErrorCategory.DISK_SPACE: "no space left",
            ErrorCategory.PERMISSION: "permission denied",
            ErrorCategory.UNKNOWN: "random error",
        }
        for _category, msg in test_messages.items():
            title, message, suggestions = ErrorHandler.get_error_info(msg)
            assert isinstance(title, str) and len(title) > 0
            assert isinstance(message, str) and len(message) > 0
            assert isinstance(suggestions, str) and len(suggestions) > 0


class TestFormatErrorDialogText:
    """Tests for ErrorHandler.format_error_dialog_text()."""

    def test_returns_html(self):
        result = ErrorHandler.format_error_dialog_text("connection timeout")
        assert "<h3" in result
        assert "Network Error" in result

    def test_includes_technical_details(self):
        result = ErrorHandler.format_error_dialog_text("some weird error message")
        assert "some weird error message" in result


class TestErrorCategoryEnum:
    """Tests for ErrorCategory enum."""

    def test_all_categories_exist(self):
        expected = [
            "NETWORK",
            "URL_INVALID",
            "VIDEO_UNAVAILABLE",
            "GEO_BLOCKED",
            "COPYRIGHT",
            "PRIVATE",
            "FORMAT",
            "DISK_SPACE",
            "PERMISSION",
            "UNKNOWN",
        ]
        for name in expected:
            assert hasattr(ErrorCategory, name)
