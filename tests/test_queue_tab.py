"""
Tests for QueueTab UI.

Tests queue display, controls, and user interactions.
Requires pytest-qt for Qt widget testing.
"""

from unittest.mock import patch

import pytest
from PySide6.QtCore import Qt

from src.backend.queue_manager import QueueManager
from src.models.download_task import DownloadTask, TaskStatus
from src.ui.queue_tab import QueueTab


@pytest.fixture
def queue_manager():
    """Create a queue manager for testing."""
    return QueueManager(max_concurrent=3)


@pytest.fixture
def queue_tab(qtbot, queue_manager):
    """Create a queue tab for testing."""
    tab = QueueTab(queue_manager)
    qtbot.addWidget(tab)
    return tab


@pytest.fixture
def sample_task():
    """Create a sample download task."""
    return DownloadTask(url="https://www.youtube.com/watch?v=test", output_directory="/tmp/downloads", quality="1080p")


@pytest.fixture
def multiple_tasks():
    """Create multiple sample tasks."""
    return [
        DownloadTask(url=f"https://www.youtube.com/watch?v=test{i}", output_directory="/tmp/downloads", quality="1080p")
        for i in range(5)
    ]


class TestQueueTabInitialization:
    """Test queue tab initialization."""

    def test_initialization(self, queue_tab):
        """Test that queue tab initializes properly."""
        assert queue_tab.queue_manager is not None
        assert queue_tab.queue_table is not None
        assert queue_tab.queue_table.columnCount() == 8

    def test_ui_elements_exist(self, queue_tab):
        """Test that all UI elements are created."""
        # Statistics labels
        assert queue_tab.total_label is not None
        assert queue_tab.pending_label is not None
        assert queue_tab.active_label is not None
        assert queue_tab.completed_label is not None
        assert queue_tab.failed_label is not None

        # Control buttons
        assert queue_tab.start_button is not None
        assert queue_tab.pause_button is not None
        assert queue_tab.stop_button is not None

        # Task management buttons
        assert queue_tab.move_up_button is not None
        assert queue_tab.move_down_button is not None
        assert queue_tab.remove_button is not None

        # Clear buttons
        assert queue_tab.clear_completed_button is not None
        assert queue_tab.clear_failed_button is not None

    def test_table_headers(self, queue_tab):
        """Test that table headers are set correctly."""
        expected_headers = ["Video Name", "URL", "Quality", "Status", "Progress", "Speed", "Output", "Actions"]
        for col in range(8):
            header_text = queue_tab.queue_table.horizontalHeaderItem(col).text()
            assert header_text == expected_headers[col]


class TestQueueTabDisplay:
    """Test queue display functionality."""

    def test_empty_queue_display(self, queue_tab):
        """Test display with empty queue."""
        assert queue_tab.queue_table.rowCount() == 0
        assert "Total: 0" in queue_tab.total_label.text()

    def test_display_single_task(self, queue_tab, queue_manager, sample_task):
        """Test displaying a single task."""
        with patch.object(queue_manager, "_try_start_next"):
            queue_manager.add_task(sample_task)

        # Queue should update automatically via signal
        assert queue_tab.queue_table.rowCount() == 1
        assert "Total: 1" in queue_tab.total_label.text()

    def test_display_multiple_tasks(self, queue_tab, queue_manager, multiple_tasks):
        """Test displaying multiple tasks."""
        with patch.object(queue_manager, "_try_start_next"):
            for task in multiple_tasks:
                queue_manager.add_task(task)

        assert queue_tab.queue_table.rowCount() == 5
        assert "Total: 5" in queue_tab.total_label.text()

    def test_url_truncation(self, queue_tab):
        """Test that long URLs are truncated."""
        long_url = "https://www.example.com/very/long/path/" + ("x" * 100)
        truncated = queue_tab._truncate_url(long_url, max_length=60)
        assert len(truncated) <= 60
        assert truncated.endswith("...")

    def test_short_url_not_truncated(self, queue_tab):
        """Test that short URLs are not truncated."""
        short_url = "https://example.com/video"
        result = queue_tab._truncate_url(short_url, max_length=60)
        assert result == short_url


class TestQueueTabStatistics:
    """Test statistics display."""

    def test_statistics_update(self, queue_tab, queue_manager, multiple_tasks):
        """Test that statistics update correctly."""
        with patch.object(queue_manager, "_try_start_next"):
            # Add tasks with different statuses
            multiple_tasks[0].status = TaskStatus.PENDING
            queue_manager.add_task(multiple_tasks[0])

            multiple_tasks[1].status = TaskStatus.DOWNLOADING
            queue_manager.add_task(multiple_tasks[1])

            multiple_tasks[2].status = TaskStatus.COMPLETED
            queue_manager.add_task(multiple_tasks[2])

            multiple_tasks[3].status = TaskStatus.ERROR
            queue_manager.add_task(multiple_tasks[3])

        # Check statistics labels
        assert "Total: 4" in queue_tab.total_label.text()
        assert "Pending: 1" in queue_tab.pending_label.text()
        assert "Active: 1" in queue_tab.active_label.text()
        assert "Completed: 1" in queue_tab.completed_label.text()
        assert "Failed: 1" in queue_tab.failed_label.text()

    def test_statistics_empty_queue(self, queue_tab):
        """Test statistics with empty queue."""
        assert "Total: 0" in queue_tab.total_label.text()
        assert "Pending: 0" in queue_tab.pending_label.text()
        assert "Active: 0" in queue_tab.active_label.text()


class TestQueueTabStatusColors:
    """Test status color coding."""

    def test_status_color_pending(self, queue_tab):
        """Test color for pending status."""
        color = queue_tab._get_status_color(TaskStatus.PENDING)
        assert color is not None

    def test_status_color_downloading(self, queue_tab):
        """Test color for downloading status."""
        color = queue_tab._get_status_color(TaskStatus.DOWNLOADING)
        assert color is not None

    def test_status_color_completed(self, queue_tab):
        """Test color for completed status."""
        color = queue_tab._get_status_color(TaskStatus.COMPLETED)
        assert color is not None

    def test_status_color_error(self, queue_tab):
        """Test color for error status."""
        color = queue_tab._get_status_color(TaskStatus.ERROR)
        assert color is not None


class TestQueueTabControls:
    """Test queue control buttons."""

    def test_start_button_click(self, qtbot, queue_tab, queue_manager):
        """Test clicking start queue button."""
        with (
            patch.object(queue_manager, "resume_queue") as mock_resume,
            patch.object(queue_manager, "start_queue") as mock_start,
        ):
            qtbot.mouseClick(queue_tab.start_button, Qt.LeftButton)
            mock_resume.assert_called_once()
            mock_start.assert_called_once()

    def test_pause_button_click(self, qtbot, queue_tab, queue_manager):
        """Test clicking pause queue button."""
        with patch.object(queue_manager, "pause_queue") as mock_pause:
            qtbot.mouseClick(queue_tab.pause_button, Qt.LeftButton)
            mock_pause.assert_called_once()

    def test_stop_button_click(self, qtbot, queue_tab, queue_manager):
        """Test clicking stop all button."""
        with patch.object(queue_manager, "stop_all") as mock_stop:
            qtbot.mouseClick(queue_tab.stop_button, Qt.LeftButton)
            mock_stop.assert_called_once()


class TestQueueTabTaskManagement:
    """Test task management operations."""

    def test_move_up_button(self, qtbot, queue_tab, queue_manager, multiple_tasks):
        """Test moving task up."""
        with patch.object(queue_manager, "_try_start_next"):
            for task in multiple_tasks:
                queue_manager.add_task(task)

        # Select row 2
        queue_tab.queue_table.selectRow(2)

        with patch.object(queue_manager, "move_task_up", return_value=True) as mock_move:
            qtbot.mouseClick(queue_tab.move_up_button, Qt.LeftButton)
            mock_move.assert_called_once_with(2)

    def test_move_down_button(self, qtbot, queue_tab, queue_manager, multiple_tasks):
        """Test moving task down."""
        with patch.object(queue_manager, "_try_start_next"):
            for task in multiple_tasks:
                queue_manager.add_task(task)

        # Select row 2
        queue_tab.queue_table.selectRow(2)

        with patch.object(queue_manager, "move_task_down", return_value=True) as mock_move:
            qtbot.mouseClick(queue_tab.move_down_button, Qt.LeftButton)
            mock_move.assert_called_once_with(2)

    def test_remove_button(self, qtbot, queue_tab, queue_manager, multiple_tasks):
        """Test removing task."""
        with patch.object(queue_manager, "_try_start_next"):
            for task in multiple_tasks:
                queue_manager.add_task(task)

        # Select row 1
        queue_tab.queue_table.selectRow(1)

        with patch.object(queue_manager, "remove_task") as mock_remove:
            qtbot.mouseClick(queue_tab.remove_button, Qt.LeftButton)
            mock_remove.assert_called_once_with(1)

    def test_move_up_no_selection(self, qtbot, queue_tab, queue_manager):
        """Test move up with no selection."""
        with patch.object(queue_manager, "move_task_up") as mock_move:
            qtbot.mouseClick(queue_tab.move_up_button, Qt.LeftButton)
            # Should not call move_task_up when nothing selected
            mock_move.assert_not_called()

    def test_remove_no_selection(self, qtbot, queue_tab, queue_manager):
        """Test remove with no selection."""
        with patch.object(queue_manager, "remove_task") as mock_remove:
            qtbot.mouseClick(queue_tab.remove_button, Qt.LeftButton)
            # Should not call remove_task when nothing selected
            mock_remove.assert_not_called()


class TestQueueTabClearOperations:
    """Test clear operations."""

    def test_clear_completed_button(self, qtbot, queue_tab, queue_manager):
        """Test clicking clear completed button."""
        with patch.object(queue_manager, "clear_completed", return_value=3) as mock_clear:
            qtbot.mouseClick(queue_tab.clear_completed_button, Qt.LeftButton)
            mock_clear.assert_called_once()

    def test_clear_failed_button(self, qtbot, queue_tab, queue_manager):
        """Test clicking clear failed button."""
        with patch.object(queue_manager, "clear_failed", return_value=2) as mock_clear:
            qtbot.mouseClick(queue_tab.clear_failed_button, Qt.LeftButton)
            mock_clear.assert_called_once()


class TestQueueTabProgressUpdates:
    """Test progress update handling."""

    def test_progress_update(self, queue_tab, queue_manager, sample_task):
        """Test handling progress updates."""
        with patch.object(queue_manager, "_try_start_next"):
            queue_manager.add_task(sample_task)

        # Simulate progress update
        progress_data = {"percent": 50.5, "speed": 1024000}
        queue_tab._on_task_progress(0, progress_data)

        # Check that progress is displayed
        progress_item = queue_tab.queue_table.item(0, 4)
        assert progress_item is not None
        assert "50.5%" in progress_item.text()

    def test_speed_update(self, queue_tab, queue_manager, sample_task):
        """Test handling speed updates."""
        with patch.object(queue_manager, "_try_start_next"):
            queue_manager.add_task(sample_task)

        # Simulate progress with speed
        progress_data = {"percent": 50, "speed": 2048000}
        queue_tab._on_task_progress(0, progress_data)

        # Check that speed is displayed
        speed_item = queue_tab.queue_table.item(0, 4)
        assert speed_item is not None
        # Speed should be formatted (e.g., "2.0 MB/s")
        assert speed_item.text() != "-"

    def test_progress_update_invalid_index(self, queue_tab):
        """Test progress update with invalid index."""
        # Should not crash with invalid index
        progress_data = {"percent": 50}
        queue_tab._on_task_progress(100, progress_data)


class TestQueueTabSignalConnections:
    """Test signal connections."""

    def test_queue_updated_signal_connected(self, queue_tab, queue_manager, sample_task):
        """Test that queue_updated signal refreshes display."""
        initial_row_count = queue_tab.queue_table.rowCount()

        with patch.object(queue_manager, "_try_start_next"):
            queue_manager.add_task(sample_task)

        # Queue should be refreshed
        assert queue_tab.queue_table.rowCount() == initial_row_count + 1

    def test_task_progress_signal_connected(self, queue_tab, queue_manager, sample_task):
        """Test that task_progress signal updates display."""
        with patch.object(queue_manager, "_try_start_next"):
            queue_manager.add_task(sample_task)

        with patch.object(queue_tab, "_on_task_progress") as mock_handler:
            # Emit progress signal
            progress_data = {"percent": 50}
            queue_manager.task_progress.emit(0, progress_data)

            # Handler should be called
            mock_handler.assert_called_once_with(0, progress_data)


class TestQueueTabTableDisplay:
    """Test table display details."""

    def test_table_row_selection(self, qtbot, queue_tab, queue_manager, multiple_tasks):
        """Test selecting table rows."""
        with patch.object(queue_manager, "_try_start_next"):
            for task in multiple_tasks:
                queue_manager.add_task(task)

        # Select row
        queue_tab.queue_table.selectRow(2)
        selected = queue_tab.queue_table.selectedItems()
        assert len(selected) > 0
        assert queue_tab.queue_table.row(selected[0]) == 2

    def test_table_displays_url(self, queue_tab, queue_manager, sample_task):
        """Test that URL is displayed in table."""
        with patch.object(queue_manager, "_try_start_next"):
            queue_manager.add_task(sample_task)

        url_item = queue_tab.queue_table.item(0, 1)
        assert url_item is not None
        # URL might be truncated, but should contain some part
        assert "youtube.com" in url_item.text()

    def test_table_displays_quality(self, queue_tab, queue_manager, sample_task):
        """Test that quality is displayed in table."""
        with patch.object(queue_manager, "_try_start_next"):
            queue_manager.add_task(sample_task)

        quality_item = queue_tab.queue_table.item(0, 2)
        assert quality_item is not None
        assert quality_item.text() == "1080p"

    def test_table_displays_status(self, queue_tab, queue_manager, sample_task):
        """Test that status is displayed in table."""
        with patch.object(queue_manager, "_try_start_next"):
            queue_manager.add_task(sample_task)

        status_item = queue_tab.queue_table.item(0, 3)
        assert status_item is not None
        assert "PENDING" in status_item.text().upper()

    def test_table_progress_for_downloading(self, queue_tab, queue_manager, sample_task):
        """Test progress display for downloading task."""
        sample_task.status = TaskStatus.DOWNLOADING
        sample_task.progress_percent = 45.5

        with patch.object(queue_manager, "_try_start_next"):
            queue_manager.add_task(sample_task)

        progress_item = queue_tab.queue_table.item(0, 4)
        assert progress_item is not None
        assert "45.5%" in progress_item.text()

    def test_table_progress_for_completed(self, queue_tab, queue_manager, sample_task):
        """Test progress display for completed task."""
        sample_task.status = TaskStatus.COMPLETED

        with patch.object(queue_manager, "_try_start_next"):
            queue_manager.add_task(sample_task)

        progress_item = queue_tab.queue_table.item(0, 4)
        assert progress_item is not None
        assert "100%" in progress_item.text()

    def test_table_progress_for_pending(self, queue_tab, queue_manager, sample_task):
        """Test progress display for pending task."""
        with patch.object(queue_manager, "_try_start_next"):
            queue_manager.add_task(sample_task)

        progress_item = queue_tab.queue_table.item(0, 4)
        assert progress_item is not None
        assert progress_item.text() == "-"

    def test_table_speed_for_downloading(self, queue_tab, queue_manager, sample_task):
        """Test speed display for downloading task."""
        sample_task.status = TaskStatus.DOWNLOADING
        sample_task.download_speed = 1024000  # 1 MB/s

        with patch.object(queue_manager, "_try_start_next"):
            queue_manager.add_task(sample_task)

        speed_item = queue_tab.queue_table.item(0, 5)
        assert speed_item is not None
        # Should show formatted speed
        assert speed_item.text() != "-"

    def test_table_output_directory(self, queue_tab, queue_manager, sample_task):
        """Test output directory display."""
        with patch.object(queue_manager, "_try_start_next"):
            queue_manager.add_task(sample_task)

        output_item = queue_tab.queue_table.item(0, 6)
        assert output_item is not None
        assert output_item.text() == sample_task.output_directory
