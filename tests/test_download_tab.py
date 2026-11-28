"""
Tests for the Download tab.

"Download" and "Add to queue" share one code path (``DownloadTab.submit``):
the same link and folder checks, the same playlist question and the same
duplicate question. Download starts at once, also while the queue is
paused; Add to queue respects a paused queue. Workers are replaced with
mocks, so no test downloads anything.
"""

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QMessageBox, QPushButton

import src.backend.queue_manager as qm_module
from src.backend.config_manager import ConfigManager
from src.backend.queue_manager import QueueManager
from src.models.download_task import TaskStatus
from src.ui import download_tab as dt_module
from src.ui.display_format import strip_isolates
from src.ui.download_tab import PLAYLIST_CANCEL, PLAYLIST_CHOOSE, PLAYLIST_WHOLE, DownloadTab
from src.utils.site_tiers import SiteTier
from src.utils.translations import get_translation_manager, tr

VIDEO = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
PLAYLIST = "https://www.youtube.com/playlist?list=PLsample123"


@pytest.fixture(autouse=True)
def force_english_ui():
    get_translation_manager().set_language("en")
    yield
    get_translation_manager().set_language("en")


@pytest.fixture(autouse=True)
def fake_worker(monkeypatch):
    """Queue workers are mocks: start() does nothing, so nothing downloads."""
    created = []

    def factory(task):
        worker = MagicMock(name=f"worker-{task.url}")
        worker.task = task
        created.append(worker)
        return worker

    monkeypatch.setattr(qm_module, "DownloadWorker", factory)
    return created


@pytest.fixture
def config_manager(tmp_path):
    out = tmp_path / "downloads"
    out.mkdir()
    manager = ConfigManager(config_path=tmp_path / "config.json")
    manager.load_config()
    manager.update_config(output_directory=str(out), last_url="")
    return manager


@pytest.fixture
def queue_manager():
    return QueueManager(max_concurrent=3)


@pytest.fixture
def window(qtbot, config_manager, queue_manager):
    """The tab inside a QMainWindow, so status messages have a status bar."""
    with patch.object(DownloadTab, "_auto_detect_clipboard_url"):
        tab = DownloadTab(config_manager, queue_manager)
    win = QMainWindow()
    win.setCentralWidget(tab)
    qtbot.addWidget(win)
    win.tab = tab
    return win


@pytest.fixture
def tab(window):
    return window.tab


class TestLayout:
    def test_only_download_is_primary(self, tab):
        primary = [b for b in tab.findChildren(QPushButton) if b.property("buttonStyle") == "primary"]
        assert primary == [tab.download_button]
        assert tab.add_to_queue_button.property("buttonStyle") == "secondary"
        assert tab.batch_button.property("buttonStyle") == "secondary"

    def test_no_inline_colors(self, tab):
        for button in tab.findChildren(QPushButton):
            assert button.styleSheet() == ""

    def test_labels_and_placeholder(self, tab):
        assert tab.url_input.placeholderText() == "Paste a video or playlist link (YouTube and many other sites)"
        assert tab.download_button.text() == "Download"
        assert tab.add_to_queue_button.text() == "Add to queue"
        assert tab.batch_button.text() == "Batch links..."

    def test_more_options_and_log_are_folded(self, tab):
        assert not tab.more_section.is_expanded()
        assert not tab.log_section.is_expanded()
        assert tab.more_section.summary_label.text() == "All off, no speed limit"

    def test_more_options_summary(self, tab):
        tab.subtitles_checkbox.setChecked(True)
        tab.speed_limit_spinbox.setValue(500)
        summary = strip_isolates(tab.more_section.summary_label.text())
        assert summary == "Subtitles (en), Speed limit 500 KB/s"
        tab.more_section.set_expanded(True)
        assert tab.more_section.content.isVisibleTo(tab.more_section)
        assert not tab.more_section.summary_label.isVisibleTo(tab.more_section)

    def test_subtitle_widgets_follow_checkbox(self, tab):
        assert not tab.subtitle_langs_input.isEnabled()
        tab.subtitles_checkbox.setChecked(True)
        assert tab.subtitle_langs_input.isEnabled() and tab.select_subs_button.isEnabled()

    def test_audio_mode_swaps_format_combo(self, tab):
        tab.download_type_combo.setCurrentIndex(tab.download_type_combo.findData("audio"))
        assert tab._is_audio_mode
        assert tab.audio_format_combo.isVisibleTo(tab) and not tab.container_combo.isVisibleTo(tab)
        assert tab.quality_combo.currentData() == "Best Quality"

    def test_quality_from_config_by_key(self, qtbot, config_manager, queue_manager):
        config_manager.update_config(default_quality="720p (HD)")
        with patch.object(DownloadTab, "_auto_detect_clipboard_url"):
            tab = DownloadTab(config_manager, queue_manager)
        qtbot.addWidget(tab)
        assert tab.quality_combo.currentData() == "720p (HD)"

    def test_fits_small_window_with_scroll_area(self, window):
        window.resize(1000, 700)
        window.show()
        assert window.tab.scroll_area.widgetResizable()
        assert window.tab.scroll_area.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff

    def test_settings_link(self, qtbot, tab):
        with qtbot.waitSignal(tab.open_settings_requested):
            tab.open_settings_button.click()

    def test_open_queue_link(self, qtbot, tab):
        with qtbot.waitSignal(tab.open_queue_requested):
            tab.now_panel.open_queue_button.click()


class TestSiteTier:
    def test_icon_and_text(self, tab):
        assert not tab.site_tier_row.isVisibleTo(tab)
        tab.url_input.setText(VIDEO)
        assert tab.site_tier_row.isVisibleTo(tab)
        assert tab.site_tier_label.tier == SiteTier.TESTED
        assert not tab.site_tier_icon.pixmap().isNull()
        tab.url_input.setText("https://vimeo.com/1")
        assert tab.site_tier_label.tier == SiteTier.EXPERIMENTAL
        assert not tab.site_tier_icon.pixmap().isNull()
        tab.url_input.setText("not a link")
        assert not tab.site_tier_row.isVisibleTo(tab)


class TestValidation:
    def test_empty_link_shows_inline_error_without_dialog(self, tab, queue_manager):
        with patch.object(QMessageBox, "warning") as warning:
            tab._on_download_clicked()
        warning.assert_not_called()
        assert tab.url_error_label.isVisibleTo(tab)
        assert tab.url_error_label.text() == "Paste a link first."
        assert tab.url_input.property("invalid") == "true"
        assert queue_manager.get_all_tasks() == []

    def test_invalid_link_message_and_reset_on_typing(self, tab):
        tab.url_input.setText("ftp://example.com/x")
        tab._on_add_to_queue_clicked()
        assert "http://" in strip_isolates(tab.url_error_label.text())
        tab.url_input.setText(VIDEO)
        assert not tab.url_error_label.isVisibleTo(tab)
        assert tab.url_input.property("invalid") == "false"

    def test_bad_folder_shows_inline_error(self, tab, queue_manager, tmp_path):
        tab.output_input.setText(str(tmp_path / "missing"))
        tab.url_input.setText(VIDEO)
        tab._on_download_clicked()
        assert tab.folder_error_label.isVisibleTo(tab)
        assert queue_manager.get_all_tasks() == []
        tab.update_output_directory(str(tmp_path))
        assert not tab.folder_error_label.isVisibleTo(tab)


class TestDownloadAndAddToQueue:
    def test_both_buttons_use_submit(self, tab):
        with patch.object(tab, "submit") as submit:
            tab.download_button.click()
            tab.add_to_queue_button.click()
        assert [c.kwargs for c in submit.call_args_list] == [{"start_now": True}, {"start_now": False}]

    def test_enter_runs_download(self, qtbot, tab):
        with patch.object(tab, "submit") as submit:
            tab.url_input.setFocus()
            qtbot.keyClick(tab.url_input, Qt.Key_Return)
        submit.assert_called_once_with(start_now=True)

    def test_download_starts_while_paused(self, window, tab, queue_manager, fake_worker):
        queue_manager.pause_queue()
        tab.url_input.setText(VIDEO)
        task = tab._on_download_clicked() or queue_manager.get_all_tasks()[0]
        assert len(fake_worker) == 1 and fake_worker[0].task is task
        fake_worker[0].start.assert_called_once()
        assert queue_manager.is_paused  # the queue itself stays paused
        assert window.statusBar().currentMessage() == "Download started."
        assert tab.url_input.text() == ""

    def test_add_to_queue_waits_while_paused(self, window, tab, queue_manager, fake_worker):
        queue_manager.pause_queue()
        tab.url_input.setText(VIDEO)
        tab._on_add_to_queue_clicked()
        assert len(queue_manager.get_all_tasks()) == 1
        assert fake_worker == []
        assert "The queue is paused" in window.statusBar().currentMessage()

    def test_add_to_queue_starts_when_running(self, window, tab, queue_manager, fake_worker):
        tab.url_input.setText(VIDEO)
        tab._on_add_to_queue_clicked()
        assert len(fake_worker) == 1
        assert window.statusBar().currentMessage() == "Added to the queue at position 1."

    def test_no_added_dialog(self, tab):
        tab.url_input.setText(VIDEO)
        with patch.object(QMessageBox, "information") as info:
            tab._on_add_to_queue_clicked()
        info.assert_not_called()

    def test_download_goes_first_when_slots_are_full(self, window, queue_manager, tab, fake_worker):
        queue_manager.queue.max_concurrent = 1
        queue_manager.pause_queue()
        tab.url_input.setText("https://www.youtube.com/watch?v=waiting1")
        tab._on_add_to_queue_clicked()
        tab.url_input.setText("https://www.youtube.com/watch?v=running1")
        tab._on_download_clicked()
        tab.url_input.setText(VIDEO)
        tab._on_download_clicked()
        assert window.statusBar().currentMessage() == "The download starts as soon as a running download finishes."
        assert [w.task.url for w in fake_worker] == ["https://www.youtube.com/watch?v=running1"]

        # The running download ends: the "Download" task starts, the waiting one does not.
        running = fake_worker[0]
        running.task.complete("a.mp4")
        queue_manager._on_worker_completed(running, "a.mp4")
        assert [w.task.url for w in fake_worker][-1] == VIDEO

    @pytest.mark.parametrize("start_now", [True, False])
    def test_duplicate_question_for_both(self, tab, queue_manager, start_now):
        queue_manager.pause_queue()
        tab.url_input.setText(VIDEO)
        tab._on_add_to_queue_clicked()
        tab.url_input.setText(VIDEO)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.No) as question:
            assert tab.submit(start_now=start_now) is None
        question.assert_called_once()
        assert len(queue_manager.get_all_tasks()) == 1

    @pytest.mark.parametrize("start_now", [True, False])
    def test_duplicate_yes_adds_again(self, tab, queue_manager, start_now):
        queue_manager.pause_queue()
        tab.url_input.setText(VIDEO)
        tab._on_add_to_queue_clicked()
        tab.url_input.setText(VIDEO)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            assert tab.submit(start_now=start_now) is not None
        assert len(queue_manager.get_all_tasks()) == 2

    @pytest.mark.parametrize("start_now", [True, False])
    def test_playlist_question_for_both(self, tab, queue_manager, start_now):
        tab.url_input.setText(PLAYLIST)
        with (
            patch.object(tab, "_ask_playlist_choice", return_value=PLAYLIST_CHOOSE) as ask,
            patch.object(tab, "_fetch_playlist_info") as fetch,
        ):
            assert tab.submit(start_now=start_now) is None
        ask.assert_called_once_with("youtube")
        fetch.assert_called_once()
        assert tab._playlist_start_now is start_now
        assert queue_manager.get_all_tasks() == []

    def test_playlist_whole_and_cancel(self, tab, queue_manager):
        queue_manager.pause_queue()
        tab.url_input.setText(PLAYLIST)
        with patch.object(tab, "_ask_playlist_choice", return_value=PLAYLIST_CANCEL):
            assert tab.submit(start_now=False) is None
        with patch.object(tab, "_ask_playlist_choice", return_value=PLAYLIST_WHOLE):
            task = tab.submit(start_now=False)
        assert task is not None and task.url == PLAYLIST

    def test_playlist_question_buttons(self, tab):
        """The question has named buttons and says YouTube with a capital Y."""
        seen = {}

        def fake_exec(box):
            seen["text"] = box.text()
            seen["buttons"] = [b.text() for b in box.buttons()]
            return 0

        with patch.object(QMessageBox, "exec", fake_exec):
            assert tab._ask_playlist_choice("youtube") == PLAYLIST_CANCEL
        assert "YouTube playlist" in seen["text"]
        assert {"Choose videos...", "Whole playlist", "Cancel"} <= set(seen["buttons"])

    def test_playlist_videos_follow_start_now(self, window, tab, queue_manager, fake_worker):
        queue_manager.pause_queue()
        tab._playlist_start_now = True
        urls = [f"https://www.youtube.com/watch?v=pl{i}" for i in range(2)]
        tab._on_playlist_videos_selected(urls, "Best Quality", ["he"])
        assert len(fake_worker) == 2
        tasks = queue_manager.get_all_tasks()
        assert all(t.download_subtitles and t.subtitle_languages == "he" for t in tasks)
        assert window.statusBar().currentMessage() == "Added 2 videos to the queue."
        assert tab._playlist_start_now is False

    def test_task_fields_from_form(self, tab, queue_manager):
        queue_manager.pause_queue()
        tab.url_input.setText(VIDEO)
        tab.thumbnail_checkbox.setChecked(True)
        tab.speed_limit_spinbox.setValue(300)
        tab.quality_combo.setCurrentIndex(tab.quality_combo.findData("720p (HD)"))
        task = tab.submit(start_now=False)
        assert task.quality == "720p (HD)"
        assert task.download_thumbnail is True
        assert task.speed_limit == 300
        assert task.status == TaskStatus.PENDING

    def test_batch_links_go_to_queue(self, window, tab, queue_manager):
        queue_manager.pause_queue()
        dialog = MagicMock()
        dialog.exec.return_value = True
        dialog.get_urls.return_value = [VIDEO, "https://vimeo.com/2"]
        with patch("src.ui.batch_input_dialog.BatchInputDialog", return_value=dialog):
            tab._on_batch_input_clicked()
        assert len(queue_manager.get_all_tasks()) == 2
        assert window.statusBar().currentMessage() == "Added 2 links to the queue."


class TestActivityLog:
    def test_queue_events_go_to_the_log(self, tab, queue_manager):
        queue_manager.task_started.emit(0, "Me at the zoo")
        queue_manager.task_completed.emit(0, "Me at the zoo.mp4")
        queue_manager.task_failed.emit(0, "boom")
        text = tab.log_widget.toPlainText()
        assert "Me at the zoo" in text and "Me at the zoo.mp4" in text and "boom" in text

    def test_subtitles_none_found_is_a_status_message(self, window, tab):
        with patch.object(QMessageBox, "information") as info:
            tab._on_subtitle_list_fetched({})
        info.assert_not_called()
        assert window.statusBar().currentMessage() == tr("msg_no_subs_available")


class TestOpenFolder:
    def test_open_folder_uses_desktop(self, tab, config_manager):
        with patch.object(dt_module, "open_local_path", return_value=True) as opener:
            tab._open_directory()
        opener.assert_called_once_with(config_manager.get_config().output_directory)

    def test_missing_folder_warns(self, tab, tmp_path):
        tab.output_input.setText(str(tmp_path / "nope"))
        with patch.object(QMessageBox, "warning") as warning:
            tab._open_directory()
        warning.assert_called_once()


class TestInfoPlaylistAndSubtitles:
    def test_info_button_routes_video_and_playlist(self, tab):
        tab.url_input.setText(VIDEO)
        with patch.object(tab, "_fetch_video_info") as video:
            tab.show_info_button.click()
        video.assert_called_once_with(VIDEO)
        tab.url_input.setText(PLAYLIST)
        tab._playlist_start_now = True
        with patch.object(tab, "_fetch_playlist_info") as playlist:
            tab.show_info_button.click()
        playlist.assert_called_once()
        assert tab._playlist_start_now is False  # videos picked after Info wait in the queue

    def test_info_dialog_download_button_starts_download(self, tab):
        from src.models.video_info import VideoInfo

        def press_download(dialog_self):
            dialog_self.download_requested.emit()
            return 1

        with (
            patch("src.ui.video_info_dialog.VideoInfoDialog._load_thumbnail"),
            patch("src.ui.video_info_dialog.VideoInfoDialog.exec", press_download),
            patch.object(tab, "_on_download_clicked") as download,
        ):
            tab._on_info_fetched(VideoInfo(title="t", url=VIDEO))
        download.assert_called_once()

    def test_info_dialog_closed_without_download(self, tab):
        from src.models.video_info import VideoInfo

        with (
            patch("src.ui.video_info_dialog.VideoInfoDialog._load_thumbnail"),
            patch("src.ui.video_info_dialog.VideoInfoDialog.exec", return_value=0),
            patch.object(tab, "_on_download_clicked") as download,
        ):
            tab._on_info_fetched(VideoInfo(title="t", url=VIDEO))
        download.assert_not_called()

    def test_error_dialog_has_copy_details(self, tab):
        shown = []
        with patch.object(QMessageBox, "exec", lambda box: shown.append(box) or 0):
            tab._on_info_fetch_failed("HTTP Error 403: Forbidden")
        assert any(b.text() == tr("button_copy_details") for b in shown[0].buttons())

    def test_info_with_bad_link_is_inline(self, tab):
        with patch.object(tab, "_fetch_video_info") as video:
            tab.show_info_button.click()
        video.assert_not_called()
        assert tab.url_error_label.isVisibleTo(tab)

    def test_info_fetched_and_failed(self, tab):
        from src.models.video_info import VideoInfo

        with patch.object(dt_module, "VideoInfoDialog") as dialog:
            tab._on_info_fetched(VideoInfo(title="t", url=VIDEO))
        dialog.return_value.exec.assert_called_once()
        assert tab.site_tier_label.tier == SiteTier.TESTED
        with patch.object(QMessageBox, "exec", return_value=0) as exec_:
            tab._on_info_fetch_failed("HTTP Error 403: Forbidden")
            tab._on_playlist_fetch_failed("HTTP Error 404: Not Found")
        assert exec_.call_count == 2
        tab._on_info_worker_finished()
        tab._on_playlist_worker_finished()
        assert tab.show_info_button.isEnabled() and tab.show_info_button.text() == "Info"

    def test_playlist_fetched_opens_dialog(self, tab):
        info = MagicMock(title="List", video_count=3)
        with patch.object(dt_module, "PlaylistDialog") as dialog:
            tab._on_playlist_fetched(info)
        dialog.return_value.exec.assert_called_once()

    def test_empty_playlist_selection(self, tab, queue_manager):
        tab._on_playlist_videos_selected([], "Best Quality")
        assert queue_manager.get_all_tasks() == []

    def test_subtitle_selection(self, tab):
        tab.subtitles_checkbox.setChecked(True)
        with patch.object(dt_module, "SubtitleSelectionDialog") as dialog:
            dialog.return_value.exec.return_value = True
            dialog.return_value.get_selected_languages.return_value = ["he", "en"]
            tab._on_subtitle_list_fetched({"he": "Hebrew", "en": "English"})
        assert tab.subtitle_langs_input.text() == "he,en"
        assert tab.selected_subtitle_codes == ["he", "en"]
        with patch.object(dt_module, "SubtitleSelectionDialog") as dialog:
            dialog.return_value.exec.return_value = True
            dialog.return_value.get_selected_languages.return_value = []
            tab._on_subtitle_list_fetched({"he": "Hebrew"})
        assert tab.subtitle_langs_input.text() == ""

    def test_subtitle_fetch_failed_and_finished(self, tab):
        tab.subtitles_checkbox.setChecked(True)
        with patch.object(QMessageBox, "critical") as critical:
            tab._on_subtitle_list_failed("no network")
        critical.assert_called_once()
        tab._on_subtitle_list_finished()
        assert tab.select_subs_button.isEnabled()
        assert tab.select_subs_button.text() == "Choose..."

    def test_choose_subtitles_needs_a_link(self, tab):
        tab.subtitles_checkbox.setChecked(True)
        with patch.object(dt_module, "SubtitleListWorker") as worker:
            tab.select_subs_button.click()
        worker.assert_not_called()
        tab.url_input.setText(VIDEO)
        with patch.object(dt_module, "SubtitleListWorker") as worker:
            tab.select_subs_button.click()
        worker.return_value.start.assert_called_once()


class TestPasteAndDrop:
    def test_paste(self, tab):
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(VIDEO)
        tab.paste_button.click()
        assert tab.url_input.text() == VIDEO

    def test_drop(self, tab):
        event = MagicMock()
        event.mimeData.return_value.hasText.return_value = True
        event.mimeData.return_value.text.return_value = f" {VIDEO} "
        tab._drag_enter_event(event)
        event.acceptProposedAction.assert_called_once()
        tab._drop_event(event)
        assert tab.url_input.text() == VIDEO
        event.mimeData.return_value.hasText.return_value = False
        tab._drag_enter_event(event)
        tab._drop_event(event)
        assert event.ignore.call_count == 2

    def test_clipboard_link_fills_empty_field(self, qtbot, config_manager, queue_manager):
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(VIDEO)
        tab = DownloadTab(config_manager, queue_manager)
        qtbot.addWidget(tab)
        assert tab.url_input.text() == VIDEO
