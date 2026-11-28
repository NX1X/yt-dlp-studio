"""Tests for the gaps found on Instagram, X, Facebook and TikTok.

A research run of the app's own download path on public posts of these sites
found these gaps. Each test below pins one fix. The info dicts are small
recordings of what yt-dlp returned. No network is used. The format and file
name tests run the vendored engine's own selector and name builder, with
made-up formats.
"""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock

import pytest

from src.backend import side_files
from src.backend import yt_dlp_wrapper as mod
from src.backend.download_options import DownloadOptions, build_ydl_opts
from src.backend.download_preferences import explain_download_error
from src.backend.side_files import iter_downloads, write_side_files
from src.utils.constants import QUALITY_OPTIONS
from src.utils.translations import get_translation_manager, tr

URL = "https://www.instagram.com/p/BQ0eAlwhDrw/"


@pytest.fixture(autouse=True)
def _english():
    get_translation_manager().set_language("en")


def _item(folder, name, *, comments=None, comment_count=None, description="Text", with_path=True):
    """Write the files of one downloaded item and return its requested_downloads entry."""
    base = os.path.join(str(folder), name)
    with open(base + ".mp4", "w", encoding="utf-8") as f:
        f.write("video")
    data = {"id": name, "title": name, "comments": comments or [], "comment_count": comment_count}
    with open(base + ".info.json", "w", encoding="utf-8") as f:
        json.dump(data, f)
    if description is not None:
        with open(base + ".description", "w", encoding="utf-8") as f:
            f.write(description)
    entry = {"filepath": base + ".mp4"}
    if with_path:
        entry["infojson_filename"] = base + ".info.json"
    return entry


def _comment(text):
    return {"author": "Ann", "text": text, "like_count": 0, "timestamp": 0}


def _carousel(folder, **kw):
    """The result of a post with two videos: a playlist whose entries hold the downloads."""
    first = _item(folder, "Video (1)", **kw)
    second = _item(folder, "Video (2)", **kw)
    return {
        "_type": "playlist",
        "title": "Post",
        "entries": [{"id": "a", "requested_downloads": [first]}, {"id": "b", "requested_downloads": [second]}],
    }


# ---------- 1. several items in one post ----------


def test_downloads_are_found_in_entries(tmp_path):
    info = _carousel(tmp_path)
    assert [d["filepath"] for d in iter_downloads(info)] == [
        str(tmp_path / "Video (1).mp4"),
        str(tmp_path / "Video (2).mp4"),
    ]


def test_nested_playlists_are_walked():
    inner = {"entries": [{"requested_downloads": [{"filepath": "x"}]}]}
    outer = {"entries": [inner, {"requested_downloads": [{"filepath": "y"}]}]}
    assert [d["filepath"] for d in iter_downloads(outer)] == ["x", "y"]


def test_output_files_of_a_playlist_result(tmp_path):
    info = _carousel(tmp_path)
    info["entries"].append({"requested_downloads": [{"filepath": str(tmp_path / "gone.mp4")}]})
    assert mod._existing_output_files(info) == [str(tmp_path / "Video (1).mp4"), str(tmp_path / "Video (2).mp4")]


def test_output_files_have_no_repeats(tmp_path):
    entry = _item(tmp_path, "One")
    info = {"requested_downloads": [entry], "entries": [{"requested_downloads": [dict(entry)]}]}
    assert mod._existing_output_files(info) == [str(tmp_path / "One.mp4")]


def test_playlist_result_counts_as_success(tmp_path):
    info = _carousel(tmp_path)
    assert mod._require_output_files(info, mod._YtDlpLogBridge()) == [
        str(tmp_path / "Video (1).mp4"),
        str(tmp_path / "Video (2).mp4"),
    ]


def test_each_item_gets_its_own_side_files(tmp_path):
    info = _carousel(tmp_path, comments=[_comment("hi")], comment_count=1)
    write_side_files(info, metadata=True, comments=True)
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "Video (1) Comments.txt",
        "Video (1).info.json",
        "Video (1).mp4",
        "Video (1)_description.txt",
        "Video (1)_metadata.txt",
        "Video (2) Comments.txt",
        "Video (2).info.json",
        "Video (2).mp4",
        "Video (2)_description.txt",
        "Video (2)_metadata.txt",
    ]


def test_side_files_ignore_other_downloads_in_the_folder(tmp_path):
    """Two queue workers share a folder. Only the paths of this result count."""
    info = _carousel(tmp_path, comments=[_comment("hi")], comment_count=1)
    other = tmp_path / "Other download.info.json"
    other.write_text(json.dumps({"title": "Other", "comments": [_comment("no")]}), encoding="utf-8")
    other_description = tmp_path / "Other download.description"
    other_description.write_text("Other text", encoding="utf-8")
    newer = os.path.getmtime(tmp_path / "Video (1).info.json") + 100
    os.utime(other, (newer, newer))

    write_side_files(info, metadata=False, comments=True)

    assert other.read_text(encoding="utf-8") == json.dumps({"title": "Other", "comments": [_comment("no")]})
    assert other_description.exists()
    assert not (tmp_path / "Other download Comments.txt").exists()
    assert (tmp_path / "Video (1) Comments.txt").exists()
    assert (tmp_path / "Video (2) Comments.txt").exists()


def test_old_info_json_in_the_folder_is_not_used(tmp_path):
    """A JSON that yt-dlp did not report for this download is never picked up."""
    (tmp_path / "Old.info.json").write_text(json.dumps({"title": "Old", "comments": [_comment("x")]}), encoding="utf-8")
    write_side_files({"requested_downloads": []}, metadata=True, comments=True)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["Old.info.json"]


def test_json_path_falls_back_to_the_video_name(tmp_path):
    entry = _item(tmp_path, "Clip", with_path=False)
    assert side_files.info_json_paths({"requested_downloads": [entry]}) == [str(tmp_path / "Clip.info.json")]


def test_json_path_prefers_the_reported_name(tmp_path):
    entry = _item(tmp_path, "Clip")
    entry["filepath"] = str(tmp_path / "Other.mp4")
    assert side_files.info_json_paths({"requested_downloads": [entry]}) == [str(tmp_path / "Clip.info.json")]


def test_whole_playlist_download_through_the_wrapper(tmp_path, monkeypatch):
    """The wrapper reports a carousel as a success and writes the files of each item."""
    from tests.test_download_characterization import _RecordingYDL

    info = _carousel(tmp_path, comments=[_comment("hi")], comment_count=1)
    _RecordingYDL.runs = []
    _RecordingYDL.extract = staticmethod(lambda ydl, url: info)
    monkeypatch.setattr(mod, "YoutubeDL", _RecordingYDL)
    monkeypatch.setattr(mod.YtDlpWrapper, "_get_ffmpeg_location", lambda self: None)
    monkeypatch.setattr(mod.YtDlpWrapper, "_get_deno_location", lambda self: None)
    wrapper = mod.YtDlpWrapper()
    ok = wrapper.download(DownloadOptions(URL, str(tmp_path), "worst", download_comments=True))
    assert ok is True
    assert wrapper.last_error is None
    assert [os.path.basename(p) for p in wrapper.last_output_files] == ["Video (1).mp4", "Video (2).mp4"]
    assert (tmp_path / "Video (1) Comments.txt").exists()
    assert (tmp_path / "Video (2) Comments.txt").exists()
    assert not (tmp_path / "Video (1).info.json").exists()


def test_post_json_is_removed_without_metadata(tmp_path):
    info = _carousel(tmp_path, comments=[_comment("hi")], comment_count=1)
    post = tmp_path / "Post.info.json"
    post.write_text("{}", encoding="utf-8")
    write_side_files(info, metadata=False, comments=True, post_json=str(post))
    assert not post.exists()


def test_post_json_is_kept_with_metadata_and_its_description_renamed(tmp_path):
    info = _carousel(tmp_path)
    post = tmp_path / "Post.info.json"
    post.write_text("{}", encoding="utf-8")
    (tmp_path / "Post.description").write_text("About the post", encoding="utf-8")
    write_side_files(info, metadata=True, comments=False, post_json=str(post))
    assert post.exists()
    assert (tmp_path / "Post_description.txt").read_text(encoding="utf-8") == "About the post"
    assert not (tmp_path / "Post.description").exists()


# ---------- 2. the template goes back after each item ----------


def _fake_downloader(template):
    ydl = MagicMock()
    ydl.params = {"outtmpl": {"default": template}}
    return ydl


def test_template_is_plain_again_after_each_item():
    plain = "/out/%(title)s%(height&_{}p|)s.%(ext)s"
    ydl = _fake_downloader(plain)
    numbered = mod._DuplicateNumberingPP(ydl, plain, None, [])
    restore = mod._RestoreTemplatePP(ydl, plain, None, [])
    ydl.params["outtmpl"]["default"] = "/out/%(title)s%(height&_{}p|)s (2).%(ext)s"
    info = {"id": "x"}
    assert restore.run(info) == ([], info)
    assert ydl.params["outtmpl"]["default"] == plain
    assert isinstance(numbered, mod._DuplicateNumberingPP)


def test_restore_runs_after_the_video(tmp_path, monkeypatch):
    from tests.test_download_characterization import _RecordingYDL

    _RecordingYDL.runs = []
    _RecordingYDL.extract = staticmethod(lambda ydl, url: {"requested_downloads": [_item(tmp_path, "A")]})
    monkeypatch.setattr(mod, "YoutubeDL", _RecordingYDL)
    monkeypatch.setattr(mod.YtDlpWrapper, "_get_ffmpeg_location", lambda self: None)
    monkeypatch.setattr(mod.YtDlpWrapper, "_get_deno_location", lambda self: None)
    mod.YtDlpWrapper().download(DownloadOptions(URL, str(tmp_path), "worst"))
    added = _RecordingYDL.runs[0]["ydl"].added
    assert [(type(pp).__name__, when) for pp, when in added] == [
        ("_ImageItemPP", "video"),  # Instagram: a photo item becomes an image download
        ("_DuplicateNumberingPP", "video"),
        ("_RestoreTemplatePP", "after_video"),
    ]


# ---------- 3, 4 and 8. comments and description files ----------


def _json_with(tmp_path, data, description=None):
    path = tmp_path / "Clip.info.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    if description is not None:
        (tmp_path / "Clip.description").write_text(description, encoding="utf-8")
    return {"requested_downloads": [{"filepath": str(tmp_path / "Clip.mp4"), "infojson_filename": str(path)}]}


def test_no_comments_removes_the_temporary_json(tmp_path):
    info = _json_with(tmp_path, {"title": "Clip", "comments": []})
    write_side_files(info, metadata=False, comments=True)
    assert list(tmp_path.iterdir()) == []


def test_no_comments_with_metadata_keeps_the_json(tmp_path):
    info = _json_with(tmp_path, {"title": "Clip"})
    write_side_files(info, metadata=True, comments=True)
    assert (tmp_path / "Clip.info.json").exists()
    assert not (tmp_path / "Clip Comments.txt").exists()


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({"title": "Clip", "comments": []}, "the post has none"),
        ({"title": "Clip"}, "does not provide comments"),
        ({"title": "Clip", "comment_count": 825}, "does not provide comments"),
        ({"title": "Clip", "comments": [], "comment_count": None}, "the post has none"),
        ({"title": "Clip", "comments": [], "comment_count": 0}, "the post has none"),
        ({"title": "Clip", "comments": [], "comment_count": 653}, "none of the 653 comments"),
    ],
)
def test_no_comments_message(tmp_path, caplog, data, expected):
    info = _json_with(tmp_path, data)
    with caplog.at_level("WARNING"):
        write_side_files(info, metadata=False, comments=True)
    text = "\n".join(caplog.messages)
    assert expected in text
    # "comments may be disabled" was wrong for a site that gives no comments at all.
    assert "may be disabled" not in text


def test_partial_comments_say_so(tmp_path):
    comments = [_comment(f"c{i}") for i in range(12)]
    info = _json_with(tmp_path, {"title": "Clip", "comments": comments, "comment_count": 653})
    write_side_files(info, metadata=False, comments=True)
    text = (tmp_path / "Clip Comments.txt").read_text(encoding="utf-8")
    assert "Total Comments: 12 of 653\n" in text
    assert "Note: this file holds only the comments the site returned (12 of 653).\n" in text
    assert "[Comment #12]" in text


def test_all_comments_have_no_note(tmp_path):
    comments = [_comment("a"), _comment("b")]
    info = _json_with(tmp_path, {"title": "Clip", "comments": comments, "comment_count": 2})
    write_side_files(info, metadata=False, comments=True)
    text = (tmp_path / "Clip Comments.txt").read_text(encoding="utf-8")
    assert "Total Comments: 2\n" in text
    assert "Note:" not in text


def test_comments_without_a_count_have_no_note(tmp_path):
    info = _json_with(tmp_path, {"title": "Clip", "comments": [_comment("a")]})
    write_side_files(info, metadata=False, comments=True)
    text = (tmp_path / "Clip Comments.txt").read_text(encoding="utf-8")
    assert "Total Comments: 1\n" in text
    assert "Note:" not in text


def test_comment_with_no_like_count_is_written(tmp_path):
    comment = {"author": "Ann", "text": "hi", "like_count": None}
    info = _json_with(tmp_path, {"title": "Clip", "comments": [comment], "comment_count": 1})
    write_side_files(info, metadata=False, comments=True)
    assert "Likes" not in (tmp_path / "Clip Comments.txt").read_text(encoding="utf-8")


@pytest.mark.parametrize("description", ["", "  \n"])
def test_empty_description_is_not_written(tmp_path, description):
    info = _json_with(tmp_path, {"title": "Clip"}, description=description)
    write_side_files(info, metadata=True, comments=False)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["Clip.info.json", "Clip_metadata.txt"]


def test_description_with_text_is_kept(tmp_path):
    info = _json_with(tmp_path, {"title": "Clip"}, description="Hello")
    write_side_files(info, metadata=True, comments=False)
    assert (tmp_path / "Clip_description.txt").read_text(encoding="utf-8") == "Hello"


# ---------- 5. annotations ----------


@pytest.mark.parametrize("flags", [{"download_metadata": True}, {"download_comments": True}])
def test_writeannotations_is_not_set(flags):
    opts = build_ydl_opts(DownloadOptions(URL, "/out", "worst", **flags))
    assert "writeannotations" not in opts


def test_annotations_are_not_in_the_texts():
    for language in ("en", "he"):
        get_translation_manager().set_language(language)
        assert "annotations" not in tr("tooltip_metadata").lower()
    get_translation_manager().set_language("he")
    assert "הערות" not in tr("tooltip_metadata")
    get_translation_manager().set_language("en")


# ---------- 6. height-capped presets ----------

_TAIL = "[vcodec!=?none]/worstvideo+bestaudio/worst"
_FORMAT_STRINGS = {
    "Best Quality": "bestvideo+bestaudio/best",
    "8K (4320p)": "bestvideo[height<=?4320]+bestaudio/best[height<=?4320]" + _TAIL,
    "4K (2160p)": "bestvideo[height<=?2160]+bestaudio/best[height<=?2160]" + _TAIL,
    "2K (1440p)": "bestvideo[height<=?1440]+bestaudio/best[height<=?1440]" + _TAIL,
    "1080p (Full HD)": "bestvideo[height<=?1080]+bestaudio/best[height<=?1080]" + _TAIL,
    "720p (HD)": "bestvideo[height<=?720]+bestaudio/best[height<=?720]" + _TAIL,
    "480p (SD)": "bestvideo[height<=?480]+bestaudio/best[height<=?480]" + _TAIL,
    "360p": "bestvideo[height<=?360]+bestaudio/best[height<=?360]" + _TAIL,
}


@pytest.mark.parametrize("name", list(_FORMAT_STRINGS))
def test_preset_format_strings(name):
    assert QUALITY_OPTIONS[name] == _FORMAT_STRINGS[name]


def _selector(spec):
    return mod.YoutubeDL({"quiet": True, "logger": mod._YtDlpLogBridge()}).build_format_selector(spec)


def _pick(spec, formats):
    """The format ids yt-dlp picks for ``spec`` from ``formats``.

    yt-dlp hands the selector the formats from worst to best, so sort them
    the same way (a stable sort keeps the order of equal ones).
    """
    formats = sorted(formats, key=lambda f: f.get("height") or 0)
    incomplete = all(f["vcodec"] == "none" or f["acodec"] == "none" for f in formats)
    try:
        return [f["format_id"] for f in _selector(spec)({"formats": formats, "incomplete_formats": incomplete})]
    except Exception as error:
        return f"ERROR {error}"


def _video(format_id, height):
    return {
        "format_id": format_id,
        "height": height,
        "vcodec": "avc1",
        "acodec": "none",
        "ext": "mp4",
        "tbr": height or 1,
        "url": "u",
        "width": height and height * 16 // 9,
    }


def _audio(format_id):
    return {"format_id": format_id, "vcodec": "none", "acodec": "aac", "ext": "m4a", "tbr": 100, "url": "u"}


def _progressive(format_id, height):
    return {
        "format_id": format_id,
        "height": height,
        "vcodec": "avc1",
        "acodec": "aac",
        "ext": "mp4",
        "tbr": height or 1,
        "url": "u",
        "width": height and height * 16 // 9,
    }


# Made-up format lists in the shapes the research run found.
YOUTUBE = [_video("v144", 144), _video("v360", 360), _video("v720", 720), _video("v1080", 1080), _audio("a")]
FACEBOOK_SD_HD = [_progressive("sd", None), _progressive("hd", None)]
FACEBOOK_DASH = [_video("dash", None), _audio("a")]
INSTAGRAM_SMALLEST_640 = [_video("v640", 640), _video("v720", 720), _audio("a")]
INSTAGRAM_PROGRESSIVE = [_progressive("p", None)]


@pytest.mark.parametrize(
    ("quality", "expected"),
    [("360p", ["v360", "a"]), ("720p (HD)", ["v720", "a"]), ("1080p (Full HD)", ["v1080", "a"])],
)
def test_known_heights_keep_todays_choice(quality, expected):
    assert _pick(QUALITY_OPTIONS[quality], YOUTUBE) == ["+".join(expected)]


@pytest.mark.parametrize("quality", [q for q in _FORMAT_STRINGS if q != "Best Quality"])
def test_formats_without_a_height_do_not_fail(quality):
    spec = QUALITY_OPTIONS[quality]
    assert _pick(spec, FACEBOOK_SD_HD) == ["hd"]
    assert _pick(spec, FACEBOOK_DASH) == ["dash+a"]
    assert _pick(spec, INSTAGRAM_PROGRESSIVE) == ["p"]


def test_all_formats_taller_than_the_cap_give_the_smallest():
    # Instagram aye83DjauH: the smallest video is 640 high, the preset says 360.
    assert _pick(QUALITY_OPTIONS["360p"], INSTAGRAM_SMALLEST_640) == ["v640+a"]
    assert _pick(QUALITY_OPTIONS["480p (SD)"], INSTAGRAM_SMALLEST_640) == ["v640+a"]


def test_old_strings_failed_on_these_formats():
    old = "bestvideo[height<=360]+bestaudio/best[height<=360]"
    assert _pick(old, FACEBOOK_SD_HD) == []
    assert _pick(old, INSTAGRAM_SMALLEST_640) == []


def test_a_cap_does_not_pick_audio_only_when_nothing_else_fits():
    only_audio_and_tall_video = [_video("v640", 640), _audio("a")]
    assert _pick(QUALITY_OPTIONS["360p"], only_audio_and_tall_video) == ["v640+a"]


def test_known_heights_pick_the_best_below_the_cap_with_mixed_formats():
    # A progressive file without a height next to video-only files with heights.
    mixed = [_progressive("sd", None), _video("v720", 720), _video("v360", 360), _audio("a")]
    assert _pick(QUALITY_OPTIONS["720p (HD)"], mixed) == ["v720+a"]


# ---------- 7. file names without "_NAp" ----------


def _name(template, info):
    ydl = mod.YoutubeDL({"quiet": True, "outtmpl": template, "windowsfilenames": True})
    return ydl.prepare_filename(info)


def test_name_has_the_height_when_it_is_known():
    template = DownloadOptions(URL, "", "worst").filename_template
    assert _name(template, {"id": "1", "title": "Clip", "ext": "mp4", "height": 720}) == "Clip_720p.mp4"


@pytest.mark.parametrize("info_extra", [{}, {"height": None}])
def test_name_has_no_na_without_a_height(info_extra):
    template = DownloadOptions(URL, "", "worst").filename_template
    name = _name(template, {"id": "1", "title": "Clip", "ext": "mp4", **info_extra})
    assert name == "Clip.mp4"
    assert "NA" not in name


def test_numbered_name_without_a_height():
    template = mod._numbered_template(DownloadOptions(URL, "", "worst").filename_template, 2)
    assert _name(template, {"id": "1", "title": "Clip", "ext": "mp4"}) == "Clip (2).mp4"
    assert _name(template, {"id": "1", "title": "Clip", "ext": "mp4", "height": 360}) == "Clip_360p (2).mp4"


# ---------- 9. photo posts ----------


@pytest.mark.parametrize(
    ("message", "url"),
    [
        (
            "ERROR: [Instagram] BqvsDleB3lV: No video formats found!; please report this issue on https://github.com/yt-dlp/yt-dlp/issues",
            "https://www.instagram.com/p/BqvsDleB3lV/",
        ),
        ("ERROR: [Instagram] BoHk1haB5tM: There is no video in this post", "https://www.instagram.com/p/BoHk1haB5tM/"),
        (
            "ERROR: [twitter] 894001459754180609: No video could be found in this tweet",
            "https://twitter.com/perrypumas/status/894001459754180609",
        ),
        (
            "ERROR: [twitter] 1: No video could be found in this tweet",
            "https://x.com/carrotsprout_/status/1577924293023133696",
        ),
    ],
)
def test_instagram_and_x_posts_without_media_get_one_clear_message(message, url):
    """Their photo posts download now, so a post that still gives nothing has no media at all."""
    text = explain_download_error([message], url=url)
    assert text == tr("error_no_media_in_post")
    assert "report" not in text.lower()
    assert "github" not in text.lower()


@pytest.mark.parametrize(
    ("message", "url"),
    [
        (
            "ERROR: Unsupported URL: https://www.facebook.com/photo/?fbid=10160743390456729",
            "https://www.facebook.com/photo/?fbid=10160743390456729",
        ),
        (
            "ERROR: Unsupported URL: https://www.facebook.com/photo.php?fbid=1&set=t.2&type=3",
            "https://www.facebook.com/photo.php?fbid=1&set=t.2&type=3",
        ),
        (
            "ERROR: Unsupported URL: https://www.facebook.com/joho.press.jp/posts/pfbid02mf",
            "https://www.facebook.com/joho.press.jp/posts/pfbid02mf",
        ),
        (
            "ERROR: Unsupported URL: https://www.facebook.com/permalink.php?story_fbid=pfbid03&id=6",
            "https://www.facebook.com/permalink.php?story_fbid=pfbid03&id=6",
        ),
    ],
)
def test_facebook_photo_posts_get_one_clear_message(message, url):
    text = explain_download_error([message], url=url)
    assert text == tr("error_no_video_in_post")
    assert "report" not in text.lower()
    assert "github" not in text.lower()


def test_photo_post_message_without_a_url():
    assert explain_download_error(["There is no video in this post"]) == tr("error_no_video_in_post")


def test_photo_post_message_is_in_both_languages():
    english = tr("error_no_video_in_post")
    get_translation_manager().set_language("he")
    hebrew = tr("error_no_video_in_post")
    get_translation_manager().set_language("en")
    assert english != hebrew
    assert "Facebook" in english
    assert "photo" in english.lower()
    assert hebrew != "error_no_video_in_post"


@pytest.mark.parametrize(
    ("message", "url"),
    [
        ("ERROR: Unsupported URL: https://example.com/page", "https://example.com/page"),
        ("ERROR: Unsupported URL: https://www.facebook.com/somepage", "https://www.facebook.com/somepage"),
        ("ERROR: Unsupported URL: https://www.youtube.com/photo", "https://www.youtube.com/photo"),
        ("No video formats found!", "https://example.com/v"),
        ("ERROR: Requested format is not available", "https://www.instagram.com/p/x/"),
    ],
)
def test_other_errors_keep_their_text(message, url):
    assert explain_download_error([message], url=url) is None


def test_failed_photo_download_shows_the_clear_message(tmp_path, monkeypatch):
    from tests.test_download_characterization import _RecordingYDL

    def extract(ydl, url):
        raise RuntimeError("ERROR: [Instagram] x: There is no video in this post")

    _RecordingYDL.runs = []
    _RecordingYDL.extract = staticmethod(extract)
    monkeypatch.setattr(mod, "YoutubeDL", _RecordingYDL)
    monkeypatch.setattr(mod.YtDlpWrapper, "_get_ffmpeg_location", lambda self: None)
    monkeypatch.setattr(mod.YtDlpWrapper, "_get_deno_location", lambda self: None)
    wrapper = mod.YtDlpWrapper()
    assert wrapper.download(DownloadOptions(URL, str(tmp_path), "worst")) is False
    # Instagram photo posts download; a post that gives no media says so.
    assert wrapper.user_error == tr("error_no_media_in_post")
    assert wrapper.last_error == tr("error_no_media_in_post")
