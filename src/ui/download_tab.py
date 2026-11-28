"""
Download tab UI for YT-DLP Studio.

One form for a link: the link field (Paste, Info, site tier, inline
errors), one row for Get / Quality / Format, the folder, a folded "More
options" section and the buttons. Below it, the "Now downloading" panel
shows the running downloads, and a folded activity log.

"Download" and "Add to queue" use the same code path (``submit``) with the
same playlist and duplicate checks. The only difference:

- Download (``start_now=True``) starts the download at once, also while
  the queue is paused. If every download slot is in use, it starts next.
- Add to queue (``start_now=False``) puts the download at the end of the
  queue. It waits its turn and does not start while the queue is paused.

The browser cookies, proxy, file name template and format options are in
the Settings tab; this tab only links there.
"""

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QKeySequence, QPainter, QPainterPath, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..backend.config_manager import ConfigManager
from ..backend.format_handler import FormatHandler
from ..backend.playlist_worker import PlaylistWorker
from ..backend.queue_manager import QueueManager
from ..backend.subtitle_list_worker import SubtitleListWorker
from ..backend.video_info_worker import VideoInfoWorker
from ..models.download_task import DownloadTask
from ..utils.constants import AUDIO_FORMATS, DEFAULT_AUDIO_FORMAT, DEFAULT_VIDEO_CONTAINER, VIDEO_CONTAINER_FORMATS
from ..utils.logger import get_logger
from ..utils.playlist_detector import PlaylistDetector
from ..utils.site_tiers import SiteTier
from ..utils.translations import tr
from ..utils.validators import Validators
from .collapsible_section import CollapsibleSection
from .display_format import ltr, open_local_path, theme_colors
from .error_dialog import show_download_error
from .log_widget import LogWidget
from .now_downloading import NowDownloadingPanel
from .playlist_dialog import PlaylistDialog
from .site_tier_label import SiteTierLabel
from .status_messages import show_status
from .subtitle_selection_dialog import SubtitleSelectionDialog
from .video_info_dialog import VideoInfoDialog

logger = get_logger()

# Answers of the "playlist detected" question
PLAYLIST_CHOOSE = "choose"
PLAYLIST_WHOLE = "whole"
PLAYLIST_CANCEL = "cancel"

# Platform names as people write them (the detector returns lower case)
_PLATFORM_NAMES = {"youtube": "YouTube", "vimeo": "Vimeo", "dailymotion": "Dailymotion", "soundcloud": "SoundCloud"}

_TIER_ICON_SIZE = 16


def _tier_pixmap(tier: SiteTier, device_ratio: float = 1.0) -> QPixmap:
    """
    Small icon for the site tier, so the tier never depends on color alone.

    Tested: a check mark in a circle. Experimental: an exclamation mark in a
    triangle. Colors come from the active theme.
    """
    size = _TIER_ICON_SIZE
    pixmap = QPixmap(int(size * device_ratio), int(size * device_ratio))
    pixmap.setDevicePixelRatio(device_ratio)
    pixmap.fill(Qt.transparent)
    colors = theme_colors()
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    if tier == SiteTier.TESTED:
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(colors["success"]))
        painter.drawEllipse(QRectF(1, 1, size - 2, size - 2))
        pen = QPen(QColor(colors["bg_primary"]), 2.0)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        path = QPainterPath(QPointF(4.5, 8.5))
        path.lineTo(7.0, 11.0)
        path.lineTo(11.5, 5.5)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)
    else:
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(colors["warning"]))
        triangle = QPainterPath(QPointF(size / 2, 1.0))
        triangle.lineTo(size - 1.0, size - 2.0)
        triangle.lineTo(1.0, size - 2.0)
        triangle.closeSubpath()
        painter.drawPath(triangle)
        pen = QPen(QColor("#1e1e1e"), 2.0)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawLine(QPointF(size / 2, 5.5), QPointF(size / 2, 9.5))
        painter.drawPoint(QPointF(size / 2, 12.0))
    painter.end()
    return pixmap


class DownloadTab(QWidget):
    """
    Download tab widget.

    Signals:
        open_queue_requested: the user wants to see the Queue tab
        open_settings_requested: the user wants the advanced options (Settings tab)
    """

    open_queue_requested = Signal()
    open_settings_requested = Signal()

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
        self.info_worker: VideoInfoWorker | None = None
        self.playlist_worker: PlaylistWorker | None = None
        self.subtitle_list_worker: SubtitleListWorker | None = None
        self.selected_subtitle_codes: list = []  # v2.0.0: Store selected subtitle language codes
        # Stable boolean tracked alongside the (translated) Download Type
        # combo. Always update via _on_download_type_changed; consult here
        # instead of comparing currentText() against an English literal.
        self._is_audio_mode: bool = False
        # How the videos picked in the playlist dialog are added: True when
        # the dialog was opened from "Download", False for "Add to queue"
        # and for "Info".
        self._playlist_start_now: bool = False
        self._setup_ui()
        self._setup_shortcuts()
        self._connect_queue_signals()
        self._load_config()
        logger.info("DownloadTab initialized")

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # The content scrolls when the window is too small for it, so no row
        # is ever squeezed.
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("downloadScroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("downloadScrollContent")
        main_layout = QVBoxLayout(content)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(12)
        self.scroll_area.setWidget(content)
        outer.addWidget(self.scroll_area)

        main_layout.addWidget(self._build_form())

        self.now_panel = NowDownloadingPanel(self.queue_manager)
        self.now_panel.open_queue_requested.connect(self.open_queue_requested.emit)
        main_layout.addWidget(self.now_panel)

        main_layout.addWidget(self._build_log_section())
        main_layout.addStretch(1)

    def _build_form(self) -> QGroupBox:
        """The link form: link, options, folder, more options and buttons."""
        group = QGroupBox(tr("tab_download"))
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(1, 1)
        label_align = Qt.AlignLeading | Qt.AlignVCenter

        # Row 0: link
        link_label = QLabel(tr("label_link"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(tr("placeholder_link"))
        self.url_input.setAccessibleName(tr("label_link"))
        self.url_input.setClearButtonEnabled(True)
        self.url_input.returnPressed.connect(self._on_download_clicked)  # Enter key triggers download
        self.url_input.textChanged.connect(self._on_url_changed)
        link_label.setBuddy(self.url_input)

        # Enable drag and drop
        self.url_input.setAcceptDrops(True)
        self.url_input.dragEnterEvent = self._drag_enter_event
        self.url_input.dropEvent = self._drop_event

        self.paste_button = QPushButton(tr("button_paste"))
        self.paste_button.setProperty("buttonStyle", "secondary")
        self.paste_button.setToolTip(tr("tooltip_paste"))
        self.paste_button.clicked.connect(self._paste_from_clipboard)

        self.show_info_button = QPushButton(tr("button_info"))
        self.show_info_button.setProperty("buttonStyle", "secondary")
        self.show_info_button.setToolTip(tr("tooltip_info"))
        self.show_info_button.clicked.connect(self._on_show_info_clicked)

        grid.addWidget(link_label, 0, 0, label_align)
        grid.addWidget(self.url_input, 0, 1)
        grid.addWidget(self.paste_button, 0, 2)
        grid.addWidget(self.show_info_button, 0, 3)

        # Row 1: site tier ("Tested site" / "Experimental site"), icon plus text
        self.site_tier_icon = QLabel()
        self.site_tier_icon.setFixedSize(_TIER_ICON_SIZE, _TIER_ICON_SIZE)
        self.site_tier_label = SiteTierLabel()
        self.site_tier_row = QWidget()
        self.site_tier_row.setObjectName("siteTierRow")
        tier_layout = QHBoxLayout(self.site_tier_row)
        tier_layout.setContentsMargins(0, 0, 0, 0)
        tier_layout.setSpacing(6)
        tier_layout.addWidget(self.site_tier_icon)
        tier_layout.addWidget(self.site_tier_label)
        tier_layout.addStretch(1)
        self.site_tier_row.setVisible(False)
        grid.addWidget(self.site_tier_row, 1, 1, 1, 3)

        # Row 2: inline error for the link
        self.url_error_label = QLabel()
        self.url_error_label.setObjectName("inlineError")
        self.url_error_label.setWordWrap(True)
        self.url_error_label.setVisible(False)
        grid.addWidget(self.url_error_label, 2, 1, 1, 3)

        # Row 3: Get / Quality / Format.
        # addItem(label, userData) keeps the translated label and the stable
        # key ("video" / "audio") apart; code reads currentData(), never
        # currentText(), so translating the labels cannot break audio mode.
        get_label = QLabel(tr("label_get"))
        self.download_type_combo = QComboBox()
        self.download_type_combo.addItem(tr("download_type_video"), "video")
        self.download_type_combo.addItem(tr("download_type_audio"), "audio")
        self.download_type_combo.setToolTip(tr("tooltip_download_type"))
        self.download_type_combo.setAccessibleName(tr("label_get"))
        get_label.setBuddy(self.download_type_combo)

        self.quality_label = QLabel(tr("label_quality_short"))
        self.quality_combo = QComboBox()
        self.quality_combo.setAccessibleName(tr("label_quality_short"))
        self.quality_combo.setMinimumContentsLength(10)
        self.quality_label.setBuddy(self.quality_combo)

        # Container and audio format names (MP4, MKV, MP3) stay English:
        # they are technical names people know in every language.
        self.format_label = QLabel(tr("label_format"))
        self.container_combo = QComboBox()
        self.container_combo.addItems(list(VIDEO_CONTAINER_FORMATS.keys()))
        self.container_combo.setCurrentText(DEFAULT_VIDEO_CONTAINER)
        self.container_combo.setToolTip(tr("tooltip_video_format"))
        self.container_combo.setAccessibleName(tr("label_format"))
        self.audio_format_combo = QComboBox()
        self.audio_format_combo.addItems(list(AUDIO_FORMATS.keys()))
        self.audio_format_combo.setCurrentText(DEFAULT_AUDIO_FORMAT)
        self.audio_format_combo.setToolTip(tr("tooltip_audio_format"))
        self.audio_format_combo.setAccessibleName(tr("label_format"))
        self.format_label.setBuddy(self.container_combo)
        # Old names, kept for code that still refers to them
        self.container_label = self.format_label
        self.audio_format_label = self.format_label

        options_row = QHBoxLayout()
        options_row.setSpacing(8)
        options_row.addWidget(self.download_type_combo)
        options_row.addSpacing(8)
        options_row.addWidget(self.quality_label)
        options_row.addWidget(self.quality_combo)
        options_row.addSpacing(8)
        options_row.addWidget(self.format_label)
        options_row.addWidget(self.container_combo)
        options_row.addWidget(self.audio_format_combo)
        options_row.addStretch(1)
        grid.addWidget(get_label, 3, 0, label_align)
        grid.addLayout(options_row, 3, 1, 1, 3)

        self.quality_combo.currentIndexChanged.connect(self._on_quality_changed)
        self.download_type_combo.currentIndexChanged.connect(self._on_download_type_changed)
        self._update_quality_options()

        # Row 4: folder
        save_label = QLabel(tr("label_save_to_short"))
        self.output_input = QLineEdit()
        self.output_input.setReadOnly(True)
        self.output_input.setFocusPolicy(Qt.ClickFocus)  # read-only: no Tab stop
        self.output_input.setAccessibleName(tr("label_save_to_short"))
        save_label.setBuddy(self.output_input)
        self.browse_button = QPushButton(tr("button_browse"))
        self.browse_button.setProperty("buttonStyle", "secondary")
        self.browse_button.clicked.connect(self._browse_directory)
        self.open_dir_button = QPushButton(tr("action_open_folder"))
        self.open_dir_button.setProperty("buttonStyle", "secondary")
        self.open_dir_button.setToolTip(tr("tooltip_open_dir"))
        self.open_dir_button.clicked.connect(self._open_directory)
        grid.addWidget(save_label, 4, 0, label_align)
        grid.addWidget(self.output_input, 4, 1)
        grid.addWidget(self.browse_button, 4, 2)
        grid.addWidget(self.open_dir_button, 4, 3)

        # Row 5: inline error for the folder
        self.folder_error_label = QLabel()
        self.folder_error_label.setObjectName("inlineError")
        self.folder_error_label.setWordWrap(True)
        self.folder_error_label.setVisible(False)
        grid.addWidget(self.folder_error_label, 5, 1, 1, 3)

        # Row 6: more options (folded)
        self.more_section = CollapsibleSection(tr("section_more_options"))
        self.more_section.set_content_widget(self._build_more_options())
        grid.addWidget(self.more_section, 6, 0, 1, 4)
        self._update_more_summary()

        # Row 7: buttons. "Download" is the only primary button.
        self.batch_button = QPushButton(tr("button_batch_links"))
        self.batch_button.setProperty("buttonStyle", "secondary")
        self.batch_button.setToolTip(tr("tooltip_batch"))
        self.batch_button.clicked.connect(self._on_batch_input_clicked)

        self.add_to_queue_button = QPushButton(tr("button_add_to_queue_short"))
        self.add_to_queue_button.setProperty("buttonStyle", "secondary")
        self.add_to_queue_button.setToolTip(tr("tooltip_add_to_queue_button"))
        self.add_to_queue_button.clicked.connect(self._on_add_to_queue_clicked)

        self.download_button = QPushButton(tr("button_download"))
        self.download_button.setProperty("buttonStyle", "primary")
        self.download_button.setToolTip(tr("tooltip_download_button"))
        self.download_button.clicked.connect(self._on_download_clicked)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addWidget(self.batch_button)
        buttons.addStretch(1)
        buttons.addWidget(self.add_to_queue_button)
        buttons.addWidget(self.download_button)
        grid.addLayout(buttons, 7, 0, 1, 4)
        return group

    def _build_more_options(self) -> QWidget:
        """Subtitles, thumbnail, metadata, comments and speed limit."""
        widget = QWidget()
        widget.setObjectName("moreOptions")
        grid = QGridLayout(widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        # Subtitles
        self.subtitles_checkbox = QCheckBox(tr("checkbox_subtitles_short"))
        self.subtitles_checkbox.setToolTip(tr("tooltip_subtitles"))
        self.subtitles_checkbox.toggled.connect(self._on_subtitles_toggled)
        self.subtitle_langs_label = QLabel(tr("label_languages"))
        self.subtitle_langs_input = QLineEdit()
        self.subtitle_langs_input.setText("en")
        self.subtitle_langs_input.setPlaceholderText(tr("placeholder_subtitle_langs"))
        self.subtitle_langs_input.setMaximumWidth(160)
        self.subtitle_langs_input.setToolTip(tr("tooltip_subtitle_langs"))
        self.subtitle_langs_input.setAccessibleName(tr("label_languages"))
        self.subtitle_langs_label.setBuddy(self.subtitle_langs_input)
        self.select_subs_button = QPushButton(tr("button_choose_subs"))
        self.select_subs_button.setProperty("buttonStyle", "secondary")
        self.select_subs_button.setToolTip(tr("tooltip_select_subs"))
        self.select_subs_button.clicked.connect(self._on_select_subtitles_clicked)
        for widget_ in (self.subtitle_langs_label, self.subtitle_langs_input, self.select_subs_button):
            widget_.setEnabled(False)
        subs_row = QHBoxLayout()
        subs_row.setSpacing(8)
        subs_row.addWidget(self.subtitles_checkbox)
        subs_row.addSpacing(12)
        subs_row.addWidget(self.subtitle_langs_label)
        subs_row.addWidget(self.subtitle_langs_input)
        subs_row.addWidget(self.select_subs_button)
        subs_row.addStretch(1)
        grid.addLayout(subs_row, 0, 0, 1, 2)

        # Extra files
        self.thumbnail_checkbox = QCheckBox(tr("checkbox_thumbnail_short"))
        self.thumbnail_checkbox.setToolTip(tr("tooltip_thumbnail"))
        self.metadata_checkbox = QCheckBox(tr("checkbox_metadata_short"))
        self.metadata_checkbox.setToolTip(tr("tooltip_metadata"))
        self.comments_checkbox = QCheckBox(tr("checkbox_comments_short"))
        self.comments_checkbox.setToolTip(tr("tooltip_comments"))
        files_row = QHBoxLayout()
        files_row.setSpacing(16)
        files_row.addWidget(self.thumbnail_checkbox)
        files_row.addWidget(self.metadata_checkbox)
        files_row.addWidget(self.comments_checkbox)
        files_row.addStretch(1)
        grid.addLayout(files_row, 1, 0, 1, 2)

        # Speed limit
        speed_label = QLabel(tr("label_speed_limit_short"))
        self.speed_limit_spinbox = QSpinBox()
        self.speed_limit_spinbox.setRange(0, 100000)
        self.speed_limit_spinbox.setValue(0)
        self.speed_limit_spinbox.setSingleStep(100)
        self.speed_limit_spinbox.setSuffix(" KB/s")
        self.speed_limit_spinbox.setSpecialValueText(tr("text_unlimited"))
        self.speed_limit_spinbox.setMinimumWidth(150)
        self.speed_limit_spinbox.setToolTip(tr("tooltip_speed_limit"))
        self.speed_limit_spinbox.setAccessibleName(tr("label_speed_limit_short"))
        # Digits and "KB/s" are left-to-right text, also in Hebrew.
        self.speed_limit_spinbox.setLayoutDirection(Qt.LeftToRight)
        speed_label.setBuddy(self.speed_limit_spinbox)
        speed_row = QHBoxLayout()
        speed_row.setSpacing(8)
        speed_row.addWidget(speed_label)
        speed_row.addWidget(self.speed_limit_spinbox)
        speed_row.addStretch(1)
        grid.addLayout(speed_row, 2, 0, 1, 2)

        # The advanced options live in the Settings tab.
        advanced_note = QLabel(tr("text_advanced_in_settings"))
        advanced_note.setProperty("labelStyle", "secondary")
        advanced_note.setWordWrap(True)
        self.open_settings_button = QPushButton(tr("button_open_settings"))
        self.open_settings_button.setProperty("buttonStyle", "link")
        self.open_settings_button.setCursor(Qt.PointingHandCursor)
        self.open_settings_button.clicked.connect(self.open_settings_requested.emit)
        advanced_row = QHBoxLayout()
        advanced_row.setSpacing(4)
        advanced_row.addWidget(advanced_note, 1)
        advanced_row.addWidget(self.open_settings_button)
        grid.addLayout(advanced_row, 3, 0, 1, 2)

        for checkbox in (
            self.subtitles_checkbox,
            self.thumbnail_checkbox,
            self.metadata_checkbox,
            self.comments_checkbox,
        ):
            checkbox.toggled.connect(self._update_more_summary)
        self.subtitle_langs_input.textChanged.connect(self._update_more_summary)
        self.speed_limit_spinbox.valueChanged.connect(self._update_more_summary)
        return widget

    def _build_log_section(self) -> CollapsibleSection:
        """The activity log, folded away by default."""
        self.log_section = CollapsibleSection(tr("section_activity_log"))
        body = QWidget()
        body.setObjectName("activityLogBody")
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.log_widget = LogWidget()
        self.log_widget.setMinimumHeight(160)
        layout.addWidget(self.log_widget)
        clear_row = QHBoxLayout()
        clear_row.addStretch(1)
        self.clear_log_button = QPushButton(tr("button_clear_log"))
        self.clear_log_button.setProperty("buttonStyle", "secondary")
        self.clear_log_button.clicked.connect(self.log_widget.clear_log)
        clear_row.addWidget(self.clear_log_button)
        layout.addLayout(clear_row)
        self.log_section.set_content_widget(body)
        return self.log_section

    def _update_more_summary(self, *_args) -> None:
        """One line next to "More options" that says what is switched on."""
        parts = []
        if self.subtitles_checkbox.isChecked():
            langs = self.subtitle_langs_input.text().strip() or "en"
            parts.append(tr("summary_subtitles", langs=ltr(langs)))
        if self.thumbnail_checkbox.isChecked():
            parts.append(tr("checkbox_thumbnail_short"))
        if self.metadata_checkbox.isChecked():
            parts.append(tr("summary_metadata"))
        if self.comments_checkbox.isChecked():
            parts.append(tr("checkbox_comments_short"))
        limit = self.speed_limit_spinbox.value()
        if limit:
            parts.append(tr("summary_speed_limit", speed=ltr(f"{limit} KB/s")))
        self.more_section.set_summary(", ".join(parts) if parts else tr("more_options_default"))

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    def update_output_directory(self, new_directory: str) -> None:
        """Update output directory (v1.9.0 smart folder logic)."""
        self._set_output_text(new_directory)
        self._set_folder_error("")
        logger.info(f"Download tab output directory updated to: {new_directory}")

    def _set_output_text(self, directory: str) -> None:
        """Show the folder from its start; the tooltip has the full path."""
        self.output_input.setText(directory)
        self.output_input.setCursorPosition(0)
        self.output_input.setToolTip(directory)

    def set_url(self, url: str) -> None:
        """Put ``url`` into the link field (for example "Download again" in History)."""
        self.url_input.setText(url)
        self.url_input.setFocus()

    def _setup_shortcuts(self) -> None:
        """Set up keyboard shortcuts for the download tab."""
        # Ctrl+V - Paste from clipboard
        paste_shortcut = QShortcut(QKeySequence("Ctrl+V"), self)
        paste_shortcut.activated.connect(self._paste_from_clipboard)

        # Ctrl+D - Download
        download_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        download_shortcut.activated.connect(self._on_download_clicked)

        # Ctrl+Shift+Q - Add to queue
        queue_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Q"), self)
        queue_shortcut.activated.connect(self._on_add_to_queue_clicked)

        # Ctrl+Shift+I - Info
        info_shortcut = QShortcut(QKeySequence("Ctrl+Shift+I"), self)
        info_shortcut.activated.connect(self._on_show_info_clicked)

        logger.debug("Keyboard shortcuts configured for DownloadTab")

    def _connect_queue_signals(self) -> None:
        """Write queue events to the activity log (signals arrive on the GUI thread)."""
        self.queue_manager.task_started.connect(self._on_task_started)
        self.queue_manager.task_completed.connect(self._on_task_completed)
        self.queue_manager.task_failed.connect(self._on_task_failed)

    def _on_task_started(self, _index: int, title: str) -> None:
        self.log_widget.append_info(f"Started: {title}")

    def _on_task_completed(self, _index: int, filename: str) -> None:
        self.log_widget.append_success(f"Finished: {filename}")

    def _on_task_failed(self, _index: int, error: str) -> None:
        self.log_widget.append_error(f"Stopped: {error}")

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
        self._set_output_text(config.output_directory)
        self._select_quality(config.default_quality)
        self.url_input.setText(config.last_url)
        logger.debug("Config loaded into DownloadTab UI")

        # Auto-detect URL from clipboard on startup
        self._auto_detect_clipboard_url()

    def _select_quality(self, value: str) -> None:
        """Select a quality by its stable key, or by its label from older config files."""
        if not value:
            return
        index = self.quality_combo.findData(value)
        if index < 0:
            index = self.quality_combo.findText(value)
        if index >= 0:
            self.quality_combo.setCurrentIndex(index)

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

    # ------------------------------------------------------------------
    # Link field: site tier and inline errors
    # ------------------------------------------------------------------

    def _on_url_changed(self, text: str) -> None:
        """Update the site tier and clear an old error while the user types."""
        self._set_url_error("")
        self.site_tier_label.update_for_url(text)
        self._sync_site_tier_icon()

    def _sync_site_tier_icon(self) -> None:
        tier = self.site_tier_label.tier
        visible = tier in (SiteTier.TESTED, SiteTier.EXPERIMENTAL)
        if visible:
            self.site_tier_icon.setPixmap(_tier_pixmap(tier, self.devicePixelRatioF()))
        self.site_tier_row.setVisible(visible)

    def _set_url_error(self, text: str) -> None:
        """Show ``text`` under the link field, or hide the error line when empty."""
        self._set_inline_error(self.url_error_label, self.url_input, text)

    def _set_folder_error(self, text: str) -> None:
        """Show ``text`` under the folder field, or hide the error line when empty."""
        self._set_inline_error(self.folder_error_label, self.output_input, text)

    @staticmethod
    def _set_inline_error(label: QLabel, field: QLineEdit, text: str) -> None:
        label.setText(text)
        label.setVisible(bool(text))
        invalid = "true" if text else "false"
        if field.property("invalid") != invalid:
            field.setProperty("invalid", invalid)
            field.style().unpolish(field)
            field.style().polish(field)
        field.setAccessibleDescription(text)

    def _check_url(self, url: str) -> bool:
        """Validate the link; show an inline error when it is not valid."""
        is_valid, error = Validators.is_valid_url(url)
        if is_valid:
            self._set_url_error("")
            return True
        key = "error_link_empty" if not url else "error_link_invalid"
        self._set_url_error(tr(key, http=ltr("http://"), https=ltr("https://")))
        self.log_widget.append_error(f"{tr('error_invalid_url')}: {error}")
        self.url_input.setFocus()
        return False

    def _check_output_dir(self, output_dir: str) -> bool:
        """Validate the folder; show an inline error when it cannot be used."""
        is_valid, error = Validators.is_valid_directory(output_dir)
        if is_valid:
            self._set_folder_error("")
            return True
        self._set_folder_error(tr("error_folder_invalid"))
        self.log_widget.append_error(f"{tr('error_invalid_directory')}: {error}")
        return False

    # ------------------------------------------------------------------
    # Options
    # ------------------------------------------------------------------

    def _on_download_type_changed(self, *_args) -> None:
        """Handle download type change (Video or Audio Only)."""
        self._update_quality_options()
        logger.info(f"Download type changed to: {self.download_type_combo.currentData()}")

    def _update_quality_options(self) -> None:
        """
        Update the quality list and the format combo for the download type.

        Each combo entry stores its stable English key as userData so callers
        can look it up in QUALITY_OPTIONS / AUDIO_QUALITY_MAP via
        ``currentData()`` regardless of which UI language is active. Never
        check ``currentText()`` against a hardcoded string here.
        """
        self._is_audio_mode = self.download_type_combo.currentData() == "audio"

        self.quality_combo.blockSignals(True)
        self.quality_combo.clear()
        if self._is_audio_mode:
            qualities = [
                (tr("quality_best"), "Best Quality"),
                (tr("quality_audio_320"), "Audio 320kbps"),
                (tr("quality_audio_256"), "Audio 256kbps"),
                (tr("quality_audio_192"), "Audio 192kbps"),
                (tr("quality_audio_128"), "Audio 128kbps"),
            ]
        else:
            qualities = [
                (tr("quality_best"), "Best Quality"),
                ("8K (4320p)", "8K (4320p)"),
                ("4K (2160p)", "4K (2160p)"),
                ("2K (1440p)", "2K (1440p)"),
                (tr("quality_1080p"), "1080p (Full HD)"),
                (tr("quality_720p"), "720p (HD)"),
                (tr("quality_480p"), "480p (SD)"),
                ("360p", "360p"),
            ]
        for label, key in qualities:
            self.quality_combo.addItem(label, key)
        self.quality_combo.setCurrentIndex(0)  # Default to Best Quality
        self.quality_combo.blockSignals(False)

        self.container_combo.setVisible(not self._is_audio_mode)
        self.audio_format_combo.setVisible(self._is_audio_mode)
        self.format_label.setBuddy(self.audio_format_combo if self._is_audio_mode else self.container_combo)

        if hasattr(self, "log_widget"):
            mode = "Audio-only mode" if self._is_audio_mode else "Video mode"
            self.log_widget.append_info(f"{mode}: select quality and format")

    def _on_quality_changed(self, *_args) -> None:
        """Log the quality choice with a short description."""
        quality = self._current_quality()
        if hasattr(self, "log_widget") and quality:
            description = FormatHandler.get_quality_description(quality)
            self.log_widget.append_info(f"Quality selected: {quality} - {description}")

    def _current_quality(self) -> str:
        # currentData() is the stable English key, currentText() the
        # translated label; the queue needs the key.
        return self.quality_combo.currentData() or self.quality_combo.currentText()

    def _on_subtitles_toggled(self, checked) -> None:
        """Enable the language field and the Choose button with the checkbox."""
        enabled = bool(checked)
        self.subtitle_langs_label.setEnabled(enabled)
        self.subtitle_langs_input.setEnabled(enabled)
        self.select_subs_button.setEnabled(enabled)

    def _browse_directory(self) -> None:
        """Open directory browser dialog."""
        current_dir = self.output_input.text()
        directory = QFileDialog.getExistingDirectory(self, tr("dialog_select_download_dir"), current_dir)

        if directory:
            self._set_output_text(directory)
            self._set_folder_error("")
            self.config_manager.update_config(output_directory=directory)
            self.log_widget.append_info(f"Output directory changed to: {directory}")

    def _open_directory(self) -> None:
        """Open the download directory in the file manager."""
        import os

        directory = self.output_input.text().strip()

        if not directory or not os.path.isdir(directory):
            QMessageBox.warning(self, tr("msg_dir_not_found"), tr("msg_dir_not_exist", directory=directory))
            return

        if open_local_path(directory):
            self.log_widget.append_success(f"Opened directory: {directory}")
        else:
            QMessageBox.critical(self, tr("error_generic"), tr("msg_failed_open_dir"))

    # ------------------------------------------------------------------
    # Download and Add to queue (one code path)
    # ------------------------------------------------------------------

    def _on_download_clicked(self) -> None:
        """Download: start at once, also while the queue is paused."""
        self.submit(start_now=True)

    def _on_add_to_queue_clicked(self) -> None:
        """Add to queue: wait for a turn; a paused queue stays paused."""
        self.submit(start_now=False)

    def submit(self, start_now: bool) -> DownloadTask | None:
        """
        Check the form and add the link to the queue.

        Download and Add to queue both call this method, so both run the
        same checks: the link, the folder, the playlist question and the
        duplicate question.

        Args:
            start_now: True for Download (start at once, also while the
                queue is paused), False for Add to queue

        Returns:
            The new task, or None if nothing was added (an error, the user
            said no, or the playlist dialog takes over)
        """
        url = self.url_input.text().strip()
        if not self._check_url(url):
            return None
        output_dir = self.output_input.text().strip()
        if not self._check_output_dir(output_dir):
            return None

        is_playlist, platform = PlaylistDetector.is_playlist_url(url)
        if is_playlist:
            choice = self._ask_playlist_choice(platform)
            if choice == PLAYLIST_CANCEL:
                return None
            if choice == PLAYLIST_CHOOSE:
                self._playlist_start_now = start_now
                self._fetch_playlist_info(url, platform)
                return None
            # PLAYLIST_WHOLE: the playlist link becomes one download.

        quality = self._current_quality()
        audio_only = self._is_audio_mode
        if self.queue_manager.is_duplicate_task(url, quality, audio_only) and not self._confirm_duplicate():
            return None

        self.config_manager.update_config(last_url=url)
        task = self._build_task(url, output_dir)
        index = self.queue_manager.add_task(task, start_now=start_now)
        self._report_added(task, index, start_now)
        self.url_input.clear()
        return task

    def _build_task(
        self,
        url: str,
        output_dir: str,
        quality: str | None = None,
        audio_only: bool | None = None,
        subtitles: tuple[bool, str, list] | None = None,
    ) -> DownloadTask:
        """Create a task from the form. Playlist videos pass their own quality and subtitles."""
        if subtitles is None:
            subtitles = (
                self.subtitles_checkbox.isChecked(),
                self.subtitle_langs_input.text().strip() or "en",
                self.selected_subtitle_codes,
            )
        download_subtitles, subtitle_languages, selected_subtitles = subtitles
        return DownloadTask(
            url=url,
            output_directory=output_dir,
            quality=self._current_quality() if quality is None else quality,
            audio_only=self._is_audio_mode if audio_only is None else audio_only,
            download_thumbnail=self.thumbnail_checkbox.isChecked(),
            download_subtitles=download_subtitles,
            subtitle_languages=subtitle_languages,
            speed_limit=self.speed_limit_spinbox.value(),
            video_container=VIDEO_CONTAINER_FORMATS.get(self.container_combo.currentText()),
            audio_format=AUDIO_FORMATS.get(self.audio_format_combo.currentText(), "mp3"),
            selected_subtitles=selected_subtitles,
            download_metadata=self.metadata_checkbox.isChecked(),
            download_comments=self.comments_checkbox.isChecked(),
            auto_number_duplicates=True,
        )

    def _report_added(self, task: DownloadTask, index: int, start_now: bool) -> None:
        """Tell the user what happens with the new task (status bar, no dialog)."""
        position = index + 1
        if start_now:
            if self.queue_manager.get_worker(task) is not None:
                text = tr("status_download_started")
            else:
                text = tr("status_download_next")
        elif self.queue_manager.is_paused:
            text = tr("status_added_paused", position=position)
        else:
            text = tr("status_added_to_queue", position=position)
        self.log_widget.append_success(f"Added to queue at position {position}: {task.url}")
        show_status(self, text)

    def _ask_playlist_choice(self, platform: str) -> str:
        """
        Ask what to do with a playlist link.

        Returns:
            PLAYLIST_CHOOSE, PLAYLIST_WHOLE or PLAYLIST_CANCEL
        """
        name = _PLATFORM_NAMES.get((platform or "").lower(), platform or "")
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle(tr("dialog_playlist_detected"))
        box.setText(tr("msg_playlist_choice", platform=name))
        choose = box.addButton(tr("button_choose_videos"), QMessageBox.AcceptRole)
        whole = box.addButton(tr("button_whole_playlist"), QMessageBox.ActionRole)
        cancel = box.addButton(tr("button_cancel"), QMessageBox.RejectRole)
        box.setDefaultButton(choose)
        box.setEscapeButton(cancel)
        box.exec()
        clicked = box.clickedButton()
        if clicked is choose:
            return PLAYLIST_CHOOSE
        if clicked is whole:
            return PLAYLIST_WHOLE
        return PLAYLIST_CANCEL

    def _confirm_duplicate(self) -> bool:
        """Ask before adding the same link with the same settings again."""
        reply = QMessageBox.question(
            self,
            tr("duplicate_download"),
            tr("duplicate_download_message"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return reply == QMessageBox.Yes

    # ------------------------------------------------------------------
    # Info, playlists and subtitles
    # ------------------------------------------------------------------

    def _on_show_info_clicked(self) -> None:
        """Handle the Info button."""
        if self.info_worker and self.info_worker.isRunning():
            self.log_widget.append_error("Already fetching video info, please wait...")
            return
        if self.playlist_worker and self.playlist_worker.isRunning():
            self.log_widget.append_error("Already fetching playlist info, please wait...")
            return

        url = self.url_input.text().strip()
        if not self._check_url(url):
            return

        is_playlist, platform = PlaylistDetector.is_playlist_url(url)
        if is_playlist:
            # Videos picked after "Info" go to the queue like "Add to queue".
            self._playlist_start_now = False
            self._fetch_playlist_info(url, platform)
        else:
            self._fetch_video_info(url)

    def _fetch_video_info(self, url: str) -> None:
        """Fetch video info for a single video URL in a worker thread."""
        self.show_info_button.setEnabled(False)
        self.show_info_button.setText(tr("button_fetching"))
        self.log_widget.append_info(f"Fetching video info: {url}")

        self.info_worker = VideoInfoWorker(url)
        self.info_worker.info_fetched.connect(self._on_info_fetched)
        self.info_worker.fetch_failed.connect(self._on_info_fetch_failed)
        self.info_worker.finished.connect(self._on_info_worker_finished)
        self.info_worker.start()

    def _fetch_playlist_info(self, url: str, platform: str) -> None:
        """Fetch playlist info for a playlist URL in a worker thread."""
        self.show_info_button.setEnabled(False)
        self.show_info_button.setText(tr("button_fetching_playlist"))
        self.log_widget.append_info(f"Detected {platform} playlist, fetching info...")

        self.playlist_worker = PlaylistWorker(url)
        self.playlist_worker.playlist_fetched.connect(self._on_playlist_fetched)
        self.playlist_worker.fetch_failed.connect(self._on_playlist_fetch_failed)
        self.playlist_worker.finished.connect(self._on_playlist_worker_finished)
        self.playlist_worker.start()

    def _on_info_fetched(self, video_info) -> None:
        """Show the video info dialog."""
        logger.info(f"Video info received: {video_info.title}")
        # The page URL from yt-dlp can differ from the entered one (short links).
        if video_info.url:
            self.site_tier_label.update_for_url(video_info.url)
            self._sync_site_tier_icon()
        self.log_widget.append_success(f"Video info fetched: {video_info.title}")

        dialog = VideoInfoDialog(video_info, self)
        # The dialog shows a Download button because this is connected. The
        # download starts after the dialog closes, so its questions (playlist,
        # duplicate) do not open on top of it.
        download_requested = []
        dialog.download_requested.connect(lambda: download_requested.append(True))
        dialog.exec()
        if download_requested:
            self._on_download_clicked()

    def _show_error_dialog(self, title_key: str, error_message: str) -> None:
        """Detailed error dialog with the friendly text, suggestions and Copy details."""
        show_download_error(self, error_message, tr(title_key))

    def _on_info_fetch_failed(self, error_message: str) -> None:
        """Handle video info fetch failure."""
        logger.error(f"Info fetch failed: {error_message}")
        self.log_widget.append_error(f"Failed to fetch video info: {error_message}")
        self._show_error_dialog("dialog_failed_fetch_video_info", error_message)

    def _on_info_worker_finished(self) -> None:
        """Handle info worker finished (cleanup)."""
        self.show_info_button.setEnabled(True)
        self.show_info_button.setText(tr("button_info"))
        logger.debug("Info worker finished")

    def _on_playlist_fetched(self, playlist_info) -> None:
        """Show the playlist dialog."""
        logger.info(f"Playlist info received: {playlist_info.title} ({playlist_info.video_count} videos)")
        self.log_widget.append_success(f"Playlist fetched: {playlist_info.title} ({playlist_info.video_count} videos)")

        dialog = PlaylistDialog(playlist_info, self)
        dialog.videos_selected.connect(self._on_playlist_videos_selected)
        dialog.exec()

    def _on_playlist_fetch_failed(self, error_message: str) -> None:
        """Handle playlist info fetch failure."""
        logger.error(f"Playlist fetch failed: {error_message}")
        self.log_widget.append_error(f"Failed to fetch playlist info: {error_message}")
        self._show_error_dialog("dialog_failed_fetch_playlist_info", error_message)

    def _on_playlist_worker_finished(self) -> None:
        """Handle playlist worker finished (cleanup)."""
        self.show_info_button.setEnabled(True)
        self.show_info_button.setText(tr("button_info"))
        logger.debug("Playlist worker finished")

    def _on_playlist_videos_selected(
        self,
        video_urls: list,
        quality: str,
        subtitle_langs: list | None = None,
    ) -> None:
        """
        Add the videos picked in the playlist dialog.

        Args:
            video_urls: List of selected video URLs.
            quality: Selected quality.
            subtitle_langs: Subtitle language codes chosen in the playlist
                dialog. Empty list (or None for older callers) means the
                playlist did not override subtitles - fall back to the
                download tab's own subtitle settings.
        """
        start_now = self._playlist_start_now
        self._playlist_start_now = False
        if not video_urls:
            self.log_widget.append_warning("No videos selected from playlist")
            return

        output_dir = self.output_input.text().strip()
        if not self._check_output_dir(output_dir):
            return

        # A non-empty `subtitle_langs` from the playlist dialog overrides the
        # tab's subtitle settings; otherwise the tab's settings apply.
        playlist_subs = list(subtitle_langs or [])
        subtitles = (True, ",".join(playlist_subs), playlist_subs) if playlist_subs else None

        audio_only = quality == tr("quality_audio_only")  # playlist dialog uses translated "Audio Only"
        for url in video_urls:
            task = self._build_task(url, output_dir, quality=quality, audio_only=audio_only, subtitles=subtitles)
            self.queue_manager.add_task(task, start_now=start_now)

        added_count = len(video_urls)
        if playlist_subs:
            self.log_widget.append_success(
                f"Added {added_count} videos to queue (subtitles: {', '.join(playlist_subs)})"
            )
        else:
            self.log_widget.append_success(f"Added {added_count} videos to queue")
        self.url_input.clear()
        show_status(self, tr("status_videos_added", count=added_count))

    def _on_select_subtitles_clicked(self) -> None:
        """Handle the Choose subtitles button (v2.0.0).

        Dispatches the yt-dlp subtitle enumeration to a ``SubtitleListWorker``
        QThread so the 2-10 second network call does NOT freeze the Qt event
        loop. Results return via ``_on_subtitle_list_fetched`` /
        ``_on_subtitle_list_failed``; until then the button is disabled and
        shows the translated "Fetching..." label.
        """
        url = self.url_input.text().strip()
        if not self._check_url(url):
            return

        # If a previous fetch is still running, ignore the second click.
        if self.subtitle_list_worker is not None and self.subtitle_list_worker.isRunning():
            return

        self.select_subs_button.setEnabled(False)
        self.select_subs_button.setText(tr("text_fetching_subs"))
        self.log_widget.append_info(f"Fetching available subtitles for: {url}")

        self.subtitle_list_worker = SubtitleListWorker(url, parent=self)
        self.subtitle_list_worker.subtitles_fetched.connect(self._on_subtitle_list_fetched)
        self.subtitle_list_worker.fetch_failed.connect(self._on_subtitle_list_failed)
        self.subtitle_list_worker.finished.connect(self._on_subtitle_list_finished)
        self.subtitle_list_worker.start()

    def _on_subtitle_list_fetched(self, available_subs: dict) -> None:
        """Worker thread succeeded; open the selection dialog on the UI thread."""
        if not available_subs:
            show_status(self, tr("msg_no_subs_available"))
            self.log_widget.append_warning("No subtitles found for this video")
            return

        dialog = SubtitleSelectionDialog(available_subs, self)
        if dialog.exec():
            selected = dialog.get_selected_languages()
            self.selected_subtitle_codes = selected

            if selected:
                self.subtitle_langs_input.setText(",".join(selected))
                self.log_widget.append_success(f"Selected {len(selected)} subtitle languages: {', '.join(selected)}")
            else:
                self.subtitle_langs_input.setText("")
                self.log_widget.append_info("No subtitles selected")

    def _on_subtitle_list_failed(self, error_msg: str) -> None:
        """Worker thread reported an error; surface it to the user."""
        logger.error(f"Subtitle fetch failed: {error_msg}")
        QMessageBox.critical(self, tr("error_generic"), error_msg)
        self.log_widget.append_error(error_msg)

    def _on_subtitle_list_finished(self) -> None:
        """Restore the button label and detach the worker so it can be reused."""
        self.select_subs_button.setEnabled(self.subtitles_checkbox.isChecked())
        self.select_subs_button.setText(tr("button_choose_subs"))
        if self.subtitle_list_worker is not None:
            self.subtitle_list_worker.deleteLater()
            self.subtitle_list_worker = None

    # ------------------------------------------------------------------
    # Batch links and drag and drop
    # ------------------------------------------------------------------

    def _on_batch_input_clicked(self) -> None:
        """Add several links at once. They go to the queue like Add to queue."""
        from .batch_input_dialog import BatchInputDialog

        dialog = BatchInputDialog(self)
        if not dialog.exec():
            return
        urls = dialog.get_urls()
        if not urls:
            return

        output_dir = self.output_input.text().strip()
        if not self._check_output_dir(output_dir):
            return

        for url in urls:
            self.queue_manager.add_task(self._build_task(url, output_dir))

        self.log_widget.append_success(f"Batch: Added {len(urls)} URLs to queue")
        show_status(self, tr("status_batch_added", count=len(urls)))

    def _drag_enter_event(self, event) -> None:
        """Accept dragged text (a link) on the link field."""
        if event.mimeData().hasText():
            event.acceptProposedAction()
            logger.debug("Drag enter accepted: text/URL detected")
        else:
            event.ignore()

    def _drop_event(self, event) -> None:
        """Put a dropped link into the link field."""
        if event.mimeData().hasText():
            text = event.mimeData().text().strip()
            self.url_input.setText(text)
            self.url_input.setFocus()
            self.log_widget.append_info(f"URL dropped: {text[:50]}...")
            logger.info(f"URL dropped into input field: {text}")
            event.acceptProposedAction()
        else:
            event.ignore()
