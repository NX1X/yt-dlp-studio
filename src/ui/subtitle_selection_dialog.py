"""
Subtitle selection dialog for YT-DLP Studio.

Allows users to select which subtitle languages to download from available options.
"""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ..utils.logger import get_logger
from ..utils.translations import tr
from .display_format import ltr

logger = get_logger()


class SubtitleSelectionDialog(QDialog):
    """
    Dialog for selecting subtitle languages.

    Displays available subtitle languages and allows user to select which ones to download.
    """

    # Signal emitted when user confirms selection
    subtitles_selected = Signal(list)  # List of selected language codes

    def __init__(self, available_subtitles: dict, parent=None):
        """
        Initialize subtitle selection dialog.

        Args:
            available_subtitles: Dict of {lang_code: language_name} from video info
            parent: Parent widget
        """
        super().__init__(parent)
        self.available_subtitles = available_subtitles or {}
        self.selected_languages = []
        self._setup_ui()
        logger.debug(f"SubtitleSelectionDialog initialized with {len(self.available_subtitles)} languages")

    @staticmethod
    def _item_text(lang_code: str, lang_info) -> str:
        """Row text such as "German (de) - auto-generated", with the name and code kept left-to-right."""
        if isinstance(lang_info, dict):
            name = lang_info.get("name", lang_code)
            is_auto = lang_info.get("auto", False)
        else:
            name, is_auto = lang_info, False
        text = ltr(f"{name} ({lang_code})")
        if is_auto:
            text += f" - {tr('text_auto_generated')}"
        return text

    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle(tr("dialog_select_subtitle_languages"))
        self.setMinimumWidth(480)
        self.setMinimumHeight(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        desc_label = QLabel(tr("text_subtitle_dialog_help"))
        desc_label.setWordWrap(True)
        desc_label.setProperty("labelStyle", "secondary")
        layout.addWidget(desc_label)

        # Subtitle list group
        list_group = QGroupBox(tr("group_subtitle_languages"))
        list_layout = QVBoxLayout(list_group)

        self.subtitle_list = QListWidget()
        # Rows are checked, not selected: the check box is the only state.
        self.subtitle_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        # A click on the row text toggles the row, too. A click on the box
        # itself is toggled by Qt; _changed_in_click stops a second toggle.
        self._changed_in_click: QListWidgetItem | None = None
        self.subtitle_list.itemChanged.connect(self._on_item_changed)
        self.subtitle_list.itemClicked.connect(self._toggle_item)

        if self.available_subtitles:
            search_layout = QHBoxLayout()
            search_label = QLabel(tr("label_search"))
            self.search_input = QLineEdit()
            self.search_input.setPlaceholderText(tr("placeholder_filter_languages"))
            self.search_input.setClearButtonEnabled(True)
            self.search_input.textChanged.connect(self._on_search_changed)
            search_label.setBuddy(self.search_input)
            search_layout.addWidget(search_label)
            search_layout.addWidget(self.search_input)
            list_layout.addLayout(search_layout)

            for lang_code, lang_info in self.available_subtitles.items():
                item = QListWidgetItem(self._item_text(lang_code, lang_info))
                item.setData(Qt.ItemDataRole.UserRole, lang_code)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.subtitle_list.addItem(item)
            list_layout.addWidget(self.subtitle_list)

            select_buttons_layout = QHBoxLayout()
            select_all_btn = QPushButton(tr("button_select_all"))
            select_all_btn.clicked.connect(self._select_all)
            select_buttons_layout.addWidget(select_all_btn)
            deselect_all_btn = QPushButton(tr("button_select_none"))
            deselect_all_btn.clicked.connect(self._deselect_all)
            select_buttons_layout.addWidget(deselect_all_btn)
            select_buttons_layout.addStretch()
            list_layout.addLayout(select_buttons_layout)
        else:
            self.search_input = QLineEdit()  # kept for callers; not shown
            no_subs_label = QLabel(tr("msg_no_subs_available"))
            no_subs_label.setProperty("labelStyle", "secondary")
            no_subs_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_subs_label.setWordWrap(True)
            list_layout.addWidget(no_subs_label)

        layout.addWidget(list_group, 1)

        button_box = QDialogButtonBox()
        ok_btn = QPushButton(tr("button_use_selected_languages"))
        ok_btn.setProperty("buttonStyle", "primary")
        ok_btn.setDefault(True)
        ok_btn.setEnabled(bool(self.available_subtitles))
        button_box.addButton(ok_btn, QDialogButtonBox.ButtonRole.AcceptRole)
        button_box.addButton(tr("cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        button_box.accepted.connect(self._on_ok_clicked)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _on_item_changed(self, item: QListWidgetItem) -> None:
        self._changed_in_click = item
        QTimer.singleShot(0, self._clear_changed_in_click)

    def _clear_changed_in_click(self) -> None:
        self._changed_in_click = None

    def _toggle_item(self, item: QListWidgetItem) -> None:
        """A click on the row text checks or unchecks it."""
        if self._changed_in_click is item:
            return
        checked = item.checkState() == Qt.CheckState.Checked
        item.setCheckState(Qt.CheckState.Unchecked if checked else Qt.CheckState.Checked)

    def _select_all(self):
        """Select all subtitle languages."""
        for i in range(self.subtitle_list.count()):
            item = self.subtitle_list.item(i)
            item.setCheckState(Qt.CheckState.Checked)

    def _deselect_all(self):
        """Deselect all subtitle languages."""
        for i in range(self.subtitle_list.count()):
            item = self.subtitle_list.item(i)
            item.setCheckState(Qt.CheckState.Unchecked)

    def _on_ok_clicked(self):
        """Handle OK button click."""
        selected = []
        for i in range(self.subtitle_list.count()):
            item = self.subtitle_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(item.data(Qt.ItemDataRole.UserRole))

        if not selected:
            reply = QMessageBox.question(
                self,
                tr("dialog_no_subtitles_selected"),
                tr("msg_continue_without_subtitles"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.No:
                return  # Stay in dialog

        self.selected_languages = selected
        logger.info(f"User selected {len(selected)} subtitle languages: {selected}")
        self.subtitles_selected.emit(selected)
        self.accept()

    def get_selected_languages(self) -> list:
        """
        Get list of selected language codes.

        Returns:
            List of language codes (e.g., ['en', 'es', 'fr'])
        """
        return self.selected_languages

    def _on_search_changed(self, text: str):
        """Filter subtitle list based on search text."""
        search_text = text.lower().strip()
        for i in range(self.subtitle_list.count()):
            item = self.subtitle_list.item(i)
            item.setHidden(bool(search_text) and search_text not in item.text().lower())
