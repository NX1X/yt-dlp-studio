"""Integration tests for the download pipeline.

These tests mock yt-dlp to verify the signal flow and state transitions
without performing real downloads.
"""

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication

from src.backend.progress_handler import ProgressHandler
from src.models.download_task import DownloadTask, TaskStatus


@pytest.fixture(scope="session")
def qapp():
    """Ensure QApplication exists for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestDownloadWorkerSuccess:
    """Test successful download flow with mocked yt-dlp."""

    @patch("src.backend.download_worker.YtDlpWrapper")
    def test_success_flow(self, MockWrapper, qapp, qtbot):
        """Verify worker emits correct signals on success."""
        from src.backend.download_worker import DownloadWorker

        # Configure mock
        mock_instance = MockWrapper.return_value
        mock_instance.get_video_info.return_value = MagicMock(title="Test Video")
        mock_instance.download.return_value = True

        task = DownloadTask(url="https://example.com/video", output_directory="/tmp", quality="Best Quality")
        worker = DownloadWorker(task)

        completed_signals = []
        worker.download_completed.connect(lambda f: completed_signals.append(f))

        worker.run()

        assert task.status == TaskStatus.COMPLETED
        assert len(completed_signals) == 1


class TestDownloadWorkerFailure:
    """Test failed download flow."""

    @patch("src.backend.download_worker.YtDlpWrapper")
    def test_failure_flow(self, MockWrapper, qapp, qtbot):
        """Verify worker emits error signal on failure."""
        from src.backend.download_worker import DownloadWorker

        mock_instance = MockWrapper.return_value
        mock_instance.get_video_info.return_value = MagicMock(title="Test Video")
        mock_instance.download.return_value = False

        task = DownloadTask(url="https://example.com/video", output_directory="/tmp", quality="Best Quality")
        worker = DownloadWorker(task)

        failed_signals = []
        worker.download_failed.connect(lambda e: failed_signals.append(e))

        worker.run()

        assert task.status == TaskStatus.ERROR
        assert len(failed_signals) == 1

    @patch("src.backend.download_worker.YtDlpWrapper")
    def test_exception_flow(self, MockWrapper, qapp, qtbot):
        """Verify worker handles exceptions gracefully."""
        from src.backend.download_worker import DownloadWorker

        mock_instance = MockWrapper.return_value
        mock_instance.get_video_info.side_effect = Exception("Network error")
        mock_instance.download.side_effect = Exception("Download failed")

        task = DownloadTask(url="https://example.com/video", output_directory="/tmp", quality="Best Quality")
        worker = DownloadWorker(task)

        failed_signals = []
        worker.download_failed.connect(lambda e: failed_signals.append(e))

        worker.run()

        assert task.status == TaskStatus.ERROR
        assert len(failed_signals) == 1


class TestDownloadWorkerCancellation:
    """Test cancellation flow."""

    @patch("src.backend.download_worker.YtDlpWrapper")
    def test_cancel_before_download(self, MockWrapper, qapp, qtbot):
        """Verify cancellation before download starts."""
        from src.backend.download_worker import DownloadWorker

        mock_instance = MockWrapper.return_value
        mock_instance.get_video_info.return_value = MagicMock(title="Test Video")
        mock_instance.download.return_value = True

        task = DownloadTask(url="https://example.com/video", output_directory="/tmp", quality="Best Quality")
        worker = DownloadWorker(task)
        worker.cancel()  # Cancel before running

        worker.run()

        assert task.status == TaskStatus.CANCELLED


class TestProgressHandlerIntegration:
    """Test progress handler with realistic yt-dlp data."""

    def test_full_progress_cycle(self):
        """Simulate a complete download progress cycle."""
        # Downloading phase
        for pct in [0, 25, 50, 75, 100]:
            raw = {
                "status": "downloading",
                "downloaded_bytes": pct * 1000,
                "total_bytes": 100000,
                "speed": 1024000.0,
                "eta": max(0, (100 - pct)),
            }
            result = ProgressHandler.parse_progress(raw)
            assert result["status"] == "downloading"
            assert result["percent"] >= 0

        # Finished phase
        raw = {"status": "finished", "total_bytes": 100000, "filename": "video.mp4"}
        result = ProgressHandler.parse_progress(raw)
        assert result["status"] == "finished"
        assert result["percent"] == 100.0
