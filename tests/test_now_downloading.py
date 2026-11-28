"""
Tests for the "Now downloading" panel, the status bar helper and the
queue state in the main window status bar, the RTL-safe display helpers,
and the queue manager's "start now" request.

The panel is fed only by QueueManager signals. The tests drive those
signals the way the queue does: the worker writes the values to the task,
then QueueManager emits ``task_progress`` on the GUI thread.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QMainWindow, QVBoxLayout, QWidget

import src.backend.queue_manager as qm_module
from src.backend.queue_manager import QueueManager
from src.models.download_task import DownloadTask, TaskStatus
from src.ui import display_format as fmt
from src.ui.collapsible_section import CollapsibleSection
from src.ui.now_downloading import NowDownloadingPanel
from src.ui.status_messages import find_status_bar, show_status
from src.ui.theme import ThemeMode, get_theme_manager
from src.utils.translations import get_translation_manager, tr


@pytest.fixture(autouse=True)
def force_english_ui():
    get_translation_manager().set_language("en")
    yield
    get_translation_manager().set_language("en")


@pytest.fixture
def fake_worker(monkeypatch):
    created = []

    def factory(task):
        worker = MagicMock()
        worker.task = task
        created.append(worker)
        return worker

    monkeypatch.setattr(qm_module, "DownloadWorker", factory)
    return created


@pytest.fixture
def queue_manager():
    manager = QueueManager(max_concurrent=3)
    manager.pause_queue()
    return manager


@pytest.fixture
def panel(qtbot, queue_manager):
    widget = NowDownloadingPanel(queue_manager)
    qtbot.addWidget(widget)
    return widget


def make_task(i=0, **fields):
    task = DownloadTask(url=f"https://www.youtube.com/watch?v=n{i}", output_directory="/tmp", quality="Best Quality")
    for name, value in fields.items():
        setattr(task, name, value)
    return task


class TestNowDownloadingPanel:
    def test_empty_state(self, panel):
        assert panel.rows() == []
        assert panel.empty_label.isVisibleTo(panel)
        assert panel.empty_label.text() == tr("now_empty")

    def test_paused_empty_state_counts_waiting(self, panel, queue_manager):
        queue_manager.add_task(make_task(0))
        assert panel.empty_label.text() == tr("now_empty_paused", count=1)
        assert panel.summary_label.text() == "1 waiting, queue paused"

    def test_row_appears_and_moves_with_progress(self, panel, queue_manager, fake_worker):
        task = make_task(0)
        queue_manager.add_task(task, start_now=True)
        worker = fake_worker[0]

        # Like DownloadWorker.run(): status first, then the started signal
        task.start()
        queue_manager._on_worker_started(worker, "Me at the zoo")
        assert len(panel.rows()) == 1
        row = panel.rows()[0]
        assert row.speed_label.text() == tr("now_starting")
        assert row.progress_bar.maximum() == 0  # busy bar before the first report

        task.title = "Me at the zoo"
        task.update_progress(47.3, download_speed=3_400_000, eta_seconds=125, downloaded_bytes=10, file_size=100)
        queue_manager._on_worker_progress(worker, {"percent": 47.3})
        assert row.progress_bar.maximum() == 1000
        assert row.progress_bar.value() == 473
        assert fmt.strip_isolates(row.percent_label.text()) == "47%"
        assert fmt.strip_isolates(row.speed_label.text()) == "3.24 MB/s"
        assert fmt.strip_isolates(row.eta_label.text()) == "2:05 left"
        assert "Me at the zoo" in row.title_label.toolTip()

        task.update_progress(100.0)
        queue_manager._on_worker_progress(worker, {"percent": 100.0})
        assert row.speed_label.text() == tr("now_processing")

        task.complete("Me at the zoo.mp4")
        queue_manager._on_worker_completed(worker, "Me at the zoo.mp4")
        assert panel.rows() == []
        assert panel.empty_label.isVisibleTo(panel)

    def test_progress_before_queue_update_builds_row(self, panel, queue_manager):
        task = make_task(0, status=TaskStatus.DOWNLOADING, progress_percent=10.0, download_speed=100.0)
        queue_manager.queue.add_task(task)  # no queue_updated yet
        queue_manager.task_progress.emit(0, {"percent": 10.0})
        assert len(panel.rows()) == 1

    def test_progress_for_unknown_index_is_ignored(self, panel):
        panel._on_task_progress(5, {"percent": 1})
        assert panel.rows() == []

    def test_rows_in_queue_order(self, panel, queue_manager):
        tasks = [make_task(i, status=TaskStatus.DOWNLOADING, title=f"T{i}") for i in range(3)]
        for task in tasks:
            queue_manager.queue.add_task(task)
        queue_manager.queue_updated.emit()
        assert [r.task for r in panel.rows()] == tasks
        queue_manager.move_task_up(2)
        assert [r.task.title for r in panel.rows()] == ["T0", "T2", "T1"]

    def test_failed_count_in_summary(self, panel, queue_manager):
        task = make_task(0)
        queue_manager.add_task(task)
        task.fail("boom")
        queue_manager.queue_updated.emit()
        assert "1 failed" in panel.summary_label.text()

    def test_link_shown_until_title_is_known(self, panel, queue_manager):
        task = make_task(0, status=TaskStatus.DOWNLOADING)
        queue_manager.queue.add_task(task)
        queue_manager.queue_updated.emit()
        assert panel.rows()[0].display_title() == fmt.ltr(task.url)


class TestStatusMessages:
    def test_show_status_finds_main_window(self, qtbot):
        window = QMainWindow()
        inner = QWidget()
        window.setCentralWidget(inner)
        qtbot.addWidget(window)
        assert show_status(inner, "Hello", 1000) is True
        assert window.statusBar().currentMessage() == "Hello"

    def test_show_status_through_dialog(self, qtbot):
        window = QMainWindow()
        qtbot.addWidget(window)
        dialog = QDialog(window)
        child = QWidget(dialog)
        QVBoxLayout(dialog).addWidget(child)
        assert find_status_bar(child) is window.statusBar()

    def test_show_status_without_window(self, qtbot):
        widget = QWidget()
        qtbot.addWidget(widget)
        assert show_status(widget, "Nobody sees this") is False
        assert show_status(None, "x") is False


class TestMainWindowStatusBar:
    @pytest.fixture
    def window(self, qtbot, tmp_path, monkeypatch):
        import src.backend.history_manager as hm_module
        import src.ui.main_window as mw_module
        from src.backend.config_manager import ConfigManager

        monkeypatch.setattr(mw_module, "APP_DATA_DIR", tmp_path)
        monkeypatch.setattr(hm_module, "APP_DATA_DIR", tmp_path)
        monkeypatch.setattr(mw_module.QApplication, "quit", MagicMock())
        manager = ConfigManager(config_path=tmp_path / "config.json")
        manager.load_config()
        manager.update_config(output_directory=str(tmp_path))
        win = mw_module.MainWindow(manager)
        qtbot.addWidget(win)
        yield win
        win.queue_manager.workers.clear()

    def test_idle_then_downloading(self, window):
        qm = window.queue_manager
        assert window.queue_status_label.text() == "Idle"
        qm.pause_queue()
        for i in range(5):
            qm.add_task(make_task(i))
        assert window.queue_status_label.text() == "Queue paused, 5 waiting"
        tasks = qm.get_all_tasks()
        tasks[0].status = TaskStatus.DOWNLOADING
        tasks[1].status = TaskStatus.DOWNLOADING
        tasks[4].status = TaskStatus.COMPLETED
        qm.queue_updated.emit()
        assert window.queue_status_label.text() == "Downloading 2 of 4"

    def test_waiting_not_paused(self, window, monkeypatch):
        qm = window.queue_manager
        monkeypatch.setattr(qm, "_try_start_next", lambda *a, **k: None)
        qm.add_task(make_task(0))
        assert window.queue_status_label.text() == "1 waiting"

    def test_tab_links(self, window):
        window.download_tab.open_queue_requested.emit()
        assert window.tabs.currentWidget() is window.queue_tab
        window.queue_tab.go_to_download_requested.emit()
        assert window.tabs.currentWidget() is window.download_tab
        window.download_tab.open_settings_requested.emit()
        assert window.tabs.currentWidget() is window.settings_tab
        window.history_tab.download_again_requested.emit("https://vimeo.com/5")
        assert window.tabs.currentWidget() is window.download_tab
        assert window.download_tab.url_input.text() == "https://vimeo.com/5"

    def test_hebrew_status(self, qtbot, window):
        get_translation_manager().set_language("he")
        assert window.queue_status_text() == tr("status_bar_idle")
        assert window.queue_status_text() != "Idle"


class TestDisplayFormat:
    def test_values_are_isolated_ltr_runs(self):
        for text in (
            fmt.speed_text(3_400_000),
            fmt.size_text(410_000_000),
            fmt.duration_text(65),
            fmt.percent_text(47.3),
        ):
            assert text.startswith(fmt.LRI)
            assert text.endswith(fmt.PDI)
        assert fmt.strip_isolates(fmt.speed_text(3_400_000)) == "3.24 MB/s"
        assert fmt.strip_isolates(fmt.percent_text(47.3)) == "47%"

    def test_empty_values(self):
        assert fmt.speed_text(0) == ""
        assert fmt.size_text(0) == ""
        assert fmt.duration_text(0) == ""
        assert fmt.ltr("") == ""

    def test_duration_with_hours(self):
        assert fmt.strip_isolates(fmt.duration_text(3725)) == "1:02:05"

    def test_quality_labels(self):
        get_translation_manager().set_language("he")
        assert fmt.quality_label("Best Quality") == tr("quality_best")
        assert fmt.quality_label("4K (2160p)") == "4K (2160p)"

    def test_status_colors_follow_theme(self):
        manager = get_theme_manager()
        old = manager.get_current_mode()
        try:
            manager.set_theme(ThemeMode.DARK)
            dark = fmt.status_color("done")
            manager.set_theme(ThemeMode.LIGHT)
            light = fmt.status_color("done")
            assert dark != light
            assert fmt.status_color("waiting") == fmt.theme_colors()["text_secondary"]
        finally:
            manager.set_theme(old)

    def test_open_local_path(self, monkeypatch, tmp_path):
        opened = []
        monkeypatch.setattr(fmt.QDesktopServices, "openUrl", lambda url: opened.append(url.toLocalFile()) or True)
        assert fmt.open_local_path(str(tmp_path)) is True
        # QUrl.toLocalFile() uses "/" on Windows too, so compare as paths.
        assert [Path(p) for p in opened] == [tmp_path]
        assert fmt.open_local_path("") is False


class TestCollapsibleSection:
    def test_toggle_and_arrows(self, qtbot):
        section = CollapsibleSection("More")
        qtbot.addWidget(section)
        section.set_summary("all off")
        assert section.header.arrowType() == Qt.RightArrow
        with qtbot.waitSignal(section.toggled) as blocker:
            section.header.click()
        assert blocker.args == [True]
        assert section.header.arrowType() == Qt.DownArrow
        section.set_expanded(False)
        section.setLayoutDirection(Qt.RightToLeft)
        assert section.header.arrowType() == Qt.LeftArrow


class TestStartNow:
    def test_start_now_while_paused(self, queue_manager, fake_worker):
        waiting = make_task(0)
        queue_manager.add_task(waiting)
        now = make_task(1)
        queue_manager.add_task(now, start_now=True)
        assert [w.task for w in fake_worker] == [now]

    def test_pause_and_stop_clear_start_now(self, queue_manager, fake_worker):
        queue_manager.queue.max_concurrent = 1
        first = make_task(0)
        queue_manager.add_task(first, start_now=True)
        second = make_task(1)
        queue_manager.add_task(second, start_now=True)
        assert queue_manager.is_start_now(second)
        queue_manager.pause_queue()
        assert not queue_manager.is_start_now(second)
        queue_manager.add_task(make_task(2), start_now=True)
        queue_manager.stop_all()
        assert queue_manager._start_now == {}

    def test_paused_signal(self, qtbot, queue_manager, fake_worker):
        with qtbot.waitSignal(queue_manager.paused_changed) as blocker:
            queue_manager.resume_queue()
        assert blocker.args == [False]

    def test_finished_slot_does_not_start_waiting_when_paused(self, queue_manager, fake_worker):
        queue_manager.queue.max_concurrent = 1
        first = make_task(0)
        queue_manager.add_task(first, start_now=True)
        queue_manager.add_task(make_task(1))
        first.complete("a.mp4")
        queue_manager._on_worker_completed(fake_worker[0], "a.mp4")
        assert len(fake_worker) == 1
