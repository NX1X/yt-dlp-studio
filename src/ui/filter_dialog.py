"""
Download Filter Dialog for YT-DLP Studio.

Allows users to filter downloads by duration, upload date, and keywords.
"""

from datetime import datetime

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from ..utils.logger import get_logger
from ..utils.translations import tr

logger = get_logger()


class FilterDialog(QDialog):
    """
    Dialog for setting download filters.

    Filters include:
    - Duration (min/max in seconds)
    - Upload date (before/after)
    - Keywords (include/exclude)
    """

    def __init__(self, parent=None):
        """
        Initialize FilterDialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.filters = {}
        self._setup_ui()
        logger.debug("FilterDialog initialized")

    def _setup_ui(self):
        """Setup the dialog UI."""
        self.setWindowTitle(tr("dialog_download_filters"))
        self.setMinimumWidth(500)

        layout = QVBoxLayout()

        # Duration Filter
        duration_group = self._create_duration_filter()
        layout.addWidget(duration_group)

        # Date Filter
        date_group = self._create_date_filter()
        layout.addWidget(date_group)

        # Keyword Filter
        keyword_group = self._create_keyword_filter()
        layout.addWidget(keyword_group)

        # Buttons
        button_layout = QHBoxLayout()

        self.reset_btn = QPushButton(tr("button_reset_filters"))
        self.reset_btn.clicked.connect(self._reset_filters)
        button_layout.addWidget(self.reset_btn)

        button_layout.addStretch()

        self.apply_btn = QPushButton(tr("button_apply_filters"))
        self.apply_btn.clicked.connect(self._apply_filters)
        self.apply_btn.setDefault(True)
        button_layout.addWidget(self.apply_btn)

        self.cancel_btn = QPushButton(tr("cancel"))
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _create_duration_filter(self) -> QGroupBox:
        """
        Create duration filter group.

        Returns:
            QGroupBox with duration controls
        """
        group = QGroupBox(tr("group_duration_filter"))
        layout = QVBoxLayout()

        # Min duration
        min_layout = QHBoxLayout()
        min_label = QLabel(tr("label_min_duration"))
        self.min_duration_spin = QSpinBox()
        self.min_duration_spin.setRange(0, 86400)  # 0 to 24 hours
        self.min_duration_spin.setValue(0)
        self.min_duration_spin.setSuffix(" sec")
        self.min_duration_spin.setSpecialValueText(tr("text_no_minimum"))
        min_layout.addWidget(min_label)
        min_layout.addWidget(self.min_duration_spin)
        layout.addLayout(min_layout)

        # Max duration
        max_layout = QHBoxLayout()
        max_label = QLabel(tr("label_max_duration"))
        self.max_duration_spin = QSpinBox()
        self.max_duration_spin.setRange(0, 86400)  # 0 to 24 hours
        self.max_duration_spin.setValue(0)
        self.max_duration_spin.setSuffix(" sec")
        self.max_duration_spin.setSpecialValueText(tr("text_no_maximum"))
        max_layout.addWidget(max_label)
        max_layout.addWidget(self.max_duration_spin)
        layout.addLayout(max_layout)

        group.setLayout(layout)
        return group

    def _create_date_filter(self) -> QGroupBox:
        """
        Create date filter group.

        Returns:
            QGroupBox with date controls
        """
        group = QGroupBox(tr("group_upload_date_filter"))
        layout = QVBoxLayout()

        # After date
        after_layout = QHBoxLayout()
        after_label = QLabel(tr("label_uploaded_after"))
        self.after_date = QDateEdit()
        self.after_date.setCalendarPopup(True)
        self.after_date.setDate(QDate(2000, 1, 1))
        self.after_date.setDisplayFormat("yyyy-MM-dd")
        after_layout.addWidget(after_label)
        after_layout.addWidget(self.after_date)
        layout.addLayout(after_layout)

        # Before date
        before_layout = QHBoxLayout()
        before_label = QLabel(tr("label_uploaded_before"))
        self.before_date = QDateEdit()
        self.before_date.setCalendarPopup(True)
        self.before_date.setDate(QDate.currentDate())
        self.before_date.setDisplayFormat("yyyy-MM-dd")
        before_layout.addWidget(before_label)
        before_layout.addWidget(self.before_date)
        layout.addLayout(before_layout)

        group.setLayout(layout)
        return group

    def _create_keyword_filter(self) -> QGroupBox:
        """
        Create keyword filter group.

        Returns:
            QGroupBox with keyword controls
        """
        group = QGroupBox(tr("group_keyword_filter"))
        layout = QVBoxLayout()

        # Include keywords
        include_layout = QVBoxLayout()
        include_label = QLabel(tr("label_include_keywords"))
        self.include_keywords = QLineEdit()
        self.include_keywords.setPlaceholderText("e.g., tutorial, python, coding")
        include_layout.addWidget(include_label)
        include_layout.addWidget(self.include_keywords)
        layout.addLayout(include_layout)

        # Exclude keywords
        exclude_layout = QVBoxLayout()
        exclude_label = QLabel(tr("label_exclude_keywords"))
        self.exclude_keywords = QLineEdit()
        self.exclude_keywords.setPlaceholderText("e.g., ads, spam, clickbait")
        exclude_layout.addWidget(exclude_label)
        exclude_layout.addWidget(self.exclude_keywords)
        layout.addLayout(exclude_layout)

        group.setLayout(layout)
        return group

    def _reset_filters(self):
        """Reset all filters to default values."""
        self.min_duration_spin.setValue(0)
        self.max_duration_spin.setValue(0)
        self.after_date.setDate(QDate(2000, 1, 1))
        self.before_date.setDate(QDate.currentDate())
        self.include_keywords.clear()
        self.exclude_keywords.clear()
        logger.debug("Filters reset to defaults")

    def _apply_filters(self):
        """Apply the current filter settings."""
        self.filters = self.get_filters()
        logger.info(f"Filters applied: {self.filters}")
        self.accept()

    def get_filters(self) -> dict:
        """
        Get current filter settings.

        Returns:
            Dictionary with filter settings
        """
        filters = {}

        # Duration filters
        min_duration = self.min_duration_spin.value()
        max_duration = self.max_duration_spin.value()

        if min_duration > 0:
            filters["min_duration"] = min_duration

        if max_duration > 0:
            filters["max_duration"] = max_duration

        # Date filters
        after_date = self.after_date.date().toPython()
        before_date = self.before_date.date().toPython()

        # Only add if not default values
        if after_date > datetime(2000, 1, 1).date():
            filters["after_date"] = after_date.strftime("%Y%m%d")

        if before_date < datetime.now().date():
            filters["before_date"] = before_date.strftime("%Y%m%d")

        # Keyword filters
        include_text = self.include_keywords.text().strip()
        if include_text:
            keywords = [k.strip() for k in include_text.split(",") if k.strip()]
            if keywords:
                filters["include_keywords"] = keywords

        exclude_text = self.exclude_keywords.text().strip()
        if exclude_text:
            keywords = [k.strip() for k in exclude_text.split(",") if k.strip()]
            if keywords:
                filters["exclude_keywords"] = keywords

        return filters

    def set_filters(self, filters: dict):
        """
        Set filter values from dictionary.

        Args:
            filters: Dictionary with filter settings
        """
        # Duration
        if "min_duration" in filters:
            self.min_duration_spin.setValue(filters["min_duration"])

        if "max_duration" in filters:
            self.max_duration_spin.setValue(filters["max_duration"])

        # Date
        if "after_date" in filters:
            date_str = filters["after_date"]
            date = datetime.strptime(date_str, "%Y%m%d").date()
            self.after_date.setDate(QDate(date.year, date.month, date.day))

        if "before_date" in filters:
            date_str = filters["before_date"]
            date = datetime.strptime(date_str, "%Y%m%d").date()
            self.before_date.setDate(QDate(date.year, date.month, date.day))

        # Keywords
        if "include_keywords" in filters:
            keywords = filters["include_keywords"]
            self.include_keywords.setText(", ".join(keywords))

        if "exclude_keywords" in filters:
            keywords = filters["exclude_keywords"]
            self.exclude_keywords.setText(", ".join(keywords))

        logger.debug(f"Filters loaded: {filters}")

    def has_active_filters(self) -> bool:
        """
        Check if any filters are active.

        Returns:
            True if any filters are set
        """
        filters = self.get_filters()
        return len(filters) > 0

    def build_ytdlp_match_filter(self) -> str | None:
        """
        Build yt-dlp match_filter string from current filters.

        Returns:
            match_filter string for yt-dlp, or None if no filters
        """
        filters = self.get_filters()
        if not filters:
            return None

        conditions = []

        # Duration filters
        if "min_duration" in filters:
            conditions.append(f"duration >= {filters['min_duration']}")

        if "max_duration" in filters:
            conditions.append(f"duration <= {filters['max_duration']}")

        # Date filters
        if "after_date" in filters:
            conditions.append(f"upload_date >= '{filters['after_date']}'")

        if "before_date" in filters:
            conditions.append(f"upload_date <= '{filters['before_date']}'")

        # Keyword filters (title matching)
        if "include_keywords" in filters:
            keyword_conditions = " | ".join([f"title ~= '(?i){keyword}'" for keyword in filters["include_keywords"]])
            conditions.append(f"({keyword_conditions})")

        if "exclude_keywords" in filters:
            for keyword in filters["exclude_keywords"]:
                conditions.append(f"title !~= '(?i){keyword}'")

        if conditions:
            match_filter = " & ".join(conditions)
            logger.debug(f"Built match_filter: {match_filter}")
            return match_filter

        return None
