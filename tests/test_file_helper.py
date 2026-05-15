"""Tests for src/utils/file_helper.py."""

import os

from src.utils.file_helper import FileHelper


class TestFormatFileSize:
    """Tests for FileHelper.format_file_size()."""

    def test_zero_bytes(self):
        assert FileHelper.format_file_size(0) == "0 B"

    def test_bytes(self):
        assert FileHelper.format_file_size(500) == "500 B"

    def test_kilobytes(self):
        result = FileHelper.format_file_size(1536)
        assert "KB" in result
        assert "1.5" in result

    def test_megabytes(self):
        result = FileHelper.format_file_size(1536000)
        assert "MB" in result

    def test_gigabytes(self):
        result = FileHelper.format_file_size(2 * 1024 * 1024 * 1024)
        assert "GB" in result
        assert "2" in result

    def test_terabytes(self):
        result = FileHelper.format_file_size(3 * 1024**4)
        assert "TB" in result


class TestFormatSpeed:
    """Tests for FileHelper.format_speed()."""

    def test_zero_speed(self):
        assert FileHelper.format_speed(0) == "0 B/s"

    def test_megabytes_per_second(self):
        result = FileHelper.format_speed(1536000)
        assert "MB/s" in result

    def test_kilobytes_per_second(self):
        result = FileHelper.format_speed(5120)
        assert "KB/s" in result


class TestFormatTime:
    """Tests for FileHelper.format_time()."""

    def test_seconds_only(self):
        assert FileHelper.format_time(45) == "45s"

    def test_minutes_seconds(self):
        assert FileHelper.format_time(90) == "1m 30s"

    def test_hours_minutes_seconds(self):
        assert FileHelper.format_time(3661) == "1h 1m 1s"

    def test_negative(self):
        assert FileHelper.format_time(-1) == "Unknown"

    def test_zero(self):
        assert FileHelper.format_time(0) == "0s"


class TestFormatSizeAlias:
    """Tests for FileHelper.format_size() alias."""

    def test_alias_matches(self):
        assert FileHelper.format_size(1536000) == FileHelper.format_file_size(1536000)


class TestFileOperations:
    """Tests for file/directory operations."""

    def test_ensure_directory_exists(self, tmp_path):
        new_dir = str(tmp_path / "new_subdir")
        assert FileHelper.ensure_directory_exists(new_dir) is True
        assert os.path.isdir(new_dir)

    def test_ensure_directory_already_exists(self, tmp_path):
        assert FileHelper.ensure_directory_exists(str(tmp_path)) is True

    def test_file_exists_true(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        assert FileHelper.file_exists(str(f)) is True

    def test_file_exists_false(self):
        assert FileHelper.file_exists("/nonexistent/file.txt") is False

    def test_directory_exists_true(self, tmp_path):
        assert FileHelper.directory_exists(str(tmp_path)) is True

    def test_directory_exists_false(self):
        assert FileHelper.directory_exists("/nonexistent/dir") is False

    def test_get_safe_path(self):
        result = FileHelper.get_safe_path("/downloads", "video.mp4")
        assert result.endswith("video.mp4")
        assert "downloads" in result

    def test_get_file_size(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        size = FileHelper.get_file_size(str(f))
        assert size is not None
        assert size > 0

    def test_get_file_size_nonexistent(self):
        assert FileHelper.get_file_size("/nonexistent/file.txt") is None
