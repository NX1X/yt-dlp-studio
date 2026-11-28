"""
End the process without crashing when worker threads are still running.

Qt aborts the process (Windows exception 0xc0000409 in Qt6Core.dll) when a
QThread object is destroyed while its thread still runs. That happened on
exit when a download did not stop within the shutdown wait: the normal
teardown destroyed the running worker. Code that gives up waiting for a
thread calls ``note_threads_left_running``; ``exit_process`` then ends the
process with ``os._exit`` after the logs are flushed, so no thread object is
destroyed. Settings, history and the queue are saved before that point.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import NoReturn

from .logger import get_logger

logger = get_logger()

_threads_left_running = 0


def note_threads_left_running(count: int) -> None:
    """Record ``count`` threads that were still running at shutdown."""
    global _threads_left_running
    _threads_left_running += max(0, count)


def threads_left_running() -> int:
    """Number of threads recorded by ``note_threads_left_running``."""
    return _threads_left_running


def exit_process(code: int) -> NoReturn:
    """Exit with ``code``. Skip Qt's teardown if a thread is still running."""
    if _threads_left_running:
        logger.warning(
            f"{_threads_left_running} worker thread(s) still running at exit; ending the process without Qt teardown"
        )
        logging.shutdown()
        os._exit(code)
    else:
        sys.exit(code)
