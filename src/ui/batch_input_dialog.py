"""
Batch URL Input Dialog for YT-DLP Studio.

Allows users to add multiple video URLs at once via text input or file import.
"""

import re
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from ..utils.constants import URL_PATTERN
from ..utils.logger import get_logger
from ..utils.translations import tr
from .theme import repolish

logger = get_logger()

# Invalid lines listed under the text field before "... and N more"
MAX_INVALID_SHOWN = 10


def split_urls(text: str) -> tuple[list[str], list[tuple[int, str]]]:
    """
    Split pasted text into valid URLs and invalid lines.

    Args:
        text: One entry per line; empty lines are ignored

    Returns:
        (valid URLs, [(line number, line text)] for the lines that are not URLs)
    """
    pattern = re.compile(URL_PATTERN)
    valid: list[str] = []
    invalid: list[tuple[int, str]] = []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if pattern.match(line):
            valid.append(line)
        else:
            invalid.append((number, line))
    return valid, invalid


class BatchInputDialog(QDialog):
    """
    Dialog for batch URL input.

    Allows users to:
    - Paste multiple URLs (one per line)
    - Import URLs from a text file
    - Validate URLs before adding
    """

    def __init__(self, parent=None):
        """
        Initialize BatchInputDialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.urls = []
        self._setup_ui()
        logger.debug("BatchInputDialog initialized")

    def _setup_ui(self):
        """Setup the dialog UI."""
        self.setWindowTitle(tr("dialog_batch_url_input"))
        self.setMinimumWidth(600)
        self.setMinimumHeight(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        instructions = QLabel(tr("msg_batch_input_instructions"))
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        self.url_text = QTextEdit()
        self.url_text.setAcceptRichText(False)
        self.url_text.setPlaceholderText(
            "https://youtube.com/watch?v=...\nhttps://youtube.com/watch?v=...\nhttps://youtube.com/playlist?list=..."
        )
        layout.addWidget(self.url_text, 1)

        # Live count of valid and invalid lines
        self.count_label = QLabel()
        self.count_label.setProperty("labelStyle", "secondary")
        layout.addWidget(self.count_label)

        # Inline feedback (empty input, invalid lines); hidden when empty
        self.feedback_label = QLabel()
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setProperty("labelStyle", "error")
        self.feedback_label.setVisible(False)
        layout.addWidget(self.feedback_label)

        # Text tools: all secondary, in one row
        tools_layout = QHBoxLayout()
        self.import_btn = QPushButton(tr("button_import_from_file"))
        self.import_btn.clicked.connect(self._import_from_file)
        tools_layout.addWidget(self.import_btn)

        self.validate_btn = QPushButton(tr("button_validate_urls"))
        self.validate_btn.clicked.connect(self._validate_urls)
        tools_layout.addWidget(self.validate_btn)

        self.clear_btn = QPushButton(tr("button_clear"))
        self.clear_btn.clicked.connect(self._clear_urls)
        tools_layout.addWidget(self.clear_btn)
        tools_layout.addStretch()
        layout.addLayout(tools_layout)

        # Dialog buttons
        self.button_box = QDialogButtonBox()
        self.ok_btn = QPushButton(tr("button_add_to_queue"))
        self.ok_btn.setProperty("buttonStyle", "primary")
        self.ok_btn.setDefault(True)
        self.button_box.addButton(self.ok_btn, QDialogButtonBox.ButtonRole.AcceptRole)
        self.cancel_btn = self.button_box.addButton(tr("cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        self.button_box.accepted.connect(self._accept_urls)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self.url_text.textChanged.connect(self._update_count)
        self._update_count()

    def _show_feedback(self, text: str = "", style: str = "error") -> None:
        """Show ``text`` under the field, or hide the feedback line when empty."""
        self.feedback_label.setText(text)
        self.feedback_label.setProperty("labelStyle", style)
        repolish(self.feedback_label)
        self.feedback_label.setVisible(bool(text))

    def _update_count(self):
        """Update the valid/invalid count label."""
        valid, invalid = split_urls(self.url_text.toPlainText())
        self.count_label.setText(tr("label_batch_counts", valid=len(valid), invalid=len(invalid)))
        self.ok_btn.setEnabled(bool(valid))
        if self.feedback_label.isVisible():
            self._show_feedback()

    def _import_from_file(self):
        """Import URLs from a text file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, tr("dialog_import_urls_from_file"), str(Path.home()), "Text Files (*.txt);;All Files (*.*)"
        )

        if file_path:
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()

                # Append to existing text
                current_text = self.url_text.toPlainText().strip()
                if current_text:
                    self.url_text.setPlainText(current_text + "\n" + content)
                else:
                    self.url_text.setPlainText(content)

                logger.info(f"Imported URLs from: {file_path}")

            except Exception as e:
                logger.exception("Error importing file")
                QMessageBox.critical(self, tr("dialog_import_error"), tr("msg_failed_import_file", error=str(e)))

    def _clear_urls(self):
        """Clear all URLs."""
        self.url_text.clear()
        logger.debug("Cleared all URLs")

    def _invalid_lines_text(self, valid: list[str], invalid: list[tuple[int, str]]) -> str:
        lines = [tr("msg_validation_invalid_lines", valid=len(valid), invalid=len(invalid))]
        lines += [tr("text_line_number", line=number, text=text) for number, text in invalid[:MAX_INVALID_SHOWN]]
        if len(invalid) > MAX_INVALID_SHOWN:
            lines.append(tr("text_and_more", count=len(invalid) - MAX_INVALID_SHOWN))
        return "\n".join(lines)

    def _validate_urls(self):
        """Check the entered lines and show the result under the field."""
        valid, invalid = split_urls(self.url_text.toPlainText())
        if not valid and not invalid:
            self._show_feedback(tr("msg_enter_at_least_one_url"))
        elif invalid:
            self._show_feedback(self._invalid_lines_text(valid, invalid))
        else:
            self._show_feedback(tr("msg_all_urls_valid", count=len(valid)), "success")
        logger.info(f"Validation: {len(valid)} valid, {len(invalid)} invalid")

    def _accept_urls(self):
        """Accept and parse URLs."""
        valid, invalid = split_urls(self.url_text.toPlainText())
        if not valid and not invalid:
            self._show_feedback(tr("msg_enter_at_least_one_url"))
            self.url_text.setFocus()
            return

        if not valid:
            self._show_feedback(tr("msg_no_valid_urls_found"))
            return

        if invalid:
            reply = QMessageBox.question(
                self,
                tr("dialog_invalid_urls_found"),
                tr("msg_proceed_with_valid_urls", valid=len(valid), invalid=len(invalid)),
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.No:
                return

        self.urls = valid
        logger.info(f"Accepted {len(self.urls)} URLs for batch download")
        self.accept()

    def get_urls(self) -> list[str]:
        """
        Get the list of validated URLs.

        Returns:
            List of URL strings
        """
        return self.urls
