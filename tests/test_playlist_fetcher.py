"""Tests for PlaylistVideoInfo formatting (src/backend/playlist_fetcher.py)."""

from src.backend.playlist_fetcher import PlaylistVideoInfo


class TestGetDurationFormatted:
    """Duration formatting must tolerate the float durations yt-dlp reports."""

    def test_float_duration_does_not_crash(self):
        # Regression: yt-dlp returns duration as a float (e.g. 245.0). The
        # ``:02d`` format code requires ints, so a float used to raise
        # ValueError and crash the playlist dialog.
        video = PlaylistVideoInfo(title="t", url="u", duration=245.0)
        assert video.get_duration_formatted() == "04:05"

    def test_float_duration_with_hours(self):
        video = PlaylistVideoInfo(title="t", url="u", duration=3661.0)
        assert video.get_duration_formatted() == "01:01:01"

    def test_int_duration_still_works(self):
        video = PlaylistVideoInfo(title="t", url="u", duration=125)
        assert video.get_duration_formatted() == "02:05"

    def test_fractional_seconds_truncate(self):
        video = PlaylistVideoInfo(title="t", url="u", duration=59.9)
        assert video.get_duration_formatted() == "00:59"

    def test_zero_or_missing_duration(self):
        assert PlaylistVideoInfo(title="t", url="u", duration=0).get_duration_formatted() == "Unknown"
        assert PlaylistVideoInfo(title="t", url="u", duration=-1).get_duration_formatted() == "Unknown"
