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
    assert check_extractors.check_video("https://example.invalid/v").status == "FAIL"


@pytest.mark.parametrize(("count", "ok"), [(0, False), (9, False), (10, True), (96, True)])
def test_playlist_needs_enough_entries(check_extractors, monkeypatch, count, ok):
    from src.backend import playlist_fetcher

    info = types.SimpleNamespace(title="29C3", videos=[object()] * count)
    monkeypatch.setattr(playlist_fetcher.PlaylistFetcher, "fetch_playlist_info", staticmethod(lambda url: info))
    assert check_extractors.check_playlist("https://example.invalid/p").ok is ok


def test_playlist_fails_when_extraction_fails(check_extractors, monkeypatch):
    from src.backend import playlist_fetcher

    monkeypatch.setattr(playlist_fetcher.PlaylistFetcher, "fetch_playlist_info", staticmethod(lambda url: None))
    assert check_extractors.check_playlist("https://example.invalid/p").status == "FAIL"


def test_main_exit_code_and_report(check_extractors, monkeypatch, tmp_path):
    R = check_extractors.Result
    passing = R("Deno", "-", "pass", "found")
    failing = R("YouTube video", "u", "FAIL", "Unexpected error:\nTraceback ...")
    blocked = R("YouTube video", "u", "blocked", check_extractors.BLOCKED_DETAIL)
    monkeypatch.setattr(check_extractors, "check_deno", lambda: passing)
    monkeypatch.setattr(check_extractors, "check_video", lambda url: failing)
    monkeypatch.setattr(check_extractors, "check_playlist", lambda url: passing)

    monkeypatch.chdir(tmp_path)
    report = tmp_path / check_extractors.REPORT_FILE
    assert check_extractors.main(["--report"]) == 1
    text = report.read_text(encoding="utf-8")
    assert "| YouTube video (u) | FAIL | Unexpected error: |" in text
    assert "<details><summary>YouTube video traceback</summary>" in text

    monkeypatch.setattr(check_extractors, "check_video", lambda url: blocked)
    assert check_extractors.main([]) == 2

    monkeypatch.setattr(check_extractors, "check_video", lambda url: passing)
    assert check_extractors.main([]) == 0


def _log_bot_check(url):
    from src.utils.logger import get_logger

    try:
        raise RuntimeError("ERROR: [youtube] x: Sign in to confirm you\u2019re not a bot. Use --cookies")
    except RuntimeError:
        get_logger().exception("Error extracting video info")
    return None


def test_bot_check_is_blocked_not_failed(check_extractors, monkeypatch):
    from src.backend import playlist_fetcher, yt_dlp_wrapper

    monkeypatch.setattr(yt_dlp_wrapper.YtDlpWrapper, "get_video_info", lambda self, url: _log_bot_check(url))
    monkeypatch.setattr(playlist_fetcher.PlaylistFetcher, "fetch_playlist_info", staticmethod(_log_bot_check))
    for result in (
        check_extractors.check_video("https://example.invalid/v"),
        check_extractors.check_playlist("https://example.invalid/p"),
    ):
        assert result.status == "blocked"
        assert not result.ok


def test_unexpected_exception_is_a_failure(check_extractors):
    def boom():
        raise RuntimeError("network down")

    result = check_extractors._run("YouTube video", "u", boom)
    assert result.status == "FAIL"
    assert "network down" in result.detail


# --- TikTok. Nothing here sends a request: the wrapper is replaced by fakes. ---

TIKTOK_AUDIO_ONLY = [{"format_id": "audio", "ext": "m4a", "vcodec": "none", "acodec": "aac"}]


@pytest.fixture
def on_actions(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")


def _log_error(text):
    """A fake get_video_info that logs `text` the way the wrapper does and returns None."""

    def fake(self, url):
        from src.utils.logger import get_logger

        try:
            raise RuntimeError(text)
        except RuntimeError:
            get_logger().exception("Error extracting video info")
        return None

    return fake


def _patch_video_info(monkeypatch, fake):
    from src.backend import yt_dlp_wrapper

    monkeypatch.setattr(yt_dlp_wrapper.YtDlpWrapper, "get_video_info", fake)


def test_tiktok_url_is_a_public_test_video_from_yt_dlp(check_extractors):
    url = check_extractors.TIKTOK_VIDEO_URL
    source = (ROOT / "vendor" / "yt_dlp_engine" / "yt_dlp" / "extractor" / "tiktok.py").read_text(encoding="utf-8")
    assert f"'url': '{url}'" in source
    assert url.startswith("https://www.tiktok.com/@")


def test_tiktok_check_passes_with_a_real_format(check_extractors, monkeypatch, on_actions):
    _patch_video_info(monkeypatch, lambda self, url: _video(TIKTOK_AUDIO_ONLY + [STORYBOARD]))
    result = check_extractors.check_tiktok_video(check_extractors.TIKTOK_VIDEO_URL)
    assert result.ok
    assert result.name == "TikTok video"


@pytest.mark.parametrize("info", [_video([]), _video([STORYBOARD])])
def test_tiktok_check_fails_without_real_formats(check_extractors, monkeypatch, on_actions, info):
    _patch_video_info(monkeypatch, lambda self, url: info)
    assert check_extractors.check_tiktok_video("https://example.invalid/v").status == "FAIL"


@pytest.mark.parametrize(
    "text",
    [
        "ERROR: [TikTok] 123: Unable to extract universal data for rehydration",
        "ERROR: [TikTok] 123: Video not available, status code 10101",
        "ERROR: [TikTok] 123: Unable to download webpage: HTTP Error 500: Internal Server Error",
        "ERROR: [TikTok] 123: Unable to solve JS challenge",
        "ERROR: [TikTok] 7107337212743830830: Unable to extract video data",
    ],
)
def test_tiktok_real_extraction_failure_is_a_failure(check_extractors, monkeypatch, on_actions, text):
    _patch_video_info(monkeypatch, _log_error(text))
    assert check_extractors.check_tiktok_video("https://example.invalid/v").status == "FAIL"


@pytest.mark.parametrize(
    "text",
    [
        "ERROR: [TikTok] 123: Your IP address is blocked from accessing this post",
        "ERROR: [TikTok] 123: TikTok is requiring login for access to this content",
        "ERROR: [TikTok] 123: You do not have permission to view this post. Log into an account that has access",
        "ERROR: [TikTok] 123: Unable to download webpage: HTTP Error 403: Forbidden",
        "ERROR: [TikTok] 123: Unable to download webpage: HTTP Error 429: Too Many Requests",
        "ERROR: [TikTok] 123: Please complete the captcha",
    ],
)
def test_tiktok_block_is_blocked_not_failed(check_extractors, monkeypatch, on_actions, text):
    _patch_video_info(monkeypatch, _log_error(text))
    result = check_extractors.check_tiktok_video("https://example.invalid/v")
    assert result.status == "blocked"
    assert result.detail == check_extractors.TIKTOK_BLOCKED_DETAIL
    assert check_extractors.exit_code([result]) == 2


def test_tiktok_block_text_is_not_a_youtube_block(check_extractors):
    result = check_extractors._extraction_failed("YouTube video", "u", ["Your IP address is blocked"])
    assert result.status == "FAIL"


def test_tiktok_check_refuses_to_run_off_github_actions(check_extractors, monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    _patch_video_info(monkeypatch, lambda self, url: pytest.fail("a request was made"))
    with pytest.raises(RuntimeError, match="GitHub Actions"):
        check_extractors.check_tiktok_video(check_extractors.TIKTOK_VIDEO_URL)


def test_main_tiktok_does_nothing_off_github_actions(check_extractors, monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(check_extractors, "check_tiktok_video", lambda url: pytest.fail("a request was made"))
    assert check_extractors.main(["--site", "tiktok", "--report"]) == 3
    assert "only on GitHub Actions" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())


def test_main_tiktok_writes_its_own_report(check_extractors, monkeypatch, tmp_path, on_actions):
    R = check_extractors.Result
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(check_extractors, "check_deno", lambda: pytest.fail("YouTube check ran"))
    monkeypatch.setattr(check_extractors, "check_video", lambda url: pytest.fail("YouTube check ran"))
    monkeypatch.setattr(
        check_extractors, "check_tiktok_video", lambda url: R("TikTok video", url, "blocked", "TikTok blocked")
    )
    assert check_extractors.main(["--site", "tiktok", "--report"]) == 2
    text = (tmp_path / check_extractors.TIKTOK_REPORT_FILE).read_text(encoding="utf-8")
    assert "| TikTok video (" in text
    assert not (tmp_path / check_extractors.REPORT_FILE).exists()


def test_main_default_site_is_youtube_and_sends_nothing_to_tiktok(check_extractors, monkeypatch, tmp_path):
    R = check_extractors.Result
    ok = R("x", "-", "pass", "ok")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(check_extractors, "check_deno", lambda: ok)
    monkeypatch.setattr(check_extractors, "check_video", lambda url: ok)
    monkeypatch.setattr(check_extractors, "check_playlist", lambda url: ok)
    monkeypatch.setattr(check_extractors, "check_tiktok_video", lambda url: pytest.fail("TikTok check ran"))
    assert check_extractors.main([]) == 0
