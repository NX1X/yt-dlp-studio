"""
Playlist viewer dialog for YT-DLP Studio.

This module provides a dialog to view and select videos from a playlist.
"""

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..backend.playlist_fetcher import PlaylistInfo
from ..utils.logger import get_logger
from ..utils.translations import tr
from .display_format import ltr

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

# Language check boxes per row in the subtitle section
_LANGUAGE_COLUMNS = 4


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

    # Table columns. The first column holds the check box and the number.
    COL_CHECK, COL_TITLE, COL_DURATION, COL_UPLOADER = range(4)

    def __init__(self, playlist_info: PlaylistInfo, parent=None):
        """
        Initialize playlist dialog.

        Args:
            playlist_info: PlaylistInfo object with playlist metadata
            parent: Parent widget
        """
        super().__init__(parent)
        self.playlist_info = playlist_info
        # Per-language subtitle checkboxes, keyed by the language key
        # ("he", "en", ...). Populated by _setup_subtitle_section.
        self.subtitle_lang_checkboxes: dict[str, QCheckBox] = {}
        # Row whose check state Qt changed during the current click
        self._changed_in_click: int | None = None
        self._setup_ui()
        self._populate_videos()
        logger.debug(f"PlaylistDialog created for: {playlist_info.title}")

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle(tr("dialog_playlist_viewer"))
        self.setMinimumSize(QSize(820, 560))

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(8)

        # Playlist info: the title and one line of facts (no group box)
        title_label = QLabel(self.playlist_info.title)
        title_label.setWordWrap(True)
        title_label.setObjectName("playlistTitleLabel")
        title_label.setProperty("labelStyle", "title")
        main_layout.addWidget(title_label)

        facts = [tr("label_videos_count", count=self.playlist_info.video_count)]
        if self.playlist_info.uploader:
            facts.append(f"{tr('label_uploader')}: {self.playlist_info.uploader}")
        stats_label = QLabel("   |   ".join(facts))
        stats_label.setProperty("labelStyle", "secondary")
        main_layout.addWidget(stats_label)
        main_layout.addSpacing(4)

        # Toolbar: selection, count and quality
        controls_layout = QHBoxLayout()
        select_all_btn = QPushButton(tr("button_select_all"))
        select_all_btn.clicked.connect(self._select_all)
        controls_layout.addWidget(select_all_btn)

        select_none_btn = QPushButton(tr("button_select_none"))
        select_none_btn.clicked.connect(self._select_none)
        controls_layout.addWidget(select_none_btn)

        self.selected_count_label = QLabel()
        self.selected_count_label.setProperty("labelStyle", "secondary")
        controls_layout.addSpacing(8)
        controls_layout.addWidget(self.selected_count_label)
        controls_layout.addStretch()

        quality_label = QLabel(tr("label_quality_playlist"))
        controls_layout.addWidget(quality_label)
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(
            [tr("quality_best"), tr("quality_1080p"), tr("quality_720p"), tr("quality_480p"), tr("quality_audio_only")]
        )
        quality_label.setBuddy(self.quality_combo)
        controls_layout.addWidget(self.quality_combo)
        main_layout.addLayout(controls_layout)

        # Videos table: it gets all the free space
        self.videos_table = QTableWidget()
        self.videos_table.setColumnCount(4)
        self.videos_table.setHorizontalHeaderLabels(
            [tr("col_index"), tr("col_title"), tr("col_duration"), tr("col_uploader")]
        )
        header = self.videos_table.horizontalHeader()
        # Fixed: the size hint leaves out the check box and the cell padding.
        header.setSectionResizeMode(self.COL_CHECK, QHeaderView.Fixed)
        self.videos_table.setColumnWidth(self.COL_CHECK, 72)
        header.setSectionResizeMode(self.COL_TITLE, QHeaderView.Stretch)
        header.setSectionResizeMode(self.COL_DURATION, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_UPLOADER, QHeaderView.ResizeToContents)
        self.videos_table.verticalHeader().setVisible(False)
        self.videos_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.videos_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.videos_table.setAlternatingRowColors(True)
        self.videos_table.setWordWrap(False)
        self.videos_table.itemChanged.connect(self._on_item_changed)
        self.videos_table.cellClicked.connect(self._on_cell_clicked)
        # Space checks or unchecks the selected rows.
        toggle = QShortcut(QKeySequence(Qt.Key.Key_Space), self.videos_table)
        toggle.setContext(Qt.ShortcutContext.WidgetShortcut)
        toggle.activated.connect(self._toggle_selected_rows)
        main_layout.addWidget(self.videos_table, 1)

        # Subtitles section (per-playlist override), closed by default
        self._setup_subtitle_section(main_layout)

        # Buttons
        self.button_box = QDialogButtonBox()
        self.add_button = QPushButton()
        self.add_button.setProperty("buttonStyle", "primary")
        self.add_button.setDefault(True)
        self.button_box.addButton(self.add_button, QDialogButtonBox.ButtonRole.AcceptRole)
        self.button_box.addButton(tr("cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        self.button_box.accepted.connect(self._on_download_clicked)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

    def _setup_subtitle_section(self, parent_layout: QVBoxLayout) -> None:
        """Build the per-playlist subtitle picker.

        A header button opens the section; it is closed by default. Inside,
        the languages stay disabled until the master check box is ticked, so
        the playlist downloads the same as before by default.
        """
        self.subtitle_header = QToolButton()
        self.subtitle_header.setText(tr("group_playlist_subtitles"))
        self.subtitle_header.setCheckable(True)
        self.subtitle_header.setChecked(False)
        self.subtitle_header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.subtitle_header.setProperty("sectionHeader", True)
        self.subtitle_header.toggled.connect(self._set_subtitles_expanded)
        parent_layout.addWidget(self.subtitle_header)

        self.subtitle_section = QWidget()
        group_layout = QVBoxLayout(self.subtitle_section)
        group_layout.setContentsMargins(24, 0, 0, 0)
        group_layout.setSpacing(6)

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
        hint_label.setProperty("labelStyle", "secondary")
        group_layout.addWidget(hint_label)

        # Languages in one compact grid
        langs_grid = QGridLayout()
        langs_grid.setHorizontalSpacing(16)
        langs_grid.setVerticalSpacing(4)
        langs_grid.addWidget(QLabel(tr("label_playlist_subtitle_languages")), 0, 0)
        for idx, (key, tr_key, _codes) in enumerate(_SUBTITLE_LANGUAGE_CHOICES):
            checkbox = QCheckBox(tr(tr_key))
            checkbox.setChecked(False)
            checkbox.setEnabled(False)  # gated by the master toggle
            row, col = divmod(idx, _LANGUAGE_COLUMNS)
            langs_grid.addWidget(checkbox, row, col + 1)
            self.subtitle_lang_checkboxes[key] = checkbox
        langs_grid.setColumnStretch(_LANGUAGE_COLUMNS + 1, 1)
        group_layout.addLayout(langs_grid)

        # Free-form override for any code not in the preset list.
        other_row = QHBoxLayout()
        other_label = QLabel(tr("label_playlist_subtitle_other"))
        other_label.setEnabled(False)
        self.subtitle_other_input = QLineEdit()
        self.subtitle_other_input.setPlaceholderText(tr("placeholder_playlist_subtitle_other"))
        self.subtitle_other_input.setToolTip(tr("tooltip_playlist_subtitle_other"))
        self.subtitle_other_input.setEnabled(False)
        self.subtitle_other_input.setMaximumWidth(320)
        other_label.setBuddy(self.subtitle_other_input)
        other_row.addWidget(other_label)
        other_row.addWidget(self.subtitle_other_input)
        other_row.addStretch()
        group_layout.addLayout(other_row)

        # Keep references so the master toggle can enable/disable them later.
        self._subtitle_dependent_widgets: list[QWidget] = [
            *self.subtitle_lang_checkboxes.values(),
            other_label,
            self.subtitle_other_input,
        ]

        parent_layout.addWidget(self.subtitle_section)
        self._set_subtitles_expanded(False)

    def _set_subtitles_expanded(self, expanded: bool) -> None:
        """Open or close the subtitle section (the arrow points at the text when closed)."""
        self.subtitle_section.setVisible(expanded)
        if expanded:
            arrow = Qt.ArrowType.DownArrow
        elif QApplication.layoutDirection() == Qt.LayoutDirection.RightToLeft:
            arrow = Qt.ArrowType.LeftArrow
        else:
            arrow = Qt.ArrowType.RightArrow
        self.subtitle_header.setArrowType(arrow)

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

    # ---------- video list ----------

    def _populate_videos(self) -> None:
        """Populate the videos table. Every video starts checked."""
        self.videos_table.blockSignals(True)
        self.videos_table.setRowCount(len(self.playlist_info.videos))

        for idx, video in enumerate(self.playlist_info.videos):
            check_item = QTableWidgetItem(str(video.index))
            check_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)
            check_item.setCheckState(Qt.Checked)
            self.videos_table.setItem(idx, self.COL_CHECK, check_item)

            title_item = QTableWidgetItem(video.title)
            title_item.setToolTip(video.title)
            self.videos_table.setItem(idx, self.COL_TITLE, title_item)

            duration_item = QTableWidgetItem(
                ltr(video.get_duration_formatted()) if video.duration > 0 else tr("text_unknown_label")
            )
            duration_item.setTextAlignment(Qt.AlignCenter)
            self.videos_table.setItem(idx, self.COL_DURATION, duration_item)

            self.videos_table.setItem(idx, self.COL_UPLOADER, QTableWidgetItem(video.uploader or "-"))

        self.videos_table.blockSignals(False)
        self._update_selection_count()
        logger.debug(f"Populated {len(self.playlist_info.videos)} videos in table")

    def is_row_checked(self, row: int) -> bool:
        """True if the video in ``row`` will be added."""
        return self.videos_table.item(row, self.COL_CHECK).checkState() == Qt.Checked

    def set_row_checked(self, row: int, checked: bool) -> None:
        """Check or uncheck the video in ``row``."""
        self.videos_table.item(row, self.COL_CHECK).setCheckState(Qt.Checked if checked else Qt.Unchecked)

    def selected_video_count(self) -> int:
        """Number of checked videos."""
        return sum(self.is_row_checked(row) for row in range(self.videos_table.rowCount()))

    def _update_selection_count(self) -> None:
        selected = self.selected_video_count()
        total = self.videos_table.rowCount()
        self.selected_count_label.setText(tr("label_selected_count", selected=selected, total=total))
        self.add_button.setText(tr("button_add_videos_to_queue", count=selected))
        self.add_button.setEnabled(selected > 0)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() != self.COL_CHECK:
            return
        self._changed_in_click = item.row()
        QTimer.singleShot(0, self._clear_changed_in_click)
        self._update_selection_count()

    def _clear_changed_in_click(self) -> None:
        self._changed_in_click = None

    def _on_cell_clicked(self, row: int, _column: int) -> None:
        """A click anywhere in a row checks or unchecks it.

        A click on the check box itself is already handled by Qt (it changes
        the item first), so it is not toggled a second time.
        """
        if self._changed_in_click == row:
            return
        self.set_row_checked(row, not self.is_row_checked(row))

    def _toggle_selected_rows(self) -> None:
        rows = sorted({index.row() for index in self.videos_table.selectionModel().selectedRows()})
        if not rows:
            return
        # All checked -> uncheck them; otherwise check them all.
        check = not all(self.is_row_checked(row) for row in rows)
        for row in rows:
            self.set_row_checked(row, check)

    def _select_all(self) -> None:
        """Select all videos."""
        for row in range(self.videos_table.rowCount()):
            self.set_row_checked(row, True)
        logger.debug("Selected all videos")

    def _select_none(self) -> None:
        """Deselect all videos."""
        for row in range(self.videos_table.rowCount()):
            self.set_row_checked(row, False)
        logger.debug("Deselected all videos")

    def _on_download_clicked(self) -> None:
        """Handle download button click."""
        selected_urls = [
            self.playlist_info.videos[row].url
            for row in range(self.videos_table.rowCount())
            if self.is_row_checked(row)
        ]

        if not selected_urls:
            QMessageBox.warning(self, tr("dialog_no_videos_selected"), tr("msg_select_at_least_one_video"))
            return

        # Get selected quality
        quality = self.quality_combo.currentText()

        # Resolve subtitle languages for this playlist (may be empty -
        # the download tab then falls back to its own subtitle settings).
        subtitle_langs = self.get_selected_subtitle_languages()
        if self.subtitles_enabled_checkbox.isChecked() and not subtitle_langs:
            self.subtitle_header.setChecked(True)
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
