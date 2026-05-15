"""Tests for src/models/ - VideoInfo, DownloadHistory, AppConfig."""

from datetime import datetime

from src.models.app_config import AppConfig
from src.models.download_history import DownloadHistory, HistoryEntry
from src.models.video_info import VideoInfo

# ============ VideoInfo Tests ============


class TestVideoInfoCreation:
    """Tests for VideoInfo creation and defaults."""

    def test_basic_creation(self):
        info = VideoInfo(title="Test Video", url="https://example.com")
        assert info.title == "Test Video"
        assert info.url == "https://example.com"
        assert info.duration == 0
        assert info.formats == []
        assert info.subtitles == {}
        assert info.automatic_captions == {}

    def test_from_yt_dlp_dict(self):
        data = {
            "title": "My Video",
            "webpage_url": "https://youtube.com/watch?v=abc",
            "duration": 300,
            "thumbnail": "https://img.example.com/thumb.jpg",
            "description": "A test video",
            "uploader": "TestChannel",
            "upload_date": "20240101",
            "view_count": 1000,
            "like_count": 50,
            "formats": [{"format_id": "22"}],
            "extractor": "youtube",
            "subtitles": {"en": [{"ext": "vtt"}]},
            "automatic_captions": {"es": [{"ext": "vtt"}]},
        }
        info = VideoInfo.from_yt_dlp_dict(data)
        assert info.title == "My Video"
        assert info.duration == 300
        assert info.uploader == "TestChannel"
        assert len(info.formats) == 1
        assert "en" in info.subtitles

    def test_from_yt_dlp_dict_missing_fields(self):
        info = VideoInfo.from_yt_dlp_dict({})
        assert info.title == "Unknown Title"
        assert info.url == ""
        assert info.duration == 0


class TestVideoInfoMethods:
    """Tests for VideoInfo methods."""

    def test_get_subtitle_languages(self):
        info = VideoInfo(
            title="Test",
            url="https://example.com",
            subtitles={"en": [], "fr": []},
            automatic_captions={"es": [], "en": []},
        )
        langs = info.get_available_subtitle_languages()
        assert "en" in langs
        assert "fr" in langs
        assert "es" in langs

    def test_get_subtitle_languages_empty(self):
        info = VideoInfo(title="Test", url="https://example.com")
        assert info.get_available_subtitle_languages() == []

    def test_duration_formatted_minutes(self):
        info = VideoInfo(title="Test", url="https://example.com", duration=125)
        assert info.get_duration_formatted() == "02:05"

    def test_duration_formatted_hours(self):
        info = VideoInfo(title="Test", url="https://example.com", duration=3725)
        assert info.get_duration_formatted() == "01:02:05"

    def test_duration_formatted_zero(self):
        info = VideoInfo(title="Test", url="https://example.com", duration=0)
        assert info.get_duration_formatted() == "Unknown"

    def test_short_title_short(self):
        info = VideoInfo(title="Short Title", url="https://example.com")
        assert info.get_short_title() == "Short Title"

    def test_short_title_long(self):
        long_title = "A" * 100
        info = VideoInfo(title=long_title, url="https://example.com")
        result = info.get_short_title(50)
        assert len(result) == 50
        assert result.endswith("...")


# ============ HistoryEntry Tests ============


class TestHistoryEntry:
    """Tests for HistoryEntry."""

    def _make_entry(self, **kwargs):
        defaults = dict(
            url="https://youtube.com/watch?v=test",
            title="Test Video",
            quality="Best Quality",
            output_directory="/downloads",
            filename="test.mp4",
            status="completed",
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            file_size=50000000,
            download_speed=5000000.0,
            platform="youtube",
        )
        defaults.update(kwargs)
        return HistoryEntry(**defaults)

    def test_creation(self):
        entry = self._make_entry()
        assert entry.title == "Test Video"
        assert entry.status == "completed"

    def test_to_dict(self):
        entry = self._make_entry()
        d = entry.to_dict()
        assert d["url"] == "https://youtube.com/watch?v=test"
        assert d["status"] == "completed"
        assert isinstance(d["timestamp"], str)

    def test_from_dict_roundtrip(self):
        entry = self._make_entry()
        d = entry.to_dict()
        restored = HistoryEntry.from_dict(d)
        assert restored.title == entry.title
        assert restored.url == entry.url
        assert restored.timestamp == entry.timestamp


# ============ DownloadHistory Tests ============


class TestDownloadHistory:
    """Tests for DownloadHistory."""

    def _make_entry(self, title="Video", status="completed", platform="youtube"):
        return HistoryEntry(
            url="https://youtube.com/watch?v=test",
            title=title,
            quality="Best",
            output_directory="/dl",
            filename=f"{title}.mp4",
            status=status,
            timestamp=datetime.now(),
            file_size=1000000,
            download_speed=500000.0,
            platform=platform,
        )

    def test_add_entry_to_front(self):
        history = DownloadHistory()
        history.add_entry(self._make_entry("First"))
        history.add_entry(self._make_entry("Second"))
        assert history.entries[0].title == "Second"

    def test_max_entries_trim(self):
        history = DownloadHistory(max_entries=3)
        for i in range(5):
            history.add_entry(self._make_entry(f"Video {i}"))
        assert len(history.entries) == 3

    def test_get_entries_no_filter(self):
        history = DownloadHistory()
        history.add_entry(self._make_entry("A"))
        history.add_entry(self._make_entry("B"))
        assert len(history.get_entries()) == 2

    def test_get_entries_status_filter(self):
        history = DownloadHistory()
        history.add_entry(self._make_entry("A", status="completed"))
        history.add_entry(self._make_entry("B", status="failed"))
        result = history.get_entries(status="completed")
        assert len(result) == 1
        assert result[0].title == "A"

    def test_get_entries_limit(self):
        history = DownloadHistory()
        for i in range(10):
            history.add_entry(self._make_entry(f"V{i}"))
        assert len(history.get_entries(limit=3)) == 3

    def test_search_by_title(self):
        history = DownloadHistory()
        history.add_entry(self._make_entry("Cat Video"))
        history.add_entry(self._make_entry("Dog Video"))
        result = history.search("cat")
        assert len(result) == 1

    def test_get_statistics(self):
        history = DownloadHistory()
        history.add_entry(self._make_entry("A", status="completed"))
        history.add_entry(self._make_entry("B", status="failed"))
        stats = history.get_statistics()
        assert stats["total_downloads"] == 2
        assert stats["completed"] == 1
        assert stats["failed"] == 1
        assert stats["success_rate"] == 50.0

    def test_get_statistics_empty(self):
        stats = DownloadHistory().get_statistics()
        assert stats["total_downloads"] == 0
        assert stats["success_rate"] == 0

    def test_clear_all(self):
        history = DownloadHistory()
        history.add_entry(self._make_entry("A"))
        history.add_entry(self._make_entry("B"))
        count = history.clear()
        assert count == 2
        assert len(history.entries) == 0

    def test_clear_by_status(self):
        history = DownloadHistory()
        history.add_entry(self._make_entry("A", status="completed"))
        history.add_entry(self._make_entry("B", status="failed"))
        count = history.clear(status="failed")
        assert count == 1
        assert len(history.entries) == 1

    def test_json_roundtrip(self):
        history = DownloadHistory()
        history.add_entry(self._make_entry("Test"))
        json_str = history.to_json()
        restored = DownloadHistory.from_json(json_str)
        assert len(restored.entries) == 1
        assert restored.entries[0].title == "Test"

    def test_export_csv(self):
        history = DownloadHistory()
        history.add_entry(self._make_entry("Test"))
        csv = history.export_to_csv()
        assert "Timestamp" in csv
        assert "Test" in csv


# ============ AppConfig Tests ============


class TestAppConfig:
    """Tests for AppConfig."""

    def test_defaults(self):
        config = AppConfig(output_directory="/downloads")
        assert config.default_quality == "Best Quality"
        assert config.window_width == 900
        assert config.window_height == 700

    def test_to_dict(self):
        config = AppConfig(output_directory="/downloads")
        d = config.to_dict()
        assert d["output_directory"] == "/downloads"
        assert d["default_quality"] == "Best Quality"

    def test_from_dict(self):
        d = {
            "output_directory": "/dl",
            "default_quality": "720p (HD)",
            "window_width": 1000,
            "window_height": 800,
            "last_url": "",
        }
        config = AppConfig.from_dict(d)
        assert config.output_directory == "/dl"
        assert config.default_quality == "720p (HD)"

    def test_roundtrip(self):
        config = AppConfig(output_directory="/downloads", default_quality="1080p (Full HD)")
        d = config.to_dict()
        restored = AppConfig.from_dict(d)
        assert restored.output_directory == config.output_directory
        assert restored.default_quality == config.default_quality

    def test_validate_valid(self):
        config = AppConfig(output_directory="/downloads")
        assert config.validate() is True

    def test_validate_empty_directory(self):
        config = AppConfig(output_directory="")
        assert config.validate() is False

    def test_validate_small_window(self):
        config = AppConfig(output_directory="/downloads", window_width=100, window_height=100)
        assert config.validate() is False

    def test_validate_invalid_quality(self):
        config = AppConfig(output_directory="/downloads", default_quality="FakeQuality")
        assert config.validate() is False

    def test_repr(self):
        config = AppConfig(output_directory="/downloads")
        r = repr(config)
        assert "AppConfig" in r
