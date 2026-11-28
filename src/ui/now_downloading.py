"""
"Now downloading" panel for the Download tab.

Shows the downloads that run now (one row each: title, slim progress bar,
percent, speed and time left), a line with the waiting and failed counts,
and a link to the Queue tab. With nothing running it shows an empty state.

The panel is fed only by ``QueueManager`` signals. QueueManager emits them
on the GUI thread (its worker connections are queued), so the slots here
may touch widgets. The panel never reads from a worker thread; it reads the
task objects, which the queue owns.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..backend.queue_manager import QueueManager
from ..models.download_task import DownloadTask, TaskStatus
from ..utils.translations import tr
from .display_format import duration_text, link_text, percent_text, speed_text


class DownloadRow(QWidget):
    """One running download: title, progress bar, percent, speed, time left."""

    def __init__(self, task: DownloadTask, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("nowDownloadingRow")
        self.task = task

        self.title_label = QLabel()
        self.title_label.setObjectName("nowTitle")
        self.title_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.title_label.setMinimumWidth(120)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("rowProgress")
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedWidth(180)

        self.percent_label = QLabel()
        self.speed_label = QLabel()
        self.eta_label = QLabel()
        metrics = QFontMetrics(self.font())
        self.percent_label.setMinimumWidth(metrics.horizontalAdvance("100%") + 8)
        self.speed_label.setMinimumWidth(metrics.horizontalAdvance("999.99 MB/s") + 8)
        self.eta_label.setMinimumWidth(metrics.horizontalAdvance("00:00:00") + 8)
        for label in (self.percent_label, self.speed_label, self.eta_label):
            label.setProperty("labelStyle", "secondary")
            label.setAlignment(Qt.AlignVCenter | Qt.AlignTrailing)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(12)
        layout.addWidget(self.title_label, 1)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.percent_label)
        layout.addWidget(self.speed_label)
        layout.addWidget(self.eta_label)
        self.refresh()

    def display_title(self) -> str:
        """Title, or the link while yt-dlp has not reported the title yet."""
        return self.task.title or self.task.filename or link_text(self.task.url)

    def refresh(self) -> None:
        """Show the current values of the task."""
        task = self.task
        title = self.display_title()
        self._full_title = title
        self._elide_title()
        self.title_label.setToolTip(f"{title}\n{link_text(task.url)}")

        percent = float(task.progress_percent or 0.0)
        self.progress_bar.setValue(int(percent * 10))
        if percent <= 0 and not task.download_speed:
            # No progress report yet: yt-dlp is still reading the page.
            self.progress_bar.setRange(0, 0)
            self.percent_label.setText("")
            self.speed_label.setText(tr("now_starting"))
            self.eta_label.setText("")
            self.progress_bar.setAccessibleName(tr("now_starting"))
            return
        if self.progress_bar.maximum() == 0:
            self.progress_bar.setRange(0, 1000)
            self.progress_bar.setValue(int(percent * 10))
        if percent >= 100:
            # The file is complete; yt-dlp may still merge or convert it.
            self.percent_label.setText(percent_text(100))
            self.speed_label.setText(tr("now_processing"))
            self.eta_label.setText("")
        else:
            self.percent_label.setText(percent_text(percent))
            self.speed_label.setText(speed_text(task.download_speed))
            eta = duration_text(task.eta_seconds)
            self.eta_label.setText(tr("now_time_left", time=eta) if eta else "")
        self.progress_bar.setAccessibleName(tr("now_progress_accessible", title=title, percent=percent_text(percent)))

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        self._elide_title()

    def _elide_title(self) -> None:
        title = getattr(self, "_full_title", "")
        width = max(40, self.title_label.width())
        mode = Qt.ElideMiddle if not (self.task.title or self.task.filename) else Qt.ElideRight
        self.title_label.setText(self.title_label.fontMetrics().elidedText(title, mode, width))


class NowDownloadingPanel(QGroupBox):
    """Live view of the running downloads, fed by QueueManager signals."""

    open_queue_requested = Signal()

    def __init__(self, queue_manager: QueueManager, parent: QWidget | None = None):
        super().__init__(tr("group_now_downloading"), parent)
        self.setObjectName("nowDownloadingPanel")
        self.queue_manager = queue_manager
        self._rows: dict[int, DownloadRow] = {}  # id(task) -> row

        self.rows_layout = QVBoxLayout()
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(6)

        self.empty_label = QLabel(tr("now_empty"))
        self.empty_label.setObjectName("nowEmpty")
        self.empty_label.setProperty("labelStyle", "secondary")
        self.empty_label.setWordWrap(True)

        self.summary_label = QLabel()
        self.summary_label.setObjectName("nowSummary")
        self.summary_label.setProperty("labelStyle", "secondary")

        self.open_queue_button = QPushButton(tr("button_open_queue"))
        self.open_queue_button.setProperty("buttonStyle", "link")
        self.open_queue_button.setCursor(Qt.PointingHandCursor)
        self.open_queue_button.setToolTip(tr("tooltip_open_queue"))
        self.open_queue_button.clicked.connect(self.open_queue_requested.emit)

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.addWidget(self.summary_label, 1)
        footer.addWidget(self.open_queue_button)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addLayout(self.rows_layout)
        layout.addWidget(self.empty_label)
        layout.addLayout(footer)

        queue_manager.queue_updated.connect(self.refresh)
        queue_manager.task_progress.connect(self._on_task_progress)
        paused_changed = getattr(queue_manager, "paused_changed", None)
        if paused_changed is not None:
            paused_changed.connect(self.refresh)
        self.refresh()

    def running_tasks(self) -> list[DownloadTask]:
        """Tasks that download now, in queue order."""
        return [task for task in self.queue_manager.get_all_tasks() if task.status == TaskStatus.DOWNLOADING]

    def rows(self) -> list[DownloadRow]:
        """Row widgets in display order."""
        return [self.rows_layout.itemAt(i).widget() for i in range(self.rows_layout.count())]

    def refresh(self) -> None:
        """Rebuild the rows and the summary from the queue (GUI thread)."""
        running = self.running_tasks()
        wanted = {id(task): task for task in running}

        for key in list(self._rows):
            if key not in wanted:
                row = self._rows.pop(key)
                self.rows_layout.removeWidget(row)
                row.deleteLater()
        for position, task in enumerate(running):
            row = self._rows.get(id(task))
            if row is None:
                row = DownloadRow(task)
                self._rows[id(task)] = row
            if self.rows_layout.indexOf(row) != position:
                self.rows_layout.removeWidget(row)
                self.rows_layout.insertWidget(position, row)
            row.refresh()

        stats = self.queue_manager.get_queue_statistics()
        paused = bool(getattr(self.queue_manager, "is_paused", False))
        if running:
            self.empty_label.setVisible(False)
        else:
            if paused and stats.get("pending", 0):
                self.empty_label.setText(tr("now_empty_paused", count=stats.get("pending", 0)))
            else:
                self.empty_label.setText(tr("now_empty"))
            self.empty_label.setVisible(True)

        parts = []
        if stats.get("pending", 0):
            parts.append(tr("summary_waiting", count=stats["pending"]))
        if stats.get("failed", 0):
            parts.append(tr("summary_failed", count=stats["failed"]))
        if paused:
            parts.append(tr("summary_paused"))
        self.summary_label.setText(", ".join(parts))
        self.summary_label.setVisible(bool(parts))

    def _on_task_progress(self, index: int, _progress: dict) -> None:
        """Update the row of one task. The worker already wrote the values to the task."""
        tasks = self.queue_manager.get_all_tasks()
        if not 0 <= index < len(tasks):
            return
        task = tasks[index]
        row = self._rows.get(id(task))
        if row is None:
            # The task started before its queue_updated arrived.
            self.refresh()
            return
        row.refresh()
