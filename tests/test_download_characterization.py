"""Characterization tests for ``YtDlpWrapper.download()``.

These tests pin what the download flow hands to yt-dlp, so a refactor of
``download()`` cannot change behavior unnoticed. For each input they record:

- the exact options dict passed to ``YoutubeDL(...)``, postprocessors included,
- the post-processors added with ``add_post_processor`` (duplicate numbering),
- whether subtitle failures were made non-fatal,
- the result: return value, ``last_output_files``, ``last_title``, ``last_error``.

The expected values were recorded from the code before the refactor. A change
here is a change of behavior, so it needs a reason in the PR.

Changed on purpose in 0.5.0 (each change is marked "Fixed in 0.5.0" below):

- With metadata on, FFmpegMetadata now stays in the post-processor list when
  other post-processors exist. Before, the later list replaced it. The
  "postprocessors" key is now always the last option.
- The metadata and comments files take the base name of the video
  ("name_metadata.txt", "name Comments.txt"), not "name.info_metadata.txt",
  and "name.description" is renamed to "name_description.txt".

YoutubeDL is replaced by a recording fake; no network is used.
"""

from __future__ import annotations

import json
import os
import time

import pytest

from src.backend import yt_dlp_wrapper as mod
from src.backend.download_options import DownloadOptions
from src.backend.download_worker import DownloadWorker
from src.models.download_task import DownloadTask, TaskStatus
from src.utils.constants import QUALITY_NAMES

FFMPEG_DIR = "/opt/ffmpeg"
DENO_PATH = "/opt/deno/deno"
URL = "https://www.youtube.com/watch?v=abc123"
OUT = "<OUT>"


class _RecordingYDL:
    """Fake YoutubeDL that records how the wrapper configures it."""

    runs: list[dict] = []
    # Called as extract(ydl, url) for download=True; returns the info dict.
    extract = None

    def __init__(self, params=None):
        self.params = params or {}
        self.added = []
        self._original_write_subtitles = self._write_subtitles_impl
        self._write_subtitles = self._original_write_subtitles
        type(self).runs.append({"ydl": self, "params": self.params})

    def _write_subtitles_impl(self, info, filename):
        return []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def add_post_processor(self, pp, when="post_process"):
        self.added.append((pp, when))

    def report_warning(self, msg):
        pass

    def extract_info(self, url, download=True):
        if not download:
            return {"id": "abc123", "title": "Probe Title"}
        return type(self).extract(self, url)


def _write_output(ydl, name="Clip_720p.mp4", info=None):
    """Write one output file into the template's folder and report it."""
    folder = os.path.dirname(ydl.params["outtmpl"])
    path = os.path.join(folder, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write("data")
    result = {"id": "abc123", "title": "Clip", "requested_downloads": [{"filepath": path}]}
    result.update(info or {})
    return result


@pytest.fixture
def fake_ydl(monkeypatch):
    _RecordingYDL.runs = []
    _RecordingYDL.extract = staticmethod(lambda ydl, url: _write_output(ydl))
    monkeypatch.setattr(mod, "YoutubeDL", _RecordingYDL)
    monkeypatch.setattr(mod.YtDlpWrapper, "_get_ffmpeg_location", lambda self: FFMPEG_DIR)
    monkeypatch.setattr(mod.YtDlpWrapper, "_get_deno_location", lambda self: DENO_PATH)
    # The comments post-processing waits 1 s for yt-dlp; skip that here.
    monkeypatch.setattr(time, "sleep", lambda s: None)
    yield _RecordingYDL
    assert not mod._reserved_outputs, "a download left a reservation behind"


def _normalize(value, out_dir):
    """Replace the temporary output folder with ``<OUT>`` (and use ``/``)."""
    if isinstance(value, str):
        if value.startswith(out_dir):
            return OUT + value[len(out_dir) :].replace(os.sep, "/")
        return value
    if isinstance(value, list):
        return [_normalize(v, out_dir) for v in value]
    if isinstance(value, dict):
        return {k: _normalize(v, out_dir) for k, v in value.items()}
    return value


def _call_download(wrapper, **kwargs):
    """The one place that knows how download() is called."""
    return wrapper.download(DownloadOptions(**kwargs))


def _snapshot(wrapper, run, ok, out_dir):
    ydl = run["ydl"]
    params = dict(run["params"])

    # Objects, not config: check them here and keep them out of the snapshot.
    assert params.pop("progress_hooks") == [wrapper._progress_hook]
    assert isinstance(params.pop("logger"), mod._YtDlpLogBridge)

    added = []
    for pp, when in ydl.added:
        assert isinstance(pp, mod._DuplicateNumberingPP)
        added.append(
            {
                "when": when,
                "template": _normalize(pp._template, out_dir),
                "audio_format": pp._audio_format,
            }
        )
    return {
        "ydl_opts": _normalize(params, out_dir),
        "added_pps": added,
        "subtitles_non_fatal": ydl._write_subtitles is not ydl._original_write_subtitles,
        "ok": ok,
        "last_output_files": [_normalize(p, out_dir) for p in wrapper.last_output_files],
        "last_title": wrapper.last_title,
        "last_error": wrapper.last_error,
    }


def _run_wrapper(tmp_path, fake, **kwargs):
    out_dir = str(tmp_path)
    params = {"url": URL, "output_dir": out_dir, "format_string": "bestvideo+bestaudio/best"}
    params.update(kwargs)
    wrapper = mod.YtDlpWrapper()
    ok = _call_download(wrapper, **params)
    (run,) = fake.runs
    return _snapshot(wrapper, run, ok, out_dir)


# Base options every download gets (with FFmpeg and Deno found).
_BASE = {
    "format": "bestvideo+bestaudio/best",
    "outtmpl": OUT + "/%(title)s_%(height)sp.%(ext)s",
    "quiet": False,
    "no_warnings": False,
    "windowsfilenames": True,
    "ignoreerrors": "only_download",
    "noplaylist": True,
    "nooverwrites": True,
    "ffmpeg_location": FFMPEG_DIR,
    "js_runtimes": {"deno": {"path": DENO_PATH}},
}
_AUDIO_BASE = {**_BASE, "format": "bestaudio", "outtmpl": OUT + "/%(title)s_%(quality)s.%(ext)s", "keepvideo": False}
_THUMB_PP = {"key": "FFmpegThumbnailsConvertor", "format": "jpg"}
_METADATA_PP = {"key": "FFmpegMetadata", "add_infojson": "if_exists"}
_EMBED_SUBS_PP = {"key": "FFmpegEmbedSubtitle"}
_SUBS = {
    "writesubtitles": True,
    "writeautomaticsub": True,
    "subtitlesformat": "srt",
    "sleep_interval_subtitles": 2,
}
_METADATA = {
    "writeinfojson": True,
    "clean_infojson": False,
    "writedescription": True,
    "writeannotations": True,
    "getcomments": True,
}
_VIDEO_NUMBERING = [{"when": "video", "template": OUT + "/%(title)s_%(height)sp.%(ext)s", "audio_format": None}]


def _audio_pp(codec, quality):
    return {
        "key": "FFmpegExtractAudio",
        "preferredcodec": codec,
        "preferredquality": quality,
        "nopostoverwrites": False,
    }


def _audio_numbering(codec):
    return [{"when": "video", "template": OUT + "/%(title)s_%(quality)s.%(ext)s", "audio_format": codec}]


# name -> (download() keyword arguments, expected ydl_opts, expected added pps, subtitles non-fatal)
CASES = {
    "video_defaults": (
        {},
        {**_BASE, "writethumbnail": True, "postprocessors": [_THUMB_PP]},
        _VIDEO_NUMBERING,
        False,
    ),
    "video_no_thumbnail_no_postprocessors": (
        {"download_thumbnail": False},
        dict(_BASE),
        _VIDEO_NUMBERING,
        False,
    ),
    "video_720p_mp4": (
        {
            "format_string": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "video_container": "mp4",
            "download_thumbnail": False,
        },
        {
            **_BASE,
            "format": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "merge_output_format": "mp4",
        },
        _VIDEO_NUMBERING,
        False,
    ),
    "video_mkv": (
        {"video_container": "mkv", "download_thumbnail": False},
        {**_BASE, "merge_output_format": "mkv"},
        _VIDEO_NUMBERING,
        False,
    ),
    "video_webm": (
        {"video_container": "webm", "download_thumbnail": False},
        {**_BASE, "merge_output_format": "webm"},
        _VIDEO_NUMBERING,
        False,
    ),
    "video_speed_limit": (
        {"speed_limit": 512, "download_thumbnail": False},
        {**_BASE, "ratelimit": 512 * 1024},
        _VIDEO_NUMBERING,
        False,
    ),
    "video_negative_speed_limit_ignored": (
        {"speed_limit": -5, "download_thumbnail": False},
        dict(_BASE),
        _VIDEO_NUMBERING,
        False,
    ),
    "video_no_auto_number": (
        {"auto_number_duplicates": False, "download_thumbnail": False},
        dict(_BASE),
        [],
        False,
    ),
    "playlist_url_still_single_video": (
        {"url": URL + "&list=PL0123456789", "download_thumbnail": False},
        dict(_BASE),
        _VIDEO_NUMBERING,
        False,
    ),
    "subtitles_from_language_string": (
        {"download_subtitles": True, "subtitle_languages": " en, he ,,es ", "download_thumbnail": False},
        {**_BASE, **_SUBS, "subtitleslangs": ["en", "he", "es"], "postprocessors": [_EMBED_SUBS_PP]},
        _VIDEO_NUMBERING,
        True,
    ),
    "subtitles_selected_list_wins": (
        {
            "download_subtitles": True,
            "subtitle_languages": "fr",
            "selected_subtitles": ["en", "iw"],
            "download_thumbnail": False,
        },
        {**_BASE, **_SUBS, "subtitleslangs": ["en", "iw"], "postprocessors": [_EMBED_SUBS_PP]},
        _VIDEO_NUMBERING,
        True,
    ),
    "subtitles_empty_selection_falls_back": (
        {"download_subtitles": True, "subtitle_languages": "de", "selected_subtitles": [], "download_thumbnail": False},
        {**_BASE, **_SUBS, "subtitleslangs": ["de"], "postprocessors": [_EMBED_SUBS_PP]},
        _VIDEO_NUMBERING,
        True,
    ),
    "subtitles_off_ignores_selection": (
        {"download_subtitles": False, "selected_subtitles": ["en"], "download_thumbnail": False},
        dict(_BASE),
        _VIDEO_NUMBERING,
        False,
    ),
    "subtitles_and_thumbnail": (
        {"download_subtitles": True, "subtitle_languages": "en"},
        {
            **_BASE,
            **_SUBS,
            "subtitleslangs": ["en"],
            "writethumbnail": True,
            "postprocessors": [_THUMB_PP, _EMBED_SUBS_PP],
        },
        _VIDEO_NUMBERING,
        True,
    ),
    "metadata_only_keeps_ffmpeg_metadata": (
        {"download_metadata": True, "download_thumbnail": False},
        {**_BASE, **_METADATA, "postprocessors": [_METADATA_PP]},
        _VIDEO_NUMBERING,
        False,
    ),
    # Fixed in 0.5.0: up to 0.4.1 the later postprocessors list replaced the
    # one that held FFmpegMetadata, so the metadata was never embedded when
    # any other pp was configured. It now runs last.
    "metadata_with_thumbnail_keeps_ffmpeg_metadata": (
        {"download_metadata": True},
        {**_BASE, **_METADATA, "writethumbnail": True, "postprocessors": [_THUMB_PP, _METADATA_PP]},
        _VIDEO_NUMBERING,
        False,
    ),
    "comments_only": (
        {"download_comments": True, "download_thumbnail": False},
        {**_BASE, "getcomments": True, "writeinfojson": True},
        _VIDEO_NUMBERING,
        False,
    ),
    "subtitles_and_comments_space_requests": (
        {"download_subtitles": True, "download_comments": True, "download_thumbnail": False},
        {
            **_BASE,
            **_SUBS,
            "subtitleslangs": ["en"],
            "getcomments": True,
            "writeinfojson": True,
            "sleep_interval_requests": 1,
            "postprocessors": [_EMBED_SUBS_PP],
        },
        _VIDEO_NUMBERING,
        True,
    ),
    "everything_on": (
        {
            "download_subtitles": True,
            "selected_subtitles": ["en"],
            "download_metadata": True,
            "download_comments": True,
            "video_container": "mp4",
            "speed_limit": 100,
        },
        {
            **_BASE,
            **_SUBS,
            **_METADATA,
            "subtitleslangs": ["en"],
            "merge_output_format": "mp4",
            "ratelimit": 100 * 1024,
            "writethumbnail": True,
            "sleep_interval_requests": 1,
            # Fixed in 0.5.0: FFmpegMetadata was dropped here.
            "postprocessors": [_THUMB_PP, _EMBED_SUBS_PP, _METADATA_PP],
        },
        _VIDEO_NUMBERING,
        True,
    ),
    "audio_with_metadata_tags_the_audio_file": (
        {"audio_only": True, "download_metadata": True, "download_thumbnail": False},
        {**_AUDIO_BASE, **_METADATA, "postprocessors": [_audio_pp("mp3", "192"), _METADATA_PP]},
        _audio_numbering("mp3"),
        False,
    ),
    "audio_mp3_192_default_thumbnail": (
        {"audio_only": True},
        {**_AUDIO_BASE, "writethumbnail": True, "postprocessors": [_audio_pp("mp3", "192"), _THUMB_PP]},
        _audio_numbering("mp3"),
        False,
    ),
    "audio_ignores_container_and_format_string": (
        {
            "audio_only": True,
            "video_container": "mkv",
            "format_string": "best[height<=360]",
            "download_thumbnail": False,
        },
        {**_AUDIO_BASE, "postprocessors": [_audio_pp("mp3", "192")]},
        _audio_numbering("mp3"),
        False,
    ),
    "audio_with_subtitles_does_not_embed": (
        {"audio_only": True, "download_subtitles": True, "download_thumbnail": False},
        {**_AUDIO_BASE, **_SUBS, "subtitleslangs": ["en"], "postprocessors": [_audio_pp("mp3", "192")]},
        _audio_numbering("mp3"),
        True,
    ),
    "audio_no_auto_number": (
        {"audio_only": True, "auto_number_duplicates": False, "download_thumbnail": False},
        {**_AUDIO_BASE, "postprocessors": [_audio_pp("mp3", "192")]},
        [],
        False,
    ),
}

_AUDIO_FORMAT_CASES = [("mp3", "320"), ("m4a", "256"), ("opus", "128"), ("flac", "0"), ("wav", "192"), ("vorbis", "0")]
for _codec, _quality in _AUDIO_FORMAT_CASES:
    CASES[f"audio_{_codec}_{_quality}"] = (
        {"audio_only": True, "audio_format": _codec, "audio_quality": _quality, "download_thumbnail": False},
        {**_AUDIO_BASE, "postprocessors": [_audio_pp(_codec, _quality)]},
        _audio_numbering(_codec),
        False,
    )


@pytest.mark.parametrize("name", list(CASES))
def test_ydl_options_matrix(name, tmp_path, fake_ydl):
    kwargs, expected_opts, expected_added, subs_non_fatal = CASES[name]
    snap = _run_wrapper(tmp_path, fake_ydl, **kwargs)
    assert snap["ydl_opts"] == expected_opts
    assert snap["added_pps"] == expected_added
    assert snap["subtitles_non_fatal"] is subs_non_fatal
    assert snap["ok"] is True
    assert snap["last_output_files"] == [OUT + "/Clip_720p.mp4"]
    assert snap["last_title"] == "Clip"
    assert snap["last_error"] is None


def test_options_without_ffmpeg_and_deno(tmp_path, fake_ydl, monkeypatch):
    monkeypatch.setattr(mod.YtDlpWrapper, "_get_ffmpeg_location", lambda self: None)
    monkeypatch.setattr(mod.YtDlpWrapper, "_get_deno_location", lambda self: None)
    snap = _run_wrapper(tmp_path, fake_ydl, download_thumbnail=False)
    expected = {k: v for k, v in _BASE.items() if k not in ("ffmpeg_location", "js_runtimes")}
    assert snap["ydl_opts"] == expected


def test_option_key_order_is_kept(tmp_path, fake_ydl):
    """The options dict is logged as JSON; keep its key order stable."""
    _run_wrapper(
        tmp_path,
        fake_ydl,
        download_subtitles=True,
        download_metadata=True,
        download_comments=True,
        video_container="mp4",
        speed_limit=100,
    )
    keys = [k for k in fake_ydl.runs[0]["params"]]
    assert keys == [
        "format",
        "outtmpl",
        "progress_hooks",
        "quiet",
        "no_warnings",
        "windowsfilenames",
        "ignoreerrors",
        "noplaylist",
        "nooverwrites",
        "ffmpeg_location",
        "js_runtimes",
        "merge_output_format",
        "ratelimit",
        "writethumbnail",
        "writesubtitles",
        "writeautomaticsub",
        "subtitleslangs",
        "subtitlesformat",
        "sleep_interval_subtitles",
        "writeinfojson",
        "clean_infojson",
        "writedescription",
        "writeannotations",
        "getcomments",
        "sleep_interval_requests",
        # Changed in 0.5.0: always last (it was where metadata put it).
        "postprocessors",
        "logger",
    ]


# ---------- result reporting ----------


def test_failure_when_nothing_is_written(tmp_path, fake_ydl):
    def extract(ydl, url):
        ydl.params["logger"].error("ERROR: Requested format is not available")
        return None

    fake_ydl.extract = staticmethod(extract)
    snap = _run_wrapper(tmp_path, fake_ydl, download_thumbnail=False)
    assert snap["ok"] is False
    assert snap["last_output_files"] == []
    assert snap["last_title"] is None
    assert snap["last_error"] == "yt-dlp finished without writing a file: ERROR: Requested format is not available"


def test_failure_without_logged_error(tmp_path, fake_ydl):
    fake_ydl.extract = staticmethod(lambda ydl, url: {"title": "X", "requested_downloads": []})
    snap = _run_wrapper(tmp_path, fake_ydl, download_thumbnail=False)
    assert snap["ok"] is False
    assert snap["last_error"] == "yt-dlp finished without writing a file: no error was reported"


def test_failure_when_extract_raises(tmp_path, fake_ydl):
    def extract(ydl, url):
        raise ValueError("boom")

    fake_ydl.extract = staticmethod(extract)
    wrapper = mod.YtDlpWrapper()
    ok = _call_download(wrapper, url=URL, output_dir=str(tmp_path), format_string="best")
    assert ok is False
    assert wrapper.last_error == "boom"
    assert wrapper._last_error_type == "ValueError"
    assert wrapper.last_output_files == []


def test_cancel_during_download_returns_false(tmp_path, fake_ydl):
    wrapper = mod.YtDlpWrapper()

    def extract(ydl, url):
        wrapper.cancel_download()
        return _write_output(ydl)

    fake_ydl.extract = staticmethod(extract)
    ok = _call_download(wrapper, url=URL, output_dir=str(tmp_path), format_string="best")
    assert ok is False
    assert wrapper.last_output_files == []
    assert wrapper.last_title is None
    assert wrapper.last_error is None


def test_cancel_before_call_is_reset(tmp_path, fake_ydl):
    """download() clears an earlier cancel request and runs."""
    wrapper = mod.YtDlpWrapper()
    wrapper.cancel_download()
    ok = _call_download(wrapper, url=URL, output_dir=str(tmp_path), format_string="best")
    assert ok is True


def test_non_string_title_gives_none(tmp_path, fake_ydl):
    fake_ydl.extract = staticmethod(lambda ydl, url: _write_output(ydl, info={"title": 42}))
    snap = _run_wrapper(tmp_path, fake_ydl, download_thumbnail=False)
    assert snap["ok"] is True
    assert snap["last_title"] is None


def test_all_existing_output_files_are_reported(tmp_path, fake_ydl):
    def extract(ydl, url):
        info = _write_output(ydl, name="a.mp4")
        second = _write_output(ydl, name="b.mp4")
        missing = {"filepath": os.path.join(str(tmp_path), "gone.mp4")}
        info["requested_downloads"] += second["requested_downloads"] + [missing]
        return info

    fake_ydl.extract = staticmethod(extract)
    snap = _run_wrapper(tmp_path, fake_ydl, download_thumbnail=False)
    assert snap["last_output_files"] == [OUT + "/a.mp4", OUT + "/b.mp4"]


# ---------- metadata and comments side files ----------

_INFO_JSON = {
    "title": "Clip",
    "uploader": "Uploader",
    "channel": "Channel",
    "channel_id": "UC123",
    "id": "abc123",
    "webpage_url": URL,
    "upload_date": "20050423",
    "duration": 3725,
    "view_count": 1234567,
    "like_count": 890,
    "comment_count": 2,
    "width": 1280,
    "height": 720,
    "fps": 30,
    "format": "22 - 1280x720",
    "vcodec": "avc1",
    "acodec": "mp4a",
    "categories": ["Music", "Comedy"],
    "tags": ["a", "b", "c", "d", "e"],
    "thumbnail": "https://example.com/t.jpg",
    "comments": [
        {"author": "Ann", "text": "First!", "like_count": 1200, "timestamp": 0},
        {"author": "Bob", "text": "Nice", "like_count": 0, "timestamp": 86400},
    ],
}

_METADATA_TXT = """\
================================================================================
VIDEO METADATA
================================================================================

[ESSENTIAL INFORMATION]
Title: Clip
Uploader: Uploader
Channel: Channel
Channel ID: UC123
Video ID: abc123
URL: https://www.youtube.com/watch?v=abc123

[UPLOAD DATE]
April 23, 2005

[DURATION]
1h 2m 5s

[STATISTICS]
Views: 1,234,567
Likes: 890
Comments: 2

[VIDEO QUALITY]
Resolution: 1280x720
FPS: 30
Format: 22 - 1280x720
Video Codec: avc1
Audio Codec: mp4a

[CATEGORIES]
Music, Comedy

[TAGS]
a, b, c, d
e

[THUMBNAIL URL]
https://example.com/t.jpg

================================================================================
End of Metadata
================================================================================
"""

_COMMENTS_TXT = """\
================================================================================
VIDEO COMMENTS
================================================================================

Video Title: Clip
Total Comments: 2
================================================================================

[Comment #1]
Author: Ann
Likes: 1,200

First!
--------------------------------------------------------------------------------

[Comment #2]
Author: Bob
Date: 1970-01-02 00:00:00

Nice
--------------------------------------------------------------------------------

"""


@pytest.fixture
def utc(monkeypatch):
    if not hasattr(time, "tzset"):
        pytest.skip("time.tzset is not available on this platform")
    monkeypatch.setenv("TZ", "UTC")
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()


def _extract_with_sidecars(info=_INFO_JSON):
    def extract(ydl, url):
        folder = os.path.dirname(ydl.params["outtmpl"])
        base = os.path.join(folder, "Clip_720p")
        with open(base + ".info.json", "w", encoding="utf-8") as f:
            json.dump(info, f)
        with open(base + ".description", "w", encoding="utf-8") as f:
            f.write("The description")
        return _write_output(ydl)

    return staticmethod(extract)


def test_metadata_side_files(tmp_path, fake_ydl, utc):
    fake_ydl.extract = _extract_with_sidecars()
    snap = _run_wrapper(tmp_path, fake_ydl, download_metadata=True, download_thumbnail=False)
    assert snap["ok"] is True
    # Fixed in 0.5.0: up to 0.4.1 the base name came from
    # splitext("x.info.json"), so it kept ".info" ("Clip_720p.info_metadata.txt")
    # and the ".description" file was never renamed.
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "Clip_720p.info.json",
        "Clip_720p.mp4",
        "Clip_720p_description.txt",
        "Clip_720p_metadata.txt",
    ]
    assert (tmp_path / "Clip_720p_metadata.txt").read_text(encoding="utf-8") == _METADATA_TXT
    assert (tmp_path / "Clip_720p_description.txt").read_text(encoding="utf-8") == "The description"
    assert (tmp_path / "Clip_720p.info.json").read_text(encoding="utf-8") == json.dumps(
        _INFO_JSON, indent=2, ensure_ascii=False
    )


def test_metadata_side_files_minimal_info(tmp_path, fake_ydl, utc):
    """Missing fields print N/A; empty sections are left out."""
    fake_ydl.extract = _extract_with_sidecars({"upload_date": "2005"})
    _run_wrapper(tmp_path, fake_ydl, download_metadata=True, download_thumbnail=False)
    text = (tmp_path / "Clip_720p_metadata.txt").read_text(encoding="utf-8")
    assert text == (
        "=" * 80 + "\nVIDEO METADATA\n" + "=" * 80 + "\n\n"
        "[ESSENTIAL INFORMATION]\nTitle: N/A\nUploader: N/A\nChannel: N/A\nChannel ID: N/A\n"
        "Video ID: N/A\nURL: N/A\n\n"
        "[STATISTICS]\n\n"
        "[VIDEO QUALITY]\nResolution: N/AxN/A\nFPS: N/A\nFormat: N/A\nVideo Codec: N/A\nAudio Codec: N/A\n\n"
        + "=" * 80
        + "\nEnd of Metadata\n"
        + "=" * 80
        + "\n"
    )


def test_metadata_bad_upload_date_is_written_raw(tmp_path, fake_ydl, utc):
    fake_ydl.extract = _extract_with_sidecars({"upload_date": "2005ABCD", "duration": 59})
    _run_wrapper(tmp_path, fake_ydl, download_metadata=True, download_thumbnail=False)
    text = (tmp_path / "Clip_720p_metadata.txt").read_text(encoding="utf-8")
    assert "[UPLOAD DATE]\n2005ABCD\n\n" in text
    assert "[DURATION]\n0m 59s\n\n" in text


def test_comments_side_file_removes_json(tmp_path, fake_ydl, utc):
    fake_ydl.extract = _extract_with_sidecars()
    snap = _run_wrapper(tmp_path, fake_ydl, download_comments=True, download_thumbnail=False)
    assert snap["ok"] is True
    # Fixed in 0.5.0: was "Clip_720p.info Comments.txt".
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "Clip_720p Comments.txt",
        "Clip_720p.description",
        "Clip_720p.mp4",
    ]
    assert (tmp_path / "Clip_720p Comments.txt").read_text(encoding="utf-8") == _COMMENTS_TXT


def test_comments_and_metadata_keep_json(tmp_path, fake_ydl, utc):
    fake_ydl.extract = _extract_with_sidecars()
    _run_wrapper(tmp_path, fake_ydl, download_comments=True, download_metadata=True, download_thumbnail=False)
    # Fixed in 0.5.0: base names without ".info", description renamed.
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "Clip_720p Comments.txt",
        "Clip_720p.info.json",
        "Clip_720p.mp4",
        "Clip_720p_description.txt",
        "Clip_720p_metadata.txt",
    ]


def test_comments_none_found_keeps_json(tmp_path, fake_ydl, utc):
    fake_ydl.extract = _extract_with_sidecars({"title": "Clip", "comments": []})
    _run_wrapper(tmp_path, fake_ydl, download_comments=True, download_thumbnail=False)
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "Clip_720p.description",
        "Clip_720p.info.json",
        "Clip_720p.mp4",
    ]


def test_side_files_without_info_json_still_succeed(tmp_path, fake_ydl):
    snap = _run_wrapper(tmp_path, fake_ydl, download_comments=True, download_metadata=True, download_thumbnail=False)
    assert snap["ok"] is True
    assert sorted(p.name for p in tmp_path.iterdir()) == ["Clip_720p.mp4"]


def test_broken_info_json_does_not_fail_download(tmp_path, fake_ydl):
    def extract(ydl, url):
        (tmp_path / "Clip_720p.info.json").write_text("{not json", encoding="utf-8")
        return _write_output(ydl)

    fake_ydl.extract = staticmethod(extract)
    snap = _run_wrapper(tmp_path, fake_ydl, download_comments=True, download_metadata=True, download_thumbnail=False)
    assert snap["ok"] is True


# ---------- the worker: quality presets and task fields ----------


@pytest.fixture
def no_sound(monkeypatch):
    import sys

    monkeypatch.setitem(sys.modules, "winsound", None)
    from PySide6.QtWidgets import QApplication

    monkeypatch.setattr(QApplication, "beep", staticmethod(lambda: None))


def _run_worker(tmp_path, fake, **task_fields):
    task = DownloadTask(url=URL, output_directory=str(tmp_path), **task_fields)
    worker = DownloadWorker(task)
    worker.run()
    # Run 0 is get_video_info, run 1 is the download.
    probe, run = fake.runs
    assert probe["params"]["skip_download"] is True
    return task, worker, _snapshot(worker.wrapper, run, task.status == TaskStatus.COMPLETED, str(tmp_path))


_VIDEO_PRESET_FORMATS = {
    "Best Quality": "bestvideo+bestaudio/best",
    "8K (4320p)": "bestvideo[height<=4320]+bestaudio/best[height<=4320]",
    "4K (2160p)": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
    "2K (1440p)": "bestvideo[height<=1440]+bestaudio/best[height<=1440]",
    "1080p (Full HD)": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720p (HD)": "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480p (SD)": "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]",
}
_AUDIO_PRESET_QUALITY = {
    "Best Quality": "0",
    "Audio 320kbps": "320",
    "Audio 256kbps": "256",
    "Audio 192kbps": "192",
    "Audio 128kbps": "128",
}


def test_presets_cover_all_quality_names():
    assert set(_VIDEO_PRESET_FORMATS) | set(_AUDIO_PRESET_QUALITY) == set(QUALITY_NAMES)


@pytest.mark.parametrize("quality", list(_VIDEO_PRESET_FORMATS))
def test_worker_video_presets(quality, tmp_path, fake_ydl, no_sound):
    task, _, snap = _run_worker(tmp_path, fake_ydl, quality=quality)
    # DownloadTask defaults: thumbnail on, container auto, numbering on.
    assert snap["ydl_opts"] == {
        **_BASE,
        "format": _VIDEO_PRESET_FORMATS[quality],
        "writethumbnail": True,
        "postprocessors": [_THUMB_PP],
    }
    assert snap["added_pps"] == _VIDEO_NUMBERING
    assert task.status == TaskStatus.COMPLETED
    assert task.filename == "Clip_720p.mp4"
    assert task.title == "Clip"


@pytest.mark.parametrize("quality", list(_AUDIO_PRESET_QUALITY))
def test_worker_audio_presets(quality, tmp_path, fake_ydl, no_sound):
    task, _, snap = _run_worker(tmp_path, fake_ydl, quality=quality, audio_only=True, audio_format="opus")
    assert snap["ydl_opts"] == {
        **_AUDIO_BASE,
        "writethumbnail": True,
        "postprocessors": [_audio_pp("opus", _AUDIO_PRESET_QUALITY[quality]), _THUMB_PP],
    }
    assert snap["added_pps"] == _audio_numbering("opus")


def test_worker_passes_every_task_field(tmp_path, fake_ydl, no_sound):
    task, _, snap = _run_worker(
        tmp_path,
        fake_ydl,
        quality="720p (HD)",
        download_thumbnail=False,
        download_subtitles=True,
        subtitle_languages="fr",
        selected_subtitles=["en", "he"],
        speed_limit=64,
        video_container="mkv",
        download_metadata=False,
        download_comments=True,
        auto_number_duplicates=False,
    )
    assert snap["ydl_opts"] == {
        **_BASE,
        **_SUBS,
        "format": _VIDEO_PRESET_FORMATS["720p (HD)"],
        "merge_output_format": "mkv",
        "ratelimit": 64 * 1024,
        "subtitleslangs": ["en", "he"],
        "getcomments": True,
        "writeinfojson": True,
        "sleep_interval_requests": 1,
        "postprocessors": [_EMBED_SUBS_PP],
    }
    assert snap["added_pps"] == []
    assert snap["subtitles_non_fatal"] is True
    assert task.status == TaskStatus.COMPLETED


def test_worker_reports_failure(tmp_path, fake_ydl, no_sound):
    fake_ydl.extract = staticmethod(lambda ydl, url: None)
    task = DownloadTask(url=URL, output_directory=str(tmp_path), quality="Best Quality")
    failed = []
    worker = DownloadWorker(task)
    worker.download_failed.connect(failed.append)
    worker.run()
    assert task.status == TaskStatus.ERROR
    assert task.error_message == "Download failed"
    assert failed == ["Download failed"]
    assert worker.wrapper.last_error == "yt-dlp finished without writing a file: no error was reported"
