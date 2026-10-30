"""Tests for DownloadWorker result handling (file name and title)."""

import os
from types import SimpleNamespace

import pytest

from src.backend.download_worker import DownloadWorker
from src.models.download_task import DownloadTask, TaskStatus

OUT_DIR = os.path.join(os.sep, "downloads")


def make_task(**kwargs):
    defaults = {"url": "https://www.youtube.com/watch?v=x", "output_directory": OUT_DIR, "quality": "720p"}
    defaults.update(kwargs)
    task = DownloadTask(**defaults)
    task.start()
    return task


def finish(task, output_files=(), title=None):
    """Run the worker's success path with a fake wrapper result."""
    worker = DownloadWorker(task)
    worker.wrapper = SimpleNamespace(last_output_files=list(output_files), last_title=title)
    emitted = []
    worker.download_completed.connect(emitted.append)
    worker._handle_success()
    return emitted


@pytest.fixture(autouse=True)
def no_sound(monkeypatch):
    """Keep the completion sound out of the test run."""
    import sys

    monkeypatch.setitem(sys.modules, "winsound", None)
    from PySide6.QtWidgets import QApplication

    monkeypatch.setattr(QApplication, "beep", staticmethod(lambda: None))


def test_success_uses_real_file_name_and_title():
    task = make_task()
    path = os.path.join(OUT_DIR, "Me at the zoo_240p.mp4")
    emitted = finish(task, [path], "Me at the zoo")

    assert task.status == TaskStatus.COMPLETED
    assert task.filename == "Me at the zoo_240p.mp4"
    assert task.title == "Me at the zoo"
    assert task.output_path() == path
    assert emitted == ["Me at the zoo_240p.mp4"]


def test_success_uses_first_output_file():
    task = make_task(audio_only=True)
    finish(task, [os.path.join(OUT_DIR, "song.mp3"), os.path.join(OUT_DIR, "other.mp3")])
    assert task.filename == "song.mp3"


def test_fallback_when_no_path_is_reported():
    task = make_task()
    emitted = finish(task)
    assert task.filename == "video file"
    assert task.title == ""
    assert emitted == ["video file"]


def test_audio_fallback_when_no_path_is_reported():
    task = make_task(audio_only=True)
    finish(task)
    assert task.filename == "audio file"


def test_fallback_without_wrapper():
    task = make_task()
    worker = DownloadWorker(task)
    worker._handle_success()
    assert task.filename == "video file"


def test_history_uses_title_and_file_name(tmp_path, monkeypatch):
    from src.backend import history_manager as hm_module

    monkeypatch.setattr(hm_module, "APP_DATA_DIR", tmp_path)
    manager = hm_module.HistoryManager()
    task = make_task()
    finish(task, [os.path.join(OUT_DIR, "Me at the zoo_240p.mp4")], "Me at the zoo")

    manager.add_download(task, "completed")

    entry = manager.get_history()[0]
    assert entry.title == "Me at the zoo"
    assert entry.filename == "Me at the zoo_240p.mp4"
    assert entry.output_directory == OUT_DIR


def test_history_title_falls_back_to_file_name(tmp_path, monkeypatch):
    from src.backend import history_manager as hm_module

    monkeypatch.setattr(hm_module, "APP_DATA_DIR", tmp_path)
    manager = hm_module.HistoryManager()
    task = make_task()
    task.complete("clip.mp4")

    manager.add_download(task, "completed")

    assert manager.get_history()[0].title == "clip.mp4"
