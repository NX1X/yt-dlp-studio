"""Unit tests for DownloadOptions and build_ydl_opts (pure, no yt-dlp run)."""

from __future__ import annotations

import dataclasses
import os

import pytest

from src.backend.download_options import (
    AUDIO_FILENAME_TEMPLATE,
    VIDEO_FILENAME_TEMPLATE,
    DownloadOptions,
    build_postprocessors,
    build_ydl_opts,
)

OUT = os.path.join("downloads", "here")


def _opts(**kwargs):
    return DownloadOptions("https://example.com/v", OUT, "best", **kwargs)


def test_defaults_match_the_old_download_signature():
    o = _opts()
    assert (o.audio_only, o.audio_quality, o.audio_format, o.video_container) == (False, "192", "mp3", None)
    assert (o.download_thumbnail, o.download_subtitles, o.subtitle_languages) == (True, False, "en")
    assert (o.selected_subtitles, o.download_metadata, o.download_comments) == (None, False, False)
    assert (o.speed_limit, o.auto_number_duplicates) == (0, True)


def test_options_are_keyword_only_after_format_string():
    with pytest.raises(TypeError):
        DownloadOptions("u", OUT, "best", True)  # type: ignore[misc]


def test_options_are_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        _opts().audio_only = True  # type: ignore[misc]


def test_output_template_by_mode():
    assert _opts().output_template == os.path.join(OUT, VIDEO_FILENAME_TEMPLATE)
    assert _opts(audio_only=True).output_template == os.path.join(OUT, AUDIO_FILENAME_TEMPLATE)


def test_extract_audio_format_only_for_audio():
    assert _opts(audio_format="flac").extract_audio_format is None
    assert _opts(audio_only=True, audio_format="flac").extract_audio_format == "flac"


@pytest.mark.parametrize(
    ("selected", "text", "expected"),
    [
        (None, "en", ["en"]),
        (None, " en, he ,,", ["en", "he"]),
        ([], "de", ["de"]),
        (["iw"], "fr", ["iw"]),
        (None, "", []),
    ],
)
def test_subtitle_language_list(selected, text, expected):
    assert _opts(selected_subtitles=selected, subtitle_languages=text).subtitle_language_list == expected


def test_build_is_pure_without_runtimes():
    ydl_opts = build_ydl_opts(_opts(download_thumbnail=False))
    assert ydl_opts == {
        "format": "best",
        "outtmpl": os.path.join(OUT, VIDEO_FILENAME_TEMPLATE),
        "progress_hooks": [],
        "quiet": False,
        "no_warnings": False,
        "windowsfilenames": True,
        "ignoreerrors": "only_download",
        "noplaylist": True,
        "nooverwrites": True,
    }


def test_build_passes_hooks_and_runtimes():
    def hook(d):
        return None

    ydl_opts = build_ydl_opts(_opts(), progress_hooks=[hook], ffmpeg_location="/ff", deno_path="/deno")
    assert ydl_opts["progress_hooks"] == [hook]
    assert ydl_opts["ffmpeg_location"] == "/ff"
    assert ydl_opts["js_runtimes"] == {"deno": {"path": "/deno"}}


def test_build_returns_a_new_dict_each_time():
    o = _opts()
    first = build_ydl_opts(o)
    first["format"] = "changed"
    first["postprocessors"].clear()
    assert build_ydl_opts(o)["format"] == "best"
    assert build_ydl_opts(o)["postprocessors"] == [{"key": "FFmpegThumbnailsConvertor", "format": "jpg"}]


def test_postprocessor_order():
    pps = build_postprocessors(_opts(audio_only=True, download_subtitles=True))
    assert [pp["key"] for pp in pps] == ["FFmpegExtractAudio", "FFmpegThumbnailsConvertor"]
    pps = build_postprocessors(_opts(download_subtitles=True))
    assert [pp["key"] for pp in pps] == ["FFmpegThumbnailsConvertor", "FFmpegEmbedSubtitle"]
    assert build_postprocessors(_opts(download_thumbnail=False)) == []


def test_replace_makes_a_variant():
    base = _opts()
    audio = dataclasses.replace(base, audio_only=True)
    assert build_ydl_opts(audio)["format"] == "bestaudio"
    assert build_ydl_opts(base)["format"] == "best"
