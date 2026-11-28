"""
A section that folds away: a header button with an arrow, a one-line
summary next to it, and the content below.

The header is a checkable ``QToolButton``. Keyboard users open and close it
with Space or Enter, like any button. The arrow points to the reading
direction when the section is closed (right in English, left in Hebrew)
and down when it is open.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QToolButton, QVBoxLayout, QWidget


class CollapsibleSection(QWidget):
    """Header plus content that the user can fold away."""

    toggled = Signal(bool)  # True when the section opens

    def __init__(self, title: str, parent: QWidget | None = None, expanded: bool = False):
        super().__init__(parent)
        self.setObjectName("collapsibleSection")

        self.header = QToolButton()
        self.header.setObjectName("collapsibleHeader")
        self.header.setText(title)
        self.header.setCheckable(True)
        self.header.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.header.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.header.setAccessibleName(title)
        self.header.toggled.connect(self._on_header_toggled)

        self.summary_label = QLabel()
        self.summary_label.setObjectName("collapsibleSummary")
        self.summary_label.setProperty("labelStyle", "secondary")
        self.summary_label.setTextInteractionFlags(Qt.NoTextInteraction)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)
        header_row.addWidget(self.header)
        header_row.addWidget(self.summary_label)
        header_row.addStretch(1)

        self.content = QWidget()
        self.content.setObjectName("collapsibleContent")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(24, 4, 0, 4)
        self.content_layout.setSpacing(8)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addLayout(header_row)
        layout.addWidget(self.content)

        self.header.setChecked(expanded)
        self._apply_state(expanded)

    def is_expanded(self) -> bool:
        """True if the content is shown."""
        return self.header.isChecked()

    def set_expanded(self, expanded: bool) -> None:
        """Open or close the section."""
        self.header.setChecked(expanded)

    def set_summary(self, text: str) -> None:
        """Text next to the header. It shows only while the section is closed."""
        self.summary_label.setText(text)
        self.summary_label.setVisible(bool(text) and not self.is_expanded())

    def set_content_widget(self, widget: QWidget) -> None:
        """Put ``widget`` into the section."""
        self.content_layout.addWidget(widget)

    def changeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().changeEvent(event)
        if event.type() == event.Type.LayoutDirectionChange:
            self._apply_state(self.is_expanded())

    def _on_header_toggled(self, expanded: bool) -> None:
        self._apply_state(expanded)
        self.toggled.emit(expanded)

    def _apply_state(self, expanded: bool) -> None:
        if expanded:
            arrow = Qt.DownArrow
        else:
            arrow = Qt.LeftArrow if self.layoutDirection() == Qt.RightToLeft else Qt.RightArrow
        self.header.setArrowType(arrow)
        self.content.setVisible(expanded)
        self.summary_label.setVisible(bool(self.summary_label.text()) and not expanded)
