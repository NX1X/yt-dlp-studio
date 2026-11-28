"""
Tests for the theme, the saved theme, the Settings and About tabs and the dialogs.

Runs headless with QT_QPA_PLATFORM=offscreen. Message boxes are patched.
"""

import json
import re
from unittest.mock import patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QMessageBox, QStatusBar

import src.backend.history_manager as hm_module
import src.ui.main_window as mw_module
from src.backend.config_manager import ConfigManager
from src.backend.playlist_fetcher import PlaylistInfo, PlaylistVideoInfo
from src.models.app_config import AppConfig
from src.ui import theme as theme_module
from src.ui.batch_input_dialog import BatchInputDialog, split_urls
from src.ui.display_format import LRI, PDI, ltr
from src.ui.error_dialog import build_download_error_dialog
from src.ui.log_widget import LogWidget
from src.ui.playlist_dialog import PlaylistDialog
from src.ui.progress_bar import DownloadProgressWidget
from src.ui.settings_tab import SettingsTab
from src.ui.status_messages import show_status
from src.ui.subtitle_selection_dialog import SubtitleSelectionDialog
from src.ui.theme import ICON_DIR, ModernTheme, ThemeMode, get_theme_manager
from src.ui.update_dialog import UpdateDialog, is_web_url
from src.utils.translations import TRANSLATIONS, get_translation_manager, tr


@pytest.fixture(autouse=True)
def english_ui_and_dark_theme():
    """Fixed language, and the dark theme again after each test."""
    get_translation_manager().set_language("en")
    yield
    get_translation_manager().set_language("en")
    get_theme_manager().set_theme(ThemeMode.DARK)


@pytest.fixture
def config_manager(tmp_path):
    out_dir = tmp_path / "downloads"
    out_dir.mkdir()
    manager = ConfigManager(config_path=tmp_path / "config.json")
    manager.load_config()
    manager.update_config(output_directory=str(out_dir))
    return manager


@pytest.fixture
def make_window(qtbot, tmp_path, monkeypatch):
    """Build a MainWindow that keeps its queue and history in tmp_path."""
    monkeypatch.setattr(mw_module, "APP_DATA_DIR", tmp_path)
    monkeypatch.setattr(hm_module, "APP_DATA_DIR", tmp_path)
    windows = []

    def _make(config_manager):
        window = mw_module.MainWindow(config_manager)
        qtbot.addWidget(window)
        windows.append(window)
        return window

    yield _make
    for window in windows:
        window.notification_manager.hide_tray_icon()


# ---------------------------------------------------------------- theme


class TestTheme:
    def test_both_palettes_have_the_same_tokens(self):
        assert set(ModernTheme.COLORS["dark"]) == set(ModernTheme.COLORS["light"])

    @pytest.mark.parametrize(
        "value, expected",
        [("dark", ThemeMode.DARK), ("light", ThemeMode.LIGHT), ("auto", ThemeMode.DARK), ("purple", ThemeMode.DARK)],
    )
    def test_mode_from_saved_value(self, value, expected):
        assert ThemeMode.from_value(value) is expected

    @pytest.mark.parametrize("mode", [ThemeMode.DARK, ThemeMode.LIGHT])
    def test_every_icon_in_the_style_sheet_exists(self, mode):
        names = re.findall(r"url\(themeicons:([^)]+)\)", ModernTheme.get_stylesheet(mode))
        assert names
        for name in names:
            assert (ICON_DIR / name).is_file(), name

    def test_plain_button_is_secondary_and_primary_is_opt_in(self):
        sheet = ModernTheme.get_stylesheet(ThemeMode.DARK)
        plain = sheet.split("QPushButton {", 1)[1].split("}", 1)[0]
        assert ModernTheme.COLORS["dark"]["accent_primary"] not in plain
        assert 'QPushButton[buttonStyle="primary"]' in sheet

    def test_light_contrast_fixes(self):
        light = ModernTheme.COLORS["light"]
        assert light["warning"] == "#b45309"
        assert light["success"] == "#047857"
        assert light["error"] == "#c42b1c"
        assert light["link"] == "#005a9e"
        assert light["border_input"] == "#8a8a8a"

    def test_apply_theme_sets_app_style_and_palette(self, qtbot):
        manager = get_theme_manager()
        with qtbot.waitSignal(manager.theme_changed, timeout=1000) as blocker:
            manager.apply_theme(ThemeMode.LIGHT)
        app = QApplication.instance()
        assert blocker.args == ["light"]
        assert ModernTheme.COLORS["light"]["bg_primary"] in app.styleSheet()
        assert app.palette().link().color().name() == ModernTheme.COLORS["light"]["link"]
        manager.apply_theme(ThemeMode.DARK)


# ------------------------------------------------------- saved theme


class TestSavedTheme:
    def test_default_is_dark(self):
        assert AppConfig(output_directory="/tmp").theme == "dark"

    def test_old_config_without_field_loads_dark(self, tmp_path):
        path = tmp_path / "config.json"
        data = AppConfig(output_directory=str(tmp_path)).to_dict()
        del data["theme"]
        path.write_text(json.dumps(data), encoding="utf-8")
        assert ConfigManager(config_path=path).load_config().theme == "dark"

    def test_app_starts_in_saved_theme(self, make_window, config_manager):
        config_manager.update_config(theme="light")
        window = make_window(config_manager)
        assert get_theme_manager().get_current_mode() is ThemeMode.LIGHT
        assert window.settings_tab.theme_combo.currentData() == "light"

    def test_theme_combo_applies_and_saves(self, make_window, config_manager):
        window = make_window(config_manager)
        combo = window.settings_tab.theme_combo
        combo.setCurrentIndex(combo.findData("light"))
        assert get_theme_manager().get_current_mode() is ThemeMode.LIGHT
        with open(config_manager.config_path, encoding="utf-8") as f:
            assert json.load(f)["theme"] == "light"


# -------------------------------------------------------- settings tab


class TestSettingsTab:
    @pytest.fixture
    def tab(self, qtbot, config_manager):
        tab = SettingsTab(config_manager)
        qtbot.addWidget(tab)
        return tab

    def test_quality_saved_as_stable_key_in_hebrew(self, qtbot, config_manager):
        get_translation_manager().set_language("he")
        tab = SettingsTab(config_manager)
        qtbot.addWidget(tab)
        tab.language_combo.setCurrentIndex(tab.language_combo.findData("he"))
        tab.quality_combo.setCurrentIndex(tab.quality_combo.findData("720p (HD)"))
        with patch("src.ui.settings_tab.save_language"):
            tab._save_settings()
        assert config_manager.get_config().default_quality == "720p (HD)"

    def test_save_confirms_in_status_bar_not_a_message_box(self, make_window, config_manager):
        window = make_window(config_manager)
        with patch.object(QMessageBox, "information") as info:
            window.settings_tab._save_settings()
        info.assert_not_called()
        assert window.statusBar().currentMessage() == tr("status_settings_saved")

    def test_copy_path_goes_to_status_bar(self, make_window, config_manager):
        window = make_window(config_manager)
        with patch.object(QMessageBox, "information") as info:
            window.settings_tab._copy_path("/tmp/example")
        info.assert_not_called()
        assert QApplication.clipboard().text() == "/tmp/example"
        assert window.statusBar().currentMessage() == tr("msg_path_copied")

    def test_form_labels_line_up(self, tab):
        widths = {label.minimumWidth() for label in tab._form_labels}
        assert len(widths) == 1

    def test_advanced_options_section_is_kept(self, tab):
        assert tab.advanced_options.parent() is not None


# ---------------------------------------------------------- status bar


class TestStatusMessages:
    def test_shows_in_main_window(self, qtbot):
        window = QMainWindow()
        window.setStatusBar(QStatusBar())
        child = QLabel()
        window.setCentralWidget(child)
        qtbot.addWidget(window)
        assert show_status(child, "Saved.") is True
        assert window.statusBar().currentMessage() == "Saved."

    def test_without_window_only_logs(self, qtbot, monkeypatch):
        monkeypatch.setattr(QApplication, "topLevelWidgets", staticmethod(lambda: []))
        label = QLabel()
        qtbot.addWidget(label)
        assert show_status(label, "Saved.") is False


# ------------------------------------------------------------- dialogs


def _playlist(count=3):
    videos = [
        PlaylistVideoInfo(title=f"Video {i}", url=f"https://example.com/v{i}", duration=60, uploader="U", index=i)
        for i in range(1, count + 1)
    ]
    return PlaylistInfo(title="List", url="https://example.com/list", video_count=count, uploader="U", videos=videos)


class TestDialogs:
    def test_batch_counts_valid_and_invalid(self, qtbot):
        valid, invalid = split_urls("https://a.example.com/x\n\nnot a url\nhttps://b.example.com/y")
        assert valid == ["https://a.example.com/x", "https://b.example.com/y"]
        assert invalid == [(3, "not a url")]
        dialog = BatchInputDialog()
        qtbot.addWidget(dialog)
        dialog.url_text.setPlainText("https://a.example.com/x\nnope")
        assert dialog.count_label.text() == tr("label_batch_counts", valid=1, invalid=1)
        assert dialog.clear_btn.text() == TRANSLATIONS["en"]["button_clear"]

    def test_playlist_rows_are_checkable_items(self, qtbot):
        dialog = PlaylistDialog(_playlist(3))
        qtbot.addWidget(dialog)
        assert dialog.selected_video_count() == 3
        dialog.set_row_checked(1, False)
        assert dialog.selected_video_count() == 2
        assert dialog.add_button.text() == tr("button_add_videos_to_queue", count=2)
        with qtbot.waitSignal(dialog.videos_selected, timeout=1000) as blocker:
            dialog._on_download_clicked()
        assert blocker.args[0] == ["https://example.com/v1", "https://example.com/v3"]

    def test_playlist_subtitles_closed_by_default(self, qtbot):
        dialog = PlaylistDialog(_playlist(1))
        qtbot.addWidget(dialog)
        assert dialog.subtitle_section.isHidden()
        dialog.subtitle_header.setChecked(True)
        assert not dialog.subtitle_section.isHidden()

    def test_subtitle_dialog_is_translated(self, qtbot):
        get_translation_manager().set_language("he")
        dialog = SubtitleSelectionDialog({"en": "English", "de": {"name": "German", "auto": True}})
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == TRANSLATIONS["he"]["dialog_select_subtitle_languages"]
        assert TRANSLATIONS["he"]["text_auto_generated"] in dialog.subtitle_list.item(1).text()

    def test_subtitle_dialog_returns_checked_codes(self, qtbot):
        dialog = SubtitleSelectionDialog({"en": "English", "es": "Spanish"})
        qtbot.addWidget(dialog)
        dialog.subtitle_list.item(1).setCheckState(Qt.Checked)
        dialog._on_ok_clicked()
        assert dialog.get_selected_languages() == ["es"]

    def test_update_dialog_renders_markdown_and_keeps_buttons(self, qtbot):
        dialog = UpdateDialog({"version": "9.9.9", "body": "## New\n- one\n- two", "html_url": "javascript:alert(1)"})
        qtbot.addWidget(dialog)
        assert "## New" not in dialog.notes_text.toPlainText()
        assert "New" in dialog.notes_text.toPlainText()
        assert "javascript" not in dialog.links_label.text()
        assert dialog.download_btn.property("buttonStyle") == "primary"
        assert dialog.skip_btn.property("buttonStyle") is None

    @pytest.mark.parametrize(
        "url, ok",
        [("https://github.com/x", True), ("http://a.b", True), ("file:///etc/passwd", False), ("javascript:x", False)],
    )
    def test_update_dialog_opens_only_web_links(self, url, ok):
        assert is_web_url(url) is ok

    def test_update_dialog_ignores_raw_html_in_notes(self, qtbot):
        dialog = UpdateDialog({"version": "9.9.9", "body": "Hi <b>there</b>"})
        qtbot.addWidget(dialog)
        # Raw HTML is shown as text, not rendered.
        assert "<b>there</b>" in dialog.notes_text.toPlainText()

    def test_error_dialog_copy_keeps_it_open(self, qtbot):
        box = build_download_error_dialog(None, "HTTP Error 403: Forbidden")
        qtbot.addWidget(box)
        box.show()
        copy_button = next(b for b in box.buttons() if b.text() == tr("button_copy_details"))
        copy_button.click()
        assert QApplication.clipboard().text() == "HTTP Error 403: Forbidden"
        assert box.isVisible()
        assert copy_button.text() == tr("text_copied")
        box.close()


# ------------------------------------------------------- shared widgets


class TestSharedWidgets:
    def test_progress_widget_has_no_inline_colors(self, qtbot):
        widget = DownloadProgressWidget()
        qtbot.addWidget(widget)
        widget.set_error_state("boom")
        assert widget.progress_bar.styleSheet() == ""
        assert widget.progress_bar.property("progressState") == "error"
        widget.reset()
        assert widget.progress_bar.property("progressState") == ""

    def test_progress_values_stay_left_to_right(self, qtbot):
        widget = DownloadProgressWidget()
        qtbot.addWidget(widget)
        widget.update_progress(50, speed=1_500_000, total_bytes=10_000_000)
        assert LRI in widget.speed_label.text()
        assert PDI in widget.speed_label.text()

    def test_log_redraws_in_new_theme_colors(self, qtbot):
        log = LogWidget()
        qtbot.addWidget(log)
        log.append_warning("careful <b>")
        dark = ModernTheme.COLORS["dark"]["warning"]
        light = ModernTheme.COLORS["light"]["warning"]
        assert dark in log.toHtml()
        get_theme_manager().apply_theme(ThemeMode.LIGHT)
        assert light in log.toHtml()
        assert "careful <b>" in log.toPlainText()
        get_theme_manager().apply_theme(ThemeMode.DARK)

    def test_ltr_wraps_in_isolate(self):
        assert ltr("12 MB") == f"{LRI}12 MB{PDI}"

    def test_widgets_have_no_inline_hex_colors(self):
        # Widgets in part A take colors from the theme only.
        from pathlib import Path

        ui = Path(theme_module.__file__).parent
        for name in (
            "progress_bar.py",
            "log_widget.py",
            "video_info_dialog.py",
            "subtitle_selection_dialog.py",
            "playlist_dialog.py",
            "batch_input_dialog.py",
            "update_dialog.py",
            "about_tab.py",
            "settings_tab.py",
        ):
            text = (ui / name).read_text(encoding="utf-8")
            assert not re.search(r"#[0-9a-fA-F]{6}\b", text), name
