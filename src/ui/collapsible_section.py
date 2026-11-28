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

# The arrow is a character in front of the title, not Qt's drawn arrow
# (setArrowType). Qt draws that arrow inside the icon area without making
# room for it, so at Windows display scaling the bold title ran into it.
# Text gets its spacing from the font at every scale. U+00A0 keeps the gap.
ARROW_OPEN = "\u25be"  # small down-pointing triangle
ARROW_CLOSED_LTR = "\u25b8"  # small right-pointing triangle
ARROW_CLOSED_RTL = "\u25c2"  # small left-pointing triangle


def section_header_text(title: str, expanded: bool, right_to_left: bool) -> str:
    """Header text with the open or closed arrow in front of ``title``."""
    if expanded:
        arrow = ARROW_OPEN
    else:
        arrow = ARROW_CLOSED_RTL if right_to_left else ARROW_CLOSED_LTR
    # The arrow is a neutral character, so a leading direction mark puts it
    # at the start of the line: right of the title in Hebrew, left in English.
    mark = "\u200f" if right_to_left else "\u200e"
    return f"{mark}{arrow}\u00a0\u00a0{title}"


class CollapsibleSection(QWidget):
    """Header plus content that the user can fold away."""

    toggled = Signal(bool)  # True when the section opens

    def __init__(self, title: str, parent: QWidget | None = None, expanded: bool = False):
        super().__init__(parent)
        self.setObjectName("collapsibleSection")

        self.header = QToolButton()
        self.header.setObjectName("collapsibleHeader")
        self._title = title
        self.header.setText(title)
        self.header.setCheckable(True)
        self.header.setToolButtonStyle(Qt.ToolButtonTextOnly)
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
        right_to_left = self.layoutDirection() == Qt.RightToLeft
        self.header.setText(section_header_text(self._title, expanded, right_to_left))
        self.content.setVisible(expanded)
        self.summary_label.setVisible(bool(self.summary_label.text()) and not expanded)
