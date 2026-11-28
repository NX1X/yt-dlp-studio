"""
Video information preview dialog.

This module provides a dialog to display video metadata including
thumbnail, title, duration, uploader, and other information.
"""

import urllib.request

from PySide6.QtCore import QMetaMethod, QSize, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from ..models.video_info import VideoInfo
from ..utils.logger import get_logger
from ..utils.translations import tr
from .bidi import ltr

logger = get_logger()

# Thumbnail size in the dialog (16:9)
THUMBNAIL_SIZE = QSize(320, 180)

# Site names that str.capitalize() gets wrong
_PLATFORM_NAMES = {"youtube": "YouTube", "tiktok": "TikTok", "soundcloud": "SoundCloud", "twitter": "X (Twitter)"}


def platform_name(extractor: str) -> str:
    """Return a display name for a yt-dlp extractor key ("youtube:tab" -> "YouTube")."""
    key = (extractor or "").split(":")[0].strip()
    return _PLATFORM_NAMES.get(key.lower(), key.capitalize())


class VideoInfoDialog(QDialog):
    """
    Dialog to display video information.

    Shows video metadata in a nice formatted dialog with thumbnail,
    title, duration, uploader, views, upload date, and description.

    Signals:
        download_requested: The user clicked Download. The button shows only
            when something is connected to this signal.
    """

    download_requested = Signal()

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
        self.setMinimumSize(QSize(640, 420))

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        title_label = QLabel(self.video_info.title)
        title_label.setWordWrap(True)
        title_label.setProperty("labelStyle", "title")
        title_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        main_layout.addWidget(title_label)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(12)

        # Thumbnail
        thumbnail_group = QGroupBox(tr("group_thumbnail"))
        thumbnail_layout = QVBoxLayout(thumbnail_group)
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setFixedSize(THUMBNAIL_SIZE)
        self.thumbnail_label.setProperty("labelStyle", "secondary")
        self.thumbnail_label.setText(tr("text_loading_thumbnail"))
        thumbnail_layout.addWidget(self.thumbnail_label, 0, Qt.AlignCenter)
        content_layout.addWidget(thumbnail_group, 0)

        # Details
        info_group = QGroupBox(tr("group_details"))
        form = QFormLayout(info_group)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        rows: list[tuple[str, str]] = [
            ("label_channel", self.video_info.uploader or tr("text_unknown")),
            ("label_duration", ltr(self.video_info.get_duration_formatted())),
        ]
        if self.video_info.upload_date:
            rows.append(("label_uploaded", ltr(self._format_upload_date(self.video_info.upload_date))))
        if self.video_info.view_count > 0:
            rows.append(("label_views", ltr(f"{self.video_info.view_count:,}")))
        if self.video_info.like_count > 0:
            rows.append(("label_likes", ltr(f"{self.video_info.like_count:,}")))
        if self.video_info.extractor:
            rows.append(("label_platform", platform_name(self.video_info.extractor)))

        rtl = QApplication.layoutDirection() == Qt.LayoutDirection.RightToLeft
        start_side = (Qt.AlignRight | Qt.AlignAbsolute) if rtl else Qt.AlignLeft
        for key, value in rows:
            name = QLabel(tr(key))
            name.setProperty("labelStyle", "secondary")
            value_label = QLabel(value)
            # Start side of the UI, also for English values in the Hebrew UI
            # (Qt would align English text to the left there).
            value_label.setAlignment(start_side | Qt.AlignVCenter)
            value_label.setWordWrap(True)
            value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            form.addRow(name, value_label)
        content_layout.addWidget(info_group, 1)

        main_layout.addLayout(content_layout)

        # Description
        if self.video_info.description:
            desc_group = QGroupBox(tr("group_description"))
            desc_layout = QVBoxLayout(desc_group)
            self.description_view = QTextBrowser()
            self.description_view.setOpenLinks(False)
            self.description_view.setPlainText(self._get_truncated_description())
            self.description_view.setMinimumHeight(90)
            self.description_view.setFocusPolicy(Qt.ClickFocus)
            desc_layout.addWidget(self.description_view)
            main_layout.addWidget(desc_group, 1)
        else:
            main_layout.addStretch(1)

        # Buttons: Close, and Download when the caller handles it
        self.button_box = QDialogButtonBox()
        self.close_button = self.button_box.addButton(tr("button_close"), QDialogButtonBox.ButtonRole.RejectRole)
        self.download_button = QPushButton(tr("button_video_info_download"))
        self.download_button.setProperty("buttonStyle", "primary")
        self.button_box.addButton(self.download_button, QDialogButtonBox.ButtonRole.AcceptRole)
        self.download_button.setVisible(False)
        self.button_box.rejected.connect(self.reject)
        self.button_box.accepted.connect(self._on_download)
        main_layout.addWidget(self.button_box)

    def showEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Show the Download button only if a caller listens for it."""
        connected = self.isSignalConnected(QMetaMethod.fromSignal(self.download_requested))
        self.download_button.setVisible(connected)
        if connected:
            self.download_button.setDefault(True)
        super().showEvent(event)

    def _on_download(self) -> None:
        self.download_requested.emit()
        self.accept()

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
        except Exception:
            return date_str

    def _get_truncated_description(self, max_length: int = 2000) -> str:
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

            pixmap = QPixmap()
            pixmap.loadFromData(image_data)

            if pixmap.isNull():
                self.thumbnail_label.setText(tr("text_failed_load_thumbnail"))
                logger.error("Failed to load thumbnail image")
                return

            self.set_thumbnail(pixmap)
            logger.info("Thumbnail loaded successfully")

        except Exception:
            self.thumbnail_label.setText(tr("text_failed_load_thumbnail"))
            logger.exception("Error loading thumbnail")

    def set_thumbnail(self, pixmap: QPixmap) -> None:
        """Show ``pixmap`` scaled to fit the thumbnail area, keeping its aspect ratio."""
        self.thumbnail_label.setPixmap(pixmap.scaled(THUMBNAIL_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation))
