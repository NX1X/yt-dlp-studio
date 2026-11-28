"""
Tests for the History tab: the summary line, search plus the status
filter, the "No matches" state, the row menu, the Clear menu and the
status bar messages instead of information pop-ups.
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox

import src.backend.history_manager as hm_module
from src.backend.history_manager import HistoryManager
from src.models.download_task import DownloadTask
from src.ui import history_tab as ht_module
from src.ui.display_format import strip_isolates
from src.ui.history_tab import COL_QUALITY, COL_SIZE, COL_STATUS, COL_TITLE, HistoryTab
from src.ui.table_delegates import STATUS_KIND_ROLE
from src.utils.translations import get_translation_manager, tr

ENTRIES = [
    ("Lofi Beats to Study To - 2 Hour Mix", "Best Quality", "completed", 412_000_000),
    ("How Rainbows Form", "1080p (Full HD)", "completed", 98_500_000),
    ("Unboxing the Tiny Desk Synth", "720p (HD)", "failed", 0),
    ("Mountain Timelapse 4K", "Best Quality", "cancelled", 12_000_000),
]


@pytest.fixture(autouse=True)
def force_english_ui():
    get_translation_manager().set_language("en")
    yield
    get_translation_manager().set_language("en")


@pytest.fixture
def history_manager(tmp_path, monkeypatch):
    monkeypatch.setattr(hm_module, "APP_DATA_DIR", tmp_path)
    manager = HistoryManager()
    now = datetime(2026, 11, 28, 12, 0)
    for i, (title, quality, status, size) in enumerate(ENTRIES):
        task = DownloadTask(
            url=f"https://www.youtube.com/watch?v=h{i}", output_directory=str(tmp_path), quality=quality
        )
        task.title = title
        task.filename = f"{i}.mp4"
        task.file_size = size
        task.download_speed = 2_000_000
        manager.add_download(task, status, error_message="HTTP Error 403: Forbidden" if status == "failed" else "")
    for i, entry in enumerate(manager.history.entries):
        entry.timestamp = now - timedelta(hours=i)
    return manager


@pytest.fixture
def window(qtbot, history_manager):
    tab = HistoryTab(history_manager)
    win = QMainWindow()
    win.setCentralWidget(tab)
    qtbot.addWidget(win)
    win.tab = tab
    return win


@pytest.fixture
def tab(window):
    return window.tab


def titles(tab):
    return [tab.history_table.item(r, COL_TITLE).text() for r in range(tab.history_table.rowCount())]


class TestSummaryAndTable:
    def test_summary_line(self, tab):
        text = strip_isolates(tab.stats_label.text())
        assert text == "4 downloads: 2 done, 1 failed, 1 cancelled, 486.85 MB in total"
        assert "Success rate" in tab.stats_label.toolTip()

    def test_columns_and_full_title(self, tab):
        headers = [tab.history_table.horizontalHeaderItem(c).text() for c in range(5)]
        assert headers == ["Date/Time", "Title", "Status", "Quality", "Size"]
        assert "Lofi Beats to Study To - 2 Hour Mix" in titles(tab)

    def test_status_kind_and_quality_label(self, tab):
        row = titles(tab).index("Unboxing the Tiny Desk Synth")
        assert tab.history_table.item(row, COL_STATUS).data(STATUS_KIND_ROLE) == "failed"
        assert "HTTP Error 403" in tab.history_table.item(row, COL_TITLE).toolTip()
        assert tab.history_table.item(row, COL_QUALITY).text() == tr("quality_720p")

    def test_size_is_rtl_safe(self, tab):
        text = tab.history_table.item(0, COL_SIZE).text()
        assert text.startswith("\u2066") and text.endswith("\u2069")

    def test_empty_history(self, qtbot, tmp_path, monkeypatch):
        monkeypatch.setattr(hm_module, "APP_DATA_DIR", tmp_path / "empty")
        tab = HistoryTab(HistoryManager())
        qtbot.addWidget(tab)
        assert tab._history_stack.currentIndex() == 1
        assert not tab.clear_button.isEnabled()

    def test_refresh_shows_new_entries(self, tab, history_manager):
        task = DownloadTask(url="https://vimeo.com/9", output_directory="/tmp", quality="360p")
        task.title = "Fresh"
        history_manager.add_download(task, "completed")
        tab.refresh()
        assert titles(tab)[0] == "Fresh"


class TestSearchAndFilter:
    def test_search(self, tab):
        tab.search_input.setText("rainbow")
        assert titles(tab) == ["How Rainbows Form"]
        # Search results keep their status kinds (colors)
        assert tab.history_table.item(0, COL_STATUS).data(STATUS_KIND_ROLE) == "done"

    def test_search_by_link(self, tab):
        tab.search_input.setText("watch?v=h3")
        assert titles(tab) == ["Mountain Timelapse 4K"]

    def test_status_filter(self, tab):
        tab.status_filter.setCurrentIndex(tab.status_filter.findData("completed"))
        assert sorted(titles(tab)) == ["How Rainbows Form", "Lofi Beats to Study To - 2 Hour Mix"]
        tab.status_filter.setCurrentIndex(tab.status_filter.findData("failed"))
        assert titles(tab) == ["Unboxing the Tiny Desk Synth"]

    def test_search_and_filter_together(self, tab):
        tab.status_filter.setCurrentIndex(tab.status_filter.findData("failed"))
        tab.search_input.setText("lofi")
        assert titles(tab) == []
        assert tab._history_stack.currentIndex() == 2  # "No matches", not the first-run empty state
        tab.search_input.clear()
        assert titles(tab) == ["Unboxing the Tiny Desk Synth"]
        assert tab._history_stack.currentIndex() == 0

    def test_search_results_newest_first(self, tab):
        tab.search_input.setText("o")
        rows = titles(tab)
        assert rows[0] == "Mountain Timelapse 4K"  # added last, newest


class TestRowMenu:
    def _menu(self, tab, title):
        row = titles(tab).index(title)
        return {a.objectName(): a for a in tab.build_context_menu(row).actions() if a.objectName()}

    def test_actions_enabled_by_status(self, tab):
        done = self._menu(tab, "How Rainbows Form")
        failed = self._menu(tab, "Unboxing the Tiny Desk Synth")
        assert done["open_file"].isEnabled() and not failed["open_file"].isEnabled()
        assert failed["download_again"].isEnabled() and failed["copy_link"].isEnabled()

    def test_copy_link(self, window, tab):
        self._menu(tab, "How Rainbows Form")["copy_link"].trigger()
        assert QGuiApplication.clipboard().text() == "https://www.youtube.com/watch?v=h1"
        assert window.statusBar().currentMessage() == "Link copied."

    def test_download_again(self, qtbot, tab):
        with qtbot.waitSignal(tab.download_again_requested) as blocker:
            self._menu(tab, "Unboxing the Tiny Desk Synth")["download_again"].trigger()
        assert blocker.args == ["https://www.youtube.com/watch?v=h2"]

    def test_remove_from_history_menu_item(self, window, tab, history_manager):
        self._menu(tab, "How Rainbows Form")["remove"].trigger()
        assert "How Rainbows Form" not in titles(tab)
        assert len(history_manager.get_history()) == 3
        assert window.statusBar().currentMessage() == "Removed the entry from the history."
        assert strip_isolates(tab.stats_label.text()).startswith("3 downloads")

    def test_remove_is_in_the_menu_text(self, tab):
        row = titles(tab).index("How Rainbows Form")
        texts = [a.text() for a in tab.build_context_menu(row).actions()]
        assert "Remove from history" in texts

    def test_delete_key_removes_the_selected_entry(self, tab):
        row = titles(tab).index("Unboxing the Tiny Desk Synth")
        tab.history_table.selectRow(row)
        tab.delete_shortcut.activated.emit()
        assert "Unboxing the Tiny Desk Synth" not in titles(tab)
        assert len(titles(tab)) == 3

    def test_delete_key_without_selection_does_nothing(self, tab):
        tab.history_table.clearSelection()
        tab.delete_shortcut.activated.emit()
        assert len(titles(tab)) == 4

    def test_open_file_and_folder(self, tab, tmp_path):
        (tmp_path / "1.mp4").write_bytes(b"x")
        with patch.object(ht_module, "open_local_path", return_value=True) as opener:
            self._menu(tab, "How Rainbows Form")["open_file"].trigger()
            self._menu(tab, "How Rainbows Form")["open_folder"].trigger()
        assert [c.args[0] for c in opener.call_args_list] == [str(tmp_path / "1.mp4"), str(tmp_path)]

    def test_missing_file_warns(self, tab):
        with patch.object(QMessageBox, "warning") as warning, patch.object(ht_module, "open_local_path") as opener:
            self._menu(tab, "Lofi Beats to Study To - 2 Hour Mix")["open_file"].trigger()
        warning.assert_called_once()
        opener.assert_not_called()

    def test_double_click(self, qtbot, tab):
        row = titles(tab).index("Unboxing the Tiny Desk Synth")
        with qtbot.waitSignal(tab.download_again_requested):
            tab._on_row_double_clicked(row, 0)


class TestClearAndExport:
    def test_clear_menu_items(self, tab):
        texts = [a.text() for a in tab.clear_button.menu().actions() if not a.isSeparator()]
        assert texts == ["Clear completed", "Clear failed", "Clear all history"]
        assert tab.clear_button.property("buttonStyle") == "danger"

    def test_clear_completed_asks_and_reports_in_status_bar(self, window, tab):
        with (
            patch.object(QMessageBox, "question", return_value=QMessageBox.Yes) as question,
            patch.object(QMessageBox, "information") as info,
        ):
            tab.clear_completed_action.trigger()
        question.assert_called_once()
        info.assert_not_called()
        assert "How Rainbows Form" not in titles(tab)
        assert window.statusBar().currentMessage() == "Removed 2 entries from the history."

    def test_clear_all_no_keeps_entries(self, tab):
        with patch.object(QMessageBox, "question", return_value=QMessageBox.No):
            tab.clear_all_action.trigger()
        assert len(titles(tab)) == 4

    def test_export_reports_in_status_bar(self, window, tab, tmp_path):
        target = tmp_path / "out.csv"
        with patch.object(QFileDialog, "getSaveFileName", return_value=(str(target), "")):
            tab._export_csv()
        assert target.exists()
        assert "History saved to" in window.statusBar().currentMessage()

    def test_open_downloads_folder_uses_config(self, qtbot, history_manager, tmp_path):
        from src.backend.config_manager import ConfigManager

        config = ConfigManager(config_path=tmp_path / "c.json")
        config.load_config()
        config.update_config(output_directory=str(tmp_path))
        tab = HistoryTab(history_manager, config_manager=config)
        qtbot.addWidget(tab)
        with patch.object(ht_module, "open_local_path", return_value=True) as opener:
            tab.open_dir_button.click()
        opener.assert_called_once_with(str(tmp_path))


class TestHebrew:
    def test_hebrew_summary_and_filter(self, qtbot, history_manager):
        get_translation_manager().set_language("he")
        tab = HistoryTab(history_manager)
        qtbot.addWidget(tab)
        assert tab.status_filter.itemText(0) == tr("filter_all_statuses")
        assert strip_isolates(tab.stats_label.text()).startswith("4 הורדות")
