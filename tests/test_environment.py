"""
Tests for the startup diagnostics: the hidden-window subprocess helper, the
FFmpeg version probe, the startup Environment line, the About tab FFmpeg row
and the quiet impersonation warning.

No real FFmpeg is started: ``subprocess.run`` and the FFmpeg lookup are
patched. Runs headless with QT_QPA_PLATFORM=offscreen.
"""

import logging
import subprocess
import sys
from types import SimpleNamespace

import pytest

import src.backend.environment as env
from src.backend.yt_dlp_wrapper import YtDlpWrapper, _YtDlpLogBridge
from src.utils import process
from src.utils.translations import get_translation_manager, tr

FFMPEG_OUTPUT = (
    "ffmpeg version 7.1.1-1ubuntu1 Copyright (c) 2000-2025 the FFmpeg developers\n"
    "built with gcc 14 (Ubuntu 14.2.0-19ubuntu2)\n"
    "libavutil      59. 39.100 / 59. 39.100\n"
)

APP_LOGGER = "YT-DLP Studio"


@pytest.fixture(autouse=True)
def _clean_state():
    """English UI and an empty FFmpeg cache for every test."""
    get_translation_manager().set_language("en")
    env.reset_ffmpeg_cache()
    yield
    env.reset_ffmpeg_cache()


@pytest.fixture
def fake_ffmpeg(monkeypatch, tmp_path):
    """Pretend FFmpeg lives at a path; record every subprocess.run call."""
    path = tmp_path / "ffmpeg"
    path.write_text("")
    monkeypatch.setattr(env, "find_ffmpeg", lambda: str(path))
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0, stdout=FFMPEG_OUTPUT, stderr="")

    monkeypatch.setattr(env.subprocess, "run", fake_run)
    return SimpleNamespace(path=str(path), calls=calls)


# ---------- hidden_window_kwargs ----------


def test_hidden_window_kwargs_on_windows(monkeypatch):
    monkeypatch.setattr(process.sys, "platform", "win32")
    kwargs = process.hidden_window_kwargs()
    assert kwargs == {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)}
    assert kwargs["creationflags"] == 0x08000000


def test_hidden_window_kwargs_on_linux(monkeypatch):
    monkeypatch.setattr(process.sys, "platform", "linux")
    assert process.hidden_window_kwargs() == {}


def test_ffmpeg_probe_hides_window_on_windows(monkeypatch, fake_ffmpeg):
    monkeypatch.setattr(process.sys, "platform", "win32")
    assert env.probe_ffmpeg_version() == (env.FFMPEG_OK, "7.1.1-1ubuntu1")
    args, kwargs = fake_ffmpeg.calls[0]
    assert args == [fake_ffmpeg.path, "-version"]
    assert kwargs["creationflags"] == 0x08000000
    assert kwargs["timeout"] == env.FFMPEG_TIMEOUT_S


def test_ffmpeg_probe_passes_no_flags_on_linux(monkeypatch, fake_ffmpeg):
    monkeypatch.setattr(process.sys, "platform", "linux")
    env.probe_ffmpeg_version()
    _, kwargs = fake_ffmpeg.calls[0]
    assert "creationflags" not in kwargs


# ---------- FFmpeg version ----------


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        (FFMPEG_OUTPUT, "7.1.1-1ubuntu1"),
        ("ffmpeg version n7.1 Copyright (c) 2000-2024\n", "n7.1"),
        (
            "ffmpeg version 2025-01-01-git-abc123-full_build-www.gyan.dev Copyright\n",
            "2025-01-01-git-abc123-full_build-www.gyan.dev",
        ),
        ("\n\nffmpeg version 9.0.2 Copyright\n", "9.0.2"),
        ("not ffmpeg at all\n", None),
        ("", None),
    ],
)
def test_parse_ffmpeg_version(output, expected):
    assert env.parse_ffmpeg_version(output) == expected


def test_ffmpeg_version_text_from_probe(fake_ffmpeg):
    assert env.ffmpeg_version_text() == "7.1.1-1ubuntu1"


def test_ffmpeg_probe_runs_once(fake_ffmpeg):
    env.get_ffmpeg_version_info()
    env.get_ffmpeg_version_info()
    env.ffmpeg_version_text()
    assert len(fake_ffmpeg.calls) == 1
    assert env.cached_ffmpeg_version_info() == (env.FFMPEG_OK, "7.1.1-1ubuntu1")


def test_cached_info_is_none_before_probe():
    assert env.cached_ffmpeg_version_info() is None


def test_missing_ffmpeg_returns_translated_fallback(monkeypatch):
    monkeypatch.setattr(env, "find_ffmpeg", lambda: None)

    def must_not_run(*_args, **_kwargs):
        raise AssertionError("subprocess.run must not be called without FFmpeg")

    monkeypatch.setattr(env.subprocess, "run", must_not_run)
    assert env.ffmpeg_version_text() == tr("text_ffmpeg_not_found")

    get_translation_manager().set_language("he")
    assert env.ffmpeg_version_text() == tr("text_ffmpeg_not_found")
    assert env.ffmpeg_version_text() != "Not found in PATH"


def test_ffmpeg_file_vanished_returns_not_found(monkeypatch, fake_ffmpeg):
    def gone(*_args, **_kwargs):
        raise FileNotFoundError("ffmpeg")

    monkeypatch.setattr(env.subprocess, "run", gone)
    assert env.ffmpeg_version_text() == tr("text_ffmpeg_not_found")


def test_ffmpeg_timeout_returns_error_text(monkeypatch, fake_ffmpeg):
    def hang(args, **kwargs):
        raise subprocess.TimeoutExpired(args, kwargs.get("timeout"))

    monkeypatch.setattr(env.subprocess, "run", hang)
    assert env.probe_ffmpeg_version() == (env.FFMPEG_ERROR, None)
    assert env.ffmpeg_version_text() == tr("text_ffmpeg_error")


def test_ffmpeg_bad_exit_returns_unknown_text(monkeypatch, fake_ffmpeg):
    monkeypatch.setattr(env.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=1, stdout="", stderr="x"))
    assert env.ffmpeg_version_text() == tr("text_ffmpeg_unknown")


def test_find_ffmpeg_resolves_binary_in_folder(monkeypatch, tmp_path):
    binary = tmp_path / ("ffmpeg.exe" if env.os.name == "nt" else "ffmpeg")
    binary.write_text("")
    monkeypatch.setattr(YtDlpWrapper, "_get_ffmpeg_location", lambda self: str(tmp_path))
    assert env.find_ffmpeg() == str(binary)


def test_find_ffmpeg_accepts_file_path_and_never_raises(monkeypatch, tmp_path):
    binary = tmp_path / "ffmpeg-custom"
    binary.write_text("")
    monkeypatch.setattr(YtDlpWrapper, "_get_ffmpeg_location", lambda self: str(binary))
    assert env.find_ffmpeg() == str(binary)

    monkeypatch.setattr(YtDlpWrapper, "_get_ffmpeg_location", lambda self: str(tmp_path / "missing"))
    assert env.find_ffmpeg() is None

    def boom(self):
        raise OSError("disk gone")

    monkeypatch.setattr(YtDlpWrapper, "_get_ffmpeg_location", boom)
    assert env.find_ffmpeg() is None


# ---------- Environment line ----------


def test_environment_line_contains_every_part(monkeypatch, fake_ffmpeg, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(env.os, "name", "nt")
    deno = tmp_path / "deno.exe"
    monkeypatch.setattr(YtDlpWrapper, "_get_deno_location", lambda self: str(deno))
    import src.backend.update_checker as uc

    monkeypatch.setattr(uc, "is_installed_copy", lambda: True)
    monkeypatch.setattr(env, "_qt_version", lambda: "6.11.2")
    monkeypatch.setattr(env, "_python_version", lambda: "3.14.7")

    line = env.environment_line()

    assert line.startswith("Environment: ")
    assert f"app {env.APP_VERSION}" in line
    assert f"engine {YtDlpWrapper.get_ytdlp_version()}" in line
    assert "FFmpeg 7.1.1-1ubuntu1 (bundled)" in line
    assert f"Deno {env.DENO_VERSION} (bundled)" in line
    assert "Python 3.14.7" in line
    assert "Qt 6.11.2" in line
    assert line.endswith("install kind: installer")


def test_environment_line_from_source(monkeypatch, fake_ffmpeg):
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(YtDlpWrapper, "_get_deno_location", lambda self: "/usr/local/bin/deno")
    line = env.environment_line()
    assert "FFmpeg 7.1.1-1ubuntu1 (system)" in line
    assert "Deno (system)" in line
    assert "install kind: source" in line


def test_deno_part_is_never_started(monkeypatch):
    def must_not_run(*_args, **_kwargs):
        raise AssertionError("Deno must not be started")

    monkeypatch.setattr(env.subprocess, "run", must_not_run)
    monkeypatch.setattr(YtDlpWrapper, "_get_deno_location", lambda self: None)
    assert env._deno_part() == "Deno not found"
    local = str(env._project_root / "deno" / "deno")
    monkeypatch.setattr(YtDlpWrapper, "_get_deno_location", lambda self: local)
    assert env._deno_part() == "Deno (local)"


@pytest.mark.parametrize(
    ("os_name", "platform", "windows_installed", "linux_kind", "expected"),
    [
        ("nt", "win32", True, None, "installer"),
        ("nt", "win32", False, None, "portable"),
        ("posix", "linux", False, "appimage", "appimage"),
        ("posix", "linux", False, "deb", "deb"),
        ("posix", "linux", False, "rpm", "rpm"),
        ("posix", "linux", False, None, "archive"),
    ],
)
def test_install_kind_frozen(monkeypatch, os_name, platform, windows_installed, linux_kind, expected):
    import src.backend.update_checker as uc

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(env.os, "name", os_name)
    monkeypatch.setattr(env.sys, "platform", platform)
    monkeypatch.setattr(uc, "is_installed_copy", lambda: windows_installed)
    monkeypatch.setattr(uc, "linux_install_kind", lambda: linux_kind)
    assert env.install_kind() == expected


def test_environment_line_survives_every_lookup_failing(monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("lookup failed")

    monkeypatch.setattr(YtDlpWrapper, "get_ytdlp_version", staticmethod(boom))
    monkeypatch.setattr(env, "get_ffmpeg_version_info", boom)
    monkeypatch.setattr(YtDlpWrapper, "_get_deno_location", boom)
    monkeypatch.setattr(env, "_python_version", boom)
    monkeypatch.setattr(env, "_qt_version", boom)
    monkeypatch.setattr(env, "install_kind", boom)

    line = env.environment_line()

    assert line.startswith("Environment: app ")
    assert "engine unknown" in line
    assert "FFmpeg unknown" in line
    assert "Deno unknown" in line
    assert "Python unknown" in line
    assert "Qt unknown" in line
    assert "install kind: unknown" in line


def test_log_environment_logs_one_info_line(monkeypatch, caplog):
    monkeypatch.setattr(env, "environment_line", lambda: "Environment: test")
    with caplog.at_level(logging.DEBUG, logger=APP_LOGGER):
        env.log_environment()
    infos = [r for r in caplog.records if r.levelno == logging.INFO]
    assert [r.getMessage() for r in infos] == ["Environment: test"]


def test_log_environment_never_raises(monkeypatch, caplog):
    def boom():
        raise RuntimeError("broken")

    monkeypatch.setattr(env, "environment_line", boom)
    with caplog.at_level(logging.DEBUG, logger=APP_LOGGER):
        env.log_environment()
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any("Could not log the environment" in m for m in warnings)


def test_start_environment_log_runs_in_background(monkeypatch):
    seen = []
    monkeypatch.setattr(env, "log_environment", lambda: seen.append(env.threading.current_thread().name))
    thread = env.start_environment_log()
    assert thread is not None
    thread.join(timeout=5)
    assert seen == ["environment-log"]


# ---------- About tab ----------


def test_about_tab_does_not_probe_at_build(qtbot, monkeypatch):
    from src.ui.about_tab import AboutTab

    def must_not_probe():
        raise AssertionError("FFmpeg must not be probed while the tab is built")

    monkeypatch.setattr("src.ui.about_tab.get_ffmpeg_version_info", must_not_probe)
    tab = AboutTab()
    qtbot.addWidget(tab)
    assert tr("text_ffmpeg_checking") in tab._system_info_label.text()


def test_about_tab_fills_ffmpeg_row_when_shown(qtbot, monkeypatch):
    from src.ui.about_tab import AboutTab

    monkeypatch.setattr("src.ui.about_tab.get_ffmpeg_version_info", lambda: (env.FFMPEG_OK, "9.0.2"))
    tab = AboutTab()
    qtbot.addWidget(tab)
    tab.show()
    qtbot.waitUntil(lambda: "9.0.2" in tab._system_info_label.text(), timeout=5000)
    assert tr("text_ffmpeg_checking") not in tab._system_info_label.text()


def test_about_tab_uses_cached_result(qtbot, monkeypatch):
    from src.ui.about_tab import AboutTab

    monkeypatch.setattr("src.ui.about_tab.cached_ffmpeg_version_info", lambda: (env.FFMPEG_NOT_FOUND, None))

    def must_not_probe():
        raise AssertionError("cached result must be used")

    monkeypatch.setattr("src.ui.about_tab.get_ffmpeg_version_info", must_not_probe)
    tab = AboutTab()
    qtbot.addWidget(tab)
    tab._start_ffmpeg_probe()
    assert tr("text_ffmpeg_not_found") in tab._system_info_label.text()


# ---------- yt-dlp warnings ----------

IMPERSONATION_WARNING = (
    "[generic] Extracting URL: The extractor specified to use impersonation for this download, "
    "but no impersonate target is available. If you encounter errors, then see  "
    "https://github.com/yt-dlp/yt-dlp#impersonation  for information on installing the required dependencies"
)


def test_impersonation_warning_goes_to_debug(caplog):
    with caplog.at_level(logging.DEBUG, logger=APP_LOGGER):
        _YtDlpLogBridge().warning(IMPERSONATION_WARNING)
    records = [r for r in caplog.records if "impersonate" in r.getMessage()]
    assert len(records) == 1
    assert records[0].levelno == logging.DEBUG


def test_unrelated_warning_stays_warning(caplog):
    with caplog.at_level(logging.DEBUG, logger=APP_LOGGER):
        _YtDlpLogBridge().warning("Requested format is not available")
    records = [r for r in caplog.records if "Requested format" in r.getMessage()]
    assert len(records) == 1
    assert records[0].levelno == logging.WARNING
    assert records[0].getMessage() == "yt-dlp: Requested format is not available"


def test_named_impersonate_targets_warning_stays_warning(caplog):
    """Only the 'no target available' message is quiet, not a request for a named target."""
    msg = (
        "The extractor specified to use impersonation for this download, "
        "but none of these impersonate targets are available: chrome"
    )
    with caplog.at_level(logging.DEBUG, logger=APP_LOGGER):
        _YtDlpLogBridge().warning(msg)
    records = [r for r in caplog.records if "impersonat" in r.getMessage()]
    assert records[0].levelno == logging.WARNING
