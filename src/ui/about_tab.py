"""
About tab for YT-DLP Studio.

Displays application information, system component versions, credits, and
keyboard shortcuts. Replaces the previous dark-theme-only HTML colours
with palette-aware styling so the tab reads correctly under both light
and dark themes, and runs every user-facing string through ``tr()`` so
the Hebrew runtime no longer sees English islands.
"""

from __future__ import annotations

import sys
import threading

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..backend.environment import (
    cached_ffmpeg_version_info,
    ffmpeg_version_text,
    get_ffmpeg_version_info,
)
from ..backend.yt_dlp_wrapper import YtDlpWrapper
from ..utils.constants import APP_NAME, APP_VERSION
from ..utils.logger import get_logger
from ..utils.translations import get_translation_manager, tr

logger = get_logger()

GITHUB_URL = "https://github.com/NX1X/yt-dlp-studio"
NXTOOLS_URL = "https://nx1xlab.dev/nxtools"

# Single accent colour that is visible on both the dark and light themes
# (Qt's mini-CSS in QTextBrowser does NOT support palette() so we cannot
# defer to the theme manager). A medium blue with high contrast against
# both white and near-black backgrounds.
_LINK_COLOR = "#1976d2"


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
    """About tab displaying application information.

    The FFmpeg version needs a process start, so it is not read while the
    tab is built at startup. The row shows "Checking..." until the tab is
    first shown, then a background thread fills it in. When the startup
    environment log has already probed FFmpeg, the cached value is used at
    once.
    """

    # (status, version) from the FFmpeg probe. Emitted from a worker thread;
    # Qt queues it to the GUI thread.
    _ffmpeg_info_ready = Signal(str, str)

    def __init__(self):
        super().__init__()
        self._ffmpeg_text = tr("text_ffmpeg_checking")
        self._ffmpeg_probe_started = False
        self._system_info_label: QLabel | None = None
        self._ffmpeg_info_ready.connect(self._on_ffmpeg_info)
        self._setup_ui()
        logger.debug("AboutTab initialized")

    # ------------------------------------------------------------ FFmpeg

    def showEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().showEvent(event)
        self._start_ffmpeg_probe()

    def _start_ffmpeg_probe(self) -> None:
        """Fill in the FFmpeg row once, without blocking the GUI thread."""
        if self._ffmpeg_probe_started:
            return
        self._ffmpeg_probe_started = True
        cached = cached_ffmpeg_version_info()
        if cached is not None:
            self._on_ffmpeg_info(cached[0], cached[1] or "")
            return
        threading.Thread(target=self._probe_ffmpeg, name="about-ffmpeg-probe", daemon=True).start()

    def _probe_ffmpeg(self) -> None:
        """Worker thread: run the probe and hand the result to the GUI thread."""
        status, version = get_ffmpeg_version_info()
        try:
            self._ffmpeg_info_ready.emit(status, version or "")
        except RuntimeError:
            # The tab was destroyed while the probe ran (app closing).
            pass

    def _on_ffmpeg_info(self, status: str, version: str) -> None:
        self._ffmpeg_text = ffmpeg_version_text((status, version or None))
        if self._system_info_label is not None:
            self._system_info_label.setText(self._wrap_html(self._system_info_html()))

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

        body = f"<p><b>{APP_NAME}</b> {tr('about_description')}</p>"
        text = self._make_rich_label(body, max_height=80)
        layout.addWidget(text)
        return group

    def _build_system_info_group(self) -> QGroupBox:
        """Concrete software-stack version data. Moved from Settings tab."""
        group = QGroupBox(tr("group_about_system_info"))
        layout = QVBoxLayout(group)

        text = self._make_rich_label(self._system_info_html(), max_height=140)
        self._system_info_label = text
        layout.addWidget(text)
        return group

    def _system_info_html(self) -> str:
        rows = [
            (tr("label_app_version"), APP_VERSION),
            (tr("label_yt_dlp_version"), _detect_ytdlp_version()),
            (tr("label_ffmpeg_version"), self._ffmpeg_text),
            (tr("label_python_version"), _detect_python_version()),
            (tr("label_pyside_version"), _detect_pyside_version()),
        ]

        body_rows = "".join(
            f'<tr><td style="padding: 4px 16px 4px 0;"><b>{label}</b></td><td style="padding: 4px 0;">{value}</td></tr>'
            for label, value in rows
        )
        return f'<table style="border-spacing: 0;">{body_rows}</table>'

    def _build_developer_group(self) -> QGroupBox:
        group = QGroupBox(tr("group_about_developer"))
        layout = QVBoxLayout(group)

        intro = tr("text_about_developer_intro")
        body = (
            f"<p>{intro}</p>"
            f"<p><b>{tr('label_website')}</b> "
            f'<a href="{NXTOOLS_URL}" style="color: {_LINK_COLOR};">{NXTOOLS_URL}</a></p>'
        )
        text = self._make_rich_label(body, max_height=110)
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
        text = self._make_rich_label(body, max_height=380)
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

        text = self._make_rich_label(general + download_tab_shortcuts + queue_tab_shortcuts, max_height=300)
        layout.addWidget(text)
        return group

    # ----------------------------------------------------------- helpers

    def _make_rich_label(self, body_html: str, *, max_height: int = 0) -> QLabel:
        """Render an HTML block as a QLabel that grows to fit its content.

        Replaces the previous QTextBrowser-based helper, which always shows
        an internal scrollbar when the body exceeds the widget height. A
        QLabel with word wrap sizes to its preferred height, so the outer
        QScrollArea handles the scroll just once for the whole tab.

        Sets ``dir="rtl"`` on the root when the active UI language is Hebrew
        so internal tables flow in the natural reading direction. Drops all
        hardcoded text colours so Qt's palette can pick the right shade per
        theme; only the link colour is hardcoded because Qt's mini-CSS does
        not support ``palette()`` lookups for ``<a>`` styling.

        Args:
            body_html: The HTML body to render.
            max_height: Ignored. Accepted for API compatibility with the old
                helper so callers do not need a parallel migration. Kept as a
                no-op so we can re-introduce a per-block height cap later
                without touching every call site.
        """
        del max_height  # explicit no-op

        is_rtl = self._is_rtl()
        label = QLabel(self._wrap_html(body_html))
        label.setTextFormat(Qt.RichText)
        label.setWordWrap(True)
        # Allow clicking links + selecting text without making the label
        # editable. TextBrowserInteraction is what QTextBrowser uses by
        # default.
        label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        label.setOpenExternalLinks(True)
        # Grow to fit content; the outer QScrollArea provides overflow.
        label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        label.setAlignment(Qt.AlignRight | Qt.AlignTop if is_rtl else Qt.AlignLeft | Qt.AlignTop)
        return label

    @staticmethod
    def _is_rtl() -> bool:
        return get_translation_manager().get_language() == "he"

    def _wrap_html(self, body_html: str) -> str:
        """Wrap a body in a ``<div>`` with the reading direction of the UI language."""
        dir_attr = "rtl" if self._is_rtl() else "ltr"
        return f'<div dir="{dir_attr}">{body_html}</div>'

    def _open_github(self) -> None:
        QDesktopServices.openUrl(QUrl(GITHUB_URL))
        logger.debug("Opened GitHub repository")
