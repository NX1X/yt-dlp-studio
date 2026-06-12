"""Unit tests for YtDlpWrapper path resolution and caching.

These tests cover the parts of the wrapper that are safe to exercise without
network or a real yt-dlp invocation: import wiring, FFmpeg/Deno location
caching, and the cancellation/error flags.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.backend.yt_dlp_wrapper import YtDlpWrapper


@pytest.fixture(autouse=True)
def reset_location_caches():
    """Reset the class-level FFmpeg/Deno caches before each test.

    The wrapper memoises filesystem lookups on the class itself, which makes
    a single resolution effectively a process-wide singleton. Tests must
    reset both flags so each scenario starts from a clean slate.
    """
    YtDlpWrapper._ffmpeg_cache = None
    YtDlpWrapper._ffmpeg_cache_checked = False
    YtDlpWrapper._deno_cache = None
    YtDlpWrapper._deno_cache_checked = False
    yield
    YtDlpWrapper._ffmpeg_cache = None
    YtDlpWrapper._ffmpeg_cache_checked = False
    YtDlpWrapper._deno_cache = None
    YtDlpWrapper._deno_cache_checked = False


def test_engine_imports_at_pinned_version():
    """The wrapper module must successfully import yt_dlp at our pinned version."""
    from src.backend import yt_dlp_wrapper as wrapper

    assert hasattr(wrapper, "YoutubeDL")
    assert hasattr(wrapper, "ytdlp_version")
    assert wrapper.ytdlp_version.__version__ == "2026.06.09"


def test_curl_cffi_is_available():
    """curl_cffi must be installed and detected by yt-dlp.

    Without it, yt-dlp's networking layer can't impersonate a real browser's
    TLS/JA3 fingerprint, and YouTube replies with HTTP 429 on subtitle and
    comment endpoints. That used to silently abort entire video downloads.

    If this test fails, check pyproject.toml [project.dependencies] and the
    PyInstaller spec's collect_all('curl_cffi') wiring.
    """
    from yt_dlp.dependencies import curl_cffi as curl_cffi_flag

    _ASSERT_MSG = "curl_cffi is not importable. Re-add 'curl_cffi>=0.15.0' to pyproject.toml dependencies."
    assert curl_cffi_flag is not None, _ASSERT_MSG

    # The impersonation request handler must enumerate Chrome targets.
    from yt_dlp.networking._curlcffi import CurlCFFIRH

    target_names = {str(t) for t in CurlCFFIRH._SUPPORTED_IMPERSONATE_TARGET_MAP.keys()}
    chrome_targets = [t for t in target_names if t.startswith("chrome")]
    assert chrome_targets, "curl_cffi advertises no Chrome impersonation targets"


def test_default_impersonate_target_is_chrome():
    """The wrapper module must resolve a Chrome impersonation target at import time."""
    from src.backend.yt_dlp_wrapper import _DEFAULT_IMPERSONATE_TARGET

    assert _DEFAULT_IMPERSONATE_TARGET is not None, (
        "_DEFAULT_IMPERSONATE_TARGET is None - curl_cffi may be missing or "
        "ImpersonateTarget.from_str('chrome') failed at import time."
    )
    assert "chrome" in str(_DEFAULT_IMPERSONATE_TARGET).lower()

    # The constructed target must round-trip through yt-dlp's validator.
    from yt_dlp.networking.impersonate import ImpersonateTarget

    assert isinstance(_DEFAULT_IMPERSONATE_TARGET, ImpersonateTarget)


def test_youtubedl_accepts_default_impersonate_target():
    """A YoutubeDL instance must accept our impersonate target without raising."""
    from yt_dlp import YoutubeDL

    from src.backend.yt_dlp_wrapper import _DEFAULT_IMPERSONATE_TARGET

    if _DEFAULT_IMPERSONATE_TARGET is None:
        pytest.skip("impersonation unavailable in this environment")

    ydl = YoutubeDL(
        {
            "quiet": True,
            "simulate": True,
            "impersonate": _DEFAULT_IMPERSONATE_TARGET,
        }
    )
    assert ydl is not None


def test_yt_dlp_ejs_is_available():
    """The yt-dlp-ejs solver package must be installed and detected by yt-dlp.

    Without it, yt-dlp 2026.06.09 falls back to a 245-byte stub lib script for
    Deno, which fails to solve YouTube JS challenges and silently drops formats.
    The full lib script is ~147KB and ships only via the yt_dlp_ejs package
    (or via a runtime download from GitHub which we deliberately do not enable).

    If this test fails, check pyproject.toml [project.dependencies] and the
    PyInstaller spec hiddenimports for yt_dlp_ejs.
    """
    # yt-dlp's dependency probe: this is the flag the EJS provider checks at runtime.
    from yt_dlp.dependencies import yt_dlp_ejs as ejs_flag

    assert ejs_flag is not None, (
        "yt_dlp_ejs is not importable. yt-dlp 2026.06.09 needs it to solve "
        "YouTube JS challenges without a runtime GitHub download. "
        "Re-add 'yt-dlp-ejs>=0.8.0' to pyproject.toml dependencies."
    )

    # And the solver functions exist and return non-stub script bodies.
    from yt_dlp_ejs.yt import solver

    lib_size = len(solver.lib())
    core_size = len(solver.core())
    assert lib_size > 100_000, f"lib script too small ({lib_size}B); expected >100KB of solver code"
    assert core_size > 1_000, f"core script too small ({core_size}B); expected >1KB of solver code"


def test_ffmpeg_lookup_is_cached():
    """Second call must not hit the filesystem again."""
    w = YtDlpWrapper()

    with patch("shutil.which", return_value="/usr/bin/ffmpeg") as mock_which:
        first = w._get_ffmpeg_location()
        second = w._get_ffmpeg_location()
        third = w._get_ffmpeg_location()

    assert first == second == third
    # Cache means shutil.which only fires once across three calls.
    assert mock_which.call_count <= 1


def test_ffmpeg_lookup_returns_none_when_missing(monkeypatch):
    monkeypatch.setattr("sys.frozen", False, raising=False)
    with patch("shutil.which", return_value=None):
        with patch("os.path.exists", return_value=False):
            result = YtDlpWrapper()._get_ffmpeg_location()
    assert result is None


def test_ffmpeg_cache_shared_across_instances():
    """The cache lives on the class, so two instances must agree."""
    a = YtDlpWrapper()
    b = YtDlpWrapper()

    with patch("shutil.which", return_value="/usr/bin/ffmpeg") as mock_which:
        a._get_ffmpeg_location()
        b._get_ffmpeg_location()
        b._get_ffmpeg_location()

    assert mock_which.call_count == 1


def test_deno_lookup_is_cached():
    w = YtDlpWrapper()

    with patch("shutil.which", return_value="/usr/bin/deno") as mock_which:
        first = w._get_deno_location()
        second = w._get_deno_location()

    assert first == second
    assert mock_which.call_count <= 1


def test_deno_lookup_returns_none_when_missing(monkeypatch):
    monkeypatch.setattr("sys.frozen", False, raising=False)
    with patch("shutil.which", return_value=None):
        with patch("pathlib.Path.exists", return_value=False):
            result = YtDlpWrapper()._get_deno_location()
    assert result is None


def test_initial_state():
    """A fresh wrapper has no cancellation request and no recorded error."""
    w = YtDlpWrapper()
    assert w._download_cancelled is False
    assert w._last_error is None
    assert w._last_error_type is None


def test_progress_callback_is_stored():
    def sentinel(_payload):
        return None

    w = YtDlpWrapper(progress_callback=sentinel)
    assert w.progress_callback is sentinel


def test_progress_callback_defaults_to_none():
    w = YtDlpWrapper()
    assert w.progress_callback is None


class _FakeYDL:
    """Minimal stand-in for a YoutubeDL instance used by the subtitle-resilience tests."""

    def __init__(self, write_subtitles_impl):
        self._write_subtitles = write_subtitles_impl
        self.warnings: list[str] = []

    def report_warning(self, msg):
        self.warnings.append(msg)


def test_make_subtitles_non_fatal_swallows_exceptions():
    """A raising _write_subtitles must return [] and produce a warning."""
    from src.backend.yt_dlp_wrapper import _make_subtitles_non_fatal

    def boom(info_dict, filename):
        raise RuntimeError("HTTP Error 429: Too Many Requests")

    ydl = _FakeYDL(boom)
    _make_subtitles_non_fatal(ydl)

    result = ydl._write_subtitles({"id": "abc"}, "/tmp/foo.mp4")

    assert result == [], "wrapped _write_subtitles must return an empty list on failure"
    assert len(ydl.warnings) == 1
    assert "Subtitle download failed" in ydl.warnings[0]
    assert "429" in ydl.warnings[0]


def test_make_subtitles_non_fatal_passes_through_success():
    """If subtitles download successfully the wrapper must return the originals."""
    from src.backend.yt_dlp_wrapper import _make_subtitles_non_fatal

    expected = [("/tmp/foo.en.srt", "/tmp/foo.en.srt")]

    def ok(info_dict, filename):
        return expected

    ydl = _FakeYDL(ok)
    _make_subtitles_non_fatal(ydl)

    assert ydl._write_subtitles({"id": "abc"}, "/tmp/foo.mp4") is expected
    assert ydl.warnings == []


def test_make_subtitles_non_fatal_preserves_original_signature():
    """The wrapped method must forward (info_dict, filename) verbatim."""
    from src.backend.yt_dlp_wrapper import _make_subtitles_non_fatal

    seen = {}

    def capture(info_dict, filename):
        seen["info_dict"] = info_dict
        seen["filename"] = filename
        return []

    ydl = _FakeYDL(capture)
    _make_subtitles_non_fatal(ydl)
    ydl._write_subtitles({"id": "xyz"}, "/tmp/path.mp4")

    assert seen["info_dict"] == {"id": "xyz"}
    assert seen["filename"] == "/tmp/path.mp4"


# ---------- sleep_interval_requests wiring (rate-limit defence) ----------


class _CapturingYDL:
    """Stand-in for YoutubeDL that records ydl_opts and short-circuits."""

    captured: dict = {}

    def __init__(self, opts):
        _CapturingYDL.captured = dict(opts)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def extract_info(self, url, download=True):
        # Return a minimal info_dict so the wrapper's post-processing
        # block exits cleanly (no metadata search, no merge).
        return {"id": "test"}

    @property
    def _write_subtitles(self):
        return lambda info, fn: []

    @_write_subtitles.setter
    def _write_subtitles(self, value):
        # _make_subtitles_non_fatal tries to swap this; allow it silently.
        pass


def _run_download_with_capture(monkeypatch, **kwargs):
    """Run YtDlpWrapper.download() against a fake YoutubeDL and return captured opts."""
    from src.backend import yt_dlp_wrapper as mod

    _CapturingYDL.captured = {}
    monkeypatch.setattr(mod, "YoutubeDL", _CapturingYDL)

    defaults = dict(
        url="https://example.com/video",
        output_dir=".",
        format_string="best",
        audio_only=False,
        audio_quality="192",
        download_thumbnail=False,
        download_subtitles=False,
        subtitle_languages="en",
        speed_limit=0,
        video_container=None,
        audio_format="mp3",
        selected_subtitles=None,
        download_metadata=False,
        download_comments=False,
        auto_number_duplicates=True,
    )
    defaults.update(kwargs)

    wrapper = mod.YtDlpWrapper()
    wrapper.download(**defaults)
    return _CapturingYDL.captured


def test_sleep_interval_requests_set_when_subs_and_comments(monkeypatch):
    """The subtitles+comments combo is what triggers the YouTube 429 cascade."""
    opts = _run_download_with_capture(
        monkeypatch,
        download_subtitles=True,
        download_comments=True,
    )
    assert opts.get("sleep_interval_requests") == 1


def test_sleep_interval_requests_set_when_subs_and_metadata(monkeypatch):
    """Metadata download internally fetches comments too, same rate-limit risk."""
    opts = _run_download_with_capture(
        monkeypatch,
        download_subtitles=True,
        download_metadata=True,
    )
    assert opts.get("sleep_interval_requests") == 1


def test_sleep_interval_requests_not_set_subs_only(monkeypatch):
    """Subtitles alone do not produce enough requests to trip the rate limit."""
    opts = _run_download_with_capture(
        monkeypatch,
        download_subtitles=True,
        download_comments=False,
        download_metadata=False,
    )
    assert "sleep_interval_requests" not in opts


def test_sleep_interval_requests_not_set_comments_only(monkeypatch):
    """Comments without subtitles need no extra spacing - we only care if subs
    can land, and comments can absorb 429s on their own."""
    opts = _run_download_with_capture(
        monkeypatch,
        download_subtitles=False,
        download_comments=True,
    )
    assert "sleep_interval_requests" not in opts


def test_sleep_interval_subtitles_always_set_when_subs_enabled(monkeypatch):
    """The per-subtitle 2s sleep is still applied independent of comments."""
    opts = _run_download_with_capture(
        monkeypatch,
        download_subtitles=True,
        download_comments=False,
    )
    assert opts.get("sleep_interval_subtitles") == 2
