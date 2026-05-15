"""
Queue tab UI for YT-DLP Studio.

Displays and manages the download queue.
"""

from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..backend.queue_manager import QueueManager
from ..models.download_task import DownloadTask, TaskStatus
from ..utils.file_helper import FileHelper
from ..utils.logger import get_logger
from ..utils.translations import tr

logger = get_logger()


class QueueTab(QWidget):
    """
    Queue management tab.

    Displays download queue in table format with controls
    to manage, reorder, and monitor downloads.
    """

    def __init__(self, queue_manager: QueueManager, parent=None):
        """
        Initialize queue tab.

        Args:
            queue_manager: QueueManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.queue_manager = queue_manager
        self._setup_ui()
        self._setup_shortcuts()
        self._connect_signals()
        logger.info("QueueTab initialized")

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        main_layout = QVBoxLayout(self)

        # Statistics bar
        stats_group = QGroupBox(tr("queue_statistics"))
        stats_layout = QHBoxLayout()

        self.total_label = QLabel(f"{tr('stat_total')}: 0")
        self.pending_label = QLabel(f"{tr('stat_pending')}: 0")
        self.active_label = QLabel(f"{tr('stat_active')}: 0")
        self.completed_label = QLabel(f"{tr('stat_completed')}: 0")
        self.failed_label = QLabel(f"{tr('stat_failed')}: 0")

        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(QLabel("|"))
        stats_layout.addWidget(self.pending_label)
        stats_layout.addWidget(QLabel("|"))
        stats_layout.addWidget(self.active_label)
        stats_layout.addWidget(QLabel("|"))
        stats_layout.addWidget(self.completed_label)
        stats_layout.addWidget(QLabel("|"))
        stats_layout.addWidget(self.failed_label)
        stats_layout.addStretch()

        stats_group.setLayout(stats_layout)
        main_layout.addWidget(stats_group)

        # Queue table
        queue_group = QGroupBox(tr("queue_download_queue"))
        queue_layout = QVBoxLayout()

        self.queue_table = QTableWidget()
        self.queue_table.setColumnCount(8)  # v2.1.0: Added Actions column
        self.queue_table.setHorizontalHeaderLabels(
            [
                tr("col_video_name"),
                tr("col_url"),
                tr("col_quality"),
                tr("col_status"),
                tr("col_progress"),
                tr("col_speed"),
                tr("col_output"),
                "Actions",
            ]
        )

        # Set column widths
        header = self.queue_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Video Name (v1.7.0)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # URL
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Quality
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Status
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Progress
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Speed
        header.setSectionResizeMode(6, QHeaderView.Stretch)  # Output
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # Actions (v2.1.0)

        # Enable selection
        self.queue_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.queue_table.setSelectionMode(QTableWidget.SingleSelection)

        queue_layout.addWidget(self.queue_table)
        queue_group.setLayout(queue_layout)
        main_layout.addWidget(queue_group)

        # Control buttons (v1.8.0 - clean, professional, consistent sizing)
        button_layout = QHBoxLayout()

        # Queue control buttons
        self.start_button = QPushButton(tr("button_start_queue"))
        self.start_button.setMinimumWidth(120)
        self.start_button.clicked.connect(self._on_start_clicked)

        self.pause_button = QPushButton(tr("button_pause_queue"))
        self.pause_button.setMinimumWidth(120)
        self.pause_button.clicked.connect(self._on_pause_clicked)

        self.stop_button = QPushButton(tr("button_stop_all"))
        self.stop_button.setMinimumWidth(120)
        self.stop_button.clicked.connect(self._on_stop_clicked)

        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addStretch()

        # Task management buttons
        self.move_up_button = QPushButton(tr("button_move_up"))
        self.move_up_button.setMinimumWidth(100)
        self.move_up_button.clicked.connect(self._on_move_up_clicked)

        self.move_down_button = QPushButton(tr("button_move_down"))
        self.move_down_button.setMinimumWidth(100)
        self.move_down_button.clicked.connect(self._on_move_down_clicked)

        self.remove_button = QPushButton(tr("button_remove"))
        self.remove_button.setMinimumWidth(100)
        self.remove_button.clicked.connect(self._on_remove_clicked)

        button_layout.addWidget(self.move_up_button)
        button_layout.addWidget(self.move_down_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addStretch()

        # File operations (v1.7.0)
        self.open_file_button = QPushButton(tr("button_open_file"))
        self.open_file_button.setMinimumWidth(120)
        self.open_file_button.clicked.connect(self._on_open_file_clicked)
        self.open_file_button.setToolTip(tr("tooltip_open_file"))

        button_layout.addWidget(self.open_file_button)
        button_layout.addStretch()

        # Clear buttons
        self.clear_completed_button = QPushButton(tr("button_clear_completed"))
        self.clear_completed_button.setMinimumWidth(140)
        self.clear_completed_button.clicked.connect(self._on_clear_completed_clicked)

        self.clear_failed_button = QPushButton(tr("button_clear_failed"))
        self.clear_failed_button.setMinimumWidth(140)
        self.clear_failed_button.clicked.connect(self._on_clear_failed_clicked)

        button_layout.addWidget(self.clear_completed_button)
        button_layout.addWidget(self.clear_failed_button)

        main_layout.addLayout(button_layout)

    def _setup_shortcuts(self) -> None:
        """Set up keyboard shortcuts for the queue tab."""
        # Delete - Remove selected task
        delete_shortcut = QShortcut(QKeySequence("Delete"), self)
        delete_shortcut.activated.connect(self._on_remove_clicked)

        # Ctrl+Up - Move task up
        up_shortcut = QShortcut(QKeySequence("Ctrl+Up"), self)
        up_shortcut.activated.connect(self._on_move_up_clicked)

        # Ctrl+Down - Move task down
        down_shortcut = QShortcut(QKeySequence("Ctrl+Down"), self)
        down_shortcut.activated.connect(self._on_move_down_clicked)

        # Space - Start/Pause queue
        space_shortcut = QShortcut(QKeySequence("Space"), self)
        space_shortcut.activated.connect(self._toggle_queue)

        logger.debug("Keyboard shortcuts configured for QueueTab")

    def _toggle_queue(self) -> None:
        """Toggle queue between started and paused."""
        stats = self.queue_manager.get_queue_statistics()
        if stats["active"] > 0 or stats["pending"] > 0:
            # Queue is active, pause it
            self._on_pause_clicked()
        else:
            # Queue is paused, start it
            self._on_start_clicked()

    def _connect_signals(self) -> None:
        """Connect queue manager signals."""
        self.queue_manager.queue_updated.connect(self._refresh_queue)
        self.queue_manager.task_progress.connect(self._on_task_progress)

    def _refresh_queue(self) -> None:
        """Refresh the queue display."""
        # Update statistics
        stats = self.queue_manager.get_queue_statistics()
        self.total_label.setText(f"{tr('stat_total')}: {stats['total']}")
        self.pending_label.setText(f"{tr('stat_pending')}: {stats['pending']}")
        self.active_label.setText(f"{tr('stat_active')}: {stats['active']}")
        self.completed_label.setText(f"{tr('stat_completed')}: {stats['completed']}")
        self.failed_label.setText(f"{tr('stat_failed')}: {stats['failed']}")

        # Update table
        tasks = self.queue_manager.get_all_tasks()
        self.queue_table.setRowCount(len(tasks))

        for row, task in enumerate(tasks):
            # Video Name (v1.7.0) - show filename or "Fetching..." if not available
            if task.filename:
                video_name = task.filename
            elif hasattr(task, "title") and task.title:
                video_name = task.title
            else:
                video_name = tr("text_fetching")
            name_item = QTableWidgetItem(video_name)
            name_item.setToolTip(video_name)
            self.queue_table.setItem(row, 0, name_item)

            # URL (truncated)
            url_item = QTableWidgetItem(self._truncate_url(task.url, 40))
            url_item.setToolTip(task.url)  # Full URL on hover
            self.queue_table.setItem(row, 1, url_item)

            # Quality (Format)
            quality_item = QTableWidgetItem(task.quality)
            self.queue_table.setItem(row, 2, quality_item)

            # Status
            status_item = QTableWidgetItem(task.status.value.upper())
            status_item.setForeground(self._get_status_color(task.status))
            self.queue_table.setItem(row, 3, status_item)

            # Progress
            if task.status == TaskStatus.DOWNLOADING:
                progress_text = f"{task.progress_percent:.1f}%"
            elif task.status == TaskStatus.COMPLETED:
                progress_text = "100%"
            else:
                progress_text = "-"
            progress_item = QTableWidgetItem(progress_text)
            self.queue_table.setItem(row, 4, progress_item)

            # Speed
            if task.status == TaskStatus.DOWNLOADING and task.download_speed > 0:
                speed_text = FileHelper.format_speed(task.download_speed)
            else:
                speed_text = "-"
            speed_item = QTableWidgetItem(speed_text)
            self.queue_table.setItem(row, 5, speed_item)

            # Output directory
            output_item = QTableWidgetItem(task.output_directory)
            output_item.setToolTip(task.output_directory)
            self.queue_table.setItem(row, 6, output_item)

            # Actions (v2.1.0)
            action_widget = self._create_action_buttons(row, task)
            self.queue_table.setCellWidget(row, 7, action_widget)

    def _on_task_progress(self, index: int, progress_data: dict) -> None:
        """
        Handle task progress update.

        Args:
            index: Task index
            progress_data: Progress data dictionary
        """
        if index < self.queue_table.rowCount():
            # Update progress column (v1.7.0: column 4 instead of 3)
            percent = progress_data.get("percent", 0)
            progress_item = QTableWidgetItem(f"{percent:.1f}%")
            self.queue_table.setItem(index, 4, progress_item)

            # Update speed column (v1.7.0: column 5 instead of 4)
            speed = progress_data.get("speed", 0)
            if speed > 0:
                speed_text = FileHelper.format_speed(speed)
            else:
                speed_text = "-"
            speed_item = QTableWidgetItem(speed_text)
            self.queue_table.setItem(index, 5, speed_item)

    def _on_start_clicked(self) -> None:
        """Handle start queue button click."""
        self.queue_manager.resume_queue()
        self.queue_manager.start_queue()
        logger.info("Queue started by user")

    def _on_pause_clicked(self) -> None:
        """Handle pause queue button click."""
        self.queue_manager.pause_queue()
        logger.info("Queue paused by user")

    def _on_stop_clicked(self) -> None:
        """Handle stop all button click."""
        self.queue_manager.stop_all()
        logger.info("All downloads stopped by user")

    def _on_move_up_clicked(self) -> None:
        """Handle move up button click."""
        selected = self.queue_table.selectedItems()
        if selected:
            row = self.queue_table.row(selected[0])
            if self.queue_manager.move_task_up(row):
                self.queue_table.selectRow(row - 1)

    def _on_move_down_clicked(self) -> None:
        """Handle move down button click."""
        selected = self.queue_table.selectedItems()
        if selected:
            row = self.queue_table.row(selected[0])
            if self.queue_manager.move_task_down(row):
                self.queue_table.selectRow(row + 1)

    def _on_remove_clicked(self) -> None:
        """Handle remove button click."""
        selected = self.queue_table.selectedItems()
        if selected:
            row = self.queue_table.row(selected[0])
            self.queue_manager.remove_task(row)

    def _on_clear_completed_clicked(self) -> None:
        """Handle clear completed button click."""
        count = self.queue_manager.clear_completed()
        logger.info(f"Cleared {count} completed tasks")

    def _on_clear_failed_clicked(self) -> None:
        """Handle clear failed button click."""
        count = self.queue_manager.clear_failed()
        logger.info(f"Cleared {count} failed tasks")

    def _on_open_file_clicked(self) -> None:
        """Handle open file button click (v1.7.0)."""
        import os
        import platform
        import subprocess

        from PySide6.QtWidgets import QMessageBox

        selected = self.queue_table.selectedItems()
        if not selected:
            QMessageBox.information(self, tr("msg_no_selection"), tr("msg_select_download"))
            return

        row = self.queue_table.row(selected[0])
        tasks = self.queue_manager.get_all_tasks()

        if row >= len(tasks):
            return

        task = tasks[row]

        # Check if task is completed
        if task.status != TaskStatus.COMPLETED:
            QMessageBox.warning(self, tr("msg_not_completed"), tr("msg_not_completed_desc"))
            return

        # Get file path
        if not task.filename:
            QMessageBox.warning(self, tr("msg_file_not_found"), tr("msg_file_path_unknown"))
            return

        file_path = os.path.join(task.output_directory, task.filename)

        if not os.path.exists(file_path):
            QMessageBox.warning(self, tr("msg_file_not_found"), f"{tr('msg_file_not_found_desc')}:\n{file_path}")
            return

        try:
            # Open file based on platform
            system = platform.system()

            if system == "Windows":
                os.startfile(file_path)
            elif system == "Darwin":  # macOS
                subprocess.Popen(["open", file_path])
            else:  # Linux and other Unix-like
                subprocess.Popen(["xdg-open", file_path])

            logger.info(f"Opened file: {file_path}")

        except Exception as e:
            logger.error(f"Failed to open file: {e}")
            QMessageBox.critical(self, tr("error"), f"{tr('msg_failed_open_file')}:\n{e}")

    @staticmethod
    def _truncate_url(url: str, max_length: int = 60) -> str:
        """
        Truncate URL for display.

        Args:
            url: Full URL
            max_length: Maximum length

        Returns:
            Truncated URL
        """
        if len(url) <= max_length:
            return url
        return url[: max_length - 3] + "..."

    def _create_action_buttons(self, row: int, task: DownloadTask) -> QWidget:
        """
        Create action buttons for task row (v2.1.0).

        Args:
            row: Row index
            task: DownloadTask

        Returns:
            Widget with action buttons
        """
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        # Cancel button - only for pending or downloading tasks
        if task.status in [TaskStatus.PENDING, TaskStatus.DOWNLOADING]:
            cancel_button = QPushButton(tr("button_cancel"))
            cancel_button.setMaximumWidth(60)
            cancel_button.setStyleSheet("""
                QPushButton {
                    background-color: #c74440;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    padding: 2px 6px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #e05148;
                }
                QPushButton:pressed {
                    background-color: #a83733;
                }
            """)
            cancel_button.clicked.connect(lambda checked, r=row: self._on_cancel_task(r))
            layout.addWidget(cancel_button)

        # Retry button - only for failed tasks
        elif task.status == TaskStatus.ERROR:
            retry_button = QPushButton(tr("button_retry"))
            retry_button.setMaximumWidth(60)
            retry_button.setStyleSheet("""
                QPushButton {
                    background-color: #0e639c;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    padding: 2px 6px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #1177bb;
                }
                QPushButton:pressed {
                    background-color: #0d5689;
                }
            """)
            retry_button.clicked.connect(lambda checked, r=row: self._on_retry_task(r))
            layout.addWidget(retry_button)

        layout.addStretch()
        return widget

    def _on_cancel_task(self, row: int) -> None:
        """
        Cancel individual task (v2.1.0).

        Args:
            row: Task row index
        """
        task = self.queue_manager.get_all_tasks()[row]
        if task.status == TaskStatus.DOWNLOADING:
            # Cancel the running worker
            if row in self.queue_manager.workers:
                self.queue_manager.workers[row].cancel()
                logger.info(f"Cancelled downloading task at row {row}")
        elif task.status == TaskStatus.PENDING:
            # Remove pending task
            self.queue_manager.remove_task(row)
            logger.info(f"Removed pending task at row {row}")

    def _on_retry_task(self, row: int) -> None:
        """
        Retry failed task (v2.1.0).

        Args:
            row: Task row index
        """
        task = self.queue_manager.get_all_tasks()[row]
        if task.status == TaskStatus.ERROR:
            # Reset task status to pending
            task.status = TaskStatus.PENDING
            task.error_message = ""
            task.progress_percent = 0.0
            self.queue_manager.queue_updated.emit()
            # Try to start it
            if self.queue_manager._auto_start:
                self.queue_manager._try_start_next()
            logger.info(f"Retrying failed task at row {row}")

    @staticmethod
    def _get_status_color(status: TaskStatus):
        """
        Get color for status.

        Args:
            status: Task status

        Returns:
            Qt color
        """
        from PySide6.QtGui import QColor

        colors = {
            TaskStatus.PENDING: QColor("#858585"),  # Gray
            TaskStatus.DOWNLOADING: QColor("#0e639c"),  # Blue
            TaskStatus.COMPLETED: QColor("#4ec9b0"),  # Green
            TaskStatus.ERROR: QColor("#f48771"),  # Red
            TaskStatus.CANCELLED: QColor("#858585"),  # Gray
        }
        return colors.get(status, QColor("#ffffff"))
