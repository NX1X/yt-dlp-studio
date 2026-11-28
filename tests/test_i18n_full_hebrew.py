"""Hebrew coverage: plural forms, stable format keys, error texts, log lines.

These tests cover the changes of the "full Hebrew" pass. The audit and the
Hebrew screen scan (test_i18n_audit.py, test_hebrew_ui_has_no_english.py)
guard against new English text; this file checks that the moved texts work.
"""

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QMainWindow

import src.backend.queue_manager as qm_module
from src.backend.config_manager import ConfigManager
from src.backend.format_handler import FormatHandler
from src.backend.queue_manager import QueueManager
from src.backend.yt_dlp_wrapper import YtDlpWrapper
from src.ui.download_tab import DownloadTab
from src.utils.constants import AUDIO_FORMATS, VIDEO_CONTAINER_FORMATS
from src.utils.error_handler import ErrorCategory, ErrorHandler
from src.utils.translations import TRANSLATIONS, get_translation_manager, tr, tr_count


@pytest.fixture
def language():
    manager = get_translation_manager()

    def _set(code):
        manager.set_language(code)

    yield _set
    manager.set_language("en")


class TestTrCount:
    def test_one_uses_the_singular_text_in_hebrew(self, language):
        language("he")
        assert tr_count("summary_waiting", 1) == tr("summary_waiting_one", count=1)
        assert "1 ממתינות" not in tr_count("summary_waiting", 1)

    def test_other_numbers_use_the_plain_text(self, language):
        language("he")
        assert tr_count("summary_waiting", 2) == "2 ממתינות"
        assert tr_count("summary_waiting", 0) == "0 ממתינות"

    def test_english_uses_good_singular_forms(self, language):
        language("en")
        assert tr_count("status_videos_added", 1) == "Added 1 video to the queue."
        assert tr_count("status_videos_added", 3) == "Added 3 videos to the queue."

    def test_key_without_singular_text_uses_the_plain_text(self, language):
        language("he")
        assert "label_videos_count_one" not in TRANSLATIONS["he"]
        assert tr_count("label_videos_count", 1) == tr("label_videos_count", count=1)

    def test_hebrew_singular_texts_do_not_say_one_as_a_digit_with_a_plural(self):
        for key, text in TRANSLATIONS["he"].items():
            if key.endswith("_one"):
                assert "1 " not in text.replace("{count}", "N"), f"{key}: {text}"


class TestStableFormatKeys:
    @pytest.fixture
    def window(self, qtbot, tmp_path, monkeypatch, language):
        monkeypatch.setattr(qm_module, "DownloadWorker", lambda task: MagicMock(task=task))
        config = ConfigManager(config_path=tmp_path / "config.json")
        config.load_config()
        config.update_config(output_directory=str(tmp_path))
        language("he")
        with patch.object(DownloadTab, "_auto_detect_clipboard_url"):
            tab = DownloadTab(config, QueueManager(max_concurrent=3))
        window = QMainWindow()
        window.setCentralWidget(tab)
        qtbot.addWidget(window)
        window.tab = tab
        return window

    @pytest.fixture
    def tab(self, window):
        return window.tab

    def test_labels_are_hebrew_and_data_is_the_stable_key(self, tab):
        assert tab.container_combo.count() == len(VIDEO_CONTAINER_FORMATS)
        assert tab.audio_format_combo.count() == len(AUDIO_FORMATS)
        for i, key in enumerate(VIDEO_CONTAINER_FORMATS):
            assert tab.container_combo.itemData(i) == key
        for i, key in enumerate(AUDIO_FORMATS):
            assert tab.audio_format_combo.itemData(i) == key
        assert tab.container_combo.itemText(0) == tr("format_video_mp4")
        assert "Compatibility" not in tab.container_combo.itemText(0)
        assert "Compatible" not in tab.audio_format_combo.itemText(0)

    def test_download_uses_the_key_not_the_label(self, tab):
        tab.container_combo.setCurrentIndex(tab.container_combo.findData("WebM"))
        tab.audio_format_combo.setCurrentIndex(tab.audio_format_combo.findData("FLAC (Lossless)"))
        task = tab._build_task("https://www.youtube.com/watch?v=x", tab.output_input.text())
        assert task.video_container == "webm"
        assert task.audio_format == "flac"

    def test_defaults_are_unchanged(self, tab):
        task = tab._build_task("https://www.youtube.com/watch?v=x", tab.output_input.text())
        assert task.video_container == "mp4"
        assert task.audio_format == "mp3"


class TestErrorTexts:
    @pytest.mark.parametrize("category", list(ErrorCategory))
    def test_every_category_has_texts_in_both_languages(self, language, category):
        for code in ("en", "he"):
            language(code)
            title, message, suggestions = ErrorHandler.get_error_info("xyz")
            assert title
            assert message
            assert suggestions
        prefix = f"errcat_{category.value}"
        for part in ("title", "message", "suggestions"):
            assert TRANSLATIONS["en"][f"{prefix}_{part}"]
            assert TRANSLATIONS["he"][f"{prefix}_{part}"]

    def test_english_text_is_unchanged(self, language):
        language("en")
        title, message, suggestions = ErrorHandler.get_error_info("connection timeout")
        assert title == "Network Error"
        assert message == "Unable to connect to the internet or the video server."
        assert suggestions.splitlines()[0] == "• Check your internet connection"
        assert len(suggestions.splitlines()) == 4

    def test_unknown_error_shows_the_raw_detail(self, language):
        language("he")
        title, message, _ = ErrorHandler.get_error_info("weird failure")
        assert title == tr("errcat_unknown_title")
        assert "weird failure" in message


class TestOtherMovedTexts:
    def test_quality_descriptions_in_hebrew(self, language):
        language("he")
        assert "Recommended" not in FormatHandler.get_quality_description("1080p (Full HD)")
        assert FormatHandler.get_quality_description("nope") == tr("quality_desc_none")

    def test_language_names_in_hebrew(self, language):
        language("he")
        wrapper = YtDlpWrapper()
        assert wrapper._get_language_name("de") == "גרמנית"
        assert wrapper._get_language_name("iw") == wrapper._get_language_name("he") == "עברית"
        assert wrapper._get_language_name("xx") == "XX"

    def test_language_names_in_english_are_unchanged(self, language):
        language("en")
        wrapper = YtDlpWrapper()
        assert wrapper._get_language_name("zh-Hans") == "Chinese (Simplified)"
        assert wrapper._get_language_name("uk") == "Ukrainian"

    def test_activity_log_levels_are_translated(self, qtbot, language):
        from src.ui.log_widget import LogWidget

        language("he")
        log = LogWidget()
        qtbot.addWidget(log)
        log.append_error("x")
        log.append_info("y")
        text = log.toPlainText()
        assert "ERROR" not in text
        assert "INFO" not in text
        assert tr("log_level_error") in text
        assert tr("log_level_info") in text

    def test_activity_log_levels_in_english_are_unchanged(self, qtbot, language):
        from src.ui.log_widget import LogWidget

        language("en")
        log = LogWidget()
        qtbot.addWidget(log)
        log.append_error("x")
        assert "ERROR: x" in log.toPlainText()
