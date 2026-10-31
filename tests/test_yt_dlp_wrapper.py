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
    """The wrapper module must successfully import yt_dlp at our pinned version.

    Compares against YTDLP_VERSION rather than a literal so the vendored tree
    and the constant cannot drift apart, and so the bump workflow (which
    updates only the constant) does not need to edit this test.
    """
    from src.backend import yt_dlp_wrapper as wrapper
    from src.utils.constants import YTDLP_VERSION

    assert hasattr(wrapper, "YoutubeDL")
    assert hasattr(wrapper, "ytdlp_version")
    assert wrapper.ytdlp_version.__version__ == YTDLP_VERSION


# ---------- curl_cffi stays out (software-origin policy) ----------

_PROJECT_ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent


def test_curl_cffi_is_not_a_runtime_dependency():
    """curl_cffi is banned by the project's software-origin policy.

    It must not come back as a runtime dependency through a well-meaning
    Renovate bump or a copy from an older branch.
    """
    # Plain text parsing, not tomllib: tomllib is 3.11+ and the project
    # supported Python 3.10 when this was written; harmless on 3.11+.
    text = (_PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    block = text[text.index("\ndependencies = [") + 1 :]  # +1 skips the leading newline
    block = block[: block.index("\n]")]
    entries = [ln.strip() for ln in block.splitlines()[1:] if ln.strip() and not ln.strip().startswith("#")]
    assert entries, "could not find any runtime dependencies in pyproject.toml"
    assert not [e for e in entries if e.strip('",').lower().replace("-", "_").startswith("curl_cffi")]


@pytest.mark.parametrize("spec", ["build.spec", "build_linux.spec"])
def test_curl_cffi_is_excluded_from_bundles(spec):
    """Both PyInstaller specs must exclude curl_cffi and never collect it.

    The vendored yt-dlp auto-detects curl_cffi, so excluding it in the spec is
    what guarantees it stays out of the EXE even if a build machine has it.
    """
    text = (_PROJECT_ROOT / "packaging" / spec).read_text(encoding="utf-8")
    assert "collect_all('curl_cffi')" not in text
    excludes = text[text.index("excludes=[") :]
    excludes = excludes[: excludes.index("]")]
    assert "'curl_cffi'" in excludes


def test_download_never_requests_impersonation(monkeypatch):
    """The wrapper must not ask yt-dlp for browser impersonation (needs curl_cffi)."""
    opts = _run_download_with_capture(monkeypatch)
    assert "impersonate" not in opts


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

    result = ydl._write_subtitles({"id": "abc"}, "video.mp4")

    assert result == [], "wrapped _write_subtitles must return an empty list on failure"
    assert len(ydl.warnings) == 1
    assert "Subtitle download failed" in ydl.warnings[0]
    assert "429" in ydl.warnings[0]


def test_make_subtitles_non_fatal_passes_through_success():
    """If subtitles download successfully the wrapper must return the originals."""
    from src.backend.yt_dlp_wrapper import _make_subtitles_non_fatal

    expected = [("video.en.srt", "video.en.srt")]

    def ok(info_dict, filename):
        return expected

    ydl = _FakeYDL(ok)
    _make_subtitles_non_fatal(ydl)

    assert ydl._write_subtitles({"id": "abc"}, "video.mp4") is expected
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
    ydl._write_subtitles({"id": "xyz"}, "video.mp4")

    assert seen["info_dict"] == {"id": "xyz"}
    assert seen["filename"] == "video.mp4"


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

    def add_post_processor(self, pp, when="post_process"):
        # The duplicate-numbering hook; this fake never runs it.
        pass

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

    defaults = {
        "url": "https://example.com/video",
        "output_dir": ".",
        "format_string": "best",
        "audio_only": False,
        "audio_quality": "192",
        "download_thumbnail": False,
        "download_subtitles": False,
        "subtitle_languages": "en",
        "speed_limit": 0,
        "video_container": None,
        "audio_format": "mp3",
        "selected_subtitles": None,
        "download_metadata": False,
        "download_comments": False,
        "auto_number_duplicates": True,
    }
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


# ---------- success requires a file on disk (false-success regression) ----------


def _run_download_returning(monkeypatch, tmp_path, info, error=None):
    """Run download() against a fake YoutubeDL whose extract_info returns ``info``.

    ``error`` is sent through the configured yt-dlp logger first, the way
    yt-dlp reports a download error under ignoreerrors='only_download'.
    """
    from src.backend import yt_dlp_wrapper as mod

    class _FakeYDL(_CapturingYDL):
        def extract_info(self, url, download=True):
            if error:
                _CapturingYDL.captured["logger"].error(error)
            return info

    monkeypatch.setattr(mod, "YoutubeDL", _FakeYDL)
    wrapper = mod.YtDlpWrapper()
    ok = wrapper.download(
        url="https://example.com/video",
        output_dir=str(tmp_path),
        format_string="best",
        download_thumbnail=False,
    )
    return ok, wrapper


def test_download_fails_when_ytdlp_returns_none(monkeypatch, tmp_path):
    """v0.1.3 logged 'DOWNLOAD COMPLETED SUCCESSFULLY' with nothing on disk.

    With ignoreerrors='only_download', an unavailable format makes
    extract_info return None instead of raising.
    """
    msg = "ERROR: [youtube] abc: Requested format is not available"
    ok, wrapper = _run_download_returning(monkeypatch, tmp_path, None, error=msg)
    assert ok is False
    assert "Requested format is not available" in wrapper._last_error


def test_download_fails_when_reported_file_is_missing(monkeypatch, tmp_path):
    info = {"requested_downloads": [{"filepath": str(tmp_path / "gone.mp4")}]}
    ok, wrapper = _run_download_returning(monkeypatch, tmp_path, info)
    assert ok is False
    assert "without writing a file" in wrapper._last_error


def test_download_succeeds_when_file_exists(monkeypatch, tmp_path):
    out = tmp_path / "video.mp4"
    out.write_bytes(b"x")
    info = {"requested_downloads": [{"filepath": str(out)}]}
    ok, _ = _run_download_returning(monkeypatch, tmp_path, info)
    assert ok is True


def test_ytdlp_logger_is_wired(monkeypatch):
    """yt-dlp's own errors must reach the app log, not the discarded stderr."""
    opts = _run_download_with_capture(monkeypatch)
    bridge = opts.get("logger")
    assert bridge is not None
    for method in ("debug", "info", "warning", "error"):
        assert callable(getattr(bridge, method))


def test_existing_output_files_filters_missing(tmp_path):
    from src.backend.yt_dlp_wrapper import _existing_output_files

    real = tmp_path / "a.mp3"
    real.write_bytes(b"x")
    info = {"requested_downloads": [{"filepath": str(real)}, {"filepath": str(tmp_path / "b.mp3")}, {}]}
    assert _existing_output_files(info) == [str(real)]
    assert _existing_output_files(None) == []
    assert _existing_output_files({"id": "x"}) == []


# ---------- download result: output paths and title ----------


def test_download_exposes_output_files_and_title(monkeypatch, tmp_path):
    out = tmp_path / "Me at the zoo_240p.mp4"
    out.write_bytes(b"x")
    info = {"title": "Me at the zoo", "requested_downloads": [{"filepath": str(out)}]}
    ok, wrapper = _run_download_returning(monkeypatch, tmp_path, info)
    assert ok is True
    assert wrapper.last_output_files == [str(out)]
    assert wrapper.last_title == "Me at the zoo"
    assert wrapper.last_error is None


def test_output_files_are_a_copy(monkeypatch, tmp_path):
    out = tmp_path / "video.mp4"
    out.write_bytes(b"x")
    info = {"requested_downloads": [{"filepath": str(out)}]}
    _, wrapper = _run_download_returning(monkeypatch, tmp_path, info)
    wrapper.last_output_files.clear()
    assert wrapper.last_output_files == [str(out)]


def test_empty_title_gives_none(monkeypatch, tmp_path):
    out = tmp_path / "video.mp4"
    out.write_bytes(b"x")
    info = {"title": "", "requested_downloads": [{"filepath": str(out)}]}
    _, wrapper = _run_download_returning(monkeypatch, tmp_path, info)
    assert wrapper.last_title is None


def test_failed_download_has_no_output_files(monkeypatch, tmp_path):
    info = {"title": "Gone", "requested_downloads": [{"filepath": str(tmp_path / "gone.mp4")}]}
    ok, wrapper = _run_download_returning(monkeypatch, tmp_path, info)
    assert ok is False
    assert wrapper.last_output_files == []
    assert wrapper.last_title is None
    assert wrapper.last_error == wrapper._last_error
    assert "without writing a file" in wrapper.last_error


def test_result_is_reset_on_each_download(monkeypatch, tmp_path):
    """A failed second download must not keep the first download's result."""
    from src.backend import yt_dlp_wrapper as mod

    out = tmp_path / "first.mp4"
    out.write_bytes(b"x")
    results = [
        {"title": "First", "requested_downloads": [{"filepath": str(out)}]},
        None,
    ]

    class _SequenceYDL(_CapturingYDL):
        def extract_info(self, url, download=True):
            return results.pop(0)

    monkeypatch.setattr(mod, "YoutubeDL", _SequenceYDL)
    wrapper = mod.YtDlpWrapper()
    kwargs = {"url": "https://example.com/v", "output_dir": str(tmp_path), "format_string": "best"}

    assert wrapper.download(**kwargs) is True
    assert wrapper.last_title == "First"
    assert wrapper.last_error is None

    assert wrapper.download(**kwargs) is False
    assert wrapper.last_output_files == []
    assert wrapper.last_title is None
    assert wrapper.last_error


def test_new_wrapper_has_empty_result():
    from src.backend.yt_dlp_wrapper import YtDlpWrapper

    w = YtDlpWrapper()
    assert w.last_output_files == []
    assert w.last_title is None
    assert w.last_error is None
