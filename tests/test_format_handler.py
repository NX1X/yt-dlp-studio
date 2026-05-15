"""Tests for src/backend/format_handler.py."""

from src.backend.format_handler import FormatHandler


class TestGetFormatString:
    """Tests for FormatHandler.get_format_string()."""

    def test_best_quality(self):
        result = FormatHandler.get_format_string("Best Quality")
        assert result == "bestvideo+bestaudio/best"

    def test_1080p(self):
        result = FormatHandler.get_format_string("1080p (Full HD)")
        assert "1080" in result

    def test_720p(self):
        result = FormatHandler.get_format_string("720p (HD)")
        assert "720" in result

    def test_audio_320kbps(self):
        result = FormatHandler.get_format_string("Audio 320kbps")
        assert "bestaudio" in result

    def test_unknown_defaults_to_best(self):
        result = FormatHandler.get_format_string("NonexistentQuality")
        assert result == "bestvideo+bestaudio/best"


class TestIsAudioOnly:
    """Tests for FormatHandler.is_audio_only()."""

    def test_audio_320(self):
        assert FormatHandler.is_audio_only("Audio 320kbps") is True

    def test_audio_192(self):
        assert FormatHandler.is_audio_only("Audio 192kbps") is True

    def test_best_quality(self):
        assert FormatHandler.is_audio_only("Best Quality") is False

    def test_video_1080p(self):
        assert FormatHandler.is_audio_only("1080p (Full HD)") is False


class TestGetAudioQuality:
    """Tests for FormatHandler.get_audio_quality()."""

    def test_320kbps(self):
        assert FormatHandler.get_audio_quality("Audio 320kbps") == "320"

    def test_128kbps(self):
        assert FormatHandler.get_audio_quality("Audio 128kbps") == "128"

    def test_best_quality(self):
        assert FormatHandler.get_audio_quality("Best Quality") == "0"

    def test_unknown_defaults_to_192(self):
        assert FormatHandler.get_audio_quality("Nonexistent") == "192"


class TestGetAvailableQualities:
    """Tests for FormatHandler.get_available_qualities()."""

    def test_returns_list(self):
        result = FormatHandler.get_available_qualities()
        assert isinstance(result, list)
        assert len(result) == 12  # 8 video + 4 audio


class TestValidateQuality:
    """Tests for FormatHandler.validate_quality()."""

    def test_valid(self):
        valid, error = FormatHandler.validate_quality("Best Quality")
        assert valid is True
        assert error == ""

    def test_invalid(self):
        valid, error = FormatHandler.validate_quality("FakeQuality")
        assert valid is False
        assert "Invalid" in error


class TestGetDefaultQuality:
    """Tests for FormatHandler.get_default_quality()."""

    def test_default(self):
        assert FormatHandler.get_default_quality() == "Best Quality"


class TestGetQualityDescription:
    """Tests for FormatHandler.get_quality_description()."""

    def test_known(self):
        desc = FormatHandler.get_quality_description("1080p (Full HD)")
        assert "1920x1080" in desc

    def test_unknown(self):
        desc = FormatHandler.get_quality_description("NonexistentQuality")
        assert desc == "No description available"
