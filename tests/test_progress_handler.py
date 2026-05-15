"""Tests for src/backend/progress_handler.py."""

from src.backend.progress_handler import ProgressHandler


class TestParseProgressDownloading:
    """Tests for ProgressHandler.parse_progress() with downloading status."""

    def test_with_total_bytes(self):
        raw = {
            "status": "downloading",
            "downloaded_bytes": 5000,
            "total_bytes": 10000,
            "speed": 1024000.0,
            "eta": 30,
            "filename": "video.mp4",
        }
        result = ProgressHandler.parse_progress(raw)
        assert result["status"] == "downloading"
        assert result["percent"] == 50.0
        assert result["speed"] == 1024000.0
        assert result["eta"] == 30
        assert result["downloaded"] == 5000
        assert result["total"] == 10000

    def test_with_estimate(self):
        raw = {
            "status": "downloading",
            "downloaded_bytes": 3000,
            "total_bytes_estimate": 10000,
            "speed": 500000.0,
            "eta": 14,
        }
        result = ProgressHandler.parse_progress(raw)
        assert result["percent"] == 30.0
        assert result["total"] == 10000

    def test_no_total_uses_percent_str(self):
        raw = {
            "status": "downloading",
            "downloaded_bytes": 0,
            "_percent_str": "45.5%",
        }
        result = ProgressHandler.parse_progress(raw)
        assert result["percent"] == 45.5

    def test_speed_none(self):
        raw = {"status": "downloading", "downloaded_bytes": 0}
        result = ProgressHandler.parse_progress(raw)
        assert result["speed"] == 0.0

    def test_eta_none(self):
        raw = {"status": "downloading", "downloaded_bytes": 0}
        result = ProgressHandler.parse_progress(raw)
        assert result["eta"] == 0


class TestParseProgressFinished:
    """Tests for ProgressHandler.parse_progress() with finished status."""

    def test_finished(self):
        raw = {"status": "finished", "total_bytes": 50000, "filename": "video.mp4"}
        result = ProgressHandler.parse_progress(raw)
        assert result["status"] == "finished"
        assert result["percent"] == 100.0
        assert result["downloaded"] == 50000
        assert result["total"] == 50000


class TestParseProgressError:
    """Tests for ProgressHandler.parse_progress() with error status."""

    def test_error(self):
        raw = {"status": "error"}
        result = ProgressHandler.parse_progress(raw)
        assert result["status"] == "error"

    def test_unknown_status(self):
        raw = {"status": "unknown_thing"}
        result = ProgressHandler.parse_progress(raw)
        assert result["status"] == "unknown_thing"


class TestParseProgressExceptionHandling:
    """Tests for exception handling in parse_progress."""

    def test_corrupted_data(self):
        # Should not crash
        result = ProgressHandler.parse_progress({"status": "downloading", "total_bytes": "not_a_number"})
        assert isinstance(result, dict)
        assert "status" in result


class TestCreateProgressMessage:
    """Tests for ProgressHandler.create_progress_message()."""

    def test_downloading_message(self):
        data = {"status": "downloading", "percent": 45.3, "speed": 1024000, "eta": 30}
        msg = ProgressHandler.create_progress_message(data)
        assert "45.3%" in msg
        assert "Downloading" in msg

    def test_finished_message(self):
        data = {"status": "finished"}
        msg = ProgressHandler.create_progress_message(data)
        assert "finished" in msg.lower()

    def test_error_message(self):
        data = {"status": "error"}
        msg = ProgressHandler.create_progress_message(data)
        assert "error" in msg.lower()

    def test_unknown_message(self):
        data = {"status": "some_other"}
        msg = ProgressHandler.create_progress_message(data)
        assert "some_other" in msg
