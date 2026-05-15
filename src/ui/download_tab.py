"""
Download tab UI for YT-DLP Studio.

Main interface for entering URLs and downloading videos.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..backend.config_manager import ConfigManager
from ..backend.download_worker import DownloadWorker
from ..backend.format_handler import FormatHandler
from ..backend.playlist_worker import PlaylistWorker
from ..backend.queue_manager import QueueManager
from ..backend.video_info_worker import VideoInfoWorker
from ..backend.yt_dlp_wrapper import YtDlpWrapper
from ..models.download_task import DownloadTask
from ..utils.constants import AUDIO_FORMATS, DEFAULT_AUDIO_FORMAT, DEFAULT_VIDEO_CONTAINER, VIDEO_CONTAINER_FORMATS
from ..utils.error_handler import ErrorHandler
from ..utils.logger import get_logger
from ..utils.playlist_detector import PlaylistDetector
from ..utils.translations import tr
from ..utils.validators import Validators
from .log_widget import LogWidget
from .playlist_dialog import PlaylistDialog
from .progress_bar import DownloadProgressWidget
from .subtitle_selection_dialog import SubtitleSelectionDialog
from .video_info_dialog import VideoInfoDialog

logger = get_logger()


class DownloadTab(QWidget):
    """
    Download tab widget.

    Provides interface for:
    - URL input
    - Quality selection
    - Output directory selection
    - Download button
    - Progress display
    - Log output

    Example:
        >>> tab = DownloadTab(config_manager)
        >>> # User interacts with UI
    """

    def __init__(self, config_manager: ConfigManager, queue_manager: QueueManager, parent=None):
        """
        Initialize download tab.

        Args:
            config_manager: ConfigManager instance
            queue_manager: QueueManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self.queue_manager = queue_manager
        self.current_worker: DownloadWorker | None = None
        self.info_worker: VideoInfoWorker | None = None
        self.playlist_worker: PlaylistWorker | None = None
        self.selected_subtitle_codes: list = []  # v2.0.0: Store selected subtitle language codes
        self._setup_ui()
        self._setup_shortcuts()
        self._load_config()
        logger.info("DownloadTab initialized")

    def update_output_directory(self, new_directory: str) -> None:
        """Update output directory (v1.9.0 smart folder logic)."""
        self.output_input.setText(new_directory)
        logger.info(f"Download tab output directory updated to: {new_directory}")

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)  # Add spacing between sections
        main_layout.setContentsMargins(8, 8, 8, 8)  # Add margins

        # Input section
        input_group = QGroupBox(tr("tab_download"))
        input_layout = QVBoxLayout()
        input_layout.setSpacing(10)  # Add spacing between input rows

        # URL input
        url_layout = QHBoxLayout()
        url_label = QLabel(tr("label_url"))
        url_label.setMinimumWidth(80)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(tr("download_url_placeholder"))
        self.url_input.returnPressed.connect(self._on_download_clicked)  # Enter key triggers download

        # Enable drag and drop
        self.url_input.setAcceptDrops(True)
        self.url_input.dragEnterEvent = self._drag_enter_event
        self.url_input.dropEvent = self._drop_event

        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)

        # Paste from Clipboard button
        self.paste_button = QPushButton(tr("button_paste"))
        self.paste_button.setMinimumWidth(80)
        self.paste_button.setToolTip(tr("tooltip_paste"))
        self.paste_button.clicked.connect(self._paste_from_clipboard)
        self.paste_button.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
                border: 1px solid #6a6a6a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
                padding: 7px 11px 5px 13px;
            }
        """)
        url_layout.addWidget(self.paste_button)

        # Show Info button
        self.show_info_button = QPushButton(tr("button_show_info"))
        self.show_info_button.setMinimumWidth(100)
        self.show_info_button.clicked.connect(self._on_show_info_clicked)
        self.show_info_button.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
            QPushButton:disabled {
                background-color: #3e3e3e;
                color: #858585;
            }
        """)
        url_layout.addWidget(self.show_info_button)

        input_layout.addLayout(url_layout)

        # v3.0.0: Download Type selection (Video or Audio)
        type_layout = QHBoxLayout()
        type_label = QLabel("Download Type:")
        type_label.setMinimumWidth(80)
        self.download_type_combo = QComboBox()
        self.download_type_combo.addItems(["Video", "Audio Only"])
        self.download_type_combo.currentTextChanged.connect(self._on_download_type_changed)
        self.download_type_combo.setToolTip("Choose whether to download video or extract audio only")
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.download_type_combo)
        input_layout.addLayout(type_layout)

        # Quality selection (dynamically updated based on download type)
        quality_layout = QHBoxLayout()
        self.quality_label = QLabel(tr("label_quality"))
        self.quality_label.setMinimumWidth(80)
        self.quality_combo = QComboBox()
        self.quality_combo.currentTextChanged.connect(self._on_quality_changed)
        quality_layout.addWidget(self.quality_label)
        quality_layout.addWidget(self.quality_combo)
        input_layout.addLayout(quality_layout)

        # v2.0.0: Video Container Format selection (only visible for video downloads)
        self.container_layout = QHBoxLayout()
        self.container_label = QLabel("Video Format:")
        self.container_label.setMinimumWidth(80)
        self.container_combo = QComboBox()
        self.container_combo.addItems(list(VIDEO_CONTAINER_FORMATS.keys()))
        self.container_combo.setCurrentText(DEFAULT_VIDEO_CONTAINER)
        self.container_combo.setToolTip("Choose video container format (MP4 recommended for compatibility)")
        self.container_layout.addWidget(self.container_label)
        self.container_layout.addWidget(self.container_combo)
        input_layout.addLayout(self.container_layout)

        # v2.0.0: Audio Format selection (only visible for audio downloads)
        self.audio_format_layout = QHBoxLayout()
        self.audio_format_label = QLabel("Audio Format:")
        self.audio_format_label.setMinimumWidth(80)
        self.audio_format_combo = QComboBox()
        self.audio_format_combo.addItems(list(AUDIO_FORMATS.keys()))
        self.audio_format_combo.setCurrentText(DEFAULT_AUDIO_FORMAT)
        self.audio_format_combo.setToolTip(
            "Choose audio format for audio-only downloads (MP3 recommended for compatibility)"
        )
        self.audio_format_layout.addWidget(self.audio_format_label)
        self.audio_format_layout.addWidget(self.audio_format_combo)
        input_layout.addLayout(self.audio_format_layout)

        # Initialize UI based on default download type (Video)
        self._update_quality_options()

        # Output directory
        output_layout = QHBoxLayout()
        output_label = QLabel(tr("label_save_to"))
        output_label.setMinimumWidth(80)
        self.output_input = QLineEdit()
        self.output_input.setReadOnly(True)
        self.browse_button = QPushButton(tr("button_browse"))
        self.browse_button.clicked.connect(self._browse_directory)

        # Open Directory button (v1.7.0)
        self.open_dir_button = QPushButton(tr("button_open_dir"))
        self.open_dir_button.setToolTip(tr("tooltip_open_dir"))
        self.open_dir_button.clicked.connect(self._open_directory)
        self.open_dir_button.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
        """)

        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_input)
        output_layout.addWidget(self.browse_button)
        output_layout.addWidget(self.open_dir_button)
        input_layout.addLayout(output_layout)

        # v1.7.0 features: Download options
        options_layout = QHBoxLayout()

        # Thumbnail checkbox
        self.thumbnail_checkbox = QCheckBox(tr("checkbox_thumbnail"))
        self.thumbnail_checkbox.setChecked(False)
        self.thumbnail_checkbox.setToolTip(tr("tooltip_thumbnail"))
        options_layout.addWidget(self.thumbnail_checkbox)

        # Subtitles checkbox
        self.subtitles_checkbox = QCheckBox(tr("checkbox_subtitles"))
        self.subtitles_checkbox.setChecked(False)
        self.subtitles_checkbox.stateChanged.connect(self._on_subtitles_toggled)
        self.subtitles_checkbox.setToolTip(tr("tooltip_subtitles"))
        options_layout.addWidget(self.subtitles_checkbox)

        # Subtitle languages input
        self.subtitle_langs_label = QLabel(tr("label_subtitle_langs"))
        self.subtitle_langs_label.setEnabled(False)
        options_layout.addWidget(self.subtitle_langs_label)

        self.subtitle_langs_input = QLineEdit()
        self.subtitle_langs_input.setText("en")
        self.subtitle_langs_input.setPlaceholderText(tr("placeholder_subtitle_langs"))
        self.subtitle_langs_input.setMaximumWidth(120)
        self.subtitle_langs_input.setEnabled(False)
        self.subtitle_langs_input.setToolTip(tr("tooltip_subtitle_langs"))
        options_layout.addWidget(self.subtitle_langs_input)

        # v2.0.0: Select Subtitles button
        self.select_subs_button = QPushButton("Select Subs")
        self.select_subs_button.setEnabled(False)
        self.select_subs_button.setMinimumWidth(100)
        self.select_subs_button.clicked.connect(self._on_select_subtitles_clicked)
        self.select_subs_button.setToolTip("Fetch and select specific subtitle languages")
        self.select_subs_button.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
            QPushButton:disabled {
                background-color: #3e3e3e;
                color: #858585;
            }
        """)
        options_layout.addWidget(self.select_subs_button)

        # v2.1.0: Metadata checkbox
        self.metadata_checkbox = QCheckBox(tr("checkbox_metadata"))
        self.metadata_checkbox.setChecked(False)
        self.metadata_checkbox.setToolTip(tr("tooltip_metadata"))
        options_layout.addWidget(self.metadata_checkbox)

        # v2.0.0: Comments checkbox
        self.comments_checkbox = QCheckBox(tr("checkbox_comments"))
        self.comments_checkbox.setChecked(False)
        self.comments_checkbox.setToolTip(tr("tooltip_comments"))
        options_layout.addWidget(self.comments_checkbox)

        options_layout.addStretch()

        input_layout.addLayout(options_layout)

        # Speed limit option
        speed_layout = QHBoxLayout()

        speed_label = QLabel(tr("label_speed_limit"))
        speed_label.setMinimumWidth(80)
        speed_layout.addWidget(speed_label)

        self.speed_limit_spinbox = QSpinBox()
        self.speed_limit_spinbox.setRange(0, 100000)
        self.speed_limit_spinbox.setValue(0)
        self.speed_limit_spinbox.setSuffix(" KB/s")
        self.speed_limit_spinbox.setSpecialValueText(tr("text_unlimited"))
        self.speed_limit_spinbox.setMaximumWidth(150)
        self.speed_limit_spinbox.setToolTip(tr("tooltip_speed_limit"))
        speed_layout.addWidget(self.speed_limit_spinbox)

        speed_layout.addStretch()

        input_layout.addLayout(speed_layout)

        # Download buttons
        button_layout = QHBoxLayout()

        # Batch Input button (v1.7.0)
        self.batch_button = QPushButton(tr("button_batch_input"))
        self.batch_button.setMinimumWidth(140)
        self.batch_button.setMinimumHeight(35)
        self.batch_button.clicked.connect(self._on_batch_input_clicked)
        self.batch_button.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
        """)
        self.batch_button.setToolTip(tr("tooltip_batch"))
        button_layout.addWidget(self.batch_button)

        button_layout.addStretch()

        # Add to Queue button
        self.add_to_queue_button = QPushButton(tr("button_add_to_queue"))
        self.add_to_queue_button.setMinimumWidth(140)
        self.add_to_queue_button.setMinimumHeight(35)
        self.add_to_queue_button.clicked.connect(self._on_add_to_queue_clicked)
        self.add_to_queue_button.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
            QPushButton:disabled {
                background-color: #3e3e3e;
                color: #858585;
            }
        """)
        button_layout.addWidget(self.add_to_queue_button)

        # Download Now button
        self.download_button = QPushButton(tr("button_download_now"))
        self.download_button.setMinimumWidth(150)
        self.download_button.setMinimumHeight(35)
        self.download_button.clicked.connect(self._on_download_clicked)
        self.download_button.setStyleSheet("""
            QPushButton {
                background-color: #0e639c;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1177bb;
                border: 1px solid #1a85cc;
            }
            QPushButton:pressed {
                background-color: #0d5689;
                padding: 9px 15px 7px 17px;
            }
            QPushButton:disabled {
                background-color: #3e3e3e;
                color: #858585;
            }
        """)
        button_layout.addWidget(self.download_button)
        button_layout.addStretch()
        input_layout.addLayout(button_layout)

        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group)

        # Progress section
        progress_group = QGroupBox(tr("group_progress"))
        progress_layout = QVBoxLayout()
        self.progress_widget = DownloadProgressWidget()
        progress_layout.addWidget(self.progress_widget)
        progress_group.setLayout(progress_layout)
        main_layout.addWidget(progress_group)

        # Log section (v1.9.0 - collapsible)
        log_layout_container = QVBoxLayout()

        # Toggle button for log
        toggle_layout = QHBoxLayout()
        self.toggle_log_button = QPushButton(tr("button_show_log"))
        self.toggle_log_button.setMinimumWidth(150)
        self.toggle_log_button.clicked.connect(self._toggle_log_visibility)
        toggle_layout.addWidget(self.toggle_log_button)
        toggle_layout.addStretch()
        log_layout_container.addLayout(toggle_layout)

        # Log group (hidden by default)
        self.log_group = QGroupBox(tr("group_log"))
        log_layout = QVBoxLayout()
        self.log_widget = LogWidget()
        self.log_widget.setMinimumHeight(150)
        log_layout.addWidget(self.log_widget)

        # Clear log button
        clear_layout = QHBoxLayout()
        clear_layout.addStretch()
        self.clear_log_button = QPushButton(tr("button_clear_log"))
        self.clear_log_button.clicked.connect(self.log_widget.clear_log)
        clear_layout.addWidget(self.clear_log_button)
        log_layout.addLayout(clear_layout)

        self.log_group.setLayout(log_layout)
        self.log_group.setVisible(False)  # Hidden by default
        log_layout_container.addWidget(self.log_group)

        main_layout.addLayout(log_layout_container)

    def _toggle_log_visibility(self) -> None:
        """Toggle log visibility (v1.9.0)."""
        is_visible = self.log_group.isVisible()
        self.log_group.setVisible(not is_visible)

        if is_visible:
            self.toggle_log_button.setText(tr("button_show_log"))
        else:
            self.toggle_log_button.setText(tr("button_hide_log"))

    def _setup_shortcuts(self) -> None:
        """Set up keyboard shortcuts for the download tab."""
        # Ctrl+V - Paste from clipboard
        paste_shortcut = QShortcut(QKeySequence("Ctrl+V"), self)
        paste_shortcut.activated.connect(self._paste_from_clipboard)

        # Ctrl+D - Download Now
        download_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        download_shortcut.activated.connect(self._on_download_clicked)

        # Ctrl+Shift+Q - Add to Queue
        queue_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Q"), self)
        queue_shortcut.activated.connect(self._on_add_to_queue_clicked)

        # Ctrl+Shift+I - Show Info
        info_shortcut = QShortcut(QKeySequence("Ctrl+Shift+I"), self)
        info_shortcut.activated.connect(self._on_show_info_clicked)

        logger.debug("Keyboard shortcuts configured for DownloadTab")

    def _paste_from_clipboard(self) -> None:
        """Paste URL from clipboard into URL field."""
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()

        if text:
            self.url_input.setText(text)
            self.url_input.setFocus()
            self.log_widget.append_info(f"Pasted from clipboard: {text[:50]}...")
            logger.debug(f"URL pasted from clipboard: {text}")

    def _load_config(self) -> None:
        """Load configuration and set UI values."""
        config = self.config_manager.get_config()
        self.output_input.setText(config.output_directory)
        self.quality_combo.setCurrentText(config.default_quality)
        self.url_input.setText(config.last_url)
        logger.debug("Config loaded into DownloadTab UI")

        # Auto-detect URL from clipboard on startup
        self._auto_detect_clipboard_url()

    def _auto_detect_clipboard_url(self) -> None:
        """Auto-detect and fill URL from clipboard if valid."""
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()

        if not text:
            return

        # Check if clipboard contains a valid URL
        is_valid, _ = Validators.is_valid_url(text)

        if is_valid:
            # Only auto-fill if URL field is empty or contains last_url
            current_url = self.url_input.text().strip()
            config = self.config_manager.get_config()

            if not current_url or current_url == config.last_url:
                self.url_input.setText(text)
                self.log_widget.append_info("Auto-detected URL from clipboard")
                logger.info(f"Auto-filled URL from clipboard: {text[:50]}...")
            else:
                logger.debug("URL field not empty, skipping auto-fill")

    def _on_download_type_changed(self, download_type: str) -> None:
        """
        Handle download type change (Video or Audio Only).

        Args:
            download_type: Selected download type ("Video" or "Audio Only")
        """
        self._update_quality_options()
        logger.info(f"Download type changed to: {download_type}")

    def _update_quality_options(self) -> None:
        """
        Update quality dropdown and show/hide format options based on download type.
        v3.0.0: Separate video and audio quality options for better UX
        """
        download_type = self.download_type_combo.currentText()
        is_audio = download_type == "Audio Only"

        # Clear and update quality combo
        self.quality_combo.clear()

        if is_audio:
            # Show audio quality options only
            audio_qualities = ["Best Quality", "Audio 320kbps", "Audio 256kbps", "Audio 192kbps", "Audio 128kbps"]
            self.quality_combo.addItems(audio_qualities)
            self.quality_combo.setCurrentText("Best Quality")  # Default

            # Hide video format, show audio format
            self.container_label.setVisible(False)
            self.container_combo.setVisible(False)
            self.audio_format_label.setVisible(True)
            self.audio_format_combo.setVisible(True)

            if hasattr(self, "log_widget"):
                self.log_widget.append_info("Audio-only mode: Select quality and audio format")
        else:
            # Show video quality options only
            video_qualities = [
                "Best Quality",
                "8K (4320p)",
                "4K (2160p)",
                "2K (1440p)",
                "1080p (Full HD)",
                "720p (HD)",
                "480p (SD)",
                "360p",
            ]
            self.quality_combo.addItems(video_qualities)
            self.quality_combo.setCurrentText("Best Quality")  # Default

            # Show video format, hide audio format
            self.container_label.setVisible(True)
            self.container_combo.setVisible(True)
            self.audio_format_label.setVisible(False)
            self.audio_format_combo.setVisible(False)

            if hasattr(self, "log_widget"):
                self.log_widget.append_info("Video mode: Select quality and video format")

    def _on_quality_changed(self, quality: str) -> None:
        """
        Handle quality selection change.

        Args:
            quality: Selected quality name
        """
        if hasattr(self, "log_widget"):
            description = FormatHandler.get_quality_description(quality)
            self.log_widget.append_info(f"Quality selected: {quality} - {description}")

    def _browse_directory(self) -> None:
        """Open directory browser dialog."""
        current_dir = self.output_input.text()
        directory = QFileDialog.getExistingDirectory(self, tr("dialog_select_download_dir"), current_dir)

        if directory:
            self.output_input.setText(directory)
            self.config_manager.update_config(output_directory=directory)
            self.log_widget.append_info(f"Output directory changed to: {directory}")

    def _open_directory(self) -> None:
        """Open the download directory in file explorer (v1.7.0)."""
        import os
        import platform
        import subprocess

        directory = self.output_input.text().strip()

        if not directory or not os.path.exists(directory):
            QMessageBox.warning(self, tr("msg_dir_not_found"), tr("msg_dir_not_exist", directory=directory))
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

            self.log_widget.append_success(f"Opened directory: {directory}")
            logger.info(f"Opened download directory: {directory}")

        except Exception as e:
            logger.error(f"Failed to open directory: {e}")
            QMessageBox.critical(self, tr("error_generic"), tr("msg_failed_open_dir"))

    def _on_add_to_queue_clicked(self) -> None:
        """Handle add to queue button click."""
        # Get inputs
        url = self.url_input.text().strip()
        output_dir = self.output_input.text().strip()
        quality = self.quality_combo.currentText()

        # Validate URL
        is_valid, error = Validators.is_valid_url(url)
        if not is_valid:
            QMessageBox.warning(self, tr("error_invalid_url"), error)
            self.log_widget.append_error(f"{tr('error_invalid_url')}: {error}")
            return

        # Validate directory
        is_valid, error = Validators.is_valid_directory(output_dir)
        if not is_valid:
            QMessageBox.warning(self, tr("error_invalid_dir"), error)
            self.log_widget.append_error(f"{tr('error_invalid_dir')}: {error}")
            return

        # Check if URL is a playlist
        is_playlist, platform = PlaylistDetector.is_playlist_url(url)

        if is_playlist:
            # Ask user if they want to fetch playlist info
            reply = QMessageBox.question(
                self,
                tr("dialog_playlist_detected"),
                tr("msg_playlist_detected_options", platform=platform),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )

            if reply == QMessageBox.Yes:
                # Fetch and show playlist dialog
                self._fetch_playlist_info(url, platform)
                return

        # Save last URL
        self.config_manager.update_config(last_url=url)

        # Determine if this is an audio-only download (v3.0.0: from download type)
        audio_only = self.download_type_combo.currentText() == "Audio Only"

        # Check for duplicate download (same URL + quality + format)
        if self.queue_manager.is_duplicate_task(url, quality, audio_only):
            reply = QMessageBox.question(
                self,
                tr("duplicate_download"),
                tr("duplicate_download_message"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )

            if reply == QMessageBox.No:
                return  # User chose not to add duplicate

        # Create download task with v2.1.0 options
        task = DownloadTask(
            url=url,
            output_directory=output_dir,
            quality=quality,
            audio_only=audio_only,
            download_thumbnail=self.thumbnail_checkbox.isChecked(),
            download_subtitles=self.subtitles_checkbox.isChecked(),
            subtitle_languages=self.subtitle_langs_input.text().strip() or "en",
            speed_limit=self.speed_limit_spinbox.value(),
            video_container=VIDEO_CONTAINER_FORMATS.get(self.container_combo.currentText()),
            audio_format=AUDIO_FORMATS.get(self.audio_format_combo.currentText(), "mp3"),
            selected_subtitles=self.selected_subtitle_codes,  # v2.0.0
            download_metadata=self.metadata_checkbox.isChecked(),  # v2.1.0
            download_comments=self.comments_checkbox.isChecked(),  # v2.0.0
            auto_number_duplicates=True,  # v2.1.0 - always enabled
        )

        # Add to queue
        index = self.queue_manager.add_task(task)
        self.log_widget.append_success(f"Added to queue at position {index + 1}: {url}")

        # Clear URL input for next entry
        self.url_input.clear()

        # Show info message
        QMessageBox.information(self, tr("dialog_added_to_queue"), tr("msg_video_added_to_queue", position=index + 1))

    def _on_download_clicked(self) -> None:
        """Handle download button click - adds to queue and starts immediately."""
        # Get inputs
        url = self.url_input.text().strip()
        output_dir = self.output_input.text().strip()
        quality = self.quality_combo.currentText()

        # Validate URL
        is_valid, error = Validators.is_valid_url(url)
        if not is_valid:
            QMessageBox.warning(self, tr("error_invalid_url"), error)
            self.log_widget.append_error(f"{tr('error_invalid_url')}: {error}")
            return

        # Validate directory
        is_valid, error = Validators.is_valid_directory(output_dir)
        if not is_valid:
            QMessageBox.warning(self, tr("error_invalid_directory"), error)
            self.log_widget.append_error(f"{tr('error_invalid_directory')}: {error}")
            return

        # Save last URL
        self.config_manager.update_config(last_url=url)

        # Determine if this is an audio-only download (v3.0.0: from download type)
        audio_only = self.download_type_combo.currentText() == "Audio Only"

        # Create download task with v2.1.0 options
        task = DownloadTask(
            url=url,
            output_directory=output_dir,
            quality=quality,
            audio_only=audio_only,
            download_thumbnail=self.thumbnail_checkbox.isChecked(),
            download_subtitles=self.subtitles_checkbox.isChecked(),
            subtitle_languages=self.subtitle_langs_input.text().strip() or "en",
            speed_limit=self.speed_limit_spinbox.value(),
            video_container=VIDEO_CONTAINER_FORMATS.get(self.container_combo.currentText()),
            audio_format=AUDIO_FORMATS.get(self.audio_format_combo.currentText(), "mp3"),
            selected_subtitles=self.selected_subtitle_codes,  # v2.0.0
            download_metadata=self.metadata_checkbox.isChecked(),  # v2.1.0
            download_comments=self.comments_checkbox.isChecked(),  # v2.0.0
            auto_number_duplicates=True,  # v2.1.0 - always enabled
        )

        # Add to queue - queue manager will auto-start it
        # This provides unified tracking in the Queue tab
        index = self.queue_manager.add_task(task)
        self.log_widget.append_success(f"Download started and added to queue at position {index + 1}")
        self.log_widget.append_info("Check the Queue tab to monitor progress")

        # Clear URL input for next entry
        self.url_input.clear()

    def _start_download(self, task: DownloadTask) -> None:
        """
        Start download in background worker.

        Args:
            task: DownloadTask to process
        """
        logger.info(f"Starting download: {task.url}")

        # Reset UI and show preparing state (v1.9.0)
        self.progress_widget.reset()
        self.progress_widget.set_preparing_state()
        self.log_widget.append_info(f"{tr('status_preparing')}: {task.url}")

        # Disable download button
        self.download_button.setEnabled(False)
        self.download_button.setText(tr("button_downloading"))

        # Create worker
        self.current_worker = DownloadWorker(task)

        # Connect signals
        self.current_worker.progress_updated.connect(self._on_progress_updated)
        self.current_worker.download_started.connect(self._on_download_started)
        self.current_worker.download_completed.connect(self._on_download_completed)
        self.current_worker.download_failed.connect(self._on_download_failed)
        self.current_worker.log_message.connect(self.log_widget.append_log)

        # Start worker
        self.current_worker.start()

    def _on_progress_updated(self, progress_data: dict) -> None:
        """
        Handle progress update from worker.

        Args:
            progress_data: Progress dictionary
        """
        self.progress_widget.update_progress(
            percent=progress_data.get("percent", 0),
            speed=progress_data.get("speed", 0),
            eta=progress_data.get("eta", 0),
            total_bytes=progress_data.get("total", 0),
            downloaded_bytes=progress_data.get("downloaded", 0),
        )

    def _on_download_started(self, title: str) -> None:
        """
        Handle download started signal.

        Args:
            title: Video title
        """
        self.log_widget.append_success(f"Download started: {title}")
        self.progress_widget.set_status("Downloading...")

    def _on_download_completed(self, filename: str) -> None:
        """
        Handle download completed signal.

        Args:
            filename: Output filename
        """
        logger.info(f"Download completed: {filename}")
        self.log_widget.append_success(f"Download completed: {filename}")
        self.progress_widget.set_success_state()

        # Re-enable button
        self.download_button.setEnabled(True)
        self.download_button.setText(tr("button_download_now"))

        # Show success message
        QMessageBox.information(self, tr("dialog_download_complete"), tr("msg_download_complete", filename=filename))

    def _on_download_failed(self, error_message: str) -> None:
        """
        Handle download failed signal.

        Args:
            error_message: Error description
        """
        logger.error(f"Download failed: {error_message}")
        self.log_widget.append_error(f"Download failed: {error_message}")
        self.progress_widget.set_error_state(error_message[:100])

        # Re-enable button
        self.download_button.setEnabled(True)
        self.download_button.setText(tr("button_download_now"))

        # Get better error info
        error_html = ErrorHandler.format_error_dialog_text(error_message)

        # Show detailed error dialog
        error_dialog = QMessageBox(self)
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setWindowTitle(tr("dialog_download_failed"))
        error_dialog.setTextFormat(Qt.RichText)
        error_dialog.setText(error_html)
        error_dialog.setStandardButtons(QMessageBox.Ok)
        error_dialog.exec()

    def _on_show_info_clicked(self) -> None:
        """Handle show info button click."""
        # Check if info worker is already running
        if self.info_worker and self.info_worker.isRunning():
            self.log_widget.append_error("Already fetching video info, please wait...")
            return

        # Check if playlist worker is already running
        if self.playlist_worker and self.playlist_worker.isRunning():
            self.log_widget.append_error("Already fetching playlist info, please wait...")
            return

        # Get URL
        url = self.url_input.text().strip()

        # Validate URL
        is_valid, error = Validators.is_valid_url(url)
        if not is_valid:
            QMessageBox.warning(self, tr("error_invalid_url"), error)
            self.log_widget.append_error(f"{tr('error_invalid_url')}: {error}")
            return

        # Check if URL is a playlist
        is_playlist, platform = PlaylistDetector.is_playlist_url(url)

        if is_playlist:
            # Handle as playlist
            self._fetch_playlist_info(url, platform)
        else:
            # Handle as single video
            self._fetch_video_info(url)

    def _fetch_video_info(self, url: str) -> None:
        """
        Fetch video info for a single video URL.

        Args:
            url: Video URL
        """
        # Disable button while fetching
        self.show_info_button.setEnabled(False)
        self.show_info_button.setText(tr("button_fetching"))

        self.log_widget.append_info(f"Fetching video info: {url}")

        # Create and start worker
        self.info_worker = VideoInfoWorker(url)
        self.info_worker.info_fetched.connect(self._on_info_fetched)
        self.info_worker.fetch_failed.connect(self._on_info_fetch_failed)
        self.info_worker.finished.connect(self._on_info_worker_finished)
        self.info_worker.start()

    def _fetch_playlist_info(self, url: str, platform: str) -> None:
        """
        Fetch playlist info for a playlist URL.

        Args:
            url: Playlist URL
            platform: Platform type (e.g., 'youtube', 'vimeo')
        """
        # Disable button while fetching
        self.show_info_button.setEnabled(False)
        self.show_info_button.setText(tr("button_fetching_playlist"))

        self.log_widget.append_info(f"Detected {platform} playlist, fetching info...")

        # Create and start worker
        self.playlist_worker = PlaylistWorker(url)
        self.playlist_worker.playlist_fetched.connect(self._on_playlist_fetched)
        self.playlist_worker.fetch_failed.connect(self._on_playlist_fetch_failed)
        self.playlist_worker.finished.connect(self._on_playlist_worker_finished)
        self.playlist_worker.start()

    def _on_info_fetched(self, video_info) -> None:
        """
        Handle video info fetched successfully.

        Args:
            video_info: VideoInfo object
        """
        logger.info(f"Video info received: {video_info.title}")
        self.log_widget.append_success(f"Video info fetched: {video_info.title}")

        # Show dialog
        dialog = VideoInfoDialog(video_info, self)
        dialog.exec()

    def _on_info_fetch_failed(self, error_message: str) -> None:
        """
        Handle video info fetch failure.

        Args:
            error_message: Error description
        """
        logger.error(f"Info fetch failed: {error_message}")
        self.log_widget.append_error(f"Failed to fetch video info: {error_message}")

        # Get better error info
        error_html = ErrorHandler.format_error_dialog_text(error_message)

        # Show detailed error dialog
        error_dialog = QMessageBox(self)
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setWindowTitle(tr("dialog_failed_fetch_video_info"))
        error_dialog.setTextFormat(Qt.RichText)
        error_dialog.setText(error_html)
        error_dialog.setStandardButtons(QMessageBox.Ok)
        error_dialog.exec()

    def _on_info_worker_finished(self) -> None:
        """Handle info worker finished (cleanup)."""
        # Re-enable button
        self.show_info_button.setEnabled(True)
        self.show_info_button.setText(tr("button_show_info"))
        logger.debug("Info worker finished")

    def _on_playlist_fetched(self, playlist_info) -> None:
        """
        Handle playlist info fetched successfully.

        Args:
            playlist_info: PlaylistInfo object
        """
        logger.info(f"Playlist info received: {playlist_info.title} ({playlist_info.video_count} videos)")
        self.log_widget.append_success(f"Playlist fetched: {playlist_info.title} ({playlist_info.video_count} videos)")

        # Show playlist dialog
        dialog = PlaylistDialog(playlist_info, self)
        dialog.videos_selected.connect(self._on_playlist_videos_selected)
        dialog.exec()

    def _on_playlist_fetch_failed(self, error_message: str) -> None:
        """
        Handle playlist info fetch failure.

        Args:
            error_message: Error description
        """
        logger.error(f"Playlist fetch failed: {error_message}")
        self.log_widget.append_error(f"Failed to fetch playlist info: {error_message}")

        # Get better error info
        error_html = ErrorHandler.format_error_dialog_text(error_message)

        # Show detailed error dialog
        error_dialog = QMessageBox(self)
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setWindowTitle(tr("dialog_failed_fetch_playlist_info"))
        error_dialog.setTextFormat(Qt.RichText)
        error_dialog.setText(error_html)
        error_dialog.setStandardButtons(QMessageBox.Ok)
        error_dialog.exec()

    def _on_playlist_worker_finished(self) -> None:
        """Handle playlist worker finished (cleanup)."""
        # Re-enable button
        self.show_info_button.setEnabled(True)
        self.show_info_button.setText(tr("button_show_info"))
        logger.debug("Playlist worker finished")

    def _on_playlist_videos_selected(self, video_urls: list, quality: str) -> None:
        """
        Handle selected videos from playlist dialog.

        Args:
            video_urls: List of selected video URLs
            quality: Selected quality
        """
        if not video_urls:
            self.log_widget.append_warning("No videos selected from playlist")
            return

        output_dir = self.output_input.text().strip()

        # Validate directory
        is_valid, error = Validators.is_valid_directory(output_dir)
        if not is_valid:
            QMessageBox.warning(self, tr("error_invalid_directory"), error)
            self.log_widget.append_error(f"{tr('error_invalid_directory')}: {error}")
            return

        # Add each video to queue with v1.7.0 options
        added_count = 0
        audio_only = quality == tr("quality_audio_only")  # playlist dialog uses translated "Audio Only"
        for url in video_urls:
            task = DownloadTask(
                url=url,
                output_directory=output_dir,
                quality=quality,
                audio_only=audio_only,
                download_thumbnail=self.thumbnail_checkbox.isChecked(),
                download_subtitles=self.subtitles_checkbox.isChecked(),
                subtitle_languages=self.subtitle_langs_input.text().strip() or "en",
                speed_limit=self.speed_limit_spinbox.value(),
                video_container=VIDEO_CONTAINER_FORMATS.get(self.container_combo.currentText()),
                audio_format=AUDIO_FORMATS.get(self.audio_format_combo.currentText(), "mp3"),
                selected_subtitles=self.selected_subtitle_codes,  # v2.0.0
                download_metadata=self.metadata_checkbox.isChecked(),  # v2.1.0
                download_comments=self.comments_checkbox.isChecked(),  # v2.0.0
                auto_number_duplicates=True,  # v2.1.0 - always enabled
            )
            self.queue_manager.add_task(task)
            added_count += 1

        self.log_widget.append_success(f"Added {added_count} videos to queue")

        # Clear URL input
        self.url_input.clear()

        # Show success message
        QMessageBox.information(
            self, tr("dialog_playlist_added_to_queue"), tr("msg_playlist_added_to_queue", count=added_count)
        )

    def _on_subtitles_toggled(self, state: int) -> None:
        """
        Handle subtitles checkbox toggle.

        Args:
            state: Checkbox state
        """
        enabled = bool(state)
        self.subtitle_langs_label.setEnabled(enabled)
        self.subtitle_langs_input.setEnabled(enabled)
        self.select_subs_button.setEnabled(enabled)  # v2.0.0: Enable/disable button

    def _on_select_subtitles_clicked(self) -> None:
        """Handle Select Subtitles button click (v2.0.0)."""
        url = self.url_input.text().strip()

        # Validate URL
        is_valid, error = Validators.is_valid_url(url)
        if not is_valid:
            QMessageBox.warning(self, tr("error_invalid_url"), error)
            self.log_widget.append_error(f"{tr('error_invalid_url')}: {error}")
            return

        # Disable button and show fetching state
        self.select_subs_button.setEnabled(False)
        self.select_subs_button.setText("Fetching...")
        self.log_widget.append_info(f"Fetching available subtitles for: {url}")

        try:
            # Fetch available subtitles
            wrapper = YtDlpWrapper()
            available_subs = wrapper.get_available_subtitles(url)

            if not available_subs:
                QMessageBox.information(
                    self, "No Subtitles Available", "This video doesn't have any subtitles available."
                )
                self.log_widget.append_warning("No subtitles found for this video")
            else:
                # Show subtitle selection dialog
                dialog = SubtitleSelectionDialog(available_subs, self)
                if dialog.exec():
                    selected = dialog.get_selected_languages()
                    self.selected_subtitle_codes = selected

                    if selected:
                        # Update the subtitle languages input
                        self.subtitle_langs_input.setText(",".join(selected))
                        self.log_widget.append_success(
                            f"Selected {len(selected)} subtitle languages: {', '.join(selected)}"
                        )
                    else:
                        self.subtitle_langs_input.setText("")
                        self.log_widget.append_info("No subtitles selected")

        except Exception as e:
            logger.error(f"Failed to fetch subtitles: {e}")
            QMessageBox.critical(self, "Error", f"Failed to fetch subtitles:\n{str(e)}")
            self.log_widget.append_error(f"Error fetching subtitles: {e}")

        finally:
            # Re-enable button
            self.select_subs_button.setEnabled(True)
            self.select_subs_button.setText("Select Subs")

    def _on_batch_input_clicked(self) -> None:
        """Handle batch input button click (v1.7.0)."""
        from .batch_input_dialog import BatchInputDialog

        dialog = BatchInputDialog(self)
        if dialog.exec():
            urls = dialog.get_urls()

            if not urls:
                return

            output_dir = self.output_input.text().strip()
            quality = self.quality_combo.currentText()

            # Validate directory
            is_valid, error = Validators.is_valid_directory(output_dir)
            if not is_valid:
                QMessageBox.warning(self, tr("error_invalid_directory"), error)
                self.log_widget.append_error(f"{tr('error_invalid_directory')}: {error}")
                return

            # Add each URL to queue with current settings
            added_count = 0
            audio_only = self.download_type_combo.currentText() == "Audio Only"
            for url in urls:
                task = DownloadTask(
                    url=url,
                    output_directory=output_dir,
                    quality=quality,
                    audio_only=audio_only,
                    download_thumbnail=self.thumbnail_checkbox.isChecked(),
                    download_subtitles=self.subtitles_checkbox.isChecked(),
                    subtitle_languages=self.subtitle_langs_input.text().strip() or "en",
                    speed_limit=self.speed_limit_spinbox.value(),
                    video_container=VIDEO_CONTAINER_FORMATS.get(self.container_combo.currentText()),
                    audio_format=AUDIO_FORMATS.get(self.audio_format_combo.currentText(), "mp3"),
                    selected_subtitles=self.selected_subtitle_codes,  # v2.0.0
                    download_metadata=self.metadata_checkbox.isChecked(),  # v2.1.0
                    download_comments=self.comments_checkbox.isChecked(),  # v2.0.0
                    auto_number_duplicates=True,  # v2.1.0 - always enabled
                )
                self.queue_manager.add_task(task)
                added_count += 1

            self.log_widget.append_success(f"Batch: Added {added_count} URLs to queue")

            # Show success message
            QMessageBox.information(self, tr("dialog_batch_added"), tr("msg_batch_added_to_queue", count=added_count))

    def _drag_enter_event(self, event) -> None:
        """
        Handle drag enter event for URL input.

        Args:
            event: Drag enter event
        """
        if event.mimeData().hasText():
            event.acceptProposedAction()
            logger.debug("Drag enter accepted: text/URL detected")
        else:
            event.ignore()

    def _drop_event(self, event) -> None:
        """
        Handle drop event for URL input.

        Args:
            event: Drop event
        """
        if event.mimeData().hasText():
            text = event.mimeData().text().strip()
            self.url_input.setText(text)
            self.url_input.setFocus()
            self.log_widget.append_info(f"URL dropped: {text[:50]}...")
            logger.info(f"URL dropped into input field: {text}")
            event.acceptProposedAction()
        else:
            event.ignore()
