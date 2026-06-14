"""
Playlist viewer dialog for YT-DLP Studio.

This module provides a dialog to view and select videos from a playlist.
"""

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,  # needed for thumbnail display
)

from ..backend.playlist_fetcher import PlaylistInfo
from ..utils.logger import get_logger
from ..utils.translations import tr

logger = get_logger()


# Ordered so the most-likely language for this app's audience appears first.
# Hebrew maps to BOTH the modern (`he`) and the legacy ISO 639 (`iw`) codes
# because YouTube serves Hebrew subtitles under either one depending on the
# upload year and the channel.
_SUBTITLE_LANGUAGE_CHOICES: list[tuple[str, str, tuple[str, ...]]] = [
    ("he", "checkbox_subtitle_lang_he", ("he", "iw")),
    ("en", "checkbox_subtitle_lang_en", ("en",)),
    ("ar", "checkbox_subtitle_lang_ar", ("ar",)),
    ("es", "checkbox_subtitle_lang_es", ("es",)),
    ("fr", "checkbox_subtitle_lang_fr", ("fr",)),
    ("ru", "checkbox_subtitle_lang_ru", ("ru",)),
    ("de", "checkbox_subtitle_lang_de", ("de",)),
]


def _parse_extra_subtitle_codes(raw: str) -> list[str]:
    """Split a 'pt, it, zh-Hans' style string into a clean list of codes.

    Strips whitespace, drops empty entries, and de-duplicates while preserving
    order. Returns an empty list when the input contains no usable codes.
    """
    seen: set[str] = set()
    out: list[str] = []
    for piece in (raw or "").split(","):
        code = piece.strip()
        if code and code not in seen:
            seen.add(code)
            out.append(code)
    return out


def _collect_subtitle_languages(
    selected_keys: list[str],
    extra_raw: str,
) -> list[str]:
    """Combine the checked language presets with the free-form codes input.

    Hebrew expands to both `he` and `iw`; other presets map 1:1. Extra codes
    are appended in input order. Duplicates are removed while preserving
    first-seen order.
    """
    seen: set[str] = set()
    out: list[str] = []
    preset_map = {key: codes for key, _, codes in _SUBTITLE_LANGUAGE_CHOICES}

    for key in selected_keys:
        for code in preset_map.get(key, ()):
            if code not in seen:
                seen.add(code)
                out.append(code)

    for code in _parse_extra_subtitle_codes(extra_raw):
        if code not in seen:
            seen.add(code)
            out.append(code)

    return out


class PlaylistDialog(QDialog):
    """
    Dialog to display playlist information and select videos.

    Shows playlist metadata and list of videos with checkboxes for selection.

    Signals:
        videos_selected: Emitted when user clicks download with
            (list of video URLs, quality, list of subtitle language codes).
            The subtitle language list is empty when the user did not enable
            subtitles for this playlist; consumers should fall back to the
            parent tab's subtitle settings in that case.
    """

    videos_selected = Signal(list, str, list)  # (urls, quality, subtitle_langs)

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
        # Per-language subtitle checkboxes, keyed by the language key
        # ("he", "en", ...). Populated by _setup_subtitle_section.
        self.subtitle_lang_checkboxes: dict[str, QCheckBox] = {}
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

        # Title. The inline `color: #ffffff` was invisible in light theme and
        # bypassed the QSS theme system. Rely on the default palette and use
        # an object name so the theme can target it.
        title_label = QLabel(f"<b>{self.playlist_info.title}</b>")
        title_label.setWordWrap(True)
        title_label.setObjectName("playlistTitleLabel")
        title_label.setStyleSheet("font-size: 14px;")
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
        self.videos_table.setHorizontalHeaderLabels(
            [
                tr("col_select"),
                tr("col_index"),
                tr("col_title"),
                tr("col_duration"),
                tr("col_uploader"),
            ]
        )

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

        # Subtitles section (per-playlist override)
        self._setup_subtitle_section(main_layout)

        # Button section
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton(tr("cancel"))
        cancel_button.setMinimumWidth(100)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        # Object name ties this button to the primary-button QSS selector in
        # the theme, replacing the inline blue stylesheet that duplicated
        # rules already defined globally.
        download_button = QPushButton(tr("button_add_to_queue"))
        download_button.setMinimumWidth(150)
        download_button.setObjectName("primaryButton")
        download_button.clicked.connect(self._on_download_clicked)
        button_layout.addWidget(download_button)

        main_layout.addLayout(button_layout)

    def _setup_subtitle_section(self, parent_layout: QVBoxLayout) -> None:
        """Build the per-playlist subtitle picker.

        The whole group is collapsed (disabled) until the parent checkbox is
        ticked, so the playlist downloads the same as before by default.
        """
        group = QGroupBox(tr("group_playlist_subtitles"))
        group_layout = QVBoxLayout(group)

        # Master toggle for the whole section. Off by default.
        self.subtitles_enabled_checkbox = QCheckBox(tr("checkbox_playlist_download_subtitles"))
        self.subtitles_enabled_checkbox.setToolTip(tr("tooltip_playlist_download_subtitles"))
        self.subtitles_enabled_checkbox.setChecked(False)
        self.subtitles_enabled_checkbox.stateChanged.connect(self._on_subtitles_toggled)
        group_layout.addWidget(self.subtitles_enabled_checkbox)

        # Override-behavior hint sits right under the toggle so the user can
        # see WHY this section exists even before they tick the box.
        hint_label = QLabel(tr("label_playlist_subtitle_override_hint"))
        hint_label.setWordWrap(True)
        hint_label.setObjectName("hintLabel")
        hint_label.setStyleSheet("color: palette(mid); font-style: italic;")
        group_layout.addWidget(hint_label)

        # Language picker - 2-column grid keeps the dialog compact.
        langs_label = QLabel(tr("label_playlist_subtitle_languages"))
        group_layout.addWidget(langs_label)

        langs_grid = QGridLayout()
        for idx, (key, tr_key, _codes) in enumerate(_SUBTITLE_LANGUAGE_CHOICES):
            checkbox = QCheckBox(tr(tr_key))
            checkbox.setChecked(False)
            checkbox.setEnabled(False)  # gated by the master toggle
            row, col = divmod(idx, 2)
            langs_grid.addWidget(checkbox, row, col)
            self.subtitle_lang_checkboxes[key] = checkbox
        group_layout.addLayout(langs_grid)

        # Free-form override for any code not in the preset list.
        other_row = QHBoxLayout()
        other_label = QLabel(tr("label_playlist_subtitle_other"))
        other_label.setEnabled(False)
        self.subtitle_other_input = QLineEdit()
        self.subtitle_other_input.setPlaceholderText(tr("placeholder_playlist_subtitle_other"))
        self.subtitle_other_input.setToolTip(tr("tooltip_playlist_subtitle_other"))
        self.subtitle_other_input.setEnabled(False)
        other_row.addWidget(other_label)
        other_row.addWidget(self.subtitle_other_input)
        group_layout.addLayout(other_row)

        # Keep references so the master toggle can enable/disable them later.
        self._subtitle_dependent_widgets: list[QWidget] = [
            *self.subtitle_lang_checkboxes.values(),
            other_label,
            self.subtitle_other_input,
        ]

        parent_layout.addWidget(group)

    def _on_subtitles_toggled(self, _state: int) -> None:
        """Enable or disable the language picker based on the master toggle.

        Reads the checkbox state directly via ``isChecked()`` rather than
        interpreting the ``stateChanged`` signal payload, which is a plain
        ``int`` today but is documented to change across PySide6 versions
        (some versions emit a ``Qt.CheckState`` enum).
        """
        enabled = self.subtitles_enabled_checkbox.isChecked()
        for widget in self._subtitle_dependent_widgets:
            widget.setEnabled(enabled)

    def get_selected_subtitle_languages(self) -> list[str]:
        """Return the resolved list of subtitle language codes for this playlist.

        Returns:
            Empty list when subtitles are disabled. Otherwise a deduplicated
            list with the modern + legacy code for each ticked preset, plus
            any free-form codes the user typed.
        """
        if not self.subtitles_enabled_checkbox.isChecked():
            return []

        selected_keys = [key for key, checkbox in self.subtitle_lang_checkboxes.items() if checkbox.isChecked()]
        return _collect_subtitle_languages(selected_keys, self.subtitle_other_input.text())

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

        # Resolve subtitle languages for this playlist (may be empty -
        # the download tab then falls back to its own subtitle settings).
        subtitle_langs = self.get_selected_subtitle_languages()
        if self.subtitles_enabled_checkbox.isChecked() and not subtitle_langs:
            QMessageBox.warning(
                self,
                tr("group_playlist_subtitles"),
                tr("msg_playlist_no_subtitle_langs"),
            )
            return

        logger.info(
            f"User selected {len(selected_urls)} videos with quality: {quality}, "
            f"playlist subtitle langs: {subtitle_langs or '(inherit from tab)'}"
        )

        # Emit signal with selected videos, quality, and subtitle languages.
        self.videos_selected.emit(selected_urls, quality, subtitle_langs)

        # Close dialog
        self.accept()
