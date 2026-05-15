"""
Playlist viewer dialog for YT-DLP Studio.

This module provides a dialog to view and select videos from a playlist.
"""

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,  # ← ADD THIS - needed for thumbnail display
)

from ..backend.playlist_fetcher import PlaylistInfo
from ..utils.logger import get_logger
from ..utils.translations import tr

logger = get_logger()


class PlaylistDialog(QDialog):
    """
    Dialog to display playlist information and select videos.

    Shows playlist metadata and list of videos with checkboxes for selection.

    Signals:
        videos_selected: Emitted when user clicks download (list of video URLs, quality)
    """

    videos_selected = Signal(list, str)  # (urls, quality)

    def __init__(self, playlist_info: PlaylistInfo, parent=None):
        """
        Initialize playlist dialog.

        Args:
            playlist_info: PlaylistInfo object with playlist metadata
            parent: Parent widget
        """
        super().__init__(parent)
        self.playlist_info = playlist_info
        self.checkboxes = []  # Store checkboxes for select all/none
        self._setup_ui()
        self._populate_videos()
        logger.debug(f"PlaylistDialog created for: {playlist_info.title}")

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle(tr("dialog_playlist_viewer"))
        self.setMinimumSize(QSize(900, 600))
        self.setMaximumSize(QSize(1200, 800))

        main_layout = QVBoxLayout(self)

        # Playlist info section
        info_group = QGroupBox(tr("group_playlist_information"))
        info_layout = QVBoxLayout()

        # Title
        title_label = QLabel(f"<b>{self.playlist_info.title}</b>")
        title_label.setWordWrap(True)
        title_label.setStyleSheet("font-size: 14px; color: #ffffff;")
        info_layout.addWidget(title_label)

        # Stats row
        stats_layout = QHBoxLayout()
        stats_layout.addWidget(QLabel(tr("label_videos_count", count=self.playlist_info.video_count)))
        if self.playlist_info.uploader:
            stats_layout.addWidget(QLabel(f"| {tr('label_uploader')}: {self.playlist_info.uploader}"))
        stats_layout.addStretch()
        info_layout.addLayout(stats_layout)

        info_group.setLayout(info_layout)
        main_layout.addWidget(info_group)

        # Selection controls
        controls_layout = QHBoxLayout()

        select_all_btn = QPushButton(tr("button_select_all"))
        select_all_btn.clicked.connect(self._select_all)
        controls_layout.addWidget(select_all_btn)

        select_none_btn = QPushButton(tr("button_select_none"))
        select_none_btn.clicked.connect(self._select_none)
        controls_layout.addWidget(select_none_btn)

        controls_layout.addStretch()

        # Quality selector
        controls_layout.addWidget(QLabel(tr("label_quality_playlist")))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(
            [tr("quality_best"), tr("quality_1080p"), tr("quality_720p"), tr("quality_480p"), tr("quality_audio_only")]
        )
        controls_layout.addWidget(self.quality_combo)

        main_layout.addLayout(controls_layout)

        # Videos table
        self.videos_table = QTableWidget()
        self.videos_table.setColumnCount(5)
        self.videos_table.setHorizontalHeaderLabels(["Select", "#", "Title", "Duration", "Uploader"])

        # Set column widths
        header = self.videos_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # Select checkbox
        header.setSectionResizeMode(1, QHeaderView.Fixed)  # Index
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Title
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Duration
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Uploader

        self.videos_table.setColumnWidth(0, 60)
        self.videos_table.setColumnWidth(1, 50)

        # Enable row selection
        self.videos_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.videos_table.setAlternatingRowColors(True)

        main_layout.addWidget(self.videos_table)

        # Button section
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton(tr("cancel"))
        cancel_button.setMinimumWidth(100)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        download_button = QPushButton("Add to Queue")
        download_button.setMinimumWidth(150)
        download_button.clicked.connect(self._on_download_clicked)
        download_button.setStyleSheet("""
            QPushButton {
                background-color: #0e639c;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
            QPushButton:pressed {
                background-color: #0d5689;
            }
        """)
        button_layout.addWidget(download_button)

        main_layout.addLayout(button_layout)

    def _populate_videos(self) -> None:
        """Populate the videos table."""
        self.videos_table.setRowCount(len(self.playlist_info.videos))

        for idx, video in enumerate(self.playlist_info.videos):
            # Checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(True)  # Default: all selected
            self.checkboxes.append(checkbox)
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self.videos_table.setCellWidget(idx, 0, checkbox_widget)

            # Index
            index_item = QTableWidgetItem(str(video.index))
            index_item.setTextAlignment(Qt.AlignCenter)
            self.videos_table.setItem(idx, 1, index_item)

            # Title
            title_item = QTableWidgetItem(video.title)
            self.videos_table.setItem(idx, 2, title_item)

            # Duration
            duration_item = QTableWidgetItem(video.get_duration_formatted())
            duration_item.setTextAlignment(Qt.AlignCenter)
            self.videos_table.setItem(idx, 3, duration_item)

            # Uploader
            uploader_item = QTableWidgetItem(video.uploader or "-")
            self.videos_table.setItem(idx, 4, uploader_item)

        logger.debug(f"Populated {len(self.playlist_info.videos)} videos in table")

    def _select_all(self) -> None:
        """Select all videos."""
        for checkbox in self.checkboxes:
            checkbox.setChecked(True)
        logger.debug("Selected all videos")

    def _select_none(self) -> None:
        """Deselect all videos."""
        for checkbox in self.checkboxes:
            checkbox.setChecked(False)
        logger.debug("Deselected all videos")

    def _on_download_clicked(self) -> None:
        """Handle download button click."""
        # Get selected video URLs
        selected_urls = []
        for idx, checkbox in enumerate(self.checkboxes):
            if checkbox.isChecked():
                video = self.playlist_info.videos[idx]
                selected_urls.append(video.url)

        if not selected_urls:
            QMessageBox.warning(self, tr("dialog_no_videos_selected"), tr("msg_select_at_least_one_video"))
            return

        # Get selected quality
        quality = self.quality_combo.currentText()

        logger.info(f"User selected {len(selected_urls)} videos with quality: {quality}")

        # Emit signal with selected videos and quality
        self.videos_selected.emit(selected_urls, quality)

        # Close dialog
        self.accept()
