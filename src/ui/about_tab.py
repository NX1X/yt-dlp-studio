"""
About tab for YT-DLP Studio.

Displays application information, system component versions, credits, and
keyboard shortcuts. Replaces the previous dark-theme-only HTML colours
with palette-aware styling so the tab reads correctly under both light
and dark themes, and runs every user-facing string through ``tr()`` so
the Hebrew runtime no longer sees English islands.
"""

from __future__ import annotations

import subprocess
import sys

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ..backend.yt_dlp_wrapper import YtDlpWrapper
from ..utils.constants import APP_NAME, APP_VERSION
from ..utils.logger import get_logger
from ..utils.translations import get_translation_manager, tr

logger = get_logger()

GITHUB_URL = "https://github.com/NX1X/yt-dlp-studio"
NXTOOLS_URL = "https://nx1xlab.dev/nxtools"
BUYMEACOFFEE_URL = "https://buymeacoffee.com/nx1x"

# Single accent colour that is visible on both the dark and light themes
# (Qt's mini-CSS in QTextBrowser does NOT support palette() so we cannot
# defer to the theme manager). A medium blue with high contrast against
# both white and near-black backgrounds.
_LINK_COLOR = "#1976d2"


def _detect_ffmpeg_version() -> str:
    """Return a short FFmpeg version string or a translated fallback.

    Used by the System Information group. Never raises - callers can
    drop the return value straight into the UI.
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            first_line = result.stdout.split("\n")[0]
            if "version" in first_line:
                parts = first_line.split()
                if len(parts) >= 3:
                    return parts[2]
        return tr("text_ffmpeg_unknown")
    except FileNotFoundError:
        return tr("text_ffmpeg_not_found")
    except Exception as e:  # noqa: BLE001
        logger.error(f"Error getting FFmpeg version: {e}")
        return tr("text_ffmpeg_error")


def _detect_python_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def _detect_pyside_version() -> str:
    try:
        from PySide6 import __version__ as pyside_version

        return pyside_version
    except Exception:  # noqa: BLE001
        return tr("text_version_unknown")


def _detect_ytdlp_version() -> str:
    try:
        return YtDlpWrapper.get_ytdlp_version()
    except Exception:  # noqa: BLE001
        return tr("text_version_unknown")


class AboutTab(QWidget):
    """About tab displaying application information."""

    def __init__(self):
        super().__init__()
        self._setup_ui()
        logger.debug("AboutTab initialized")

    # ------------------------------------------------------------------ UI

    def _setup_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header: title + version + description.
        layout.addWidget(self._build_header())
        layout.addSpacing(10)

        # System information (moved from Settings tab).
        layout.addWidget(self._build_system_info_group())

        # Plain-language "what is this?" group.
        layout.addWidget(self._build_details_group())

        # Developer / NXtools section + GitHub button.
        layout.addWidget(self._build_developer_group())

        # Credits (open-source dependencies).
        layout.addWidget(self._build_credits_group())

        # Keyboard shortcuts cheat-sheet.
        layout.addWidget(self._build_shortcuts_group())

        layout.addStretch()

        scroll.setWidget(content_widget)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

    def _build_header(self) -> QWidget:
        """Title + version + one-line description block."""
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        title_label = QLabel(APP_NAME)
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(title_label)

        version_label = QLabel(f"{tr('label_current_version')} {APP_VERSION}")
        version_font = QFont()
        version_font.setPointSize(12)
        version_label.setFont(version_font)
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # No inline color: Qt's palette handles secondary text contrast.
        v.addWidget(version_label)

        return container

    def _build_details_group(self) -> QGroupBox:
        group = QGroupBox(tr("group_about_details"))
        layout = QVBoxLayout(group)

        body = (
            f"<p><b>{APP_NAME}</b> {tr('about_description')}</p>"
        )
        text = self._make_textbrowser(body, max_height=80)
        layout.addWidget(text)
        return group

    def _build_system_info_group(self) -> QGroupBox:
        """Concrete software-stack version data. Moved from Settings tab."""
        group = QGroupBox(tr("group_about_system_info"))
        layout = QVBoxLayout(group)

        rows = [
            (tr("label_app_version"), APP_VERSION),
            (tr("label_yt_dlp_version"), _detect_ytdlp_version()),
            (tr("label_ffmpeg_version"), _detect_ffmpeg_version()),
            (tr("label_python_version"), _detect_python_version()),
            (tr("label_pyside_version"), _detect_pyside_version()),
        ]

        body_rows = "".join(
            f'<tr><td style="padding: 4px 16px 4px 0;"><b>{label}</b></td>'
            f'<td style="padding: 4px 0;">{value}</td></tr>'
            for label, value in rows
        )
        body = f'<table style="border-spacing: 0;">{body_rows}</table>'

        text = self._make_textbrowser(body, max_height=140)
        layout.addWidget(text)
        return group

    def _build_developer_group(self) -> QGroupBox:
        group = QGroupBox(tr("group_about_developer"))
        layout = QVBoxLayout(group)

        intro = tr("text_about_developer_intro")
        coffee_line = tr("text_buy_me_a_coffee_blurb")
        body = (
            f"<p>{intro}</p>"
            f"<p><b>{tr('label_website')}</b> "
            f'<a href="{NXTOOLS_URL}" style="color: {_LINK_COLOR};">{NXTOOLS_URL}</a></p>'
            f"<p><b>{tr('label_support_development')}</b><br>{coffee_line}<br>"
            f'<a href="{BUYMEACOFFEE_URL}" style="color: {_LINK_COLOR};">{BUYMEACOFFEE_URL}</a></p>'
        )
        text = self._make_textbrowser(body, max_height=160)
        layout.addWidget(text)

        # GitHub button (live, no longer commented out).
        button_row = QHBoxLayout()
        github_button = QPushButton(tr("button_view_on_github"))
        github_button.setToolTip(tr("tooltip_view_on_github"))
        github_button.setProperty("buttonStyle", "secondary")
        github_button.clicked.connect(self._open_github)
        button_row.addStretch()
        button_row.addWidget(github_button)
        button_row.addStretch()
        layout.addLayout(button_row)

        return group

    def _build_credits_group(self) -> QGroupBox:
        group = QGroupBox(tr("label_credits"))
        layout = QVBoxLayout(group)

        body = (
            f"<p>{tr('text_credits_description')}</p>"
            f"<h3>{tr('header_credits_core_deps')}</h3>"
            "<p><b>yt-dlp</b><br>"
            "License: Unlicense<br>"
            f'<a href="https://github.com/yt-dlp/yt-dlp" style="color: {_LINK_COLOR};">'
            "https://github.com/yt-dlp/yt-dlp</a></p>"
            "<p><b>FFmpeg</b><br>"
            "License: LGPL 2.1+ / GPL 2+<br>"
            f'<a href="https://ffmpeg.org/" style="color: {_LINK_COLOR};">https://ffmpeg.org/</a></p>'
            f"<h3>{tr('header_credits_dev_framework')}</h3>"
            f"<p><b>Python {_detect_python_version()}</b><br>"
            "License: PSF<br>"
            f'<a href="https://www.python.org/" style="color: {_LINK_COLOR};">https://www.python.org/</a></p>'
            "<p><b>PySide6 (Qt6)</b><br>"
            "License: LGPL<br>"
            f'<a href="https://www.qt.io/qt-for-python" style="color: {_LINK_COLOR};">'
            "https://www.qt.io/qt-for-python</a></p>"
            f"<h3>{tr('header_credits_build_dist')}</h3>"
            "<p><b>PyInstaller</b><br>"
            "License: GPL<br>"
            f'<a href="https://pyinstaller.org/" style="color: {_LINK_COLOR};">https://pyinstaller.org/</a></p>'
            "<p><b>UPX</b><br>"
            "License: GPL<br>"
            f'<a href="https://upx.github.io/" style="color: {_LINK_COLOR};">https://upx.github.io/</a></p>'
            f"<p><i>{tr('text_credits_thanks')}</i></p>"
        )
        text = self._make_textbrowser(body, max_height=380)
        layout.addWidget(text)
        return group

    def _build_shortcuts_group(self) -> QGroupBox:
        group = QGroupBox(tr("shortcuts_title"))
        layout = QVBoxLayout(group)

        def _section(title: str, rows: list[tuple[str, str]]) -> str:
            row_html = "".join(
                f'<tr><td style="padding: 4px 16px 4px 0;"><b>{key}</b></td>'
                f'<td style="padding: 4px 0;">{action}</td></tr>'
                for key, action in rows
            )
            return f"<h3>{title}</h3><table style='border-spacing: 0;'>{row_html}</table>"

        general = _section(
            tr("shortcuts_general"),
            [
                ("Ctrl+Q", tr("shortcut_quit_app")),
                ("F1", tr("shortcut_show_help")),
                ("Esc", tr("shortcut_close_dialogs")),
            ],
        )
        download_tab_shortcuts = _section(
            tr("shortcuts_download_tab"),
            [
                ("Ctrl+V", tr("shortcut_paste_url")),
                ("Enter", tr("shortcut_start_download")),
                ("Ctrl+Shift+I", tr("shortcut_show_video_info")),
                ("Ctrl+D", tr("shortcut_download_now")),
                ("Ctrl+Shift+Q", tr("shortcut_add_to_queue")),
            ],
        )
        queue_tab_shortcuts = _section(
            tr("shortcuts_queue_tab"),
            [
                ("Delete", tr("shortcut_remove_task")),
                ("Ctrl+Up", tr("shortcut_move_task_up")),
                ("Ctrl+Down", tr("shortcut_move_task_down")),
            ],
        )

        text = self._make_textbrowser(
            general + download_tab_shortcuts + queue_tab_shortcuts, max_height=300
        )
        layout.addWidget(text)
        return group

    # ----------------------------------------------------------- helpers

    def _make_textbrowser(self, body_html: str, *, max_height: int) -> QTextBrowser:
        """Wrap an HTML body in a QTextBrowser with palette-friendly defaults.

        Sets `dir="rtl"` on the root when the active UI language is Hebrew
        so internal tables flow in the natural reading direction. Drops all
        hardcoded text colours so Qt's palette can pick the right shade
        per theme.
        """
        tm = get_translation_manager()
        is_rtl = tm.get_language() == "he"
        dir_attr = "rtl" if is_rtl else "ltr"
        html = (
            f'<div dir="{dir_attr}">'
            f'{body_html}'
            '</div>'
        )
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(html)
        browser.setMaximumHeight(max_height)
        return browser

    def _open_github(self) -> None:
        QDesktopServices.openUrl(QUrl(GITHUB_URL))
        logger.debug("Opened GitHub repository")
