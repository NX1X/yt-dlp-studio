"""The Hebrew UI must not show English words.

The static audit (scripts/i18n_audit.py) finds literals that skip tr(). This
test is the other half: it opens the real windows and dialogs in Hebrew, reads
every visible text (labels, buttons, tooltips, combo entries, table headers,
tab names, the Activity log) and fails on an English word. It catches text
that reaches a widget through a variable or a dictionary, which a static
check cannot see.

Sample data is Hebrew on purpose, so a name such as a video title never counts
as a leftover.
"""

import html
import re

import pytest
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QComboBox,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTableWidget,
    QTabWidget,
    QTextEdit,
    QWidget,
)

import src.backend.history_manager as hm_module
import src.ui.main_window as mw_module
from src.backend.config_manager import ConfigManager
from src.backend.playlist_fetcher import PlaylistInfo, PlaylistVideoInfo
from src.backend.yt_dlp_wrapper import YtDlpWrapper
from src.models.download_task import DownloadTask, TaskStatus
from src.models.video_info import VideoInfo
from src.ui.batch_input_dialog import BatchInputDialog
from src.ui.error_dialog import build_download_error_dialog
from src.ui.playlist_dialog import PlaylistDialog
from src.ui.subtitle_selection_dialog import SubtitleSelectionDialog
from src.ui.theme import ThemeMode, get_theme_manager
from src.ui.update_dialog import UpdateDialog
from src.ui.video_info_dialog import VideoInfoDialog
from src.utils.error_handler import ErrorCategory
from src.utils.translations import get_translation_manager

# English words that stay English in the Hebrew UI: product and format names,
# file types and keyboard keys that Hebrew speakers use as they are.
ALLOWED_WORDS = {
    "yt-dlp",
    "ytdlp",
    "dlp",
    "studio",
    "youtube",
    "instagram",
    "facebook",
    "tiktok",
    "vimeo",
    "dailymotion",
    "soundcloud",
    "ffmpeg",
    "deno",
    "github",
    "python",
    "pyside",
    "nxtools",
    "nx1x",
    "pyinstaller",
    "upx",
    "unlicense",
    "lgpl",
    "gpl",
    "psf",
    "url",
    "urls",
    "http",
    "https",
    "www",
    "com",
    "dev",
    "org",
    "mp3",
    "mp4",
    "m4a",
    "mkv",
    "webm",
    "opus",
    "flac",
    "wav",
    "ogg",
    "vorbis",
    "aac",
    "csv",
    "json",
    "txt",
    "kbps",
    "ctrl",
    "shift",
    "alt",
    "del",
    "delete",
    "esc",
    "enter",
    "vpn",
    "matroska",
    "full",  # "Full HD"
    "ultra",  # "Ultra HD 4K"
    "quad",  # "Quad HD"
    "info",  # the info.json file
    "qt",
    "jpg",
    "hevc",
    "vbr",
    "windows",
    "firefox",  # browser names in the cookies list
    "up",  # key names in shortcuts such as Ctrl+Up
    "down",
    # The language list names each language in its own language.
    "english",
    "hebrew",
    # Syntax shown as an example of a yt-dlp option or a proxy address
    "socks",
    "host",
    "ext",
    "title",
    "bestvideo",
    "bestaudio",
    "height",
    "zh-hans",
}

_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]{2,}")
_TAG = re.compile(r"<[^>]*>")
# Links, file paths, "%(name)s" templates and domain names are not words.
_NOT_WORDS = re.compile(r"https?://\S+|\S*[/\\]\S*|%\([a-z_]+\)s|\b[\w-]+\.(?:dev|com|org|io)\b")


def _english_words(text: str) -> list[str]:
    plain = _NOT_WORDS.sub(" ", html.unescape(_TAG.sub(" ", text or "")))
    return [w for w in _WORD.findall(plain) if w.lower().strip("-'") not in ALLOWED_WORDS]


def visible_texts(root: QWidget) -> list[tuple[str, str]]:
    """(where, text) for every text the user can see below ``root``."""
    found: list[tuple[str, str]] = []

    def add(widget: QWidget, kind: str, text: str) -> None:
        if text:
            found.append((f"{type(widget).__name__}.{widget.objectName() or '?'} {kind}", text))

    for widget in [root, *root.findChildren(QWidget)]:
        add(widget, "tooltip", widget.toolTip())
        add(widget, "title", widget.windowTitle() if widget.isWindow() else "")
        add(widget, "accessible", widget.accessibleName())
        for action in widget.actions():
            add(widget, "action", action.text())
            add(widget, "action tooltip", action.toolTip())
        if isinstance(widget, QLabel):
            add(widget, "label", widget.text())
        elif isinstance(widget, QAbstractButton):
            add(widget, "button", widget.text())
        elif isinstance(widget, QGroupBox):
            add(widget, "group", widget.title())
        elif isinstance(widget, QLineEdit):
            add(widget, "placeholder", widget.placeholderText())
        elif isinstance(widget, QTextEdit):
            add(widget, "placeholder", widget.placeholderText())
            if widget.objectName() == "activityLog":
                add(widget, "log", widget.toPlainText())
        elif isinstance(widget, QComboBox):
            for i in range(widget.count()):
                add(widget, f"item {i}", widget.itemText(i))
        elif isinstance(widget, QTabWidget):
            for i in range(widget.count()):
                add(widget, f"tab {i}", widget.tabText(i))
        elif isinstance(widget, QTableWidget):
            for column in range(widget.columnCount()):
                header = widget.horizontalHeaderItem(column)
                add(widget, f"header {column}", header.text() if header else "")
    return found


def leftovers(root: QWidget) -> list[str]:
    return [
        f"{where}: {text!r} -> {_english_words(text)}" for where, text in visible_texts(root) if _english_words(text)
    ]


@pytest.fixture
def hebrew(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(mw_module, "APP_DATA_DIR", tmp_path)
    monkeypatch.setattr(hm_module, "APP_DATA_DIR", tmp_path)
    get_translation_manager().set_language("he")
    yield
    get_translation_manager().set_language("en")
    QApplication.instance().setLayoutDirection(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.LeftToRight)
    get_theme_manager().set_theme(ThemeMode.DARK)


@pytest.fixture
def window(qtbot, tmp_path, hebrew):
    config = ConfigManager(config_path=tmp_path / "config.json")
    config.load_config()
    config.update_config(output_directory=str(tmp_path))
    win = mw_module.MainWindow(config)
    qtbot.addWidget(win)
    win.resize(1000, 700)
    win.show()

    manager = win.queue_manager
    manager.pause_queue()
    qualities = ["Best Quality", "1080p (Full HD)", "Audio 192kbps", "720p (HD)", "4K (2160p)"]
    states = [TaskStatus.PENDING, TaskStatus.DOWNLOADING, TaskStatus.COMPLETED, TaskStatus.ERROR, TaskStatus.CANCELLED]
    for i, (status, quality) in enumerate(zip(states, qualities, strict=True)):
        task = DownloadTask(
            url=f"https://www.youtube.com/watch?v=t{i}", output_directory=str(tmp_path), quality=quality
        )
        task.title = "סרטון לדוגמה"
        manager.add_task(task)
        task.status = status
        if status == TaskStatus.DOWNLOADING:
            task.progress_percent, task.download_speed, task.eta_seconds = 42, 2_000_000, 3700
        if status == TaskStatus.ERROR:
            task.error_message = "HTTP Error 403: Forbidden"
    manager.queue_updated.emit()
    for status in ("completed", "failed", "cancelled"):
        task = DownloadTask(
            url="https://www.youtube.com/watch?v=h", output_directory=str(tmp_path), quality="Best Quality"
        )
        task.title = "סרטון מההיסטוריה"
        task.filename = "a.mp4"
        win.history_manager.add_download(task, status, error_message="HTTP Error 404" if status == "failed" else "")
    win.history_tab.refresh()
    yield win
    win.notification_manager.hide_tray_icon()


def test_main_window_tabs(window):
    problems = []
    for index in range(window.tabs.count()):
        window.tabs.setCurrentIndex(index)
        QApplication.processEvents()
        problems += leftovers(window.tabs.widget(index))
    problems += leftovers(window.statusBar())
    assert not problems, "\n".join(problems)


def test_download_tab_in_audio_mode_and_activity_log(window):
    tab = window.download_tab
    tab.download_type_combo.setCurrentIndex(tab.download_type_combo.findData("audio"))
    tab._on_task_started(0, "סרטון")
    tab._on_task_completed(0, "a.mp4")
    tab._on_task_failed(0, "שגיאה")
    tab._on_quality_changed()
    tab._paste_from_clipboard()
    problems = leftovers(tab)
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize("category", list(ErrorCategory))
def test_error_dialog_for_every_category(window, category):
    samples = {
        ErrorCategory.NETWORK: "connection timeout",
        ErrorCategory.URL_INVALID: "unsupported url",
        ErrorCategory.VIDEO_UNAVAILABLE: "video unavailable",
        ErrorCategory.GEO_BLOCKED: "blocked in your country",
        ErrorCategory.COPYRIGHT: "removed due to copyright",
        ErrorCategory.PRIVATE: "private video",
        ErrorCategory.FORMAT: "requested format not available",
        ErrorCategory.DISK_SPACE: "no space left on device",
        ErrorCategory.PERMISSION: "permission denied",
        ErrorCategory.UNKNOWN: "תקלה",
    }
    box = build_download_error_dialog(window, samples[category])
    QApplication.processEvents()
    texts = [box.text(), box.windowTitle(), *(b.text() for b in box.buttons())]
    box.close()
    # The raw yt-dlp message under "technical details" stays English by design.
    visible = [re.sub(r"<p dir=\"ltr\".*?</p>", "", t, flags=re.S) for t in texts]
    problems = [f"{t!r} -> {_english_words(t)}" for t in visible if _english_words(t)]
    assert not problems, "\n".join(problems)


def test_ok_button_of_a_message_box_is_hebrew(window):
    box = QMessageBox(window)
    box.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
    texts = [b.text() for b in box.buttons()]
    assert not [t for t in texts if _english_words(t)], texts


def test_dialogs(window):
    video = VideoInfo(
        title="סרטון",
        url="https://youtu.be/x",
        duration=0,
        uploader="ערוץ",
        upload_date="20260101",
        view_count=1000,
        like_count=5,
        description="תיאור",
        extractor="youtube",
    )
    playlist = PlaylistInfo(
        title="רשימה",
        url="https://youtube.com/playlist?list=x",
        video_count=1,
        uploader="ערוץ",
        videos=[PlaylistVideoInfo(title="סרטון", url="https://y/1", duration=0, uploader="ערוץ", index=1)],
    )
    wrapper = YtDlpWrapper()
    subs = {c: {"name": wrapper._get_language_name(c), "auto": c == "es"} for c in ["en", "es", "he", "de", "zh-Hans"]}
    dialogs = [
        VideoInfoDialog(video, window),
        PlaylistDialog(playlist, window),
        SubtitleSelectionDialog(subs, window),
        BatchInputDialog(window),
        UpdateDialog({"version": "9.9.9", "html_url": "https://github.com/x", "body": "", "assets": []}, window),
    ]
    problems = []
    for dialog in dialogs:
        dialog.show()
        QApplication.processEvents()
        problems += [f"{type(dialog).__name__} {p}" for p in leftovers(dialog)]
        dialog.close()
    assert not problems, "\n".join(problems)
