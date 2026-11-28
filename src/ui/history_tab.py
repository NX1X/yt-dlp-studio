"""
History tab UI for YT-DLP Studio.

A one-line summary, a search field with a status filter, and the table
(Date, Title, Status, Quality, Size). The row menu and double-click open
the file or its folder, copy the link, or put the link back into the
Download tab ("Download again"). The clear actions share one menu button.
The tab refreshes on its own when a download finishes.
"""

import os

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QAction, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedLayout,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..backend.history_manager import HistoryManager
from ..utils.logger import get_logger
from ..utils.status_labels import history_status_text
from ..utils.translations import tr, tr_count
from .display_format import link_text, ltr, open_local_path, quality_label, size_text, speed_text
from .status_messages import show_status
from .table_delegates import STATUS_KIND_ROLE, StatusDelegate

logger = get_logger()

# Table columns
COL_DATE, COL_TITLE, COL_STATUS, COL_QUALITY, COL_SIZE = range(5)

# Rows shown at most (newest first)
HISTORY_LIMIT = 500

# Status filter: (stored status or None for all, translation key)
_STATUS_FILTERS = (
    (None, "filter_all_statuses"),
    ("completed", "status_completed"),
    ("failed", "status_failed"),
    ("cancelled", "status_cancelled"),
)

_STATUS_KIND = {"completed": "done", "failed": "failed", "cancelled": "cancelled"}

# Stack pages
_PAGE_TABLE, _PAGE_EMPTY, _PAGE_NO_MATCHES = range(3)


class HistoryTab(QWidget):
    """
    History tab widget showing download history and statistics.

    Signals:
        download_again_requested(str): the user wants to download this link again
    """

    download_again_requested = Signal(str)

    def __init__(self, history_manager: HistoryManager, parent=None, config_manager=None):
        """
        Initialize history tab.

        Args:
            history_manager: HistoryManager instance
            parent: Parent widget
            config_manager: ConfigManager for the download folder (optional)
        """
        super().__init__(parent)
        self.history_manager = history_manager
        self.config_manager = config_manager
        self._entries: list = []  # entries shown in the table, in row order
        self._setup_ui()
        self._load_history()
        logger.info("HistoryTab initialized")

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        self.stats_label = QLabel()
        self.stats_label.setObjectName("historySummary")
        main_layout.addWidget(self.stats_label)

        # Search, status filter and export
        search_row = QHBoxLayout()
        search_row.setSpacing(8)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(tr("placeholder_search_title_link"))
        self.search_input.setAccessibleName(tr("label_search"))
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_search)
        self.status_filter = QComboBox()
        for status, key in _STATUS_FILTERS:
            self.status_filter.addItem(tr(key), status)
        self.status_filter.setAccessibleName(tr("filter_status"))
        self.status_filter.currentIndexChanged.connect(self._apply_filter)
        self.export_button = QPushButton(tr("button_export_csv"))
        self.export_button.setProperty("buttonStyle", "secondary")
        self.export_button.clicked.connect(self._export_csv)
        search_row.addWidget(self.search_input, 1)
        search_row.addWidget(self.status_filter)
        search_row.addWidget(self.export_button)
        main_layout.addLayout(search_row)

        # History table
        history_group = QGroupBox(tr("history_download_history"))
        history_layout = QVBoxLayout(history_group)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(
            [tr("col_datetime"), tr("col_title"), tr("col_status"), tr("col_quality"), tr("col_size")]
        )
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(COL_DATE, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(COL_TITLE, QHeaderView.Stretch)
        header.setSectionResizeMode(COL_STATUS, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(COL_QUALITY, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(COL_SIZE, QHeaderView.ResizeToContents)
        header.setHighlightSections(False)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.history_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.history_table.setWordWrap(False)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.verticalHeader().setDefaultSectionSize(32)
        self.history_table.setItemDelegateForColumn(COL_STATUS, StatusDelegate(self.history_table))
        self.history_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.history_table.customContextMenuRequested.connect(self._show_context_menu)
        self.history_table.cellDoubleClicked.connect(self._on_row_double_clicked)
        # Delete removes the selected entry while the table has the focus.
        self.delete_shortcut = QShortcut(QKeySequence(QKeySequence.Delete), self.history_table)
        self.delete_shortcut.setContext(Qt.WidgetShortcut)
        self.delete_shortcut.activated.connect(lambda: self._remove_entry(self._selected_entry()))

        self._history_empty_widget = self._empty_page("history_empty", "history_empty_hint")
        self._no_matches_widget = self._empty_page("history_no_matches", "history_no_matches_hint")

        self._history_stack = QStackedLayout()
        self._history_stack.addWidget(self.history_table)
        self._history_stack.addWidget(self._history_empty_widget)
        self._history_stack.addWidget(self._no_matches_widget)
        history_layout.addLayout(self._history_stack)
        main_layout.addWidget(history_group, 1)

        # Bottom bar
        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        self.open_dir_button = QPushButton(tr("button_open_downloads_folder"))
        self.open_dir_button.setProperty("buttonStyle", "secondary")
        self.open_dir_button.setToolTip(tr("tooltip_open_downloads_dir"))
        self.open_dir_button.clicked.connect(self._open_download_directory)
        button_row.addWidget(self.open_dir_button)
        button_row.addStretch(1)

        self.clear_button = QPushButton(tr("button_clear_menu"))
        self.clear_button.setProperty("buttonStyle", "danger")
        self.clear_button.setToolTip(tr("tooltip_clear_history"))
        clear_menu = QMenu(self.clear_button)
        self.clear_completed_action = clear_menu.addAction(tr("menu_clear_history_completed"))
        self.clear_completed_action.triggered.connect(lambda: self._clear_history("completed"))
        self.clear_failed_action = clear_menu.addAction(tr("menu_clear_history_failed"))
        self.clear_failed_action.triggered.connect(lambda: self._clear_history("failed"))
        clear_menu.addSeparator()
        self.clear_all_action = clear_menu.addAction(tr("menu_clear_history_all"))
        self.clear_all_action.triggered.connect(lambda: self._clear_history(None))
        self.clear_button.setMenu(clear_menu)
        button_row.addWidget(self.clear_button)
        main_layout.addLayout(button_row)

    @staticmethod
    def _empty_page(title_key: str, hint_key: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        title = QLabel(tr(title_key))
        title.setObjectName("emptyTitle")
        title.setAlignment(Qt.AlignCenter)
        hint = QLabel(tr(hint_key))
        hint.setProperty("labelStyle", "secondary")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(hint)
        return page

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def _load_history(self) -> None:
        """Load the summary and the rows that match the search and filter."""
        self._update_summary()
        self._apply_filter()

    def _update_summary(self) -> None:
        stats = self.history_manager.get_statistics()
        self.stats_label.setText(
            tr_count(
                "history_summary",
                stats["total_downloads"],
                total=stats["total_downloads"],
                done=stats["completed"],
                failed=stats["failed"],
                cancelled=stats["cancelled"],
                size=size_text(stats["total_size_bytes"]) or ltr("0 B"),
            )
        )
        self.stats_label.setToolTip(
            tr(
                "history_summary_tooltip",
                rate=ltr(f"{stats['success_rate']:.1f}%"),
                speed=speed_text(stats["average_speed_bps"]) or ltr("0 B/s"),
            )
        )
        has_entries = stats["total_downloads"] > 0
        self.clear_button.setEnabled(has_entries)
        self.export_button.setEnabled(has_entries)

    def _matching_entries(self) -> list:
        """Entries for the search text and the status filter, newest first."""
        query = self.search_input.text().strip()
        status = self.status_filter.currentData()
        if query:
            entries = self.history_manager.search_history(query)
            entries = sorted(entries, key=lambda e: e.timestamp, reverse=True)
            if status:
                entries = [e for e in entries if e.status == status]
            return entries[:HISTORY_LIMIT]
        return self.history_manager.get_history(limit=HISTORY_LIMIT, status=status)

    def _apply_filter(self, *_args) -> None:
        """Fill the table; show the empty or "No matches" page when there are no rows."""
        entries = self._matching_entries()
        self._entries = entries
        self.history_table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            self._fill_row(row, entry)

        if entries:
            self._history_stack.setCurrentIndex(_PAGE_TABLE)
        elif self.history_manager.get_statistics()["total_downloads"] == 0:
            self._history_stack.setCurrentIndex(_PAGE_EMPTY)
        else:
            self._history_stack.setCurrentIndex(_PAGE_NO_MATCHES)

    def _fill_row(self, row: int, entry) -> None:
        date_item = QTableWidgetItem(ltr(entry.timestamp.strftime("%Y-%m-%d %H:%M")))
        self.history_table.setItem(row, COL_DATE, date_item)

        title = entry.title or entry.filename or entry.url
        title_item = QTableWidgetItem(title)
        tooltip = [title, tr("tooltip_history_link", url=link_text(entry.url))]
        if entry.status == "failed" and entry.error_message:
            tooltip.append(tr("tooltip_history_error", reason=entry.error_message[:300]))
        title_item.setToolTip("\n".join(tooltip))
        self.history_table.setItem(row, COL_TITLE, title_item)

        # Status: translated for display only; the stored value stays English.
        status_item = QTableWidgetItem(history_status_text(entry.status))
        status_item.setData(STATUS_KIND_ROLE, _STATUS_KIND.get(entry.status, "waiting"))
        self.history_table.setItem(row, COL_STATUS, status_item)

        self.history_table.setItem(row, COL_QUALITY, QTableWidgetItem(quality_label(entry.quality)))

        size_item = QTableWidgetItem(size_text(entry.file_size))
        size_item.setTextAlignment(Qt.AlignTrailing | Qt.AlignVCenter)
        self.history_table.setItem(row, COL_SIZE, size_item)

    def _on_search(self, _query: str) -> None:
        """Search as the user types; the status filter still applies."""
        self._apply_filter()

    def refresh(self) -> None:
        """Refresh the history display."""
        self._load_history()

    # ------------------------------------------------------------------
    # Row menu
    # ------------------------------------------------------------------

    def _entry_at(self, row: int):
        return self._entries[row] if 0 <= row < len(self._entries) else None

    def _selected_entry(self):
        rows = self.history_table.selectionModel().selectedRows()
        return self._entry_at(rows[0].row()) if rows else None

    @staticmethod
    def _entry_file(entry) -> str:
        if not entry.filename:
            return ""
        folder = os.path.expanduser(os.path.expandvars(entry.output_directory or ""))
        return os.path.join(folder, entry.filename)

    def build_context_menu(self, row: int) -> QMenu:
        """The right-click menu for ``row`` (also used by the tests)."""
        entry = self._entry_at(row)
        menu = QMenu(self)

        def add(key: str, text_key: str, slot, enabled: bool) -> QAction:
            action = menu.addAction(tr(text_key))
            action.setObjectName(key)
            action.setEnabled(enabled)
            action.triggered.connect(lambda: slot(entry))
            return action

        has_file = entry is not None and entry.status == "completed" and bool(entry.filename)
        add("open_file", "action_open_file", self._open_entry_file, has_file)
        add("open_folder", "action_open_folder", self._open_entry_folder, entry is not None)
        add("copy_link", "menu_copy_link", self._copy_entry_link, entry is not None)
        menu.addSeparator()
        add("download_again", "menu_download_again", self._download_again, entry is not None)
        menu.addSeparator()
        add("remove", "menu_remove_from_history", self._remove_entry, entry is not None)
        return menu

    def _show_context_menu(self, pos: QPoint) -> None:
        row = self.history_table.rowAt(pos.y())
        if row < 0:
            return
        self.history_table.selectRow(row)
        self.build_context_menu(row).exec(self.history_table.viewport().mapToGlobal(pos))

    def _on_row_double_clicked(self, row: int, _column: int) -> None:
        """Double-click opens a downloaded file; for other rows it downloads again."""
        entry = self._entry_at(row)
        if entry is None:
            return
        if entry.status == "completed" and entry.filename:
            self._open_entry_file(entry)
        else:
            self._download_again(entry)

    def _open_entry_file(self, entry) -> None:
        path = self._entry_file(entry) if entry else ""
        if not path or not os.path.isfile(path):
            QMessageBox.warning(self, tr("msg_file_not_found"), f"{tr('msg_file_not_found_desc')}:\n{path}")
            return
        if not open_local_path(path):
            QMessageBox.critical(self, tr("error"), tr("msg_failed_open_file"))

    def _open_entry_folder(self, entry) -> None:
        folder = os.path.expanduser(os.path.expandvars(entry.output_directory or "")) if entry else ""
        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(self, tr("msg_dir_not_found"), f"{tr('msg_download_dir_not_exist')}:\n{folder}")
            return
        if not open_local_path(folder):
            QMessageBox.critical(self, tr("error"), tr("msg_failed_open_dir"))

    def _copy_entry_link(self, entry) -> None:
        if entry is None:
            return
        QGuiApplication.clipboard().setText(entry.url)
        show_status(self, tr("status_link_copied"))

    def _download_again(self, entry) -> None:
        """Put the link into the Download tab; the user checks the options and starts it."""
        if entry is None:
            return
        self.download_again_requested.emit(entry.url)
        show_status(self, tr("status_link_in_download_tab"))

    def _remove_entry(self, entry) -> None:
        """Remove one entry from the history (no question: it only forgets the row)."""
        if entry is None:
            return
        if self.history_manager.remove_entry(entry):
            self._load_history()
            show_status(self, tr("status_history_entry_removed"))

    # ------------------------------------------------------------------
    # Export, clear, open folder
    # ------------------------------------------------------------------

    def _export_csv(self) -> None:
        """Export history to CSV."""
        filepath, _ = QFileDialog.getSaveFileName(
            self, tr("dialog_export_history"), "download_history.csv", tr("filter_csv_files")
        )

        if filepath:
            from pathlib import Path

            success = self.history_manager.export_to_csv(Path(filepath))
            if success:
                show_status(self, tr("status_history_exported", path=link_text(filepath)))
            else:
                QMessageBox.critical(self, tr("error"), tr("msg_export_failed"))

    def _clear_history(self, status: str | None) -> None:
        """Clear history entries (asks first)."""
        if status:
            reply = QMessageBox.question(
                self,
                tr("dialog_confirm_clear"),
                tr("msg_clear_status_confirm", status=history_status_text(status)),
                QMessageBox.Yes | QMessageBox.No,
            )
        else:
            reply = QMessageBox.question(
                self, tr("dialog_confirm_clear_all"), tr("msg_clear_all_confirm"), QMessageBox.Yes | QMessageBox.No
            )

        if reply == QMessageBox.Yes:
            count = self.history_manager.clear_history(status)
            self._load_history()
            show_status(self, tr_count("status_history_cleared", count))

    def _download_directory(self) -> str:
        if self.config_manager is None:
            from ..backend.config_manager import ConfigManager

            self.config_manager = ConfigManager()
        return self.config_manager.get_config().output_directory

    def _open_download_directory(self) -> None:
        """Open the default download folder in the file manager."""
        directory = self._download_directory()

        if not directory or not os.path.isdir(directory):
            QMessageBox.warning(self, tr("msg_dir_not_found"), f"{tr('msg_download_dir_not_exist')}:\n{directory}")
            return

        if not open_local_path(directory):
            QMessageBox.critical(self, tr("error"), tr("msg_failed_open_dir"))
