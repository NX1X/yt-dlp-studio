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
    """Redirect crash reports to a temporary directory for each test.

    Also stubs ``_show_crash_dialog`` to a no-op so the test process does NOT
    pop a modal Qt MessageBox (the test runner has a live QApplication
    instance via pytest-qt, so without this stub every test that calls
    ``_handle`` would block waiting for user input).
    """
    crash_dir = tmp_path / "crashes"
    monkeypatch.setattr(crash_handler, "CRASH_DIR", crash_dir)
    monkeypatch.setattr(crash_handler, "_show_crash_dialog", lambda path: None)
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


@pytest.mark.parametrize(
    "raw,expected_keep,expected_redacted",
    [
        # URL userinfo
        (
            "Failed: https://alice:hunter2@example.com/api",
            ["https://", "@example.com/api"],
            ["alice", "hunter2"],
        ),
        # password=value with quotes
        (
            "args: password='hunter2' user=alice",
            ["user=alice", "password="],
            ["hunter2"],
        ),
        # api_key=value without quotes
        (
            "calling endpoint with api_key=sk_live_abc123XYZ",
            ["api_key="],
            ["sk_live_abc123XYZ"],
        ),
        # Authorization Bearer
        (
            "headers: Authorization: Bearer eyJabc.def.ghi",
            ["Authorization:"],
            ["eyJabc.def.ghi"],
        ),
        # AWS access key
        (
            "boto3 uses AKIAIOSFODNN7EXAMPLE for signing",
            ["boto3 uses", "for signing"],
            ["AKIAIOSFODNN7EXAMPLE"],
        ),
        # token=value separated by colon
        (
            "config token: ghp_aabbcc11223344",
            ["config token:"],
            ["ghp_aabbcc11223344"],
        ),
    ],
)
def test_scrub_secrets_redacts_common_patterns(raw, expected_keep, expected_redacted):
    from src.utils.crash_handler import _scrub_secrets

    scrubbed = _scrub_secrets(raw)

    for keep in expected_keep:
        assert keep in scrubbed, f"expected to keep {keep!r} in {scrubbed!r}"
    for redacted in expected_redacted:
        assert redacted not in scrubbed, f"secret {redacted!r} leaked into {scrubbed!r}"
    assert "[REDACTED]" in scrubbed


def test_scrub_secrets_passes_clean_text_through():
    from src.utils.crash_handler import _scrub_secrets

    text = "ValueError: tried to open /home/user/Downloads/video.mp4"
    assert _scrub_secrets(text) == text


def test_scrub_secrets_handles_empty_and_none_like():
    from src.utils.crash_handler import _scrub_secrets

    assert _scrub_secrets("") == ""


def test_build_report_redacts_exception_message(isolated_crash_dir):
    """The exception message goes verbatim into the JSON report; scrub it."""
    exc_type, exc_value, exc_tb = _make_exc_info(RuntimeError("auth failed with token=ghp_secrettokenvalue123"))
    report = crash_handler._build_report(exc_type, exc_value, exc_tb, origin="test")

    assert "ghp_secrettokenvalue123" not in report["exception_message"]
    assert "[REDACTED]" in report["exception_message"]


def test_build_report_redacts_traceback(isolated_crash_dir):
    """A URL with embedded credentials in the traceback must be redacted."""
    try:
        url = "https://alice:hunter2@example.com/data"
        raise ValueError(f"fetch failed for {url}")
    except ValueError:
        exc_type, exc_value, exc_tb = sys.exc_info()

    report = crash_handler._build_report(exc_type, exc_value, exc_tb, origin="test")

    # The credentials appear in BOTH the message and the traceback source line.
    assert "alice" not in report["exception_message"]
    assert "hunter2" not in report["exception_message"]
    assert "alice" not in report["traceback"]
    assert "hunter2" not in report["traceback"]


def test_build_report_redacts_log_tail(isolated_crash_dir, monkeypatch):
    """Each line of log_tail must go through the scrubber."""
    monkeypatch.setattr(
        crash_handler,
        "_read_log_tail",
        lambda: [
            "2026-06-12 01:23:45 - INFO - normal line",
            "2026-06-12 01:23:46 - DEBUG - calling https://bob:p@ss@host/x",
            "2026-06-12 01:23:47 - WARNING - api_key=sk_live_xyz failed",
        ],
    )

    exc_type, exc_value, exc_tb = _make_exc_info(ValueError("boom"))
    report = crash_handler._build_report(exc_type, exc_value, exc_tb, origin="test")

    joined = "\n".join(report["log_tail"])
    assert "bob" not in joined
    assert "p@ss" not in joined
    assert "sk_live_xyz" not in joined
    assert joined.count("[REDACTED]") >= 2


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
