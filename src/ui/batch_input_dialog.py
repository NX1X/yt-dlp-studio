"""
Batch URL Input Dialog for YT-DLP Studio.

Allows users to add multiple video URLs at once via text input or file import.
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from ..utils.logger import get_logger
from ..utils.translations import tr

logger = get_logger()


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
        self.setMinimumHeight(400)

        layout = QVBoxLayout()

        # Instructions
        instructions = QLabel(tr("msg_batch_input_instructions"))
        layout.addWidget(instructions)

        # Text area for URLs
        self.url_text = QTextEdit()
        self.url_text.setPlaceholderText(
            "https://youtube.com/watch?v=...\n"
            "https://youtube.com/watch?v=...\n"
            "https://youtube.com/playlist?list=..."
        )
        layout.addWidget(self.url_text)

        # Import from file button
        import_layout = QHBoxLayout()
        self.import_btn = QPushButton(tr("button_import_from_file"))
        self.import_btn.clicked.connect(self._import_from_file)
        import_layout.addWidget(self.import_btn)
        import_layout.addStretch()
        layout.addLayout(import_layout)

        # URL count label
        self.count_label = QLabel(tr("label_urls_count", count=0))
        layout.addWidget(self.count_label)

        # Buttons
        button_layout = QHBoxLayout()

        self.validate_btn = QPushButton(tr("button_validate_urls"))
        self.validate_btn.clicked.connect(self._validate_urls)
        button_layout.addWidget(self.validate_btn)

        self.clear_btn = QPushButton(tr("button_clear"))
        self.clear_btn.clicked.connect(self._clear_urls)
        button_layout.addWidget(self.clear_btn)

        button_layout.addStretch()

        self.ok_btn = QPushButton(tr("button_add_urls"))
        self.ok_btn.clicked.connect(self._accept_urls)
        self.ok_btn.setDefault(True)
        button_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton(tr("cancel"))
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Connect text change to update count
        self.url_text.textChanged.connect(self._update_count)

    def _update_count(self):
        """Update the URL count label."""
        text = self.url_text.toPlainText().strip()
        if not text:
            count = 0
        else:
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            count = len(lines)

        self.count_label.setText(tr("label_urls_count", count=count))

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
                logger.error(f"Error importing file: {e}")
                QMessageBox.critical(self, tr("dialog_import_error"), tr("msg_failed_import_file", error=str(e)))

    def _clear_urls(self):
        """Clear all URLs."""
        self.url_text.clear()
        logger.debug("Cleared all URLs")

    def _validate_urls(self):
        """Validate entered URLs."""
        import re

        from ..utils.constants import URL_PATTERN

        text = self.url_text.toPlainText().strip()
        if not text:
            QMessageBox.information(self, tr("dialog_no_urls"), tr("msg_enter_at_least_one_url"))
            return

        lines = [line.strip() for line in text.split("\n") if line.strip()]
        valid_urls = []
        invalid_lines = []

        pattern = re.compile(URL_PATTERN)

        for i, line in enumerate(lines, 1):
            if pattern.match(line):
                valid_urls.append(line)
            else:
                invalid_lines.append(f"Line {i}: {line}")

        # Show validation results
        if invalid_lines:
            msg = f"Found {len(valid_urls)} valid URLs and {len(invalid_lines)} invalid entries:\n\n"
            msg += "\n".join(invalid_lines[:10])  # Show first 10 invalid
            if len(invalid_lines) > 10:
                msg += f"\n... and {len(invalid_lines) - 10} more"

            QMessageBox.warning(self, tr("dialog_validation_results"), msg)
        else:
            QMessageBox.information(self, tr("dialog_validation_successful"), f"All {len(valid_urls)} URLs are valid!")

        logger.info(f"Validation: {len(valid_urls)} valid, {len(invalid_lines)} invalid")

    def _accept_urls(self):
        """Accept and parse URLs."""
        import re

        from ..utils.constants import URL_PATTERN

        text = self.url_text.toPlainText().strip()
        if not text:
            QMessageBox.information(self, tr("dialog_no_urls"), tr("msg_enter_at_least_one_url"))
            return

        lines = [line.strip() for line in text.split("\n") if line.strip()]
        pattern = re.compile(URL_PATTERN)

        self.urls = [line for line in lines if pattern.match(line)]

        if not self.urls:
            QMessageBox.warning(self, tr("dialog_no_valid_urls"), tr("msg_no_valid_urls_found"))
            return

        invalid_count = len(lines) - len(self.urls)
        if invalid_count > 0:
            reply = QMessageBox.question(
                self,
                tr("dialog_invalid_urls_found"),
                f"Found {len(self.urls)} valid URLs and {invalid_count} invalid entries.\n"
                f"Do you want to proceed with the valid URLs only?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.No:
                return

        logger.info(f"Accepted {len(self.urls)} URLs for batch download")
        self.accept()

    def get_urls(self) -> list[str]:
        """
        Get the list of validated URLs.

        Returns:
            List of URL strings
        """
        return self.urls
