"""Tests for scripts/check_extractors.py, the weekly extractor check.

The real check needs network access to YouTube. These tests replace the
app's wrapper and playlist fetcher with fakes, so they run offline and
cover the pass and fail rules the workflow depends on.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def check_extractors(monkeypatch):
    spec = importlib.util.spec_from_file_location("check_extractors", ROOT / "scripts" / "check_extractors.py")
    module = importlib.util.module_from_spec(spec)
    # @dataclass looks the module up in sys.modules while the module runs.
    monkeypatch.setitem(sys.modules, "check_extractors", module)
    spec.loader.exec_module(module)
    return module


def _video(formats):
    return types.SimpleNamespace(title="Me at the zoo", formats=formats)


REAL_FORMATS = [
    {"format_id": "18", "ext": "mp4", "vcodec": "avc1", "acodec": "mp4a"},
    {"format_id": "140", "ext": "m4a", "vcodec": "none", "acodec": "mp4a"},
]
STORYBOARD = {"format_id": "sb0", "ext": "mhtml", "format_note": "storyboard", "vcodec": "none", "acodec": "none"}


def test_storyboards_are_not_real_formats(check_extractors):
    assert not check_extractors._is_real_format(STORYBOARD)
    assert all(check_extractors._is_real_format(f) for f in REAL_FORMATS)


def test_video_passes_with_real_formats(check_extractors, monkeypatch):
    from src.backend import yt_dlp_wrapper

    monkeypatch.setattr(
        yt_dlp_wrapper.YtDlpWrapper, "get_video_info", lambda self, url: _video(REAL_FORMATS + [STORYBOARD])
    )
    result = check_extractors.check_video("https://example.invalid/v")
    assert result.ok
    assert "2 formats (1 with video, 2 with audio)" in result.detail


@pytest.mark.parametrize("info", [None, _video([]), _video([STORYBOARD])])
def test_video_fails_without_real_formats(check_extractors, monkeypatch, info):
    from src.backend import yt_dlp_wrapper

    monkeypatch.setattr(yt_dlp_wrapper.YtDlpWrapper, "get_video_info", lambda self, url: info)
    assert not check_extractors.check_video("https://example.invalid/v").ok


@pytest.mark.parametrize(("count", "ok"), [(0, False), (9, False), (10, True), (96, True)])
def test_playlist_needs_enough_entries(check_extractors, monkeypatch, count, ok):
    from src.backend import playlist_fetcher

    info = types.SimpleNamespace(title="29C3", videos=[object()] * count)
    monkeypatch.setattr(playlist_fetcher.PlaylistFetcher, "fetch_playlist_info", staticmethod(lambda url: info))
    assert check_extractors.check_playlist("https://example.invalid/p").ok is ok


def test_playlist_fails_when_extraction_fails(check_extractors, monkeypatch):
    from src.backend import playlist_fetcher

    monkeypatch.setattr(playlist_fetcher.PlaylistFetcher, "fetch_playlist_info", staticmethod(lambda url: None))
    assert not check_extractors.check_playlist("https://example.invalid/p").ok


def test_main_exit_code_and_report(check_extractors, monkeypatch, tmp_path):
    passing = check_extractors.Result("Deno", "-", True, "found")
    failing = check_extractors.Result("YouTube video", "u", False, "Unexpected error:\nTraceback ...")
    monkeypatch.setattr(check_extractors, "check_deno", lambda: passing)
    monkeypatch.setattr(check_extractors, "check_video", lambda url: failing)
    monkeypatch.setattr(check_extractors, "check_playlist", lambda url: passing)

    report = tmp_path / "report.md"
    assert check_extractors.main(["--report", str(report)]) == 1
    text = report.read_text(encoding="utf-8")
    assert "| YouTube video (u) | FAIL | Unexpected error: |" in text
    assert "<details><summary>YouTube video traceback</summary>" in text

    monkeypatch.setattr(check_extractors, "check_video", lambda url: passing)
    assert check_extractors.main([]) == 0


def test_unexpected_exception_is_a_failure(check_extractors):
    def boom():
        raise RuntimeError("network down")

    result = check_extractors._run("YouTube video", "u", boom)
    assert not result.ok
    assert "network down" in result.detail
