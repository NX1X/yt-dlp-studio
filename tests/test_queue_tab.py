"""
Tests for the Queue tab.

Covers the top bar (Start, Pause, Stop all, counters), the table columns
and the progress cells, the selection bar, the right-click menu, the
keyboard (Delete asks first for running or waiting tasks, no Space
shortcut) and the Clear finished menu. Requires pytest-qt.
"""

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import QMessageBox, QPushButton

from src.backend.queue_manager import QueueManager
from src.models.download_task import DownloadTask, TaskStatus
from src.ui.display_format import strip_isolates
from src.ui.queue_tab import COL_ETA, COL_SIZE, COL_SPEED, COL_STATUS, COL_TITLE, QueueTab
from src.ui.table_delegates import PROGRESS_ROLE, STATUS_KIND_ROLE
from src.utils.translations import get_translation_manager, tr


@pytest.fixture(autouse=True)
def force_english_ui():
    """Pin the UI language to English, so text checks do not depend on the locale or test order."""
    get_translation_manager().set_language("en")
    yield
    get_translation_manager().set_language("en")


@pytest.fixture
def queue_manager():
    """A paused in-memory queue: nothing starts a real download."""
    manager = QueueManager(max_concurrent=3)
    manager.pause_queue()
    return manager


@pytest.fixture
def queue_tab(qtbot, queue_manager):
    tab = QueueTab(queue_manager)
    qtbot.addWidget(tab)
    return tab


def make_task(i: int = 0, **fields) -> DownloadTask:
    task = DownloadTask(
        url=f"https://www.youtube.com/watch?v=test{i}", output_directory="/tmp/downloads", quality="1080p"
    )
    for name, value in fields.items():
        setattr(task, name, value)
    return task


def add(queue_manager, *tasks):
    for task in tasks:
        queue_manager.add_task(task)
    queue_manager.queue_updated.emit()


def menu_actions(menu) -> dict:
    return {action.objectName(): action for action in menu.actions() if action.objectName()}


class TestLayout:
    def test_columns(self, queue_tab):
        headers = [queue_tab.queue_table.horizontalHeaderItem(c).text() for c in range(5)]
        assert headers == ["Title", "Status", "Size", "Speed", "Time left"]

    def test_no_buttons_in_cells(self, queue_tab, queue_manager):
        add(queue_manager, make_task(0), make_task(1, status=TaskStatus.ERROR))
        for row in range(queue_tab.queue_table.rowCount()):
            for column in range(queue_tab.queue_table.columnCount()):
                assert queue_tab.queue_table.cellWidget(row, column) is None

    def test_only_one_primary_button(self, queue_tab):
        primary = [b for b in queue_tab.findChildren(QPushButton) if b.property("buttonStyle") == "primary"]
        assert primary == [queue_tab.start_button]

    def test_empty_state(self, queue_tab, queue_manager):
        assert queue_tab._queue_stack.currentIndex() == 1
        assert queue_tab.counters_label.text() == "The queue is empty, queue paused"
        add(queue_manager, make_task())
        assert queue_tab._queue_stack.currentIndex() == 0

    def test_go_to_download_link(self, qtbot, queue_tab):
        with qtbot.waitSignal(queue_tab.go_to_download_requested):
            queue_tab.go_to_download_button.click()


class TestCountersAndControls:
    def test_counters_on_one_line(self, queue_tab, queue_manager):
        add(
            queue_manager,
            make_task(0, status=TaskStatus.DOWNLOADING),
            make_task(1),
            make_task(2),
            make_task(3, status=TaskStatus.ERROR),
            make_task(4, status=TaskStatus.COMPLETED),
        )
        assert queue_tab.counters_label.text() == "1 downloading, 2 waiting, 1 failed, 1 done, queue paused"

    def test_start_pause_enabled_by_state(self, queue_tab, queue_manager):
        assert queue_tab.start_button.isEnabled()
        assert not queue_tab.pause_button.isEnabled()
        with patch.object(queue_manager, "_try_start_next"):
            queue_tab.start_button.click()
        assert not queue_manager.is_paused
        assert not queue_tab.start_button.isEnabled()
        assert queue_tab.pause_button.isEnabled()
        queue_tab.pause_button.click()
        assert queue_manager.is_paused
        assert queue_tab.start_button.isEnabled()

    def test_paused_signal_updates_controls(self, queue_tab, queue_manager):
        with patch.object(queue_manager, "_try_start_next"):
            queue_manager.resume_queue()  # from elsewhere, not the tab
        assert queue_tab.pause_button.isEnabled()
        assert "queue paused" not in queue_tab.counters_label.text()

    def test_start_resumes_and_starts(self, queue_tab, queue_manager):
        with patch.object(queue_manager, "resume_queue") as resume, patch.object(queue_manager, "start_queue") as start:
            queue_tab.start_button.click()
        resume.assert_called_once()
        start.assert_called_once()

    def test_stop_all_disabled_without_running_downloads(self, queue_tab, queue_manager):
        add(queue_manager, make_task())
        assert not queue_tab.stop_button.isEnabled()

    def test_stop_all_asks_then_pauses_and_cancels(self, queue_tab, queue_manager):
        with patch.object(queue_manager, "_try_start_next"):
            queue_manager.resume_queue()
        add(queue_manager, make_task(0, status=TaskStatus.DOWNLOADING))
        with (
            patch.object(QMessageBox, "question", return_value=QMessageBox.Yes) as question,
            patch.object(queue_manager, "stop_all") as stop,
        ):
            queue_tab.stop_button.click()
        question.assert_called_once()
        stop.assert_called_once()
        assert queue_manager.is_paused

    def test_stop_all_no_keeps_running(self, queue_tab, queue_manager):
        add(queue_manager, make_task(0, status=TaskStatus.DOWNLOADING))
        with (
            patch.object(QMessageBox, "question", return_value=QMessageBox.No),
            patch.object(queue_manager, "stop_all") as stop,
        ):
            queue_tab.stop_button.click()
        stop.assert_not_called()

    def test_tooltips_explain_pause_and_stop(self, queue_tab):
        assert "finish" in queue_tab.pause_button.toolTip()
        assert "pause the queue" in queue_tab.stop_button.toolTip()


class TestRows:
    def test_title_or_link(self, queue_tab, queue_manager):
        add(queue_manager, make_task(0, title="My Video"), make_task(1))
        assert queue_tab.queue_table.item(0, COL_TITLE).text() == "My Video"
        assert (
            strip_isolates(queue_tab.queue_table.item(1, COL_TITLE).text()) == "https://www.youtube.com/watch?v=test1"
        )

    def test_tooltip_has_link_folder_and_quality(self, queue_tab, queue_manager):
        add(queue_manager, make_task(0, title="My Video", quality="1080p (Full HD)"))
        tooltip = strip_isolates(queue_tab.queue_table.item(0, COL_TITLE).toolTip())
        assert "Link: https://www.youtube.com/watch?v=test0" in tooltip
        assert "Folder: /tmp/downloads" in tooltip
        assert "Quality: 1080p (Full HD)" in tooltip

    def test_status_kinds(self, queue_tab, queue_manager):
        add(
            queue_manager,
            make_task(0),
            make_task(1, status=TaskStatus.DOWNLOADING),
            make_task(2, status=TaskStatus.COMPLETED),
            make_task(3, status=TaskStatus.ERROR),
            make_task(4, status=TaskStatus.CANCELLED),
        )
        kinds = [queue_tab.queue_table.item(r, COL_STATUS).data(STATUS_KIND_ROLE) for r in range(5)]
        assert kinds == ["waiting", "running", "done", "failed", "cancelled"]

    def test_failed_row_tooltip_shows_reason(self, queue_tab, queue_manager):
        task = make_task(0)
        add(queue_manager, task)
        task.fail("HTTP Error 403: Forbidden")
        queue_manager.queue_updated.emit()
        tooltip = queue_tab.queue_table.item(0, COL_STATUS).toolTip()
        assert tooltip
        assert "details" in tooltip

    def test_progress_cells_from_signal(self, queue_tab, queue_manager):
        task = make_task(0, status=TaskStatus.DOWNLOADING)
        add(queue_manager, task)
        task.update_progress(47.3, download_speed=3_400_000, eta_seconds=135, downloaded_bytes=1, file_size=410_000_000)
        queue_manager.task_progress.emit(0, {"percent": 47.3})

        assert queue_tab.queue_table.item(0, COL_STATUS).data(PROGRESS_ROLE) == pytest.approx(47.3)
        assert strip_isolates(queue_tab.queue_table.item(0, COL_SPEED).text()).endswith("MB/s")
        assert strip_isolates(queue_tab.queue_table.item(0, COL_SIZE).text()).endswith("MB")
        assert strip_isolates(queue_tab.queue_table.item(0, COL_ETA).text()) == "2:15"

    def test_progress_invalid_index_is_ignored(self, queue_tab):
        queue_tab._on_task_progress(100, {"percent": 50})

    def test_no_progress_for_waiting_task(self, queue_tab, queue_manager):
        add(queue_manager, make_task(0, download_speed=1000.0))
        assert queue_tab.queue_table.item(0, COL_STATUS).data(PROGRESS_ROLE) is None
        assert queue_tab.queue_table.item(0, COL_SPEED).text() == ""

    def test_rtl_speed_is_isolated(self, queue_tab, queue_manager):
        task = make_task(0, status=TaskStatus.DOWNLOADING, download_speed=3_400_000)
        add(queue_manager, task)
        text = queue_tab.queue_table.item(0, COL_SPEED).text()
        assert text.startswith("⁦") and text.endswith("⁩")

    def test_table_paints(self, queue_tab, queue_manager):
        """The delegates paint every status without errors."""
        add(
            queue_manager,
            make_task(0, status=TaskStatus.DOWNLOADING, progress_percent=40.0),
            make_task(1, status=TaskStatus.ERROR),
        )
        queue_tab.resize(900, 400)
        queue_tab.show()
        queue_tab.queue_table.selectRow(0)
        assert not queue_tab.grab().isNull()
        queue_tab.setLayoutDirection(Qt.RightToLeft)
        assert not queue_tab.grab().isNull()


class TestSelectionBar:
    def test_nothing_selected_disables_row_actions(self, queue_tab, queue_manager):
        add(queue_manager, make_task())
        for button in (
            queue_tab.open_file_button,
            queue_tab.retry_button,
            queue_tab.cancel_button,
            queue_tab.remove_button,
        ):
            assert not button.isEnabled()

    def test_actions_follow_selected_state(self, queue_tab, queue_manager):
        add(
            queue_manager,
            make_task(0),
            make_task(1, status=TaskStatus.ERROR),
            make_task(2, status=TaskStatus.COMPLETED, filename="v.mp4"),
        )
        queue_tab.queue_table.selectRow(0)
        assert queue_tab.cancel_button.isEnabled() and not queue_tab.retry_button.isEnabled()
        assert not queue_tab.move_up_button.isEnabled() and queue_tab.move_down_button.isEnabled()
        queue_tab.queue_table.selectRow(1)
        assert queue_tab.retry_button.isEnabled() and not queue_tab.cancel_button.isEnabled()
        queue_tab.queue_table.selectRow(2)
        assert queue_tab.open_file_button.isEnabled() and not queue_tab.move_down_button.isEnabled()

    def test_move_buttons(self, queue_tab, queue_manager):
        add(queue_manager, *(make_task(i) for i in range(3)))
        queue_tab.queue_table.selectRow(1)
        with patch.object(queue_manager, "move_task_up", return_value=True) as up:
            queue_tab.move_up_button.click()
        up.assert_called_once_with(1)
        queue_tab.queue_table.selectRow(1)
        with patch.object(queue_manager, "move_task_down", return_value=True) as down:
            queue_tab.move_down_button.click()
        down.assert_called_once_with(1)

    def test_move_keeps_selection_on_task(self, queue_tab, queue_manager):
        tasks = [make_task(i) for i in range(3)]
        add(queue_manager, *tasks)
        queue_tab.queue_table.selectRow(2)
        queue_tab.move_up_button.click()
        assert queue_tab._selected_task() is tasks[2]
        assert queue_manager.get_all_tasks()[1] is tasks[2]

    def test_retry_button(self, queue_tab, queue_manager):
        task = make_task(0)
        add(queue_manager, task)
        task.fail("boom")
        queue_manager.queue_updated.emit()
        queue_tab.queue_table.selectRow(0)
        queue_tab.retry_button.click()
        assert task.status == TaskStatus.PENDING

    def test_cancel_button_removes_waiting_task(self, queue_tab, queue_manager):
        add(queue_manager, make_task(0))
        queue_tab.queue_table.selectRow(0)
        queue_tab.cancel_button.click()
        assert queue_manager.get_all_tasks() == []

    def test_retry_all_failed(self, queue_tab, queue_manager):
        task = make_task(0)
        add(queue_manager, task)
        assert not queue_tab.retry_failed_button.isEnabled()
        task.fail("boom")
        queue_manager.queue_updated.emit()
        assert queue_tab.retry_failed_button.isEnabled()
        queue_tab.retry_failed_button.click()
        assert task.status == TaskStatus.PENDING
        assert not queue_tab.retry_failed_button.isEnabled()


class TestClearMenu:
    def test_clear_finished_menu(self, queue_tab, queue_manager):
        add(
            queue_manager,
            make_task(0, status=TaskStatus.COMPLETED),
            make_task(1, status=TaskStatus.ERROR),
            make_task(2, status=TaskStatus.CANCELLED),
            make_task(3),
        )
        assert queue_tab.clear_button.isEnabled()
        queue_tab.clear_completed_action.trigger()
        queue_tab.clear_failed_action.trigger()
        queue_tab.clear_cancelled_action.trigger()
        statuses = [t.status for t in queue_manager.get_all_tasks()]
        assert statuses == [TaskStatus.PENDING]
        assert not queue_tab.clear_button.isEnabled()


class TestContextMenu:
    def test_menu_for_completed_task(self, queue_tab, queue_manager):
        add(queue_manager, make_task(0, status=TaskStatus.COMPLETED, filename="v.mp4"))
        actions = menu_actions(queue_tab.build_context_menu(0))
        assert actions["open_file"].isEnabled()
        assert actions["copy_link"].isEnabled()
        assert not actions["retry"].isEnabled()
        assert not actions["error"].isEnabled()

    def test_menu_for_failed_task(self, queue_tab, queue_manager):
        add(queue_manager, make_task(0, status=TaskStatus.ERROR, error_message="HTTP Error 403: Forbidden"))
        actions = menu_actions(queue_tab.build_context_menu(0))
        assert actions["retry"].isEnabled()
        assert actions["error"].isEnabled()
        assert not actions["open_file"].isEnabled()

    def test_copy_link(self, queue_tab, queue_manager):
        add(queue_manager, make_task(7))
        queue_tab.queue_table.selectRow(0)
        menu_actions(queue_tab.build_context_menu(0))["copy_link"].trigger()
        assert QGuiApplication.clipboard().text() == "https://www.youtube.com/watch?v=test7"

    def test_show_error_details(self, queue_tab, queue_manager):
        add(queue_manager, make_task(0, status=TaskStatus.ERROR, error_message="HTTP Error 403: Forbidden"))
        queue_tab.queue_table.selectRow(0)
        with patch.object(QMessageBox, "exec", return_value=0) as exec_:
            menu_actions(queue_tab.build_context_menu(0))["error"].trigger()
        exec_.assert_called_once()

    def test_open_file_and_folder(self, queue_tab, queue_manager, tmp_path):
        (tmp_path / "v.mp4").write_bytes(b"x")
        task = make_task(0, status=TaskStatus.COMPLETED, filename="v.mp4")
        task.output_directory = str(tmp_path)
        add(queue_manager, task)
        queue_tab.queue_table.selectRow(0)
        with patch("src.ui.queue_tab.open_local_path", return_value=True) as opener:
            menu_actions(queue_tab.build_context_menu(0))["open_file"].trigger()
            menu_actions(queue_tab.build_context_menu(0))["open_folder"].trigger()
        assert [c.args[0] for c in opener.call_args_list] == [str(tmp_path / "v.mp4"), str(tmp_path)]

    def test_missing_file_warns(self, queue_tab, queue_manager, tmp_path):
        task = make_task(0, status=TaskStatus.COMPLETED, filename="gone.mp4")
        task.output_directory = str(tmp_path)
        add(queue_manager, task)
        queue_tab.queue_table.selectRow(0)
        with patch.object(QMessageBox, "warning") as warning, patch("src.ui.queue_tab.open_local_path") as opener:
            queue_tab._on_open_file_clicked()
        warning.assert_called_once()
        opener.assert_not_called()

    def test_double_click_failed_row_shows_error(self, queue_tab, queue_manager):
        add(queue_manager, make_task(0, status=TaskStatus.ERROR, error_message="boom"))
        queue_tab.queue_table.selectRow(0)
        with patch.object(queue_tab, "_on_show_error_clicked") as show:
            queue_tab._on_row_double_clicked(0, 0)
        show.assert_called_once()


class TestKeyboard:
    def test_no_space_shortcut(self, queue_tab):
        keys = [s.key() for s in queue_tab.findChildren(QShortcut)]
        assert QKeySequence("Space") not in keys
        assert not hasattr(queue_tab, "_toggle_queue")

    def test_shortcuts_are_bound_to_the_table(self, queue_tab):
        for shortcut in queue_tab.shortcuts:
            assert shortcut.parent() is queue_tab.queue_table
            assert shortcut.context() == Qt.WidgetWithChildrenShortcut

    def test_delete_finished_task_without_question(self, queue_tab, queue_manager):
        add(queue_manager, make_task(0, status=TaskStatus.COMPLETED))
        queue_tab.queue_table.selectRow(0)
        with patch.object(QMessageBox, "question") as question:
            queue_tab._on_remove_clicked()
        question.assert_not_called()
        assert queue_manager.get_all_tasks() == []

    def test_delete_waiting_task_asks_first(self, queue_tab, queue_manager):
        add(queue_manager, make_task(0))
        queue_tab.queue_table.selectRow(0)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.No) as question:
            queue_tab._on_remove_clicked()
        question.assert_called_once()
        assert len(queue_manager.get_all_tasks()) == 1
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            queue_tab._on_remove_clicked()
        assert queue_manager.get_all_tasks() == []

    def test_delete_running_task_cancels_then_removes(self, queue_tab, queue_manager):
        task = make_task(0, status=TaskStatus.DOWNLOADING)
        add(queue_manager, task)
        worker = MagicMock()
        worker.task = task
        queue_manager.workers[id(task)] = worker
        queue_tab.queue_table.selectRow(0)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes) as question:
            queue_tab._on_remove_clicked()
        question.assert_called_once()
        assert "running" in question.call_args.args[2]
        worker.cancel.assert_called_once()
        assert queue_manager.get_all_tasks() == [task]  # still there until the cancel is through

        # The worker reports the cancel; the task then leaves the queue.
        task.cancel()
        queue_manager._on_worker_failed(worker, "Download cancelled")
        assert queue_manager.get_all_tasks() == []

    def test_delete_running_task_no_keeps_it(self, queue_tab, queue_manager):
        task = make_task(0, status=TaskStatus.DOWNLOADING)
        add(queue_manager, task)
        worker = MagicMock()
        queue_manager.workers[id(task)] = worker
        queue_tab.queue_table.selectRow(0)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.No):
            queue_tab._on_remove_clicked()
        worker.cancel.assert_not_called()

    def test_delete_without_selection_does_nothing(self, queue_tab, queue_manager):
        add(queue_manager, make_task(0))
        with patch.object(queue_manager, "remove_task") as remove:
            queue_tab._on_remove_clicked()
        remove.assert_not_called()


class TestHebrew:
    def test_hebrew_headers_and_counters(self, qtbot, queue_manager):
        get_translation_manager().set_language("he")
        tab = QueueTab(queue_manager)
        qtbot.addWidget(tab)
        add(queue_manager, make_task(0))
        assert tab.queue_table.horizontalHeaderItem(COL_ETA).text() == tr("col_time_left")
        assert tab.counters_label.text() == f"{tr('summary_waiting', count=1)}, {tr('summary_paused')}"
