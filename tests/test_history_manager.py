"""Tests for src/backend/history_manager.py."""

from datetime import datetime
from unittest.mock import patch

from src.models.download_history import DownloadHistory, HistoryEntry
from src.models.download_task import DownloadTask


class TestHistoryManagerInit:
    """Tests for HistoryManager initialization with mocked APP_DATA_DIR."""

    @patch("src.backend.history_manager.APP_DATA_DIR")
    def test_init_no_file(self, mock_dir, tmp_path):
        mock_dir.__truediv__ = lambda self, x: tmp_path / x
        mock_dir.return_value = tmp_path
        from src.backend.history_manager import HistoryManager

        mgr = HistoryManager()
        assert len(mgr.history.entries) == 0

    @patch("src.backend.history_manager.APP_DATA_DIR")
    def test_init_with_existing_file(self, mock_dir, tmp_path):
        mock_dir.__truediv__ = lambda self, x: tmp_path / x
        # Pre-create history file
        history = DownloadHistory()
        history.add_entry(
            HistoryEntry(
                url="https://example.com",
                title="Test",
                quality="Best",
                output_directory="/dl",
                filename="test.mp4",
                status="completed",
                timestamp=datetime.now(),
                platform="youtube",
            )
        )
        (tmp_path / "download_history.json").write_text(history.to_json())

        from src.backend.history_manager import HistoryManager

        mgr = HistoryManager()
        assert len(mgr.history.entries) == 1


class TestHistoryManagerAddDownload:
    """Tests for HistoryManager.add_download()."""

    @patch("src.backend.history_manager.APP_DATA_DIR")
    def test_add_download(self, mock_dir, tmp_path):
        mock_dir.__truediv__ = lambda self, x: tmp_path / x
        from src.backend.history_manager import HistoryManager

        mgr = HistoryManager()

        task = DownloadTask(url="https://youtube.com/watch?v=test", output_directory="/dl", quality="Best Quality")
        task.filename = "video.mp4"
        task.file_size = 50000000
        task.download_speed = 5000000.0

        mgr.add_download(task, status="completed", platform="youtube")
        assert len(mgr.history.entries) == 1
        assert mgr.history.entries[0].status == "completed"


class TestHistoryManagerOperations:
    """Tests for search, stats, clear, export."""

    @patch("src.backend.history_manager.APP_DATA_DIR")
    def _make_manager(self, mock_dir, tmp_path):
        mock_dir.__truediv__ = lambda self, x: tmp_path / x
        from src.backend.history_manager import HistoryManager

        mgr = HistoryManager()
        # Add some entries
        for i, status in enumerate(["completed", "completed", "failed"]):
            task = DownloadTask(url=f"https://example.com/{i}", output_directory="/dl", quality="Best Quality")
            task.filename = f"video_{i}.mp4"
            task.file_size = 1000000 * (i + 1)
            task.download_speed = 500000.0
            mgr.add_download(task, status=status, platform="youtube")
        return mgr

    @patch("src.backend.history_manager.APP_DATA_DIR")
    def test_get_history(self, mock_dir, tmp_path):
        mock_dir.__truediv__ = lambda self, x: tmp_path / x
        mgr = self._make_manager(tmp_path=tmp_path)
        assert len(mgr.get_history()) == 3

    @patch("src.backend.history_manager.APP_DATA_DIR")
    def test_get_history_with_status_filter(self, mock_dir, tmp_path):
        mock_dir.__truediv__ = lambda self, x: tmp_path / x
        mgr = self._make_manager(tmp_path=tmp_path)
        assert len(mgr.get_history(status="completed")) == 2

    @patch("src.backend.history_manager.APP_DATA_DIR")
    def test_get_statistics(self, mock_dir, tmp_path):
        mock_dir.__truediv__ = lambda self, x: tmp_path / x
        mgr = self._make_manager(tmp_path=tmp_path)
        stats = mgr.get_statistics()
        assert stats["total_downloads"] == 3
        assert stats["completed"] == 2

    @patch("src.backend.history_manager.APP_DATA_DIR")
    def test_clear_history(self, mock_dir, tmp_path):
        mock_dir.__truediv__ = lambda self, x: tmp_path / x
        mgr = self._make_manager(tmp_path=tmp_path)
        count = mgr.clear_history()
        assert count == 3
        assert len(mgr.get_history()) == 0

    @patch("src.backend.history_manager.APP_DATA_DIR")
    def test_export_csv(self, mock_dir, tmp_path):
        mock_dir.__truediv__ = lambda self, x: tmp_path / x
        mgr = self._make_manager(tmp_path=tmp_path)
        csv_path = tmp_path / "export.csv"
        result = mgr.export_to_csv(csv_path)
        assert result is True
        assert csv_path.exists()
        content = csv_path.read_text()
        assert "Timestamp" in content

    @patch("src.backend.history_manager.APP_DATA_DIR")
    def test_save_and_load(self, mock_dir, tmp_path):
        mock_dir.__truediv__ = lambda self, x: tmp_path / x
        mgr = self._make_manager(tmp_path=tmp_path)
        mgr.save()
        assert (tmp_path / "download_history.json").exists()

        # Load into new manager
        mgr2 = type(mgr)()
        assert len(mgr2.history.entries) == 3

    @patch("src.backend.history_manager.APP_DATA_DIR")
    def test_load_corrupted_file(self, mock_dir, tmp_path):
        mock_dir.__truediv__ = lambda self, x: tmp_path / x
        (tmp_path / "download_history.json").write_text("not valid json{{{")
        from src.backend.history_manager import HistoryManager

        mgr = HistoryManager()
        # Should not crash, start with empty history
        assert len(mgr.history.entries) == 0
