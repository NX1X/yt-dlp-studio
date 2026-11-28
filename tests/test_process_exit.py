"""exit_process skips Qt's teardown only when a thread is still running."""

import pytest

import src.utils.process_exit as pe


def test_normal_exit_uses_sys_exit(monkeypatch):
    monkeypatch.setattr(pe, "_threads_left_running", 0)
    monkeypatch.setattr(pe.os, "_exit", lambda code: pytest.fail("os._exit must not run"))
    with pytest.raises(SystemExit) as exc:
        pe.exit_process(3)
    assert exc.value.code == 3


def test_running_thread_ends_process_without_teardown(monkeypatch):
    monkeypatch.setattr(pe, "_threads_left_running", 0)
    pe.note_threads_left_running(2)
    pe.note_threads_left_running(-5)  # ignored
    assert pe.threads_left_running() == 2
    calls = []
    monkeypatch.setattr(pe.os, "_exit", calls.append)
    monkeypatch.setattr(pe.logging, "shutdown", lambda: None)
    pe.exit_process(0)
    assert calls == [0]
