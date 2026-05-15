"""Tests for src/models/download_task.py."""

from src.models.download_task import DownloadTask, TaskStatus


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_pending(self):
        assert TaskStatus.PENDING.value == "pending"

    def test_downloading(self):
        assert TaskStatus.DOWNLOADING.value == "downloading"

    def test_completed(self):
        assert TaskStatus.COMPLETED.value == "completed"

    def test_error(self):
        assert TaskStatus.ERROR.value == "error"

    def test_cancelled(self):
        assert TaskStatus.CANCELLED.value == "cancelled"


class TestDownloadTaskCreation:
    """Tests for DownloadTask creation."""

    def test_defaults(self):
        task = DownloadTask(url="https://example.com", output_directory="/tmp", quality="Best Quality")
        assert task.status == TaskStatus.PENDING
        assert task.progress_percent == 0.0
        assert task.download_speed == 0.0
        assert task.filename == ""
        assert task.error_message == ""
        assert task.started_at is None
        assert task.completed_at is None

    def test_custom_values(self):
        task = DownloadTask(
            url="https://youtube.com/watch?v=test",
            output_directory="/downloads",
            quality="720p (HD)",
            audio_only=True,
        )
        assert task.url == "https://youtube.com/watch?v=test"
        assert task.quality == "720p (HD)"
        assert task.audio_only is True


class TestDownloadTaskLifecycle:
    """Tests for task lifecycle methods."""

    def _make_task(self):
        return DownloadTask(url="https://example.com", output_directory="/tmp", quality="Best Quality")

    def test_start(self):
        task = self._make_task()
        task.start()
        assert task.status == TaskStatus.DOWNLOADING
        assert task.started_at is not None

    def test_complete(self):
        task = self._make_task()
        task.start()
        task.complete("video.mp4")
        assert task.status == TaskStatus.COMPLETED
        assert task.filename == "video.mp4"
        assert task.progress_percent == 100.0
        assert task.completed_at is not None

    def test_fail(self):
        task = self._make_task()
        task.start()
        task.fail("Network error")
        assert task.status == TaskStatus.ERROR
        assert task.error_message == "Network error"
        assert task.completed_at is not None

    def test_cancel(self):
        task = self._make_task()
        task.start()
        task.cancel()
        assert task.status == TaskStatus.CANCELLED
        assert task.completed_at is not None


class TestUpdateProgress:
    """Tests for task progress updates."""

    def _make_task(self):
        return DownloadTask(url="https://example.com", output_directory="/tmp", quality="Best Quality")

    def test_update_progress(self):
        task = self._make_task()
        task.update_progress(50.0, download_speed=1024000, eta_seconds=30, downloaded_bytes=5000, file_size=10000)
        assert task.progress_percent == 50.0
        assert task.download_speed == 1024000
        assert task.eta_seconds == 30
        assert task.downloaded_bytes == 5000
        assert task.file_size == 10000

    def test_progress_capped_at_100(self):
        task = self._make_task()
        task.update_progress(150.0)
        assert task.progress_percent == 100.0

    def test_file_size_zero_not_overwritten(self):
        task = self._make_task()
        task.update_progress(50.0, file_size=10000)
        task.update_progress(60.0, file_size=0)
        assert task.file_size == 10000


class TestTaskState:
    """Tests for is_active() and is_finished()."""

    def _make_task(self):
        return DownloadTask(url="https://example.com", output_directory="/tmp", quality="Best Quality")

    def test_pending_is_active(self):
        task = self._make_task()
        assert task.is_active() is True
        assert task.is_finished() is False

    def test_downloading_is_active(self):
        task = self._make_task()
        task.start()
        assert task.is_active() is True
        assert task.is_finished() is False

    def test_completed_is_finished(self):
        task = self._make_task()
        task.complete("video.mp4")
        assert task.is_active() is False
        assert task.is_finished() is True

    def test_error_is_finished(self):
        task = self._make_task()
        task.fail("error")
        assert task.is_finished() is True

    def test_cancelled_is_finished(self):
        task = self._make_task()
        task.cancel()
        assert task.is_finished() is True


class TestStatusText:
    """Tests for get_status_text()."""

    def _make_task(self):
        return DownloadTask(url="https://example.com", output_directory="/tmp", quality="Best Quality")

    def test_pending_text(self):
        task = self._make_task()
        assert "Waiting" in task.get_status_text()

    def test_downloading_text(self):
        task = self._make_task()
        task.start()
        assert "Downloading" in task.get_status_text()

    def test_completed_text(self):
        task = self._make_task()
        task.complete("video.mp4")
        assert "Completed" in task.get_status_text()

    def test_error_text_includes_message(self):
        task = self._make_task()
        task.fail("Network timeout")
        text = task.get_status_text()
        assert "Error" in text
        assert "Network timeout" in text

    def test_repr(self):
        task = self._make_task()
        r = repr(task)
        assert "DownloadTask" in r
        assert "pending" in r
