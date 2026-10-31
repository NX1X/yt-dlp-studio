"""Tests for auto-numbering of duplicate output files.

The download itself is faked, but the file names come from the real vendored
YoutubeDL: the fake runs yt-dlp's ``video`` pre-process stage (where the
numbering hook lives) and then ``prepare_filename``, the same order as
``YoutubeDL.process_info``. No network is used.
"""

from __future__ import annotations

import os
import threading

import pytest

from src.backend import yt_dlp_wrapper as mod

VIDEO_INFO = {"id": "abc123", "title": "My Video", "ext": "mp4", "height": 720}
AUDIO_INFO = {"id": "abc123", "title": "My Song", "ext": "webm", "quality": "medium"}


class _FakeDownloadYDL(mod.YoutubeDL):
    """Real YoutubeDL with a fake ``extract_info`` that "downloads" ``fake_info``."""

    fake_info: dict = {}
    # Set by a test to make two downloads meet after the name is chosen.
    barrier: threading.Barrier | None = None

    def extract_info(self, url, download=True, **kwargs):
        info, _ = self.pre_process(dict(type(self).fake_info), "video")
        if type(self).barrier is not None:
            type(self).barrier.wait(timeout=10)
        path = self.prepare_filename(info)

        # FFmpegExtractAudio renames the file to the codec's extension.
        for pp in self.params.get("postprocessors") or []:
            if pp.get("key") == "FFmpegExtractAudio":
                new_ext = mod.ACODECS[pp["preferredcodec"]][0]
                path = mod.replace_extension(path, new_ext, info["ext"])

        if os.path.exists(path) and not self.params.get("overwrites", True):
            pass  # yt-dlp: "has already been downloaded", file kept as is
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write("new")
        return {**info, "requested_downloads": [{"filepath": path}]}


@pytest.fixture(autouse=True)
def _fake_ytdlp(monkeypatch):
    monkeypatch.setattr(mod, "YoutubeDL", _FakeDownloadYDL)
    monkeypatch.setattr(mod.YtDlpWrapper, "_get_ffmpeg_location", lambda self: None)
    monkeypatch.setattr(mod.YtDlpWrapper, "_get_deno_location", lambda self: None)
    _FakeDownloadYDL.barrier = None
    yield
    _FakeDownloadYDL.barrier = None
    assert not mod._reserved_outputs, "a download left a reservation behind"


def _download(tmp_path, info=VIDEO_INFO, **kwargs):
    _FakeDownloadYDL.fake_info = info
    params = {
        "url": "https://example.com/watch?v=abc123",
        "output_dir": str(tmp_path),
        "format_string": "best",
        "download_thumbnail": False,
        "auto_number_duplicates": True,
    }
    params.update(kwargs)
    wrapper = mod.YtDlpWrapper()
    ok = wrapper.download(**params)
    assert ok is True, wrapper.last_error
    (path,) = wrapper.last_output_files
    return path


def _names(tmp_path):
    return sorted(p.name for p in tmp_path.iterdir())


# ---------- template helper ----------


def test_numbered_template_adds_suffix_before_extension():
    tmpl = os.path.join("out", "%(title)s_%(height)sp.%(ext)s")
    assert mod._numbered_template(tmpl, 0) == tmpl
    assert mod._numbered_template(tmpl, 2) == os.path.join("out", "%(title)s_%(height)sp (2).%(ext)s")


def test_numbered_template_leaves_unknown_shape_alone():
    assert mod._numbered_template("%(title)s", 1) == "%(title)s"


# ---------- end-to-end through download() ----------


def test_first_download_keeps_plain_name(tmp_path):
    path = _download(tmp_path)
    assert os.path.basename(path) == "My Video_720p.mp4"
    assert _names(tmp_path) == ["My Video_720p.mp4"]


def test_existing_file_gives_number_one(tmp_path):
    (tmp_path / "My Video_720p.mp4").write_text("old")
    path = _download(tmp_path)
    assert os.path.basename(path) == "My Video_720p (1).mp4"
    assert (tmp_path / "My Video_720p.mp4").read_text() == "old"


def test_existing_number_one_gives_number_two(tmp_path):
    (tmp_path / "My Video_720p.mp4").write_text("old")
    (tmp_path / "My Video_720p (1).mp4").write_text("old")
    path = _download(tmp_path)
    assert os.path.basename(path) == "My Video_720p (2).mp4"


def test_repeated_downloads_count_up(tmp_path):
    names = [os.path.basename(_download(tmp_path)) for _ in range(3)]
    assert names == ["My Video_720p.mp4", "My Video_720p (1).mp4", "My Video_720p (2).mp4"]


def test_different_quality_is_never_numbered(tmp_path):
    (tmp_path / "My Video_720p.mp4").write_text("old")
    path = _download(tmp_path, info={**VIDEO_INFO, "height": 1080})
    assert os.path.basename(path) == "My Video_1080p.mp4"
    assert _names(tmp_path) == ["My Video_1080p.mp4", "My Video_720p.mp4"]


def test_auto_number_off_keeps_skip_behaviour(tmp_path):
    existing = tmp_path / "My Video_720p.mp4"
    existing.write_text("old")
    path = _download(tmp_path, auto_number_duplicates=False)
    assert path == str(existing)
    assert existing.read_text() == "old"
    assert _names(tmp_path) == ["My Video_720p.mp4"]


def test_audio_check_uses_converted_extension(tmp_path):
    """bestaudio arrives as .webm but the user gets .mp3; only .mp3 counts."""
    (tmp_path / "My Song_medium.webm").write_text("unrelated")
    first = _download(tmp_path, info=AUDIO_INFO, audio_only=True, audio_format="mp3")
    assert os.path.basename(first) == "My Song_medium.mp3"

    second = _download(tmp_path, info=AUDIO_INFO, audio_only=True, audio_format="mp3")
    assert os.path.basename(second) == "My Song_medium (1).mp3"


def test_audio_vorbis_maps_to_ogg(tmp_path):
    (tmp_path / "My Song_medium.ogg").write_text("old")
    path = _download(tmp_path, info=AUDIO_INFO, audio_only=True, audio_format="vorbis")
    assert os.path.basename(path) == "My Song_medium (1).ogg"


def test_video_check_uses_merged_extension(tmp_path):
    """A merge into .mkv sets info['ext'] to mkv; an old .mp4 is not a duplicate."""
    (tmp_path / "My Video_720p.mp4").write_text("old")
    path = _download(tmp_path, info={**VIDEO_INFO, "ext": "mkv"}, video_container="mkv")
    assert os.path.basename(path) == "My Video_720p.mkv"


def test_check_uses_sanitized_name(tmp_path):
    """Characters yt-dlp replaces (windowsfilenames) and template characters
    (% and $) in the title must not break the existence check."""
    info = {**VIDEO_INFO, "title": 'A: B? 100% "$HOME" <x>'}
    first = _download(tmp_path, info=info)
    second = _download(tmp_path, info=info)
    stem, ext = os.path.splitext(first)
    assert second == f"{stem} (1){ext}"
    assert "100%" in first and "$HOME" in first
    for bad in ':?"<>':
        assert bad not in os.path.basename(first)


def test_numbered_path_is_reported(tmp_path):
    (tmp_path / "My Video_720p.mp4").write_text("old")
    _FakeDownloadYDL.fake_info = VIDEO_INFO
    wrapper = mod.YtDlpWrapper()
    assert wrapper.download("https://example.com/v", str(tmp_path), "best", download_thumbnail=False)
    assert wrapper.last_output_files == [str(tmp_path / "My Video_720p (1).mp4")]


# ---------- concurrent downloads (queue workers) ----------


def test_concurrent_identical_downloads_get_different_names(tmp_path):
    """Both downloads choose a name before either file exists on disk."""
    _FakeDownloadYDL.barrier = threading.Barrier(2)
    results: list[str] = []
    errors: list[BaseException] = []

    def worker():
        try:
            results.append(_download(tmp_path))
        except BaseException as e:  # pragma: no cover - reported below
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert not errors
    assert sorted(os.path.basename(p) for p in results) == ["My Video_720p (1).mp4", "My Video_720p.mp4"]


def test_reservation_blocks_name_until_released(tmp_path):
    template = os.path.join(str(tmp_path), "%(title)s_%(height)sp.%(ext)s")
    with mod.YoutubeDL({"outtmpl": template, "windowsfilenames": True, "quiet": True}) as ydl:
        first = mod._reserve_output_template(ydl, dict(VIDEO_INFO), template, None)
        second = mod._reserve_output_template(ydl, dict(VIDEO_INFO), template, None)
        assert first[0] == template
        assert os.path.basename(second[1]) == "My Video_720p (1).mp4"

        mod._release_outputs([mod._output_key(first[1]), mod._output_key(second[1])])
        again = mod._reserve_output_template(ydl, dict(VIDEO_INFO), template, None)
        assert again[0] == template
        mod._release_outputs([mod._output_key(again[1])])


def test_reservation_released_after_failed_download(tmp_path, monkeypatch):
    def boom(self, url, download=True, **kwargs):
        self.pre_process(dict(VIDEO_INFO), "video")
        raise RuntimeError("network down")

    monkeypatch.setattr(_FakeDownloadYDL, "extract_info", boom)
    wrapper = mod.YtDlpWrapper()
    assert wrapper.download("https://example.com/v", str(tmp_path), "best", download_thumbnail=False) is False
    assert wrapper.last_output_files == []
    # The autouse fixture asserts that no reservation is left behind.
