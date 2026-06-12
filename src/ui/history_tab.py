"""
History tab UI for YT-DLP Studio.

Displays download history and statistics.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedLayout,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..backend.history_manager import HistoryManager
from ..utils.file_helper import FileHelper
from ..utils.logger import get_logger
from ..utils.translations import tr

logger = get_logger()


class HistoryTab(QWidget):
    """History tab widget showing download history and statistics."""

    def __init__(self, history_manager: HistoryManager, parent=None):
        """
        Initialize history tab.

        Args:
            history_manager: HistoryManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.history_manager = history_manager
        self._setup_ui()
        self._load_history()
        logger.info("HistoryTab initialized")

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        main_layout = QVBoxLayout(self)

        # Statistics section
        stats_group = QGroupBox(tr("history_statistics"))
        stats_layout = QVBoxLayout()
        self.stats_label = QLabel()
        stats_layout.addWidget(self.stats_label)
        stats_group.setLayout(stats_layout)
        main_layout.addWidget(stats_group)

        # Search bar
        search_layout = QHBoxLayout()
        search_label = QLabel(tr("label_search"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(tr("placeholder_search_history"))
        self.search_input.textChanged.connect(self._on_search)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        main_layout.addLayout(search_layout)

        # History table
        history_group = QGroupBox(tr("history_download_history"))
        history_layout = QVBoxLayout()

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels(
            [tr("col_datetime"), tr("col_title"), tr("col_quality"), tr("col_status"), tr("col_size"), tr("col_speed")]
        )
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.horizontalHeader().setStretchLastSection(True)

        # Empty-state placeholder shown when history_manager has zero entries.
        # Translation keys history_empty / history_empty_hint were previously
        # declared but never rendered.
        self._history_empty_widget = QWidget()
        empty_layout = QVBoxLayout(self._history_empty_widget)
        empty_layout.setAlignment(Qt.AlignCenter)
        empty_title = QLabel(tr("history_empty"))
        empty_title.setAlignment(Qt.AlignCenter)
        empty_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        empty_hint = QLabel(tr("history_empty_hint"))
        empty_hint.setAlignment(Qt.AlignCenter)
        empty_hint.setStyleSheet("color: palette(mid);")
        empty_layout.addWidget(empty_title)
        empty_layout.addWidget(empty_hint)

        self._history_stack = QStackedLayout()
        self._history_stack.addWidget(self.history_table)
        self._history_stack.addWidget(self._history_empty_widget)
        history_layout.addLayout(self._history_stack)
        history_group.setLayout(history_layout)
        main_layout.addWidget(history_group)

        # Buttons (v1.8.0 - clean, professional, consistent sizing)
        button_layout = QHBoxLayout()

        self.refresh_button = QPushButton(tr("button_refresh"))
        self.refresh_button.setMinimumWidth(120)
        self.refresh_button.clicked.connect(self._load_history)

        self.export_button = QPushButton(tr("button_export_csv"))
        self.export_button.setMinimumWidth(120)
        self.export_button.clicked.connect(self._export_csv)

        self.open_dir_button = QPushButton(tr("button_open_directory"))
        self.open_dir_button.setMinimumWidth(140)
        self.open_dir_button.clicked.connect(self._open_download_directory)
        self.open_dir_button.setToolTip(tr("tooltip_open_downloads_dir"))

        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.export_button)
        button_layout.addWidget(self.open_dir_button)
        button_layout.addStretch()

        self.clear_completed_button = QPushButton(tr("button_clear_completed"))
        self.clear_completed_button.setMinimumWidth(140)
        self.clear_completed_button.clicked.connect(lambda: self._clear_history("completed"))

        self.clear_failed_button = QPushButton(tr("button_clear_failed"))
        self.clear_failed_button.setMinimumWidth(140)
        self.clear_failed_button.clicked.connect(lambda: self._clear_history("failed"))

        self.clear_all_button = QPushButton(tr("button_clear_all"))
        self.clear_all_button.setMinimumWidth(120)
        self.clear_all_button.clicked.connect(lambda: self._clear_history(None))

        button_layout.addWidget(self.clear_completed_button)
        button_layout.addWidget(self.clear_failed_button)
        button_layout.addWidget(self.clear_all_button)

        main_layout.addLayout(button_layout)

    def _load_history(self) -> None:
        """Load and display history."""
        # Get statistics
        stats = self.history_manager.get_statistics()
        stats_text = f"""
        <b>{tr('stat_total_downloads')}:</b> {stats['total_downloads']}<br>
        <b>{tr('stat_completed')}:</b> {stats['completed']} | <b>{tr('stat_failed')}:</b> {stats['failed']} | <b>{tr('stat_cancelled')}:</b> {stats['cancelled']}<br>
        <b>{tr('stat_success_rate')}:</b> {stats['success_rate']:.1f}%<br>
        <b>{tr('stat_total_downloaded')}:</b> {FileHelper.format_size(stats['total_size_bytes'])}<br>
        <b>{tr('stat_average_speed')}:</b> {FileHelper.format_size(int(stats['average_speed_bps']))}/s
        """
        self.stats_label.setText(stats_text)

        # Load history entries
        entries = self.history_manager.get_history(limit=100)

        self.history_table.setRowCount(len(entries))
        # Swap to the empty-state placeholder when history has no entries;
        # the table (index 0) shows otherwise.
        self._history_stack.setCurrentIndex(0 if entries else 1)
        for row, entry in enumerate(entries):
            # Date/Time
            date_item = QTableWidgetItem(entry.timestamp.strftime("%Y-%m-%d %H:%M"))
            self.history_table.setItem(row, 0, date_item)

            # Title
            title_item = QTableWidgetItem(entry.title[:50])
            self.history_table.setItem(row, 1, title_item)

            # Quality
            quality_item = QTableWidgetItem(entry.quality)
            self.history_table.setItem(row, 2, quality_item)

            # Status
            status_item = QTableWidgetItem(entry.status.upper())
            if entry.status == "completed":
                status_item.setForeground(Qt.green)
            elif entry.status == "failed":
                status_item.setForeground(Qt.red)
            else:
                status_item.setForeground(Qt.gray)
            self.history_table.setItem(row, 3, status_item)

            # Size
            size_item = QTableWidgetItem(FileHelper.format_size(entry.file_size))
            self.history_table.setItem(row, 4, size_item)

            # Speed
            speed_item = QTableWidgetItem(f"{FileHelper.format_size(int(entry.download_speed))}/s")
            self.history_table.setItem(row, 5, speed_item)

    def _on_search(self, query: str) -> None:
        """Handle search input."""
        if not query.strip():
            self._load_history()
            return

        results = self.history_manager.search_history(query)

        self.history_table.setRowCount(len(results))
        for row, entry in enumerate(results):
            # Date/Time
            date_item = QTableWidgetItem(entry.timestamp.strftime("%Y-%m-%d %H:%M"))
            self.history_table.setItem(row, 0, date_item)

            # Title
            title_item = QTableWidgetItem(entry.title[:50])
            self.history_table.setItem(row, 1, title_item)

            # Quality
            quality_item = QTableWidgetItem(entry.quality)
            self.history_table.setItem(row, 2, quality_item)

            # Status
            status_item = QTableWidgetItem(entry.status.upper())
            self.history_table.setItem(row, 3, status_item)

            # Size
            size_item = QTableWidgetItem(FileHelper.format_size(entry.file_size))
            self.history_table.setItem(row, 4, size_item)

            # Speed
            speed_item = QTableWidgetItem(f"{FileHelper.format_size(int(entry.download_speed))}/s")
            self.history_table.setItem(row, 5, speed_item)

    def _export_csv(self) -> None:
        """Export history to CSV."""
        filepath, _ = QFileDialog.getSaveFileName(
            self, tr("dialog_export_history"), "download_history.csv", tr("filter_csv_files")
        )

        if filepath:
            from pathlib import Path

            success = self.history_manager.export_to_csv(Path(filepath))
            if success:
                QMessageBox.information(self, tr("msg_success"), f"{tr('msg_history_exported')}: {filepath}")
            else:
                QMessageBox.critical(self, tr("error"), tr("msg_export_failed"))

    def _clear_history(self, status: str | None) -> None:
        """Clear history entries."""
        if status:
            reply = QMessageBox.question(
                self,
                tr("dialog_confirm_clear"),
                tr("msg_clear_status_confirm", status=status),
                QMessageBox.Yes | QMessageBox.No,
            )
        else:
            reply = QMessageBox.question(
                self, tr("dialog_confirm_clear_all"), tr("msg_clear_all_confirm"), QMessageBox.Yes | QMessageBox.No
            )

        if reply == QMessageBox.Yes:
            count = self.history_manager.clear_history(status)
            self._load_history()
            QMessageBox.information(self, tr("msg_success"), tr("msg_cleared_entries", count=count))

    def _open_download_directory(self) -> None:
        """Open the download directory in file explorer (v1.7.0)."""
        import os
        import platform
        import subprocess

        from ..backend.config_manager import ConfigManager

        # Get the default download directory from config
        config_manager = ConfigManager()
        config = config_manager.get_config()
        directory = config.output_directory

        if not directory or not os.path.exists(directory):
            QMessageBox.warning(self, tr("msg_dir_not_found"), f"{tr('msg_download_dir_not_exist')}:\n{directory}")
            return

        try:
            # Open directory based on platform
            system = platform.system()

            if system == "Windows":
                os.startfile(directory)
            elif system == "Darwin":  # macOS
                subprocess.Popen(["open", directory])
            else:  # Linux and other Unix-like
                subprocess.Popen(["xdg-open", directory])

            logger.info(f"Opened download directory: {directory}")

        except Exception as e:
            logger.error(f"Failed to open directory: {e}")
            QMessageBox.critical(self, tr("error"), f"{tr('msg_failed_open_dir')}:\n{e}")

    def refresh(self) -> None:
        """Refresh the history display."""
        self._load_history()
