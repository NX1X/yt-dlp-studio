"""
Queue tab UI for YT-DLP Studio.

Top bar: Start, Pause, Stop all and the counters on one line. Table:
Title, Status (a progress bar while a task downloads), Size, Speed and Time
left. The link, folder and quality are in the title tooltip and the row
menu. Row actions sit in the selection bar under the table and in the
right-click menu, never in the cells.

Keyboard: Delete removes the selected task (it asks first for a running or
waiting task), Ctrl+Up and Ctrl+Down move it. There is no Space shortcut:
Space presses the focused button, as everywhere else.
"""

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QAction, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedLayout,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..backend.queue_manager import QueueManager
from ..models.download_task import DownloadTask, TaskStatus
from ..utils.error_handler import ErrorHandler
from ..utils.logger import get_logger
from ..utils.status_labels import task_status_text
from ..utils.translations import tr
from .display_format import duration_text, link_text, open_local_path, quality_label, size_text, speed_text
from .status_messages import show_status
from .table_delegates import IS_LINK_ROLE, PROGRESS_ROLE, STATUS_KIND_ROLE, LinkAwareDelegate, StatusDelegate

logger = get_logger()

# Table columns
COL_TITLE, COL_STATUS, COL_SIZE, COL_SPEED, COL_ETA = range(5)

_STATUS_KIND = {
    TaskStatus.PENDING: "waiting",
    TaskStatus.DOWNLOADING: "running",
    TaskStatus.COMPLETED: "done",
    TaskStatus.ERROR: "failed",
    TaskStatus.CANCELLED: "cancelled",
}

_FINISHED = (TaskStatus.COMPLETED, TaskStatus.ERROR, TaskStatus.CANCELLED)


class QueueTab(QWidget):
    """
    Queue management tab.

    Signals:
        go_to_download_requested: the empty state's "Go to Download" link
    """

    go_to_download_requested = Signal()

    def __init__(self, queue_manager: QueueManager, parent=None):
        """
        Initialize queue tab.

        Args:
            queue_manager: QueueManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.queue_manager = queue_manager
        # id(task) -> task: running tasks the user removed; they leave the
        # queue as soon as their cancel has gone through.
        self._remove_when_stopped: dict[int, DownloadTask] = {}
        self._setup_ui()
        self._setup_shortcuts()
        self._connect_signals()
        logger.info("QueueTab initialized")

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Top bar: queue controls and counters on one line
        top_bar = QWidget()
        top_bar.setObjectName("queueTopBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(8)

        self.start_button = QPushButton(tr("button_start"))
        self.start_button.setProperty("buttonStyle", "primary")
        self.start_button.setToolTip(tr("tooltip_start_queue"))
        self.start_button.clicked.connect(self._on_start_clicked)

        self.pause_button = QPushButton(tr("button_pause"))
        self.pause_button.setProperty("buttonStyle", "secondary")
        self.pause_button.setToolTip(tr("tooltip_pause_queue"))
        self.pause_button.clicked.connect(self._on_pause_clicked)

        self.stop_button = QPushButton(tr("button_stop_all_short"))
        self.stop_button.setProperty("buttonStyle", "danger")
        self.stop_button.setToolTip(tr("tooltip_stop_all"))
        self.stop_button.clicked.connect(self._on_stop_clicked)

        self.counters_label = QLabel()
        self.counters_label.setObjectName("queueCounters")
        self.counters_label.setWordWrap(True)

        top_layout.addWidget(self.start_button)
        top_layout.addWidget(self.pause_button)
        top_layout.addWidget(self.stop_button)
        top_layout.addSpacing(8)
        top_layout.addWidget(self.counters_label, 1)
        self._top_layout = top_layout
        main_layout.addWidget(top_bar)

        # Queue table
        queue_group = QGroupBox(tr("queue_download_queue"))
        queue_layout = QVBoxLayout(queue_group)
        queue_layout.setSpacing(8)

        self.queue_table = QTableWidget()
        self.queue_table.setColumnCount(5)
        self.queue_table.setHorizontalHeaderLabels(
            [tr("col_title"), tr("col_status"), tr("col_size"), tr("col_speed"), tr("col_time_left")]
        )
        header = self.queue_table.horizontalHeader()
        header.setSectionResizeMode(COL_TITLE, QHeaderView.Stretch)
        header.setSectionResizeMode(COL_STATUS, QHeaderView.Interactive)
        header.setSectionResizeMode(COL_SIZE, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(COL_SPEED, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(COL_ETA, QHeaderView.ResizeToContents)
        self.queue_table.setColumnWidth(COL_STATUS, 200)
        header.setHighlightSections(False)
        self.queue_table.verticalHeader().setDefaultSectionSize(34)
        self.queue_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.queue_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.queue_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.queue_table.setWordWrap(False)
        self.queue_table.setItemDelegateForColumn(COL_TITLE, LinkAwareDelegate(self.queue_table))
        self.queue_table.setItemDelegateForColumn(COL_STATUS, StatusDelegate(self.queue_table))
        self.queue_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.queue_table.customContextMenuRequested.connect(self._show_context_menu)
        self.queue_table.itemSelectionChanged.connect(self._update_selection_actions)
        self.queue_table.cellDoubleClicked.connect(self._on_row_double_clicked)

        # Empty-state placeholder, shown instead of the table when the
        # queue is empty.
        self._empty_state_widget = QWidget()
        empty_layout = QVBoxLayout(self._empty_state_widget)
        empty_layout.setAlignment(Qt.AlignCenter)
        self._empty_title = QLabel(tr("queue_empty"))
        self._empty_title.setObjectName("emptyTitle")
        self._empty_title.setAlignment(Qt.AlignCenter)
        self._empty_hint = QLabel(tr("queue_empty_hint"))
        self._empty_hint.setProperty("labelStyle", "secondary")
        self._empty_hint.setAlignment(Qt.AlignCenter)
        self.go_to_download_button = QPushButton(tr("button_go_to_download"))
        self.go_to_download_button.setProperty("buttonStyle", "link")
        self.go_to_download_button.setCursor(Qt.PointingHandCursor)
        self.go_to_download_button.clicked.connect(self.go_to_download_requested.emit)
        empty_layout.addWidget(self._empty_title)
        empty_layout.addWidget(self._empty_hint)
        empty_layout.addWidget(self.go_to_download_button, 0, Qt.AlignCenter)

        # QStackedLayout swaps between the table (index 0) and the empty
        # state (index 1) depending on rowCount.
        self._queue_stack = QStackedLayout()
        self._queue_stack.addWidget(self.queue_table)
        self._queue_stack.addWidget(self._empty_state_widget)
        queue_layout.addLayout(self._queue_stack)

        # Selection bar: actions for the selected row
        selection_bar = QWidget()
        selection_bar.setObjectName("selectionBar")
        bar = QHBoxLayout(selection_bar)
        bar.setContentsMargins(0, 0, 0, 0)
        bar.setSpacing(8)

        self.open_file_button = self._secondary_button("action_open_file", "tooltip_open_file")
        self.open_file_button.clicked.connect(self._on_open_file_clicked)
        self.open_folder_button = self._secondary_button("action_open_folder", "tooltip_open_task_folder")
        self.open_folder_button.clicked.connect(self._on_open_folder_clicked)
        self.retry_button = self._secondary_button("button_retry", "tooltip_retry_task")
        self.retry_button.clicked.connect(self._on_retry_selected)
        self.cancel_button = self._secondary_button("button_cancel", "tooltip_cancel_task")
        self.cancel_button.clicked.connect(self._on_cancel_selected)
        self.move_up_button = self._secondary_button("button_move_up_short", "tooltip_move_up")
        self.move_up_button.clicked.connect(self._on_move_up_clicked)
        self.move_down_button = self._secondary_button("button_move_down_short", "tooltip_move_down")
        self.move_down_button.clicked.connect(self._on_move_down_clicked)
        self.remove_button = self._secondary_button("button_remove", "tooltip_remove_task")
        self.remove_button.setProperty("buttonStyle", "danger")
        self.remove_button.clicked.connect(self._on_remove_clicked)

        for button in (
            self.open_file_button,
            self.open_folder_button,
            self.retry_button,
            self.cancel_button,
            self.move_up_button,
            self.move_down_button,
            self.remove_button,
        ):
            bar.addWidget(button)
        bar.addStretch(1)

        # Retry every failed task. Enabled only while the queue has one.
        self.retry_failed_button = self._secondary_button("button_retry_failed", "tooltip_retry_all_failed")
        self.retry_failed_button.setEnabled(False)
        self.retry_failed_button.clicked.connect(self._on_retry_all_failed_clicked)

        self.clear_button = self._secondary_button("button_clear_finished", "tooltip_clear_finished")
        clear_menu = QMenu(self.clear_button)
        self.clear_completed_action = clear_menu.addAction(tr("menu_clear_completed"))
        self.clear_completed_action.triggered.connect(self._on_clear_completed_clicked)
        self.clear_failed_action = clear_menu.addAction(tr("menu_clear_failed"))
        self.clear_failed_action.triggered.connect(self._on_clear_failed_clicked)
        self.clear_cancelled_action = clear_menu.addAction(tr("menu_clear_cancelled"))
        self.clear_cancelled_action.triggered.connect(self._on_clear_cancelled_clicked)
        self.clear_button.setMenu(clear_menu)

        # Queue-wide clean-up sits in the top bar, after the counters.
        self._top_layout.addWidget(self.retry_failed_button)
        self._top_layout.addWidget(self.clear_button)
        queue_layout.addWidget(selection_bar)
        main_layout.addWidget(queue_group, 1)

    @staticmethod
    def _secondary_button(text_key: str, tooltip_key: str) -> QPushButton:
        button = QPushButton(tr(text_key))
        button.setProperty("buttonStyle", "secondary")
        button.setToolTip(tr(tooltip_key))
        return button

    def _setup_shortcuts(self) -> None:
        """Delete, Ctrl+Up and Ctrl+Down work while the table has the focus."""
        delete_shortcut = QShortcut(QKeySequence(QKeySequence.Delete), self.queue_table)
        delete_shortcut.setContext(Qt.WidgetWithChildrenShortcut)
        delete_shortcut.activated.connect(self._on_remove_clicked)

        up_shortcut = QShortcut(QKeySequence("Ctrl+Up"), self.queue_table)
        up_shortcut.setContext(Qt.WidgetWithChildrenShortcut)
        up_shortcut.activated.connect(self._on_move_up_clicked)

        down_shortcut = QShortcut(QKeySequence("Ctrl+Down"), self.queue_table)
        down_shortcut.setContext(Qt.WidgetWithChildrenShortcut)
        down_shortcut.activated.connect(self._on_move_down_clicked)

        self.shortcuts = [delete_shortcut, up_shortcut, down_shortcut]
        logger.debug("Keyboard shortcuts configured for QueueTab")

    def _connect_signals(self) -> None:
        """Connect queue manager signals (they arrive on the GUI thread)."""
        self.queue_manager.queue_updated.connect(self._refresh_queue)
        self.queue_manager.task_progress.connect(self._on_task_progress)
        paused_changed = getattr(self.queue_manager, "paused_changed", None)
        if paused_changed is not None:
            paused_changed.connect(self._update_queue_controls)
        # Show the empty state at once, before the first queue_updated.
        self._refresh_queue()

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def _refresh_queue(self) -> None:
        """Refresh the queue display."""
        self._remove_stopped_tasks()
        tasks = self.queue_manager.get_all_tasks()
        selected = self._selected_task()

        self.queue_table.setRowCount(len(tasks))
        self._queue_stack.setCurrentIndex(0 if tasks else 1)
        for row, task in enumerate(tasks):
            self._fill_row(row, task)

        if selected is not None and selected in tasks:
            self.queue_table.selectRow(self._index_of(selected))
        self._update_queue_controls()
        self._update_selection_actions()

    def _fill_row(self, row: int, task: DownloadTask) -> None:
        """Write all cells of one row."""
        title = task.title or task.filename
        is_link = not title
        name_item = QTableWidgetItem(title or link_text(task.url))
        name_item.setData(IS_LINK_ROLE, is_link)
        name_item.setToolTip(
            tr(
                "tooltip_queue_task",
                title=title or tr("text_title_unknown"),
                url=link_text(task.url),
                folder=link_text(task.output_directory),
                quality=quality_label(task.quality),
            )
        )
        self.queue_table.setItem(row, COL_TITLE, name_item)

        status_item = QTableWidgetItem(task_status_text(task.status))
        status_item.setData(STATUS_KIND_ROLE, _STATUS_KIND.get(task.status, "waiting"))
        if task.status == TaskStatus.ERROR:
            status_item.setToolTip(self._error_tooltip(task))
        elif task.status == TaskStatus.PENDING and self.queue_manager.is_paused:
            status_item.setToolTip(tr("tooltip_waiting_paused"))
        self.queue_table.setItem(row, COL_STATUS, status_item)
        self._fill_progress_cells(row, task)

    def _fill_progress_cells(self, row: int, task: DownloadTask) -> None:
        """Progress bar, size, speed and time left of one row."""
        status_item = self.queue_table.item(row, COL_STATUS)
        downloading = task.status == TaskStatus.DOWNLOADING
        if status_item is not None:
            status_item.setData(PROGRESS_ROLE, float(task.progress_percent or 0.0) if downloading else None)

        size = size_text(task.file_size)
        speed = speed_text(task.download_speed) if downloading else ""
        eta = duration_text(task.eta_seconds) if downloading else ""
        for column, text in ((COL_SIZE, size), (COL_SPEED, speed), (COL_ETA, eta)):
            item = self.queue_table.item(row, column)
            if item is None:
                item = QTableWidgetItem()
                item.setTextAlignment(Qt.AlignTrailing | Qt.AlignVCenter)
                self.queue_table.setItem(row, column, item)
            item.setText(text)

    @staticmethod
    def _error_tooltip(task: DownloadTask) -> str:
        """Friendly reason of a failed task, the same text as the error dialog."""
        _title, message, _suggestions = ErrorHandler.get_error_info(task.error_message or "")
        return tr("tooltip_task_failed", reason=message)

    def _on_task_progress(self, index: int, _progress_data: dict) -> None:
        """
        Update the progress cells of one task.

        The worker wrote the new values to the task before it emitted the
        signal, so the cells read them from the task.
        """
        tasks = self.queue_manager.get_all_tasks()
        if not 0 <= index < len(tasks) or index >= self.queue_table.rowCount():
            return
        self._fill_progress_cells(index, tasks[index])
        self.queue_table.viewport().update()

    def _update_queue_controls(self, *_args) -> None:
        """Counters and the enabled state of Start, Pause and Stop all."""
        stats = self.queue_manager.get_queue_statistics()
        paused = self.queue_manager.is_paused
        self.start_button.setEnabled(paused)
        self.pause_button.setEnabled(not paused)
        self.stop_button.setEnabled(stats.get("active", 0) > 0)
        self.retry_failed_button.setEnabled(stats.get("failed", 0) > 0)

        tasks = self.queue_manager.get_all_tasks()
        cancelled = sum(1 for task in tasks if task.status == TaskStatus.CANCELLED)
        self.clear_completed_action.setEnabled(stats.get("completed", 0) > 0)
        self.clear_failed_action.setEnabled(stats.get("failed", 0) > 0)
        self.clear_cancelled_action.setEnabled(cancelled > 0)
        self.clear_button.setEnabled(stats.get("completed", 0) + stats.get("failed", 0) + cancelled > 0)

        parts = [] if tasks else [tr("summary_queue_empty")]
        if stats.get("active", 0):
            parts.append(tr("summary_downloading", count=stats["active"]))
        if stats.get("pending", 0):
            parts.append(tr("summary_waiting", count=stats["pending"]))
        if stats.get("failed", 0):
            parts.append(tr("summary_failed", count=stats["failed"]))
        if stats.get("completed", 0):
            parts.append(tr("summary_done", count=stats["completed"]))
        if paused:
            parts.append(tr("summary_paused"))
        self.counters_label.setText(", ".join(parts))

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def _selected_row(self) -> int:
        rows = self.queue_table.selectionModel().selectedRows() if self.queue_table.selectionModel() else []
        if rows:
            return rows[0].row()
        items = self.queue_table.selectedItems()
        return self.queue_table.row(items[0]) if items else -1

    def _selected_task(self) -> DownloadTask | None:
        row = self._selected_row()
        tasks = self.queue_manager.get_all_tasks()
        return tasks[row] if 0 <= row < len(tasks) else None

    def _index_of(self, task: DownloadTask) -> int:
        for index, queued in enumerate(self.queue_manager.get_all_tasks()):
            if queued is task:
                return index
        return -1

    def _actions_for(self, task: DownloadTask | None, row: int) -> dict[str, bool]:
        """Which row actions apply to ``task``."""
        count = len(self.queue_manager.get_all_tasks())
        if task is None:
            return dict.fromkeys(
                ("open_file", "open_folder", "copy_link", "retry", "cancel", "error", "up", "down", "remove"), False
            )
        return {
            "open_file": task.status == TaskStatus.COMPLETED and bool(task.filename),
            "open_folder": bool(task.output_directory),
            "copy_link": True,
            "retry": task.status == TaskStatus.ERROR,
            "cancel": task.status in (TaskStatus.PENDING, TaskStatus.DOWNLOADING),
            "error": task.status == TaskStatus.ERROR,
            "up": row > 0,
            "down": 0 <= row < count - 1,
            "remove": True,
        }

    def _update_selection_actions(self) -> None:
        """Enable the selection bar buttons for the selected row."""
        row = self._selected_row()
        actions = self._actions_for(self._selected_task(), row)
        self.open_file_button.setEnabled(actions["open_file"])
        self.open_folder_button.setEnabled(actions["open_folder"])
        self.retry_button.setEnabled(actions["retry"])
        self.cancel_button.setEnabled(actions["cancel"])
        self.move_up_button.setEnabled(actions["up"])
        self.move_down_button.setEnabled(actions["down"])
        self.remove_button.setEnabled(actions["remove"])

    def build_context_menu(self, row: int) -> QMenu:
        """The right-click menu for ``row`` (also used by the tests)."""
        tasks = self.queue_manager.get_all_tasks()
        task = tasks[row] if 0 <= row < len(tasks) else None
        actions = self._actions_for(task, row)
        menu = QMenu(self)

        def add(key: str, text_key: str, slot) -> QAction:
            action = menu.addAction(tr(text_key))
            action.setObjectName(key)
            action.setEnabled(actions[key])
            action.triggered.connect(slot)
            return action

        add("open_file", "action_open_file", self._on_open_file_clicked)
        add("open_folder", "action_open_folder", self._on_open_folder_clicked)
        add("copy_link", "menu_copy_link", self._on_copy_link_clicked)
        menu.addSeparator()
        add("retry", "button_retry", self._on_retry_selected)
        add("cancel", "button_cancel", self._on_cancel_selected)
        add("error", "menu_show_error", self._on_show_error_clicked)
        menu.addSeparator()
        add("up", "button_move_up_short", self._on_move_up_clicked)
        add("down", "button_move_down_short", self._on_move_down_clicked)
        add("remove", "button_remove", self._on_remove_clicked)
        return menu

    def _show_context_menu(self, pos: QPoint) -> None:
        row = self.queue_table.rowAt(pos.y())
        if row < 0:
            return
        self.queue_table.selectRow(row)
        menu = self.build_context_menu(row)
        menu.exec(self.queue_table.viewport().mapToGlobal(pos))

    def _on_row_double_clicked(self, row: int, _column: int) -> None:
        """Double-click opens a finished file, or explains a failure."""
        tasks = self.queue_manager.get_all_tasks()
        if not 0 <= row < len(tasks):
            return
        task = tasks[row]
        if task.status == TaskStatus.COMPLETED:
            self._on_open_file_clicked()
        elif task.status == TaskStatus.ERROR:
            self._on_show_error_clicked()

    # ------------------------------------------------------------------
    # Queue controls
    # ------------------------------------------------------------------

    def _on_start_clicked(self) -> None:
        """Start: resume a paused queue and start the waiting tasks."""
        self.queue_manager.resume_queue()
        self.queue_manager.start_queue()
        self._update_queue_controls()
        logger.info("Queue started by user")

    def _on_pause_clicked(self) -> None:
        """Pause: running downloads finish, no new ones start."""
        self.queue_manager.pause_queue()
        self._update_queue_controls()
        logger.info("Queue paused by user")

    def _on_stop_clicked(self) -> None:
        """Stop all: cancel the running downloads and pause the queue (asks first)."""
        active = self.queue_manager.get_queue_statistics().get("active", 0)
        if active:
            reply = QMessageBox.question(
                self,
                tr("dialog_stop_all"),
                tr("msg_stop_all_confirm", count=active),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        # Pause first, so no waiting task starts in a freed slot.
        self.queue_manager.pause_queue()
        self.queue_manager.stop_all()
        self._update_queue_controls()
        logger.info("All downloads stopped by user")

    # ------------------------------------------------------------------
    # Row actions
    # ------------------------------------------------------------------

    def _on_move_up_clicked(self) -> None:
        row = self._selected_row()
        if row > 0 and self.queue_manager.move_task_up(row):
            self.queue_table.selectRow(row - 1)

    def _on_move_down_clicked(self) -> None:
        row = self._selected_row()
        if row >= 0 and self.queue_manager.move_task_down(row):
            self.queue_table.selectRow(row + 1)

    def _on_remove_clicked(self) -> None:
        """Remove the selected task. A running or waiting task needs a yes first."""
        row = self._selected_row()
        task = self._selected_task()
        if task is None:
            return
        if task.status in (TaskStatus.DOWNLOADING, TaskStatus.PENDING):
            message = "msg_remove_downloading" if task.status == TaskStatus.DOWNLOADING else "msg_remove_waiting"
            reply = QMessageBox.question(
                self,
                tr("dialog_remove_task"),
                tr(message),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        if self.queue_manager.get_worker(task) is not None:
            # A running download leaves the queue once its cancel went through.
            self._remove_when_stopped[id(task)] = task
            self.queue_manager.cancel_task(row)
            show_status(self, tr("status_removing"))
            return
        if self.queue_manager.remove_task(row):
            show_status(self, tr("status_removed"))

    def _remove_stopped_tasks(self) -> None:
        """Remove the cancelled tasks that the user removed while they ran."""
        for key, task in list(self._remove_when_stopped.items()):
            if self.queue_manager.get_worker(task) is not None:
                continue
            del self._remove_when_stopped[key]
            index = self._index_of(task)
            if index >= 0 and task.status in _FINISHED:
                # remove_task emits queue_updated, which calls this method again.
                self.queue_manager.remove_task(index)
                show_status(self, tr("status_removed"))

    def _on_cancel_selected(self) -> None:
        row = self._selected_row()
        if row >= 0:
            self._on_cancel_task(row)

    def _on_retry_selected(self) -> None:
        row = self._selected_row()
        if row >= 0:
            self._on_retry_task(row)

    def _on_cancel_task(self, row: int) -> None:
        """
        Cancel one task.

        Args:
            row: Task row index
        """
        # The manager finds the worker by task, not by row: rows shift when
        # tasks are removed or reordered. A running task is cancelled; a
        # pending task without a worker is removed.
        if self.queue_manager.cancel_task(row):
            logger.info(f"Cancelled or removed task at row {row}")

    def _on_retry_task(self, row: int) -> None:
        """
        Retry one failed task.

        Args:
            row: Task row index
        """
        # The manager resets the task, saves the queue and starts it if the
        # queue is not paused.
        if self.queue_manager.retry_task(row):
            logger.info(f"Retrying task at row {row}")

    def _on_copy_link_clicked(self) -> None:
        task = self._selected_task()
        if task is None:
            return
        QGuiApplication.clipboard().setText(task.url)
        show_status(self, tr("status_link_copied"))

    def _on_show_error_clicked(self) -> None:
        """Show the friendly error text with suggestions for a failed task."""
        task = self._selected_task()
        if task is None or task.status != TaskStatus.ERROR:
            return
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Critical)
        box.setWindowTitle(tr("dialog_download_failed"))
        box.setTextFormat(Qt.RichText)
        box.setText(ErrorHandler.format_error_dialog_text(task.error_message or ""))
        box.setStandardButtons(QMessageBox.Ok)
        box.exec()

    def _on_clear_completed_clicked(self) -> None:
        count = self.queue_manager.clear_completed()
        logger.info(f"Cleared {count} completed tasks")
        show_status(self, tr("status_cleared_tasks", count=count))

    def _on_clear_failed_clicked(self) -> None:
        count = self.queue_manager.clear_failed()
        logger.info(f"Cleared {count} failed tasks")
        show_status(self, tr("status_cleared_tasks", count=count))

    def _on_clear_cancelled_clicked(self) -> None:
        count = 0
        for task in [t for t in self.queue_manager.get_all_tasks() if t.status == TaskStatus.CANCELLED]:
            index = self._index_of(task)
            if index >= 0 and self.queue_manager.remove_task(index):
                count += 1
        logger.info(f"Cleared {count} cancelled tasks")
        show_status(self, tr("status_cleared_tasks", count=count))

    def _on_retry_all_failed_clicked(self) -> None:
        count = self.queue_manager.retry_all_failed()
        logger.info(f"Retrying {count} failed tasks")
        show_status(self, tr("status_retrying", count=count))

    def _on_open_file_clicked(self) -> None:
        """Open the downloaded file of the selected task."""
        import os

        task = self._selected_task()
        if task is None or task.status != TaskStatus.COMPLETED:
            return
        if not task.filename:
            QMessageBox.warning(self, tr("msg_file_not_found"), tr("msg_file_path_unknown"))
            return

        file_path = task.output_path()
        # The file may have been moved or deleted after the download.
        if not os.path.isfile(file_path):
            QMessageBox.warning(self, tr("msg_file_not_found"), f"{tr('msg_file_not_found_desc')}:\n{file_path}")
            return
        if not open_local_path(file_path):
            QMessageBox.critical(self, tr("error"), tr("msg_failed_open_file"))

    def _on_open_folder_clicked(self) -> None:
        """Open the download folder of the selected task."""
        import os

        task = self._selected_task()
        if task is None:
            return
        folder = os.path.expanduser(os.path.expandvars(task.output_directory))
        if not os.path.isdir(folder):
            QMessageBox.warning(self, tr("msg_dir_not_found"), tr("msg_dir_not_exist", directory=folder))
            return
        if not open_local_path(folder):
            QMessageBox.critical(self, tr("error"), tr("msg_failed_open_dir"))

    @staticmethod
    def _truncate_url(url: str, max_length: int = 60) -> str:
        """
        Truncate URL for display.

        Args:
            url: Full URL
            max_length: Maximum length

        Returns:
            Truncated URL
        """
        if len(url) <= max_length:
            return url
        return url[: max_length - 3] + "..."

    @staticmethod
    def _get_status_color(status: TaskStatus):
        """Theme color of a status (the table delegate paints with it)."""
        from PySide6.QtGui import QColor

        from .display_format import status_color

        return QColor(status_color(_STATUS_KIND.get(status, "waiting")))
