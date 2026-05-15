"""
Tests for input validators.

Run with: pytest tests/test_validators.py -v
"""

from src.utils.validators import Validators


class TestURLValidation:
    """Test suite for URL validation."""

    def test_valid_youtube_url(self):
        """Test valid YouTube URL."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        is_valid, error = Validators.is_valid_url(url)

        assert is_valid is True
        assert error == ""

    def test_valid_vimeo_url(self):
        """Test valid Vimeo URL."""
        url = "https://vimeo.com/123456789"
        is_valid, error = Validators.is_valid_url(url)

        assert is_valid is True
        assert error == ""

    def test_invalid_url_no_protocol(self):
        """Test URL without protocol."""
        url = "youtube.com/watch?v=test"
        is_valid, error = Validators.is_valid_url(url)

        assert is_valid is False
        assert "http" in error.lower()

    def test_empty_url(self):
        """Test empty URL."""
        url = ""
        is_valid, error = Validators.is_valid_url(url)

        assert is_valid is False
        assert "empty" in error.lower()

    def test_url_with_spaces(self):
        """Test URL with spaces."""
        url = "https://youtube.com/watch ?v=test"
        is_valid, error = Validators.is_valid_url(url)

        assert is_valid is False
        assert "space" in error.lower()


class TestFilenameValidation:
    """Test suite for filename sanitization."""

    def test_sanitize_normal_filename(self):
        """Test sanitizing normal filename."""
        filename = "My Video"
        result = Validators.sanitize_filename(filename)

        assert result == "My Video"

    def test_sanitize_filename_with_invalid_chars(self):
        """Test sanitizing filename with invalid characters."""
        filename = "Video: Cool <2024>"
        result = Validators.sanitize_filename(filename)

        # Should remove :, <, >
        assert ":" not in result
        assert "<" not in result
        assert ">" not in result

    def test_sanitize_empty_filename(self):
        """Test sanitizing empty filename."""
        filename = ""
        result = Validators.sanitize_filename(filename)

        assert result == "download"  # Default name

    def test_sanitize_long_filename(self):
        """Test sanitizing very long filename."""
        filename = "a" * 300
        result = Validators.sanitize_filename(filename)

        # Should be truncated
        assert len(result) <= 200


# TODO: Add more tests:
# - test_validate_directory
# - test_validate_quality_choice
