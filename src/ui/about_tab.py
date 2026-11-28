"""
About tab for YT-DLP Studio.

A header (name, version, one sentence, links), then the system information
with a "Copy for bug report" button, the keyboard shortcuts and the credits.
All text runs through ``tr()``. Colors come from the theme: links use the
palette's link color, and the rich text is rebuilt after a theme change.
"""

from __future__ import annotations

import html
import platform
import sys
import threading

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
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
    environment_line,
    ffmpeg_version_text,
    get_ffmpeg_version_info,
)
from ..backend.yt_dlp_wrapper import YtDlpWrapper
from ..utils.constants import APP_NAME, APP_VERSION
from ..utils.logger import get_logger
from ..utils.translations import get_translation_manager, tr
from .display_format import ltr
from .status_messages import show_status
from .theme import get_theme_manager

logger = get_logger()

GITHUB_URL = "https://github.com/NX1X/yt-dlp-studio"
WEBSITE_URL = "https://studio.nx1xlab.dev"
NXTOOLS_URL = "https://nx1xlab.dev/nxtools"


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


def bug_report_text() -> str:
    """
    Return the system information to paste into a bug report.

    Blocks for the FFmpeg probe on the first call, so run it off the GUI
    thread. The text is English on purpose: it is read by the maintainer.
    """
    return "\n".join(
        [
            f"{APP_NAME} {APP_VERSION}",
            environment_line().removeprefix("Environment: "),
            f"OS: {platform.platform()}",
            f"UI language: {get_translation_manager().get_language()}",
        ]
    )


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
    # Bug report text from a worker thread.
    _bug_report_ready = Signal(str)

    def __init__(self):
        super().__init__()
        self._ffmpeg_text = tr("text_ffmpeg_checking")
        self._ffmpeg_probe_started = False
        self._system_info_label: QLabel | None = None
        # (label, function that returns its HTML body), rebuilt on a theme change
        self._rich_labels: list[tuple[QLabel, object]] = []
        self._ffmpeg_info_ready.connect(self._on_ffmpeg_info)
        self._bug_report_ready.connect(self._on_bug_report_ready)
        self._setup_ui()
        get_theme_manager().theme_changed.connect(self._refresh_rich_text)
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

    # ------------------------------------------------------- bug report

    def _copy_bug_report(self) -> None:
        """Collect the system information off the GUI thread, then copy it."""
        self.copy_report_button.setEnabled(False)
        threading.Thread(target=self._collect_bug_report, name="about-bug-report", daemon=True).start()

    def _collect_bug_report(self) -> None:
        try:
            text = bug_report_text()
        except Exception as e:  # noqa: BLE001 - copy what we have
            logger.warning(f"Could not collect all system information: {e}")
            text = f"{APP_NAME} {APP_VERSION}\nOS: {platform.platform()}"
        try:
            self._bug_report_ready.emit(text)
        except RuntimeError:
            pass

    def _on_bug_report_ready(self, text: str) -> None:
        self.copy_report_button.setEnabled(True)
        clipboard = QApplication.clipboard()
        if clipboard is None:
            return
        clipboard.setText(text)
        show_status(self, tr("msg_bug_report_copied"))
        logger.debug("Copied system information for a bug report")

    # ------------------------------------------------------------------ UI

    def _setup_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(self._build_header())
        layout.addWidget(self._build_system_info_group())
        layout.addWidget(self._build_shortcuts_group())
        layout.addWidget(self._build_credits_group())
        layout.addStretch()

        scroll.setWidget(content_widget)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _build_header(self) -> QWidget:
        """Name, version, one sentence and the links."""
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 8, 0, 8)
        v.setSpacing(6)

        # The size is set in the theme (#aboutTitle): setFont() would lose
        # to the global font size of the style sheet.
        title_label = QLabel(APP_NAME)
        title_label.setObjectName("aboutTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(title_label)

        version_label = QLabel(f"{tr('label_current_version')} {ltr(APP_VERSION)}")
        version_label.setProperty("labelStyle", "secondary")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(version_label)

        tagline = QLabel(tr("about_tagline"))
        tagline.setWordWrap(True)
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(tagline)

        developer = self._make_rich_label(
            lambda: (
                f"{tr('text_about_developer_intro')} "
                f'<a href="{NXTOOLS_URL}">{html.escape(NXTOOLS_URL.removeprefix("https://"))}</a>'
            )
        )
        developer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        developer.setProperty("labelStyle", "secondary")
        v.addWidget(developer)

        button_row = QHBoxLayout()
        button_row.addStretch()
        github_button = QPushButton(tr("button_view_on_github"))
        github_button.setToolTip(tr("tooltip_view_on_github"))
        github_button.clicked.connect(lambda: self._open_url(GITHUB_URL))
        button_row.addWidget(github_button)
        website_button = QPushButton(tr("button_visit_website"))
        website_button.setToolTip(WEBSITE_URL)
        website_button.clicked.connect(lambda: self._open_url(WEBSITE_URL))
        button_row.addWidget(website_button)
        button_row.addStretch()
        v.addSpacing(4)
        v.addLayout(button_row)
        return container

    def _build_system_info_group(self) -> QGroupBox:
        """Versions of the software stack, with a copy button for bug reports."""
        group = QGroupBox(tr("group_about_system_info"))
        layout = QVBoxLayout(group)

        text = self._make_rich_label(self._system_info_html)
        self._system_info_label = text
        layout.addWidget(text)

        row = QHBoxLayout()
        self.copy_report_button = QPushButton(tr("button_copy_bug_report"))
        self.copy_report_button.setToolTip(tr("tooltip_copy_bug_report"))
        self.copy_report_button.clicked.connect(self._copy_bug_report)
        row.addWidget(self.copy_report_button)
        row.addStretch()
        layout.addLayout(row)
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
            f'<tr><td style="padding: 3px 16px 3px 0;"><b>{label}</b></td>'
            f'<td style="padding: 3px 0;">{ltr(value)}</td></tr>'
            for label, value in rows
        )
        return f'<table style="border-spacing: 0;">{body_rows}</table>'

    def _build_credits_group(self) -> QGroupBox:
        group = QGroupBox(tr("label_credits"))
        layout = QVBoxLayout(group)
        layout.addWidget(self._make_rich_label(self._credits_html))
        return group

    @staticmethod
    def _credits_html() -> str:
        license_label = tr("label_license")

        def project(name: str, license_name: str, url: str) -> str:
            return f'<p><b>{name}</b><br>{license_label} {license_name}<br><a href="{url}">{html.escape(url)}</a></p>'

        return (
            f"<p>{tr('text_credits_description')}</p>"
            f"<h3>{tr('header_credits_core_deps')}</h3>"
            + project("yt-dlp", "Unlicense", "https://github.com/yt-dlp/yt-dlp")
            + project("FFmpeg", "LGPL 2.1+ / GPL 2+", "https://ffmpeg.org/")
            + f"<h3>{tr('header_credits_dev_framework')}</h3>"
            + project(f"Python {_detect_python_version()}", "PSF", "https://www.python.org/")
            + project("PySide6 (Qt6)", "LGPL", "https://www.qt.io/qt-for-python")
            + f"<h3>{tr('header_credits_build_dist')}</h3>"
            + project("PyInstaller", "GPL", "https://pyinstaller.org/")
            + project("UPX", "GPL", "https://upx.github.io/")
            + f"<p><i>{tr('text_credits_thanks')}</i></p>"
        )

    def _build_shortcuts_group(self) -> QGroupBox:
        group = QGroupBox(tr("shortcuts_title"))
        layout = QVBoxLayout(group)
        layout.addWidget(self._make_rich_label(self._shortcuts_html))
        return group

    @staticmethod
    def _shortcuts_html() -> str:
        def _section(title: str, rows: list[tuple[str, str]]) -> str:
            row_html = "".join(
                f'<tr><td style="padding: 3px 16px 3px 0;"><b>{ltr(key)}</b></td>'
                f'<td style="padding: 3px 0;">{action}</td></tr>'
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
                ("Ctrl+D", tr("button_download")),
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
        return general + download_tab_shortcuts + queue_tab_shortcuts

    # ----------------------------------------------------------- helpers

    def _make_rich_label(self, build_html) -> QLabel:
        """Render HTML from ``build_html()`` as a QLabel that grows to fit.

        A QLabel with word wrap sizes to its content, so the outer scroll
        area scrolls the whole tab at once. Links use the palette's link
        color (set by the theme); the label is rebuilt after a theme change
        because Qt picks the link color when it reads the HTML.
        """
        is_rtl = self._is_rtl()
        label = QLabel(self._wrap_html(build_html()))
        label.setTextFormat(Qt.RichText)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        label.setOpenExternalLinks(True)
        label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        label.setAlignment(Qt.AlignRight | Qt.AlignTop if is_rtl else Qt.AlignLeft | Qt.AlignTop)
        self._rich_labels.append((label, build_html))
        return label

    def _refresh_rich_text(self, _mode: str = "") -> None:
        """Build the rich text again so links take the new theme's color."""
        for label, build_html in self._rich_labels:
            try:
                # setText() skips an unchanged text, so clear the label first.
                label.clear()
                label.setText(self._wrap_html(build_html()))
            except RuntimeError:
                pass  # the label was deleted

    @staticmethod
    def _is_rtl() -> bool:
        return get_translation_manager().get_language() == "he"

    def _wrap_html(self, body_html: str) -> str:
        """Wrap a body in a ``<div>`` with the reading direction of the UI language."""
        dir_attr = "rtl" if self._is_rtl() else "ltr"
        return f'<div dir="{dir_attr}">{body_html}</div>'

    @staticmethod
    def _open_url(url: str) -> None:
        QDesktopServices.openUrl(QUrl(url))
        logger.debug(f"Opened {url}")
