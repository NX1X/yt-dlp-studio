"""Tests for scripts/check_bundle.py, the post-build bundle check.

The checker runs in CI right after PyInstaller. These tests feed it a fake
archive so they run without PyInstaller (the test job does not install it)
and cover Windows-style paths, which a Linux-only build test cannot.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ENGINE_VERSION = (ROOT / "src" / "utils" / "constants.py").read_text(encoding="utf-8")
ENGINE_VERSION = ENGINE_VERSION.split('YTDLP_VERSION = "', 1)[1].split('"', 1)[0]


class _FakeArchive:
    """Stand-in for PyInstaller's CArchiveReader."""

    def __init__(self, toc: dict[str, bytes], modules: set[str]):
        self.toc = toc
        self._modules = modules

    def open_embedded_archive(self, name):
        return types.SimpleNamespace(toc={m: None for m in self._modules})

    def extract(self, name):
        if name not in self.toc:
            raise KeyError(f"No entry named {name!r} found in the archive!")
        return self.toc[name]


@pytest.fixture
def check_bundle(monkeypatch):
    """Import scripts/check_bundle.py with a stub PyInstaller module."""
    readers = types.ModuleType("PyInstaller.archive.readers")
    readers.CArchiveReader = None
    for name, mod in {
        "PyInstaller": types.ModuleType("PyInstaller"),
        "PyInstaller.archive": types.ModuleType("PyInstaller.archive"),
        "PyInstaller.archive.readers": readers,
    }.items():
        monkeypatch.setitem(sys.modules, name, mod)
    spec = importlib.util.spec_from_file_location("check_bundle", ROOT / "scripts" / "check_bundle.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _windows_toc(sep: str = "\\") -> dict[str, bytes]:
    names = [
        f"yt_dlp_ejs{sep}yt{sep}solver{sep}core.min.js",
        f"yt_dlp_ejs{sep}yt{sep}solver{sep}lib.min.js",
        f"yt_dlp_engine{sep}yt_dlp{sep}YoutubeDL.py",
        f"PySide6{sep}QtCore.pyd",
        f"PySide6{sep}QtWidgets.pyd",
        "PYZ-00.pyz",
        "ffmpeg.exe",
        "ffprobe.exe",
        "deno.exe",
        "avcodec-62.dll",
        "avdevice-62.dll",
        "avfilter-11.dll",
        "avformat-62.dll",
        "avutil-60.dll",
        "swresample-6.dll",
        "swscale-9.dll",
    ]
    toc = {n: b"" for n in names}
    toc[f"yt_dlp_engine{sep}yt_dlp{sep}version.py"] = f"__version__ = '{ENGINE_VERSION}'\n".encode()
    return toc


MODULES = {"yt_dlp_ejs", "src.backend.yt_dlp_wrapper"}


def _run(check_bundle, monkeypatch, toc, tmp_path, modules=MODULES, name="yt-dlp-studio.exe"):
    monkeypatch.setattr(check_bundle, "CArchiveReader", lambda path: _FakeArchive(toc, modules))
    return check_bundle.check(tmp_path / name)


def test_windows_backslash_paths_pass(check_bundle, monkeypatch, tmp_path):
    """Regression: Windows TOC names use backslashes; extract() needs the original key."""
    assert _run(check_bundle, monkeypatch, _windows_toc("\\"), tmp_path) == []


def test_forward_slash_paths_pass(check_bundle, monkeypatch, tmp_path):
    assert _run(check_bundle, monkeypatch, _windows_toc("/"), tmp_path) == []


def test_missing_solver_scripts_fail(check_bundle, monkeypatch, tmp_path):
    """The v0.1.3 bug: the EXE shipped without the yt-dlp-ejs solver scripts."""
    toc = {k: v for k, v in _windows_toc().items() if "solver" not in k}
    failures = _run(check_bundle, monkeypatch, toc, tmp_path)
    assert any("core.min.js" in f for f in failures)
    assert any("lib.min.js" in f for f in failures)


def test_missing_ffmpeg_fails_on_windows_only(check_bundle, monkeypatch, tmp_path):
    toc = {k: v for k, v in _windows_toc().items() if k != "ffmpeg.exe"}
    assert any("ffmpeg.exe" in f for f in _run(check_bundle, monkeypatch, toc, tmp_path))
    # Linux bundles use the system FFmpeg, so the same TOC passes without .exe.
    assert not any("ffmpeg" in f for f in _run(check_bundle, monkeypatch, toc, tmp_path, name="yt-dlp-studio"))


def test_curl_cffi_is_forbidden(check_bundle, monkeypatch, tmp_path):
    toc = dict(_windows_toc())
    toc["curl_cffi\\libcurl-impersonate.dll"] = b""
    failures = _run(check_bundle, monkeypatch, toc, tmp_path)
    assert any("forbidden" in f and "curl_cffi" in f for f in failures)


def test_engine_version_mismatch_fails(check_bundle, monkeypatch, tmp_path):
    toc = dict(_windows_toc())
    toc["yt_dlp_engine\\yt_dlp\\version.py"] = b"__version__ = '1999.01.01'\n"
    failures = _run(check_bundle, monkeypatch, toc, tmp_path)
    assert any("1999.01.01" in f for f in failures)
