"""
Subtitle selection dialog for YT-DLP Studio.

Allows users to select which subtitle languages to download from available options.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
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

    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Select Subtitle Languages")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Title
        title_label = QLabel("Available Subtitle Languages")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Description
        desc_label = QLabel(
            "Select the subtitle languages you want to download.\nNote: Some languages may be auto-generated."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #888;")
        layout.addWidget(desc_label)

        # Search box
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        search_label.setStyleSheet("color: #aaa;")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type to filter languages...")
        self.search_input.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Subtitle list group
        list_group = QGroupBox("Subtitle Languages")
        list_layout = QVBoxLayout()

        # List widget with checkboxes
        self.subtitle_list = QListWidget()
        self.subtitle_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)

        # Populate list
        if self.available_subtitles:
            for lang_code, lang_info in self.available_subtitles.items():
                # lang_info might be a dict with 'name' or just a string
                if isinstance(lang_info, dict):
                    lang_name = lang_info.get("name", lang_code)
                    is_auto = lang_info.get("auto", False)
                    display_text = f"{lang_name} ({lang_code})" + (" [Auto-generated]" if is_auto else "")
                else:
                    display_text = f"{lang_info} ({lang_code})"

                item = QListWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, lang_code)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.subtitle_list.addItem(item)
        else:
            # No subtitles available
            no_subs_label = QLabel("No subtitles available for this video.")
            no_subs_label.setStyleSheet("color: #888; font-style: italic;")
            no_subs_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            list_layout.addWidget(no_subs_label)

        if self.available_subtitles:
            list_layout.addWidget(self.subtitle_list)

            # Select/Deselect all buttons
            select_buttons_layout = QHBoxLayout()

            select_all_btn = QPushButton("Select All")
            select_all_btn.clicked.connect(self._select_all)
            select_buttons_layout.addWidget(select_all_btn)

            deselect_all_btn = QPushButton("Deselect All")
            deselect_all_btn.clicked.connect(self._deselect_all)
            select_buttons_layout.addWidget(deselect_all_btn)

            select_buttons_layout.addStretch()
            list_layout.addLayout(select_buttons_layout)

        list_group.setLayout(list_layout)
        layout.addWidget(list_group)

        # Dialog buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        ok_btn = QPushButton("Download Selected")
        ok_btn.clicked.connect(self._on_ok_clicked)
        ok_btn.setDefault(True)
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #0e639c;
                color: white;
                border: none;
                border-radius: 4px;
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
        button_layout.addWidget(ok_btn)

        layout.addLayout(button_layout)

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
        # Collect selected language codes
        selected = []
        for i in range(self.subtitle_list.count()):
            item = self.subtitle_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                lang_code = item.data(Qt.ItemDataRole.UserRole)
                selected.append(lang_code)

        if not selected:
            reply = QMessageBox.question(
                self,
                "No Subtitles Selected",
                "You haven't selected any subtitle languages.\n\n"
                "Do you want to continue without downloading subtitles?",
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

        # Show all items if search is empty
        if not search_text:
            for i in range(self.subtitle_list.count()):
                self.subtitle_list.item(i).setHidden(False)
            return

        # Filter items
        for i in range(self.subtitle_list.count()):
            item = self.subtitle_list.item(i)
            item_text = item.text().lower()

            # Show if matches search
            item.setHidden(search_text not in item_text)
