"""
UI theme for YT-DLP Studio.

Dark (default) and light palettes in a VS Code like style with the Microsoft
blue accent, and the Qt style sheet built from them.

Style contract (see the style guide in docs and the review notes):

- Every color comes from ``ModernTheme.COLORS``. Widgets must not set a hex
  color inline; use a ``buttonStyle`` or ``labelStyle`` property instead, or
  ``theme_color(token)`` for colors that Qt cannot take from the style sheet
  (table item foregrounds, rich text).
- ``QPushButton`` without a property is a quiet secondary button.
  ``buttonStyle`` values: ``primary`` (one per view), ``secondary``,
  ``danger`` (secondary look, error colored), ``destructive`` (solid red, only
  for the confirm button of a destructive question), ``success``, ``link``
  (looks like a text link) and ``row`` (small button inside a table row).
- ``labelStyle`` values: ``secondary`` (9pt hint text), ``title``,
  ``subtitle``, ``error``, ``success`` and ``warning``.
- Other hooks: ``QLineEdit[inputState="error"]`` (red border),
  ``QProgressBar[progressState="error"|"success"]``,
  ``QToolButton[sectionHeader="true"]`` (header of a section that opens and
  closes) and ``QWidget#formRow`` (transparent row container).
- After changing one of these properties at run time, call ``repolish()``.
- Spacing scale 4, 8, 12, 16, 24 px. Buttons, line edits, combo boxes and
  spin boxes are 32 px high.
"""

from enum import Enum
from pathlib import Path

from PySide6.QtCore import QDir, QEasingCurve, QObject, QPropertyAnimation, QRect, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QProgressBar, QPushButton, QWidget

from ..utils.logger import get_logger

logger = get_logger()

# PNG arrows and check marks for the style sheet (see
# scripts/generate_theme_icons.py). Style sheets load them through a Qt search
# path, so a folder name with spaces (C:/Program Files/...) needs no quoting.
ICON_DIR = Path(__file__).resolve().parent.parent / "resources" / "icons" / "theme"
_ICON_PREFIX = "themeicons"


class ThemeMode(Enum):
    """Theme mode enumeration."""

    DARK = "dark"
    LIGHT = "light"
    AUTO = "auto"

    @classmethod
    def from_value(cls, value: str | None) -> "ThemeMode":
        """Return the mode for a saved value; anything unknown (and AUTO) is DARK."""
        try:
            mode = cls(value)
        except ValueError:
            return cls.DARK
        return cls.DARK if mode is cls.AUTO else mode


class ModernTheme:
    """Color palettes and the style sheet built from them."""

    # Contrast ratios of the text and border tokens are listed in the PR that
    # added them; keep text at 4.5:1 or more and control borders at 3:1.
    COLORS = {
        "dark": {
            # Backgrounds
            "bg_primary": "#1e1e1e",
            "bg_secondary": "#252526",
            "bg_tertiary": "#2d2d30",
            "bg_input": "#2d2d30",
            "bg_hover": "#37373d",
            # Text
            "text_primary": "#d4d4d4",
            "text_secondary": "#9d9d9d",
            "text_disabled": "#656565",
            "text_on_accent": "#ffffff",
            # Accent (Microsoft blue)
            "accent_primary": "#0078d4",
            "accent_hover": "#106ebe",
            "accent_pressed": "#005a9e",
            "accent_light": "#3b9ff3",
            "accent_text": "#3b9ff3",
            # States
            "success": "#4ec9b0",
            "error": "#f48771",
            "warning": "#dcdcaa",
            "status_running": "#3b9ff3",
            "danger_bg": "#c74440",
            "danger_hover": "#b33a36",
            "success_bg": "#4ec9b0",
            "text_on_success": "#1e1e1e",
            # Borders
            "border": "#3f3f46",
            "border_input": "#7a7a7a",
            "border_focus": "#3b9ff3",
            # Special
            "selection": "#264f78",
            "link": "#3794ff",
            "scrollbar": "#6e6e74",
            "scrollbar_hover": "#8a8a90",
            # Progress bar: one text color must read on the track and the chunk
            "progress_track": "#1e1e1e",
            "progress_chunk": "#0078d4",
            "progress_text": "#ffffff",
            "progress_error": "#c74440",
            "progress_success": "#0e7c66",
            # Activity log
            "log_info": "#569cd6",
        },
        "light": {
            # Backgrounds
            "bg_primary": "#ffffff",
            "bg_secondary": "#f5f5f5",
            "bg_tertiary": "#e8e8e8",
            "bg_input": "#ffffff",
            "bg_hover": "#dcdcdc",
            # Text
            "text_primary": "#1f1f1f",
            "text_secondary": "#616161",
            "text_disabled": "#a0a0a0",
            "text_on_accent": "#ffffff",
            # Accent
            "accent_primary": "#0078d4",
            "accent_hover": "#106ebe",
            "accent_pressed": "#005a9e",
            "accent_light": "#50a0ff",
            "accent_text": "#005a9e",
            # States
            "success": "#047857",
            "error": "#c42b1c",
            "warning": "#b45309",
            "status_running": "#0078d4",
            "danger_bg": "#c42b1c",
            "danger_hover": "#a82416",
            "success_bg": "#0e7c66",
            "text_on_success": "#ffffff",
            # Borders
            "border": "#d0d0d0",
            "border_input": "#8a8a8a",
            "border_focus": "#005a9e",
            # Special
            "selection": "#cce8ff",
            "link": "#005a9e",
            "scrollbar": "#8a8a8a",
            "scrollbar_hover": "#6e6e6e",
            # Progress bar
            "progress_track": "#ffffff",
            "progress_chunk": "#3a8ee0",
            "progress_text": "#1f1f1f",
            "progress_error": "#e0604f",
            "progress_success": "#1f9a7f",
            # Activity log
            "log_info": "#005a9e",
        },
    }

    @staticmethod
    def colors(mode: ThemeMode = ThemeMode.DARK) -> dict[str, str]:
        """Return the color tokens of a mode (AUTO uses the dark palette)."""
        return ModernTheme.COLORS["light" if mode == ThemeMode.LIGHT else "dark"]

    @staticmethod
    def palette(mode: ThemeMode = ThemeMode.DARK) -> QPalette:
        """
        Build the QPalette for a mode.

        The style sheet does not cover everything: rich text links, the
        placeholder text of input fields and some native parts take their
        colors from the palette.
        """
        c = ModernTheme.colors(mode)
        palette = QPalette()
        roles = {
            QPalette.ColorRole.Window: c["bg_primary"],
            QPalette.ColorRole.WindowText: c["text_primary"],
            QPalette.ColorRole.Base: c["bg_input"],
            QPalette.ColorRole.AlternateBase: c["bg_secondary"],
            QPalette.ColorRole.Text: c["text_primary"],
            QPalette.ColorRole.Button: c["bg_tertiary"],
            QPalette.ColorRole.ButtonText: c["text_primary"],
            QPalette.ColorRole.Highlight: c["accent_primary"],
            QPalette.ColorRole.HighlightedText: c["text_on_accent"],
            QPalette.ColorRole.ToolTipBase: c["bg_tertiary"],
            QPalette.ColorRole.ToolTipText: c["text_primary"],
            QPalette.ColorRole.Link: c["link"],
            QPalette.ColorRole.LinkVisited: c["link"],
            QPalette.ColorRole.PlaceholderText: c["text_secondary"],
            QPalette.ColorRole.Mid: c["border"],
        }
        for role, color in roles.items():
            palette.setColor(role, QColor(color))
        for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText, QPalette.ColorRole.ButtonText):
            palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(c["text_disabled"]))
        return palette

    @staticmethod
    def get_stylesheet(mode: ThemeMode = ThemeMode.DARK) -> str:
        """
        Get complete stylesheet for the application.

        Args:
            mode: Theme mode (DARK or LIGHT)

        Returns:
            Complete Qt style sheet
        """
        theme_name = "light" if mode == ThemeMode.LIGHT else "dark"
        c = ModernTheme.COLORS[theme_name]
        _register_icon_path()

        def icon(name: str) -> str:
            return f"url({_ICON_PREFIX}:{name}.png)"

        down = icon(f"chevron-down-{theme_name}")
        up = icon(f"chevron-up-{theme_name}")
        down_off = icon(f"chevron-down-{theme_name}-disabled")
        up_off = icon(f"chevron-up-{theme_name}-disabled")
        check = icon(f"check-{theme_name}")

        return f"""
/* ===== GLOBAL ===== */
QMainWindow, QWidget {{
    background-color: {c["bg_primary"]};
    color: {c["text_primary"]};
    font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10pt;
}}

QScrollArea, QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

/* Plain container widgets that group controls in one row of a form */
QWidget#formRow {{
    background: transparent;
}}

/* ===== BUTTONS (plain QPushButton = secondary) ===== */
QPushButton {{
    background-color: {c["bg_tertiary"]};
    color: {c["text_primary"]};
    border: 1px solid {c["border_input"]};
    border-radius: 4px;
    padding: 5px 16px;
    min-height: 20px;
    font-size: 10pt;
}}

QPushButton:hover {{
    background-color: {c["bg_hover"]};
}}

QPushButton:pressed {{
    background-color: {c["border"]};
}}

QPushButton:focus {{
    border-color: {c["border_focus"]};
}}

QPushButton:disabled {{
    background-color: {c["bg_secondary"]};
    color: {c["text_disabled"]};
    border-color: {c["border"]};
}}

QPushButton:checked {{
    background-color: {c["bg_hover"]};
    border-color: {c["border_focus"]};
}}

QPushButton[buttonStyle="primary"] {{
    background-color: {c["accent_primary"]};
    color: {c["text_on_accent"]};
    border: 1px solid {c["accent_primary"]};
    font-weight: 600;
}}

QPushButton[buttonStyle="primary"]:hover {{
    background-color: {c["accent_hover"]};
    border-color: {c["accent_hover"]};
}}

QPushButton[buttonStyle="primary"]:pressed {{
    background-color: {c["accent_pressed"]};
}}

QPushButton[buttonStyle="primary"]:focus {{
    border-color: {c["text_primary"]};
}}

QPushButton[buttonStyle="primary"]:disabled {{
    background-color: {c["bg_secondary"]};
    color: {c["text_disabled"]};
    border-color: {c["border"]};
}}

QPushButton[buttonStyle="danger"] {{
    color: {c["error"]};
    border-color: {c["error"]};
}}

QPushButton[buttonStyle="danger"]:disabled {{
    color: {c["text_disabled"]};
    border-color: {c["border"]};
}}

QPushButton[buttonStyle="destructive"] {{
    background-color: {c["danger_bg"]};
    color: #ffffff;
    border: 1px solid {c["danger_bg"]};
    font-weight: 600;
}}

QPushButton[buttonStyle="destructive"]:hover {{
    background-color: {c["danger_hover"]};
}}

QPushButton[buttonStyle="success"] {{
    background-color: {c["success_bg"]};
    color: {c["text_on_success"]};
    border: 1px solid {c["success_bg"]};
    font-weight: 600;
}}

QPushButton[buttonStyle="link"] {{
    background: transparent;
    border: none;
    color: {c["link"]};
    padding: 2px 4px;
    min-height: 0px;
}}

QPushButton[buttonStyle="link"]:hover, QPushButton[buttonStyle="link"]:focus {{
    text-decoration: underline;
}}

QPushButton[buttonStyle="row"] {{
    padding: 2px 8px;
    min-height: 0px;
}}

QToolButton {{
    background: transparent;
    color: {c["text_primary"]};
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 4px 6px;
}}

QToolButton:hover {{
    background-color: {c["bg_hover"]};
}}

QToolButton:focus {{
    border-color: {c["border_focus"]};
}}

/* Header of a section that opens and closes (arrow plus title) */
QToolButton[sectionHeader="true"] {{
    font-weight: 600;
    padding: 4px 4px;
}}

/* ===== TABS ===== */
QTabWidget::pane {{
    border: 1px solid {c["border"]};
    border-radius: 6px;
    background-color: {c["bg_primary"]};
    padding: 4px;
}}

QTabBar::tab {{
    background-color: {c["bg_secondary"]};
    color: {c["text_secondary"]};
    border: none;
    border-bottom: 3px solid transparent;
    padding: 10px 22px;
    margin-right: 4px;
    font-size: 10pt;
    font-weight: 500;
}}

QTabBar::tab:hover {{
    background-color: {c["bg_hover"]};
    color: {c["text_primary"]};
}}

QTabBar::tab:selected {{
    background-color: {c["bg_primary"]};
    color: {c["accent_text"]};
    border-bottom: 3px solid {c["accent_primary"]};
}}

/* ===== GROUP BOXES (cards) ===== */
QGroupBox {{
    background-color: {c["bg_secondary"]};
    border: 1px solid {c["border"]};
    border-radius: 8px;
    margin-top: 14px;
    padding: 14px 8px 8px 8px;
    font-weight: 600;
    font-size: 11pt;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    top: 4px;
    padding: 0 6px;
    background-color: {c["bg_secondary"]};
    color: {c["text_primary"]};
}}

/* ===== INPUT FIELDS ===== */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {c["bg_input"]};
    color: {c["text_primary"]};
    border: 1px solid {c["border_input"]};
    border-radius: 4px;
    padding: 5px 10px;
    selection-background-color: {c["selection"]};
    selection-color: {c["text_primary"]};
    font-size: 10pt;
    font-weight: normal;
}}

QLineEdit, QSpinBox, QDoubleSpinBox {{
    min-height: 20px;
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {c["border_focus"]};
    background-color: {c["bg_primary"]};
}}

QLineEdit:read-only {{
    background-color: {c["bg_secondary"]};
}}

QLineEdit:disabled, QTextEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
    background-color: {c["bg_secondary"]};
    color: {c["text_disabled"]};
    border-color: {c["border"]};
}}

QLineEdit[inputState="error"] {{
    border-color: {c["error"]};
}}

QTextEdit#activityLog {{
    font-family: 'Cascadia Mono', 'Consolas', 'DejaVu Sans Mono', 'Courier New', monospace;
    background-color: {c["bg_primary"]};
}}

/* ===== COMBO BOX ===== */
QComboBox {{
    background-color: {c["bg_input"]};
    color: {c["text_primary"]};
    border: 1px solid {c["border_input"]};
    border-radius: 4px;
    padding: 5px 10px;
    min-height: 20px;
    font-weight: normal;
}}

QComboBox:hover {{
    background-color: {c["bg_hover"]};
}}

QComboBox:focus, QComboBox:on {{
    border-color: {c["border_focus"]};
}}

QComboBox:disabled {{
    background-color: {c["bg_secondary"]};
    color: {c["text_disabled"]};
    border-color: {c["border"]};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 22px;
    border: none;
    background: transparent;
}}

QComboBox::down-arrow {{
    image: {down};
    width: 10px;
    height: 10px;
}}

QComboBox::down-arrow:disabled {{
    image: {down_off};
}}

QComboBox QAbstractItemView {{
    background-color: {c["bg_secondary"]};
    color: {c["text_primary"]};
    border: 1px solid {c["border_input"]};
    selection-background-color: {c["accent_primary"]};
    selection-color: {c["text_on_accent"]};
    outline: none;
}}

/* ===== SPIN BOX ===== */
QSpinBox, QDoubleSpinBox {{
    padding-right: 22px;
}}

QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    width: 20px;
    border: none;
    background: transparent;
}}

QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-position: top right;
}}

QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-position: bottom right;
}}

QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {c["bg_hover"]};
}}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: {up};
    width: 10px;
    height: 10px;
}}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: {down};
    width: 10px;
    height: 10px;
}}

QSpinBox::up-arrow:disabled, QSpinBox::up-arrow:off,
QDoubleSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:off {{
    image: {up_off};
}}

QSpinBox::down-arrow:disabled, QSpinBox::down-arrow:off,
QDoubleSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:off {{
    image: {down_off};
}}

/* ===== PROGRESS BAR ===== */
QProgressBar {{
    border: 1px solid {c["border_input"]};
    border-radius: 4px;
    text-align: center;
    background-color: {c["progress_track"]};
    color: {c["progress_text"]};
    font-weight: 600;
    min-height: 20px;
}}

QProgressBar::chunk {{
    background-color: {c["progress_chunk"]};
    border-radius: 3px;
}}

QProgressBar[progressState="error"]::chunk {{
    background-color: {c["progress_error"]};
}}

QProgressBar[progressState="success"]::chunk {{
    background-color: {c["progress_success"]};
}}

/* ===== TABLES AND LISTS ===== */
QTableView, QListView, QTreeView {{
    background-color: {c["bg_primary"]};
    alternate-background-color: {c["bg_secondary"]};
    color: {c["text_primary"]};
    border: 1px solid {c["border"]};
    border-radius: 6px;
    gridline-color: {c["border"]};
    selection-background-color: {c["accent_primary"]};
    selection-color: {c["text_on_accent"]};
}}

QTableView::item {{
    padding: 4px 8px;
}}

QListView::item {{
    padding: 4px 6px;
}}

QTableView::item:hover, QListView::item:hover {{
    background-color: {c["bg_hover"]};
}}

QTableView::item:selected, QListView::item:selected {{
    background-color: {c["accent_primary"]};
    color: {c["text_on_accent"]};
}}

QHeaderView::section {{
    background-color: {c["bg_secondary"]};
    color: {c["text_primary"]};
    padding: 6px 8px;
    border: none;
    border-bottom: 1px solid {c["border_input"]};
    font-weight: 600;
}}

QTableCornerButton::section {{
    background-color: {c["bg_secondary"]};
    border: none;
}}

/* ===== CHECKBOXES ===== */
QCheckBox, QRadioButton {{
    spacing: 8px;
    color: {c["text_primary"]};
    background: transparent;
}}

QCheckBox:disabled, QRadioButton:disabled {{
    color: {c["text_disabled"]};
}}

QCheckBox::indicator, QAbstractItemView::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid {c["border_input"]};
    background-color: {c["bg_input"]};
}}

QCheckBox::indicator:hover, QAbstractItemView::indicator:hover {{
    border-color: {c["border_focus"]};
}}

QCheckBox:focus {{
    outline: none;
}}

QCheckBox::indicator:checked, QAbstractItemView::indicator:checked {{
    background-color: {c["accent_primary"]};
    border-color: {c["accent_primary"]};
    image: {check};
}}

QCheckBox::indicator:disabled, QAbstractItemView::indicator:disabled {{
    background-color: {c["bg_secondary"]};
    border-color: {c["border"]};
}}

QCheckBox::indicator:checked:disabled {{
    background-color: {c["text_disabled"]};
    border-color: {c["text_disabled"]};
}}

/* ===== SCROLL BARS ===== */
QScrollBar:vertical {{
    background-color: transparent;
    width: 12px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background-color: {c["scrollbar"]};
    min-height: 30px;
    border-radius: 4px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {c["scrollbar_hover"]};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    height: 0px;
    background: none;
}}

QScrollBar:horizontal {{
    background-color: transparent;
    height: 12px;
    margin: 0px;
}}

QScrollBar::handle:horizontal {{
    background-color: {c["scrollbar"]};
    min-width: 30px;
    border-radius: 4px;
    margin: 2px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {c["scrollbar_hover"]};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    width: 0px;
    background: none;
}}

/* ===== MENUS ===== */
QMenuBar {{
    background-color: {c["bg_secondary"]};
    color: {c["text_primary"]};
    border-bottom: 1px solid {c["border"]};
    padding: 4px;
}}

QMenuBar::item {{
    padding: 6px 12px;
    border-radius: 4px;
}}

QMenuBar::item:selected {{
    background-color: {c["bg_hover"]};
}}

QMenu {{
    background-color: {c["bg_secondary"]};
    border: 1px solid {c["border_input"]};
    border-radius: 6px;
    padding: 4px;
}}

QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {c["accent_primary"]};
    color: {c["text_on_accent"]};
}}

QMenu::item:disabled {{
    color: {c["text_disabled"]};
}}

QMenu::separator {{
    height: 1px;
    background-color: {c["border"]};
    margin: 4px 8px;
}}

/* ===== STATUS BAR ===== */
QStatusBar {{
    background-color: {c["bg_secondary"]};
    color: {c["text_primary"]};
    border-top: 1px solid {c["border"]};
}}

QStatusBar QLabel {{
    color: {c["text_primary"]};
}}

/* ===== LABELS ===== */
QLabel {{
    color: {c["text_primary"]};
    background: transparent;
}}

QLabel[labelStyle="secondary"] {{
    color: {c["text_secondary"]};
    font-size: 9pt;
}}

QLabel[labelStyle="title"] {{
    font-size: 14pt;
    font-weight: 600;
    color: {c["text_primary"]};
}}

QLabel[labelStyle="subtitle"] {{
    font-size: 11pt;
    font-weight: 500;
    color: {c["text_secondary"]};
}}

QLabel[labelStyle="error"] {{
    color: {c["error"]};
}}

QLabel[labelStyle="success"] {{
    color: {c["success"]};
}}

QLabel[labelStyle="warning"] {{
    color: {c["warning"]};
}}

QLabel#aboutTitle {{
    font-size: 20pt;
    font-weight: 700;
}}

/* Site tier next to the URL field (src/ui/site_tier_label.py) */
QLabel#siteTierLabel {{
    font-size: 9pt;
    font-weight: 600;
    padding: 0px 4px;
}}

QLabel#siteTierLabel[siteTier="tested"] {{
    color: {c["success"]};
}}

QLabel#siteTierLabel[siteTier="experimental"] {{
    color: {c["warning"]};
}}

/* ===== TOOLTIPS ===== */
QToolTip {{
    background-color: {c["bg_tertiary"]};
    color: {c["text_primary"]};
    border: 1px solid {c["border_input"]};
    border-radius: 4px;
    padding: 6px 8px;
    font-size: 9pt;
}}

/* ===== DIALOGS ===== */
QDialog, QMessageBox {{
    background-color: {c["bg_primary"]};
}}

QMessageBox QLabel {{
    font-weight: normal;
}}

/* Bar with the Save and Reset buttons under the Settings tab */
QFrame#settingsButtonBar {{
    background-color: {c["bg_secondary"]};
    border-top: 1px solid {c["border"]};
}}

/* ===== TEXT BROWSER ===== */
QTextBrowser {{
    background-color: {c["bg_secondary"]};
    border: 1px solid {c["border"]};
    border-radius: 4px;
    padding: 8px;
}}
"""

    @staticmethod
    def animate_button_click(button: QPushButton):
        """
        Add smooth click animation to button.

        Args:
            button: Button to animate
        """
        try:
            # Create scale-down animation
            original_geometry = button.geometry()
            shrunk_geometry = QRect(
                original_geometry.x() + 2,
                original_geometry.y() + 2,
                original_geometry.width() - 4,
                original_geometry.height() - 4,
            )

            # Animate down
            anim_down = QPropertyAnimation(button, b"geometry")
            anim_down.setDuration(50)
            anim_down.setStartValue(original_geometry)
            anim_down.setEndValue(shrunk_geometry)
            anim_down.setEasingCurve(QEasingCurve.OutCubic)

            # Animate back up
            anim_up = QPropertyAnimation(button, b"geometry")
            anim_up.setDuration(50)
            anim_up.setStartValue(shrunk_geometry)
            anim_up.setEndValue(original_geometry)
            anim_up.setEasingCurve(QEasingCurve.OutCubic)

            # Connect animations
            anim_down.finished.connect(anim_up.start)
            anim_down.start()

        except Exception as e:
            logger.debug(f"Button animation error: {e}")

    @staticmethod
    def animate_progress(progress_bar: QProgressBar, start_value: int, end_value: int):
        """
        Animate progress bar smoothly.

        Args:
            progress_bar: Progress bar to animate
            start_value: Starting value
            end_value: Ending value
        """
        try:
            animation = QPropertyAnimation(progress_bar, b"value")
            animation.setDuration(300)
            animation.setStartValue(start_value)
            animation.setEndValue(end_value)
            animation.setEasingCurve(QEasingCurve.InOutCubic)
            animation.start()
        except Exception as e:
            logger.debug(f"Progress animation error: {e}")

    @staticmethod
    def set_widget_fade_in(widget: QWidget, duration: int = 300):
        """
        Fade in widget smoothly.

        Args:
            widget: Widget to fade in
            duration: Animation duration in ms
        """
        try:
            # Note: QPropertyAnimation for opacity requires QGraphicsOpacityEffect
            # which can cause rendering issues, so we'll use simple show()
            # More complex implementation would use QGraphicsOpacityEffect
            widget.show()
        except Exception as e:
            logger.debug(f"Fade in error: {e}")


def _register_icon_path() -> None:
    """Let style sheets find the theme icons as ``themeicons:<name>.png``."""
    if str(ICON_DIR) not in QDir.searchPaths(_ICON_PREFIX):
        QDir.addSearchPath(_ICON_PREFIX, str(ICON_DIR))


def repolish(widget: QWidget) -> None:
    """Apply the style sheet again after a style property of ``widget`` changed."""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


class ThemeManager(QObject):
    """
    Manages the application theme.

    ``apply_theme`` sets the style sheet and the palette on the whole
    application (so dialogs without a parent get the theme, too) and emits
    ``theme_changed`` for widgets that draw colors in rich text.
    """

    # Emitted with the new mode value ("dark" or "light") after apply_theme.
    theme_changed = Signal(str)

    def __init__(self):
        """Initialize theme manager."""
        super().__init__()
        self.current_mode = ThemeMode.DARK
        logger.info(f"ThemeManager initialized with mode: {self.current_mode.value}")

    def set_theme(self, mode: ThemeMode) -> str:
        """
        Set the current mode and return its style sheet (does not apply it).

        Args:
            mode: Theme mode

        Returns:
            Stylesheet string
        """
        self.current_mode = ThemeMode.from_value(mode.value)
        stylesheet = ModernTheme.get_stylesheet(self.current_mode)
        logger.info(f"Theme set to: {self.current_mode.value}")
        return stylesheet

    def apply_theme(self, mode: ThemeMode) -> str:
        """
        Set the mode and apply it to the running application.

        Args:
            mode: Theme mode

        Returns:
            The style sheet that was applied
        """
        stylesheet = self.set_theme(mode)
        app = QApplication.instance()
        if app is not None:
            app.setPalette(ModernTheme.palette(self.current_mode))
            app.setStyleSheet(stylesheet)
        self.theme_changed.emit(self.current_mode.value)
        return stylesheet

    def get_current_mode(self) -> ThemeMode:
        """Get current theme mode."""
        return self.current_mode

    def colors(self) -> dict[str, str]:
        """Return the color tokens of the current mode."""
        return ModernTheme.colors(self.current_mode)

    def toggle_theme(self) -> str:
        """
        Switch between dark and light and apply the new mode.

        Returns:
            New stylesheet
        """
        new_mode = ThemeMode.LIGHT if self.current_mode == ThemeMode.DARK else ThemeMode.DARK
        return self.apply_theme(new_mode)


# Global theme manager instance
_theme_manager = None


def get_theme_manager() -> ThemeManager:
    """
    Get global ThemeManager instance.

    Returns:
        ThemeManager instance
    """
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager


def theme_color(token: str) -> str:
    """
    Return a color token of the current theme as a hex string.

    Use it where the style sheet cannot reach: table item foregrounds
    (``QColor(theme_color("success"))``) and inline rich text.
    """
    return get_theme_manager().colors()[token]
