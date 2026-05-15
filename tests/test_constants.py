"""Tests for src/utils/constants.py."""

import re

from src.utils.constants import (
    APP_AUTHOR,
    APP_NAME,
    APP_VERSION,
    AUDIO_FORMATS,
    AUDIO_QUALITY_MAP,
    IS_LINUX,
    IS_WINDOWS,
    QUALITY_NAMES,
    QUALITY_OPTIONS,
    SIZE_UNITS,
    URL_PATTERN,
    VIDEO_CONTAINER_FORMATS,
    DownloadStatus,
    get_app_data_dir,
)


class TestAppInfo:
    """Tests for application info constants."""

    def test_app_name(self):
        assert APP_NAME == "YT-DLP Studio"

    def test_app_version_format(self):
        assert re.match(r"^\d+\.\d+\.\d+$", APP_VERSION)

    def test_app_author(self):
        assert APP_AUTHOR == "NX1X"


class TestQualityOptions:
    """Tests for quality-related constants."""

    def test_quality_options_not_empty(self):
        assert len(QUALITY_OPTIONS) > 0

    def test_quality_names_matches_options_keys(self):
        assert QUALITY_NAMES == list(QUALITY_OPTIONS.keys())

    def test_quality_options_has_best(self):
        assert "Best Quality" in QUALITY_OPTIONS

    def test_quality_options_has_audio(self):
        audio_keys = [k for k in QUALITY_OPTIONS if "Audio" in k]
        assert len(audio_keys) >= 4

    def test_audio_quality_map_keys(self):
        assert "Audio 320kbps" in AUDIO_QUALITY_MAP
        assert "Audio 128kbps" in AUDIO_QUALITY_MAP
        assert "Best Quality" in AUDIO_QUALITY_MAP


class TestFormats:
    """Tests for format constants."""

    def test_video_container_formats(self):
        assert "MP4 (Best Compatibility)" in VIDEO_CONTAINER_FORMATS
        assert VIDEO_CONTAINER_FORMATS["MP4 (Best Compatibility)"] == "mp4"

    def test_audio_formats(self):
        assert "MP3 (Most Compatible)" in AUDIO_FORMATS
        assert AUDIO_FORMATS["MP3 (Most Compatible)"] == "mp3"


class TestDownloadStatus:
    """Tests for DownloadStatus class."""

    def test_pending(self):
        assert DownloadStatus.PENDING == "pending"

    def test_downloading(self):
        assert DownloadStatus.DOWNLOADING == "downloading"

    def test_completed(self):
        assert DownloadStatus.COMPLETED == "completed"

    def test_error(self):
        assert DownloadStatus.ERROR == "error"

    def test_cancelled(self):
        assert DownloadStatus.CANCELLED == "cancelled"


class TestOtherConstants:
    """Tests for remaining constants."""

    def test_size_units(self):
        assert SIZE_UNITS == ["B", "KB", "MB", "GB", "TB"]

    def test_url_pattern_matches_valid_url(self):
        assert re.match(URL_PATTERN, "https://www.youtube.com/watch?v=test")

    def test_url_pattern_rejects_invalid(self):
        assert re.match(URL_PATTERN, "not a url") is None

    def test_platform_detection(self):
        assert IS_WINDOWS or IS_LINUX

    def test_get_app_data_dir(self):
        result = get_app_data_dir()
        assert result.exists()
        assert result.is_dir()
