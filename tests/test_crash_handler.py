"""Tests for the global crash handler."""

from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

import pytest

from src.utils import crash_handler


@pytest.fixture
def isolated_crash_dir(tmp_path, monkeypatch):
    """Redirect crash reports to a temporary directory for each test."""
    crash_dir = tmp_path / "crashes"
    monkeypatch.setattr(crash_handler, "CRASH_DIR", crash_dir)
    yield crash_dir


def _make_exc_info(exc: BaseException):
    try:
        raise exc
    except BaseException:
        return sys.exc_info()


def test_build_report_contains_required_fields(isolated_crash_dir):
    exc_type, exc_value, exc_tb = _make_exc_info(ValueError("boom"))
    report = crash_handler._build_report(exc_type, exc_value, exc_tb, origin="test")

    assert report["origin"] == "test"
    assert report["exception_type"] == "builtins.ValueError"
    assert report["exception_message"] == "boom"
    assert "Traceback" in report["traceback"]
    assert report["app_version"]
    assert report["yt_dlp_version"]
    assert report["python_version"]
    assert "log_tail" in report
    assert isinstance(report["log_tail"], list)


def test_write_report_persists_json(isolated_crash_dir):
    exc_type, exc_value, exc_tb = _make_exc_info(RuntimeError("kaboom"))
    report = crash_handler._build_report(exc_type, exc_value, exc_tb, origin="test")

    path = crash_handler._write_report(report)
    assert path is not None
    assert path.exists()
    assert path.parent == isolated_crash_dir

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["exception_type"] == "builtins.RuntimeError"
    assert payload["exception_message"] == "kaboom"


def test_keyboard_interrupt_bypasses_handler(isolated_crash_dir, monkeypatch):
    """KeyboardInterrupt should fall through to the default hook."""
    fell_through = {"value": False}

    def fake_default(exc_type, exc_value, exc_tb):
        fell_through["value"] = True

    monkeypatch.setattr(sys, "__excepthook__", fake_default)

    exc_type, exc_value, exc_tb = _make_exc_info(KeyboardInterrupt())
    crash_handler._handle(exc_type, exc_value, exc_tb, origin="test")

    assert fell_through["value"] is True
    assert not list(isolated_crash_dir.glob("*.json")), "no report should be written for KeyboardInterrupt"


def test_handle_writes_report_and_logs(isolated_crash_dir):
    exc_type, exc_value, exc_tb = _make_exc_info(KeyError("missing"))
    crash_handler._handle(exc_type, exc_value, exc_tb, origin="unit-test")

    reports = list(isolated_crash_dir.glob("crash-*.json"))
    assert len(reports) == 1

    payload = json.loads(reports[0].read_text(encoding="utf-8"))
    assert payload["origin"] == "unit-test"
    assert payload["exception_type"] == "builtins.KeyError"


def test_prune_old_crashes_keeps_max(isolated_crash_dir, monkeypatch):
    """The pruner should cap the crash directory at MAX_CRASH_FILES."""
    monkeypatch.setattr(crash_handler, "MAX_CRASH_FILES", 3)
    isolated_crash_dir.mkdir(parents=True, exist_ok=True)

    # Create 5 fake crash files with deterministic mtimes via os.utime.
    import os
    import time

    paths: list[Path] = []
    for i in range(5):
        p = isolated_crash_dir / f"crash-2026{i:02d}.json"
        p.write_text("{}", encoding="utf-8")
        os.utime(p, (time.time() + i, time.time() + i))
        paths.append(p)

    crash_handler._prune_old_crashes()

    remaining = sorted(isolated_crash_dir.glob("crash-*.json"))
    assert len(remaining) == 3, f"expected 3 newest, got {[p.name for p in remaining]}"
    # The three newest are the last three created
    assert {p.name for p in remaining} == {p.name for p in paths[-3:]}


def test_install_is_idempotent(isolated_crash_dir, monkeypatch):
    """install_crash_handler() must not stack hooks if called twice."""
    monkeypatch.setattr(crash_handler, "_installed", False)
    original_sys_hook = sys.excepthook
    original_thread_hook = threading.excepthook

    try:
        crash_handler.install_crash_handler()
        first_sys = sys.excepthook
        first_thread = threading.excepthook

        crash_handler.install_crash_handler()
        assert sys.excepthook is first_sys
        assert threading.excepthook is first_thread
    finally:
        sys.excepthook = original_sys_hook
        threading.excepthook = original_thread_hook
        monkeypatch.setattr(crash_handler, "_installed", False)


def test_threading_excepthook_writes_report(isolated_crash_dir, monkeypatch):
    """A worker thread that raises should produce a crash file."""
    monkeypatch.setattr(crash_handler, "_installed", False)
    original_hook = threading.excepthook
    crash_handler.install_crash_handler()

    try:
        def boom():
            raise ValueError("thread boom")

        t = threading.Thread(target=boom, name="boom-worker")
        t.start()
        t.join(timeout=5)

        reports = list(isolated_crash_dir.glob("crash-*.json"))
        assert len(reports) == 1
        payload = json.loads(reports[0].read_text(encoding="utf-8"))
        assert payload["origin"] == "threading.excepthook"
        assert payload["thread"] == "boom-worker"
        assert payload["exception_message"] == "thread boom"
    finally:
        threading.excepthook = original_hook
        monkeypatch.setattr(crash_handler, "_installed", False)
