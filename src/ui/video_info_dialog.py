"""
Video information preview dialog.

This module provides a dialog to display video metadata including
thumbnail, title, duration, uploader, and other information.
"""

import urllib.request

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QGroupBox, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from ..models.video_info import VideoInfo
from ..utils.logger import get_logger
from ..utils.translations import tr

logger = get_logger()


class VideoInfoDialog(QDialog):
    """
    Dialog to display video information.

    Shows video metadata in a nice formatted dialog with thumbnail,
    title, duration, uploader, views, upload date, and description.
    """

    def __init__(self, video_info: VideoInfo, parent=None):
        """
        Initialize video info dialog.

        Args:
            video_info: VideoInfo object with video metadata
            parent: Parent widget
        """
        super().__init__(parent)
        self.video_info = video_info
        self._setup_ui()
        self._load_thumbnail()
        logger.debug(f"VideoInfoDialog created for: {video_info.title}")

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle(tr("dialog_video_information"))
        self.setMinimumSize(QSize(600, 500))
        self.setMaximumSize(QSize(800, 700))

        main_layout = QVBoxLayout(self)

        # Title section
        title_label = QLabel(self.video_info.title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #ffffff;
                padding: 10px;
                background-color: #2d2d2d;
                border-radius: 5px;
            }
        """)
        main_layout.addWidget(title_label)

        # Content layout (thumbnail + info)
        content_layout = QHBoxLayout()

        # Thumbnail section
        thumbnail_group = QGroupBox(tr("group_thumbnail"))
        thumbnail_layout = QVBoxLayout()
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setMinimumSize(QSize(320, 180))
        self.thumbnail_label.setMaximumSize(QSize(480, 270))
        self.thumbnail_label.setScaledContents(False)
        self.thumbnail_label.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                border: 2px solid #3e3e3e;
                border-radius: 5px;
            }
        """)
        self.thumbnail_label.setText(tr("text_loading_thumbnail"))
        thumbnail_layout.addWidget(self.thumbnail_label)
        thumbnail_group.setLayout(thumbnail_layout)
        content_layout.addWidget(thumbnail_group)

        # Info section
        info_group = QGroupBox(tr("group_details"))
        info_layout = QVBoxLayout()

        # Uploader
        uploader_layout = QHBoxLayout()
        uploader_layout.addWidget(self._create_label_bold(tr("label_channel")))
        uploader_layout.addWidget(self._create_label_value(self.video_info.uploader or "Unknown"))
        uploader_layout.addStretch()
        info_layout.addLayout(uploader_layout)

        # Duration
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(self._create_label_bold(tr("label_duration")))
        duration_layout.addWidget(self._create_label_value(self.video_info.get_duration_formatted()))
        duration_layout.addStretch()
        info_layout.addLayout(duration_layout)

        # Upload date
        if self.video_info.upload_date:
            upload_date_formatted = self._format_upload_date(self.video_info.upload_date)
            upload_layout = QHBoxLayout()
            upload_layout.addWidget(self._create_label_bold(tr("label_uploaded")))
            upload_layout.addWidget(self._create_label_value(upload_date_formatted))
            upload_layout.addStretch()
            info_layout.addLayout(upload_layout)

        # View count
        if self.video_info.view_count > 0:
            views_layout = QHBoxLayout()
            views_layout.addWidget(self._create_label_bold(tr("label_views")))
            views_layout.addWidget(self._create_label_value(f"{self.video_info.view_count:,}"))
            views_layout.addStretch()
            info_layout.addLayout(views_layout)

        # Like count
        if self.video_info.like_count > 0:
            likes_layout = QHBoxLayout()
            likes_layout.addWidget(self._create_label_bold(tr("label_likes")))
            likes_layout.addWidget(self._create_label_value(f"{self.video_info.like_count:,}"))
            likes_layout.addStretch()
            info_layout.addLayout(likes_layout)

        # Extractor/Platform
        if self.video_info.extractor:
            platform_layout = QHBoxLayout()
            platform_layout.addWidget(self._create_label_bold(tr("label_platform")))
            platform_layout.addWidget(self._create_label_value(self.video_info.extractor.capitalize()))
            platform_layout.addStretch()
            info_layout.addLayout(platform_layout)

        info_layout.addStretch()
        info_group.setLayout(info_layout)
        content_layout.addWidget(info_group)

        main_layout.addLayout(content_layout)

        # Description section
        if self.video_info.description:
            desc_group = QGroupBox(tr("group_description"))
            desc_layout = QVBoxLayout()

            # Create scrollable description
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setMaximumHeight(150)

            desc_widget = QWidget()
            desc_widget_layout = QVBoxLayout(desc_widget)

            desc_label = QLabel(self._get_truncated_description())
            desc_label.setWordWrap(True)
            desc_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            desc_label.setStyleSheet("""
                QLabel {
                    color: #cccccc;
                    padding: 5px;
                }
            """)
            desc_widget_layout.addWidget(desc_label)
            desc_widget_layout.addStretch()

            scroll_area.setWidget(desc_widget)
            desc_layout.addWidget(scroll_area)
            desc_group.setLayout(desc_layout)
            main_layout.addWidget(desc_group)

        # Button section
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_button = QPushButton(tr("button_close"))
        close_button.setMinimumWidth(100)
        close_button.clicked.connect(self.accept)
        close_button.setStyleSheet("""
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
        button_layout.addWidget(close_button)

        main_layout.addLayout(button_layout)

    def _create_label_bold(self, text: str) -> QLabel:
        """
        Create a bold label for field names.

        Args:
            text: Label text

        Returns:
            QLabel with bold styling
        """
        label = QLabel(text)
        label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: #4ec9b0;
                min-width: 80px;
            }
        """)
        return label

    def _create_label_value(self, text: str) -> QLabel:
        """
        Create a label for field values.

        Args:
            text: Label text

        Returns:
            QLabel with value styling
        """
        label = QLabel(text)
        label.setStyleSheet("""
            QLabel {
                color: #ffffff;
            }
        """)
        return label

    def _format_upload_date(self, date_str: str) -> str:
        """
        Format upload date from YYYYMMDD to readable format.

        Args:
            date_str: Date string in YYYYMMDD format

        Returns:
            Formatted date string
        """
        if len(date_str) != 8:
            return date_str

        try:
            year = date_str[0:4]
            month = date_str[4:6]
            day = date_str[6:8]
            return f"{day}/{month}/{year}"
        except:
            return date_str

    def _get_truncated_description(self, max_length: int = 500) -> str:
        """
        Get truncated description.

        Args:
            max_length: Maximum description length

        Returns:
            Truncated description
        """
        desc = self.video_info.description
        if len(desc) <= max_length:
            return desc
        return desc[:max_length] + "..."

    def _load_thumbnail(self) -> None:
        """Load and display video thumbnail."""
        if not self.video_info.thumbnail:
            self.thumbnail_label.setText(tr("text_no_thumbnail_available"))
            logger.debug("No thumbnail URL available")
            return

        try:
            # Only fetch over http(s); reject file:/ftp:/custom schemes that
            # could turn an attacker-influenced "thumbnail" field into a local
            # file read or SSRF-style request.
            thumbnail_url = self.video_info.thumbnail
            if not thumbnail_url.lower().startswith(("http://", "https://")):
                logger.warning(f"Refusing non-HTTP thumbnail URL: {thumbnail_url!r}")
                self.thumbnail_label.setText(tr("text_no_thumbnail_available"))
                return

            # Download thumbnail (scheme validated above; noqa acknowledges S310).
            logger.debug(f"Downloading thumbnail: {thumbnail_url}")
            with urllib.request.urlopen(thumbnail_url, timeout=10) as response:  # noqa: S310
                image_data = response.read()

            # Load into pixmap
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)

            if pixmap.isNull():
                self.thumbnail_label.setText(tr("text_failed_load_thumbnail"))
                logger.error("Failed to load thumbnail image")
                return

            # Scale to fit label while maintaining aspect ratio
            scaled_pixmap = pixmap.scaled(self.thumbnail_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)

            self.thumbnail_label.setPixmap(scaled_pixmap)
            logger.info("Thumbnail loaded successfully")

        except Exception as e:
            self.thumbnail_label.setText(tr("text_failed_load_thumbnail"))
            logger.error(f"Error loading thumbnail: {e}")
