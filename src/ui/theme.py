"""
Modern UI Theme System for YT-DLP Studio.

Provides beautiful Fluent Design inspired themes with Dark/Light modes,
smooth animations, and modern styling for both consumers and tech users.
"""

from enum import Enum

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect
from PySide6.QtWidgets import QProgressBar, QPushButton, QWidget

from ..utils.logger import get_logger

logger = get_logger()


class ThemeMode(Enum):
    """Theme mode enumeration."""

    DARK = "dark"
    LIGHT = "light"
    AUTO = "auto"


class ModernTheme:
    """
    Modern theme manager with Fluent Design inspiration.

    Features:
    - Dark and Light modes
    - Beautiful color schemes
    - Smooth animations
    - Professional gradients
    - Rounded corners
    - Modern shadows
    """

    # Color Palettes
    COLORS = {
        "dark": {
            # Background colors
            "bg_primary": "#1e1e1e",  # VS Code dark
            "bg_secondary": "#252526",
            "bg_tertiary": "#2d2d30",
            "bg_hover": "#323233",
            # Text colors
            "text_primary": "#d4d4d4",
            "text_secondary": "#9d9d9d",
            "text_disabled": "#656565",
            # Accent colors (Microsoft Blue)
            "accent_primary": "#0078d4",
            "accent_hover": "#106ebe",
            "accent_pressed": "#005a9e",
            "accent_light": "#3b9ff3",
            # Success/Error/Warning
            "success": "#4ec9b0",
            "error": "#f48771",
            "warning": "#dcdcaa",
            # Border colors
            "border": "#3f3f46",
            "border_focus": "#0078d4",
            # Special colors
            "selection": "#264f78",
            "link": "#3794ff",
        },
        "light": {
            # Background colors
            "bg_primary": "#ffffff",
            "bg_secondary": "#f5f5f5",
            "bg_tertiary": "#e8e8e8",
            "bg_hover": "#e5e5e5",
            # Text colors
            "text_primary": "#1f1f1f",
            "text_secondary": "#616161",
            "text_disabled": "#a0a0a0",
            # Accent colors
            "accent_primary": "#0078d4",
            "accent_hover": "#106ebe",
            "accent_pressed": "#005a9e",
            "accent_light": "#50a0ff",
            # Success/Error/Warning
            "success": "#10b981",
            "error": "#ef4444",
            "warning": "#f59e0b",
            # Border colors
            "border": "#d0d0d0",
            "border_focus": "#0078d4",
            # Special colors
            "selection": "#cce8ff",
            "link": "#0078d4",
        },
    }

    @staticmethod
    def get_stylesheet(mode: ThemeMode = ThemeMode.DARK) -> str:
        """
        Get complete stylesheet for the application.

        Args:
            mode: Theme mode (DARK or LIGHT)

        Returns:
            Complete CSS stylesheet
        """
        theme_name = mode.value if mode != ThemeMode.AUTO else "dark"
        colors = ModernTheme.COLORS[theme_name]

        return f"""
/* ===== GLOBAL STYLES ===== */
QMainWindow, QWidget {{
    background-color: {colors["bg_primary"]};
    color: {colors["text_primary"]};
    font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10pt;
}}

/* ===== BUTTONS ===== */
QPushButton {{
    background-color: {colors["accent_primary"]};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    min-height: 36px;
    font-weight: 500;
    font-size: 10pt;
}}

QPushButton:hover {{
    background-color: {colors["accent_hover"]};
}}

QPushButton:pressed {{
    background-color: {colors["accent_pressed"]};
}}

QPushButton:disabled {{
    background-color: {colors["bg_tertiary"]};
    color: {colors["text_disabled"]};
}}

/* Secondary buttons */
QPushButton[buttonStyle="secondary"] {{
    background-color: {colors["bg_tertiary"]};
    color: {colors["text_primary"]};
    border: 1px solid {colors["border"]};
}}

QPushButton[buttonStyle="secondary"]:hover {{
    background-color: {colors["bg_hover"]};
    border-color: {colors["accent_primary"]};
}}

/* Danger buttons */
QPushButton[buttonStyle="danger"] {{
    background-color: {colors["error"]};
}}

QPushButton[buttonStyle="danger"]:hover {{
    background-color: #d63a3a;
}}

/* Success buttons */
QPushButton[buttonStyle="success"] {{
    background-color: {colors["success"]};
}}

QPushButton[buttonStyle="success"]:hover {{
    background-color: #3ba68b;
}}

/* ===== TABS ===== */
QTabWidget::pane {{
    border: 1px solid {colors["border"]};
    border-radius: 8px;
    background-color: {colors["bg_primary"]};
    padding: 8px;
}}

QTabBar::tab {{
    background-color: {colors["bg_secondary"]};
    color: {colors["text_secondary"]};
    border: none;
    border-bottom: 3px solid transparent;
    padding: 12px 24px;
    margin-right: 4px;
    font-size: 10pt;
    font-weight: 500;
}}

QTabBar::tab:hover {{
    background-color: {colors["bg_hover"]};
    color: {colors["text_primary"]};
}}

QTabBar::tab:selected {{
    background-color: {colors["bg_primary"]};
    color: {colors["accent_primary"]};
    border-bottom: 3px solid {colors["accent_primary"]};
}}

/* ===== GROUP BOXES (Cards) ===== */
QGroupBox {{
    background-color: {colors["bg_secondary"]};
    border: 1px solid {colors["border"]};
    border-radius: 12px;
    margin-top: 16px;
    padding: 20px;
    font-weight: 600;
    font-size: 11pt;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 16px;
    top: 8px;
    padding: 0 8px;
    background-color: {colors["bg_secondary"]};
    color: {colors["text_primary"]};
}}

/* ===== INPUT FIELDS ===== */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox {{
    background-color: {colors["bg_tertiary"]};
    color: {colors["text_primary"]};
    border: 2px solid {colors["border"]};
    border-radius: 6px;
    padding: 8px 12px;
    selection-background-color: {colors["selection"]};
    font-size: 10pt;
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus {{
    border-color: {colors["border_focus"]};
    background-color: {colors["bg_primary"]};
}}

QLineEdit:disabled, QTextEdit:disabled, QSpinBox:disabled {{
    background-color: {colors["bg_secondary"]};
    color: {colors["text_disabled"]};
}}

/* ===== COMBO BOX ===== */
QComboBox {{
    background-color: {colors["bg_tertiary"]};
    color: {colors["text_primary"]};
    border: 2px solid {colors["border"]};
    border-radius: 6px;
    padding: 8px 12px;
    min-height: 32px;
}}

QComboBox:hover {{
    border-color: {colors["accent_primary"]};
}}

QComboBox:focus {{
    border-color: {colors["border_focus"]};
}}

QComboBox::drop-down {{
    border: none;
    padding-right: 12px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid {colors["text_secondary"]};
    margin-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {colors["bg_secondary"]};
    border: 1px solid {colors["border"]};
    border-radius: 6px;
    selection-background-color: {colors["accent_primary"]};
    outline: none;
}}

/* ===== PROGRESS BAR ===== */
QProgressBar {{
    border: none;
    border-radius: 6px;
    text-align: center;
    background-color: {colors["bg_tertiary"]};
    color: {colors["text_primary"]};
    font-weight: 600;
    min-height: 28px;
}}

QProgressBar::chunk {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                      stop:0 {colors["accent_primary"]},
                                      stop:1 {colors["accent_light"]});
    border-radius: 5px;
}}

/* ===== TABLES ===== */
QTableWidget {{
    background-color: {colors["bg_primary"]};
    alternate-background-color: {colors["bg_secondary"]};
    border: 1px solid {colors["border"]};
    border-radius: 8px;
    gridline-color: {colors["border"]};
    selection-background-color: {colors["selection"]};
}}

QTableWidget::item {{
    padding: 8px;
}}

QTableWidget::item:hover {{
    background-color: {colors["bg_hover"]};
}}

QTableWidget::item:selected {{
    background-color: {colors["accent_primary"]};
    color: white;
}}

QHeaderView::section {{
    background-color: {colors["bg_secondary"]};
    color: {colors["text_primary"]};
    padding: 10px;
    border: none;
    border-bottom: 2px solid {colors["border"]};
    font-weight: 600;
}}

/* ===== CHECKBOXES ===== */
QCheckBox {{
    spacing: 8px;
    color: {colors["text_primary"]};
}}

QCheckBox::indicator {{
    width: 20px;
    height: 20px;
    border-radius: 4px;
    border: 2px solid {colors["border"]};
    background-color: {colors["bg_tertiary"]};
}}

QCheckBox::indicator:hover {{
    border-color: {colors["accent_primary"]};
}}

QCheckBox::indicator:checked {{
    background-color: {colors["accent_primary"]};
    border-color: {colors["accent_primary"]};
    /* Note: Qt doesn't support ::after or content property */
    /* The checkmark is rendered by Qt itself */
}}

/* ===== SCROLL BARS ===== */
QScrollBar:vertical {{
    background-color: {colors["bg_secondary"]};
    width: 14px;
    margin: 0px;
    border-radius: 7px;
}}

QScrollBar::handle:vertical {{
    background-color: {colors["bg_tertiary"]};
    min-height: 30px;
    border-radius: 7px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {colors["border"]};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background-color: {colors["bg_secondary"]};
    height: 14px;
    margin: 0px;
    border-radius: 7px;
}}

QScrollBar::handle:horizontal {{
    background-color: {colors["bg_tertiary"]};
    min-width: 30px;
    border-radius: 7px;
    margin: 2px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {colors["border"]};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* ===== MENU BAR ===== */
QMenuBar {{
    background-color: {colors["bg_secondary"]};
    color: {colors["text_primary"]};
    border-bottom: 1px solid {colors["border"]};
    padding: 4px;
}}

QMenuBar::item {{
    padding: 8px 16px;
    border-radius: 4px;
}}

QMenuBar::item:selected {{
    background-color: {colors["bg_hover"]};
}}

QMenu {{
    background-color: {colors["bg_secondary"]};
    border: 1px solid {colors["border"]};
    border-radius: 8px;
    padding: 8px;
}}

QMenu::item {{
    padding: 8px 32px 8px 16px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {colors["accent_primary"]};
    color: white;
}}

/* ===== STATUS BAR ===== */
QStatusBar {{
    background-color: {colors["bg_secondary"]};
    color: {colors["text_secondary"]};
    border-top: 1px solid {colors["border"]};
    padding: 4px;
}}

/* ===== LABELS ===== */
QLabel {{
    color: {colors["text_primary"]};
    background: transparent;
}}

QLabel[labelStyle="secondary"] {{
    color: {colors["text_secondary"]};
    font-size: 9pt;
}}

QLabel[labelStyle="title"] {{
    font-size: 14pt;
    font-weight: 600;
    color: {colors["text_primary"]};
}}

QLabel[labelStyle="subtitle"] {{
    font-size: 11pt;
    font-weight: 500;
    color: {colors["text_secondary"]};
}}

/* ===== TOOLTIPS ===== */
QToolTip {{
    background-color: {colors["bg_tertiary"]};
    color: {colors["text_primary"]};
    border: 1px solid {colors["border"]};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 9pt;
}}

/* ===== DIALOGS ===== */
QDialog {{
    background-color: {colors["bg_primary"]};
    border-radius: 12px;
}}

QMessageBox {{
    background-color: {colors["bg_primary"]};
}}

/* ===== SPIN BOX ===== */
QSpinBox::up-button, QSpinBox::down-button {{
    background-color: {colors["bg_tertiary"]};
    border: none;
    border-radius: 3px;
    width: 18px;
}}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {colors["accent_primary"]};
}}

QSpinBox::up-arrow {{
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 4px solid {colors["text_secondary"]};
}}

QSpinBox::down-arrow {{
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 4px solid {colors["text_secondary"]};
}}

/* ===== TEXT BROWSER ===== */
QTextBrowser {{
    background-color: {colors["bg_tertiary"]};
    border: 1px solid {colors["border"]};
    border-radius: 6px;
    padding: 12px;
}}

QTextBrowser a {{
    color: {colors["link"]};
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


class ThemeManager:
    """
    Manages application theme switching.
    """

    def __init__(self):
        """Initialize theme manager."""
        self.current_mode = ThemeMode.DARK
        logger.info(f"ThemeManager initialized with mode: {self.current_mode.value}")

    def set_theme(self, mode: ThemeMode) -> str:
        """
        Set application theme.

        Args:
            mode: Theme mode

        Returns:
            Stylesheet string
        """
        self.current_mode = mode
        stylesheet = ModernTheme.get_stylesheet(mode)
        logger.info(f"Theme set to: {mode.value}")
        return stylesheet

    def get_current_mode(self) -> ThemeMode:
        """Get current theme mode."""
        return self.current_mode

    def toggle_theme(self) -> str:
        """
        Toggle between dark and light themes.

        Returns:
            New stylesheet
        """
        new_mode = ThemeMode.LIGHT if self.current_mode == ThemeMode.DARK else ThemeMode.DARK
        return self.set_theme(new_mode)


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
