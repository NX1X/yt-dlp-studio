"""
Display labels for download statuses.

The queue file and the history file store statuses as plain English values
("pending", "completed", "failed", and so on). Those values never change, so
old and new files stay compatible. This module turns a stored value into
translated text, only at display time.
"""

from ..models.download_task import TaskStatus
from .translations import tr

# Translation key for each queue status.
TASK_STATUS_KEYS: dict[TaskStatus, str] = {
    TaskStatus.PENDING: "status_pending",
    TaskStatus.DOWNLOADING: "status_downloading",
    TaskStatus.COMPLETED: "status_completed",
    TaskStatus.ERROR: "status_error",
    TaskStatus.CANCELLED: "status_cancelled",
}

# Translation key for each status value that the history file stores.
HISTORY_STATUS_KEYS: dict[str, str] = {
    "completed": "status_completed",
    "failed": "status_failed",
    "cancelled": "status_cancelled",
}


def task_status_text(status: TaskStatus) -> str:
    """Return the translated label for a queue status."""
    key = TASK_STATUS_KEYS.get(status)
    return tr(key) if key else status.value


def history_status_text(status: str) -> str:
    """Return the translated label for a history status.

    An unknown value (for example from a newer version) is shown as stored.
    """
    key = HISTORY_STATUS_KEYS.get(status)
    return tr(key) if key else status
