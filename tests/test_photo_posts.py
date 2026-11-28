"""Tests for photo posts (image-only posts and carousels) from Instagram and X.

Nothing here uses the internet. The extractors are replaced by recorded
results: an Instagram-shaped result written by hand from the engine's
extractor, and two X status JSON files recorded from real public posts
(``tests/fixtures/x_status_*.json``). A small local HTTP server serves the
"images" and "videos", so the real yt-dlp downloader, post-processing and file
naming run end to end.
"""

from __future__ import annotations

import copy
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from src.backend import yt_dlp_wrapper as mod
from src.backend.download_options import IMAGE_FILENAME_TEMPLATE, DownloadOptions, build_ydl_opts
from src.backend.download_preferences import explain_download_error
from src.backend.side_files import write_metadata_files
from src.backend.twitter_photos import make_twitter_photo_ie
from src.models.video_info import VideoInfo
from src.utils.photo_posts import (
    IMAGE_FORMAT_ID,
    best_image,
    image_extension,
    image_item_update,
    is_image_item,
    is_photo_post,
    looks_like_image_item,
    supports_photo_posts,
)
from src.utils.translations import tr

FIXTURES = Path(__file__).parent / "fixtures"
IG_URL = "https://www.instagram.com/p/FAKEPOST1/"
X_PHOTOS_URL = "https://twitter.com/perrypumas/status/894001459754180609"
X_MIXED_URL = "https://x.com/carrotsprout_/status/1577924293023133696"


# ---------- no network ----------


@pytest.fixture(autouse=True)
def _no_internet(monkeypatch):
    """Fail loudly on any connection that is not to this computer."""
    import socket

    real_connect = socket.socket.connect

    def guarded(self, address, *args, **kwargs):
        host = address[0] if isinstance(address, tuple) else address
        if self.family in (socket.AF_INET, socket.AF_INET6) and host not in ("127.0.0.1", "::1", "localhost"):
            raise AssertionError(f"test tried to reach the network: {address!r}")
        return real_connect(self, address, *args, **kwargs)

    def no_lookup(host, *args, **kwargs):
        if host not in ("127.0.0.1", "::1", "localhost"):
            raise AssertionError(f"test tried a DNS lookup: {host!r}")
        return real_getaddrinfo(host, *args, **kwargs)

    real_getaddrinfo = socket.getaddrinfo
    monkeypatch.setattr(socket.socket, "connect", guarded)
    monkeypatch.setattr(socket, "getaddrinfo", no_lookup)


# ---------- a local server for the files ----------


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - http.server API
        self.server.hits.append(self.path)
        body = b"\xff\xd8\xff\xe0FAKE-FILE " + self.path.encode()
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg" if ".jpg" in self.path else "video/mp4")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture
def server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    httpd.hits = []
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    httpd.base = f"http://127.0.0.1:{httpd.server_address[1]}"
    yield httpd
    httpd.shutdown()
    httpd.server_close()


# ---------- recorded results ----------


def _thumbs(base, name):
    """Instagram lists the sizes smallest first (the engine reverses the API list)."""
    return [
        {"url": f"{base}/{name}_150.jpg", "width": 150, "height": 188},
        {"url": f"{base}/{name}_640.jpg", "width": 640, "height": 800},
        {"url": f"{base}/{name}_1080.jpg", "width": 1080, "height": 1350},
    ]


def _ig_item(base, item_id, *, video=False):
    item = {
        "id": item_id,
        "title": "Post by someone",
        "description": "A caption",
        "channel": "someone",
        "uploader": "Some One",
        "http_headers": {"Referer": "https://www.instagram.com/"},
        "formats": [],
        "thumbnails": _thumbs(base, item_id),
    }
    if video:
        item["formats"] = [
            {"url": f"{base}/{item_id}.mp4", "format_id": "1", "ext": "mp4", "vcodec": "avc1", "acodec": "mp4a"}
        ]
        item["duration"] = 3.0
    return item


def _ig_single_photo(base):
    return _ig_item(base, "FAKEPOST1")


def _ig_carousel(base, kinds):
    entries = [_ig_item(base, f"ITEM{i}", video=kind == "video") for i, kind in enumerate(kinds, 1)]
    return {"_type": "playlist", "id": "FAKEPOST1", "title": "Post by someone", "entries": entries}


class _Instagram:
    """Builds a YoutubeDL class whose Instagram extractor returns a recorded result."""

    @staticmethod
    def ydl_class(result):
        from yt_dlp.extractor.instagram import InstagramIE

        class StubInstagramIE(InstagramIE):
            @classmethod
            def ie_key(cls):
                return InstagramIE.ie_key()

            IE_NAME = InstagramIE.IE_NAME

            def _real_initialize(self):
                pass  # the real one opens an Instagram session over the network

            def _real_extract(self, url):
                return copy.deepcopy(result)

        class Stub(mod.YoutubeDL):
            def __init__(self, params=None, auto_init=True):
                super().__init__(params, auto_init)
                self.add_info_extractor(StubInstagramIE())

        return Stub


def _x_status(status_file, base):
    """A recorded X status, with the media URLs moved to the local server."""
    status = json.loads((FIXTURES / status_file).read_text(encoding="utf-8"))
    for media in status["extended_entities"]["media"]:
        if media["type"] == "photo":
            media["media_url_https"] = f"{base}/x/{Path(media['media_url_https']).name}"
        else:
            media["video_info"]["variants"] = [
                {"content_type": "video/mp4", "bitrate": 832000, "url": f"{base}/x/video.mp4"}
            ]
            media["media_url_https"] = f"{base}/x/thumb.jpg"
    return status


@pytest.fixture
def downloader(monkeypatch):
    monkeypatch.setattr(mod.YtDlpWrapper, "_get_ffmpeg_location", lambda self: None)
    monkeypatch.setattr(mod.YtDlpWrapper, "_get_deno_location", lambda self: None)

    def run(url, out_dir, ydl_class, **kwargs):
        monkeypatch.setattr(mod, "YoutubeDL", ydl_class)
        wrapper = mod.YtDlpWrapper()
        options = DownloadOptions(url, str(out_dir), kwargs.pop("format_string", "best"), **kwargs)
        ok = wrapper.download(options)
        return ok, wrapper

    yield run
    assert not mod._reserved_outputs


def _files(folder):
    return sorted(p.name for p in Path(folder).iterdir())


# ---------- pure helpers ----------


def test_only_instagram_and_x_support_photo_posts():
    assert supports_photo_posts("https://www.instagram.com/p/abc/")
    assert supports_photo_posts("https://instagr.am/p/abc/")
    assert supports_photo_posts("https://x.com/a/status/1")
    assert supports_photo_posts("https://mobile.twitter.com/a/status/1")
    assert not supports_photo_posts("https://www.facebook.com/photo/?fbid=1")
    assert not supports_photo_posts("https://www.youtube.com/watch?v=a")
    assert not supports_photo_posts("https://notx.com/a")
    assert not supports_photo_posts("not a url")


def test_best_image_takes_the_largest_whatever_the_order():
    thumbs = _thumbs("http://h", "a")
    assert best_image({"thumbnails": thumbs})["width"] == 1080
    assert best_image({"thumbnails": list(reversed(thumbs))})["width"] == 1080
    assert best_image({"thumbnails": [{"url": "http://h/x.jpg"}]})["url"] == "http://h/x.jpg"
    assert best_image({"thumbnails": [{"width": 5}]}) is None
    assert best_image({}) is None
    assert best_image(None) is None


# The sizes of a real Instagram carousel item (2026-11): no width or height in
# the result, the size is only in the "stp" part of the URL, and the unscaled
# original has none. yt-dlp lists them in URL order, not in size order.
_IG_STP = [
    "dst-jpg_e35_s150x150_tt6",
    "dst-jpg_e35_s240x240_tt6",
    "dst-jpg_e35_s320x320_tt6",
    "dst-jpg_e35_s480x480_tt6",
    "dst-jpg_e35_s640x640_sh2.08_tt6",
    "dst-jpg_e35_s720x720_tt6",
    "dst-jpg_e35_s750x750_sh2.08_tt6",
    "dst-jpg_e35_tt6",
]


def _ig_sizeless_thumbnails(order):
    return [{"url": f"https://cdn.example/v/t51/x_n.jpg?stp={stp}&_nc_cat=109&oh=1"} for stp in order]


@pytest.mark.parametrize("order", [_IG_STP, list(reversed(_IG_STP)), _IG_STP[3:] + _IG_STP[:3]])
def test_best_image_reads_the_size_from_the_url_when_there_is_no_width(order):
    best = best_image({"thumbnails": _ig_sizeless_thumbnails(order)})
    assert "stp=dst-jpg_e35_tt6&" in best["url"]
    sized = [t for t in _ig_sizeless_thumbnails(order) if "stp=dst-jpg_e35_tt6&" not in t["url"]]
    assert "s750x750" in best_image({"thumbnails": sized})["url"]


def test_best_image_reads_a_size_in_the_url_path():
    thumbs = [
        {"url": "https://cdn.example/t51/s320x320/a.jpg"},
        {"url": "https://cdn.example/t51/p1080x1350/a.jpg"},
        {"url": "https://cdn.example/t51/s150x150/a.jpg"},
    ]
    assert "p1080x1350" in best_image({"thumbnails": thumbs})["url"]


def test_a_photo_called_video_by_is_named_photo_by():
    info = {"id": "a", "title": "Video by someone", "thumbnails": _thumbs("http://h", "a")}
    assert image_item_update(info)["title"] == "Photo by someone"
    info["title"] = "Holiday"
    assert "title" not in image_item_update(info)


def test_looks_like_image_item():
    assert looks_like_image_item({"formats": [], "thumbnails": _thumbs("http://h", "a")})
    assert not looks_like_image_item({"formats": [{"url": "u"}], "thumbnails": _thumbs("http://h", "a")})
    assert not looks_like_image_item({"url": "http://h/v.mp4", "thumbnails": _thumbs("http://h", "a")})
    assert not looks_like_image_item({"formats": []})
    assert not looks_like_image_item({"entries": [{}], "thumbnails": _thumbs("http://h", "a")})


def test_image_item_update_marks_the_item_and_keeps_headers():
    info = _ig_item("http://h", "a")
    update = image_item_update(info)
    assert update["url"] == "http://h/a_1080.jpg"
    assert update["ext"] == "jpg"
    assert update["format_id"] == IMAGE_FORMAT_ID
    assert (update["width"], update["height"]) == (1080, 1350)
    assert update["http_headers"] == {"Referer": "https://www.instagram.com/"}
    assert update["thumbnails"] == []
    info.update(update)
    assert is_image_item(info)
    assert image_item_update(info) is None  # already turned


@pytest.mark.parametrize(
    ("url", "ext"),
    [
        ("https://x/a.jpg?name=orig", "jpg"),
        ("https://x/a.PNG", "png"),
        ("https://x/a.webp?x=1", "webp"),
        ("https://x/a.bin", "jpg"),
        ("https://x/a", "jpg"),
        ("https://x.y/dir.v2/a", "jpg"),
    ],
)
def test_image_extension(url, ext):
    assert image_extension(url) == ext


def test_is_photo_post():
    photo = _ig_item("http://h", "a")
    video = _ig_item("http://h", "b", video=True)
    assert is_photo_post(photo)
    assert is_photo_post({"entries": [photo, photo]})
    assert not is_photo_post({"entries": [photo, video]})
    assert not is_photo_post(video)
    assert not is_photo_post(None)


def test_video_info_marks_a_photo_post_and_survives_missing_numbers():
    info = VideoInfo.from_yt_dlp_dict({**_ig_item("http://h", "a"), "duration": None, "view_count": None})
    assert info.is_photo is True
    assert info.duration == 0
    assert info.view_count == 0
    video = VideoInfo.from_yt_dlp_dict({**_ig_item("http://h", "a", video=True)})
    assert video.is_photo is False


# ---------- options ----------


def test_photo_sites_ignore_the_no_formats_error_and_others_do_not():
    for url in (IG_URL, X_PHOTOS_URL):
        assert build_ydl_opts(DownloadOptions(url, "/o", "best"))["ignore_no_formats_error"] is True
    for url in ("https://www.youtube.com/watch?v=a", "https://www.facebook.com/x/videos/1/"):
        assert "ignore_no_formats_error" not in build_ydl_opts(DownloadOptions(url, "/o", "best"))


def test_image_template_has_no_height_and_follows_presets():
    default = DownloadOptions(IG_URL, "/o", "best")
    assert default.image_filename_template == IMAGE_FILENAME_TEMPLATE
    assert "height" not in default.image_filename_template
    audio = DownloadOptions(IG_URL, "/o", "best", audio_only=True)
    assert audio.image_filename_template == IMAGE_FILENAME_TEMPLATE
    assert audio.filename_template != IMAGE_FILENAME_TEMPLATE
    dated = DownloadOptions(IG_URL, "/o", "best", filename_preset="date_title")
    assert dated.image_filename_template == dated.filename_template
    custom = DownloadOptions(IG_URL, "/o", "best", filename_preset="custom", custom_filename_template="%(id)s.%(ext)s")
    assert custom.image_filename_template == "%(id)s.%(ext)s"
    empty_custom = DownloadOptions(IG_URL, "/o", "best", filename_preset="custom")
    assert empty_custom.image_filename_template == IMAGE_FILENAME_TEMPLATE
    assert default.image_output_template == "/o/" + IMAGE_FILENAME_TEMPLATE


# ---------- Instagram, end to end ----------


def test_instagram_photo_post_downloads_the_largest_image(tmp_path, server, downloader):
    ydl_class = _Instagram.ydl_class(_ig_single_photo(server.base))
    ok, wrapper = downloader(IG_URL, tmp_path, ydl_class)
    assert ok is True, wrapper.last_error
    assert _files(tmp_path) == ["Post by someone [FAKEPOST1].jpg"]
    assert wrapper.last_output_files == [str(tmp_path / "Post by someone [FAKEPOST1].jpg")]
    # Only the largest size was requested, and no second thumbnail file.
    assert server.hits == ["/FAKEPOST1_1080.jpg"]
    assert b"FAKEPOST1_1080.jpg" in (tmp_path / "Post by someone [FAKEPOST1].jpg").read_bytes()


def test_instagram_photo_carousel_downloads_every_photo(tmp_path, server, downloader):
    ydl_class = _Instagram.ydl_class(_ig_carousel(server.base, ["photo", "photo", "photo"]))
    ok, wrapper = downloader(IG_URL, tmp_path, ydl_class)
    assert ok is True, wrapper.last_error
    assert _files(tmp_path) == [f"Post by someone [ITEM{i}].jpg" for i in (1, 2, 3)]
    assert len(wrapper.last_output_files) == 3


def test_instagram_mixed_carousel_keeps_videos_as_videos(tmp_path, server, downloader):
    ydl_class = _Instagram.ydl_class(_ig_carousel(server.base, ["video", "photo", "video", "photo"]))
    ok, wrapper = downloader(IG_URL, tmp_path, ydl_class, download_thumbnail=False)
    assert ok is True, wrapper.last_error
    # Videos use the video template, photos the photo one, in either order.
    assert _files(tmp_path) == sorted(
        [
            "Post by someone [ITEM2].jpg",
            "Post by someone [ITEM4].jpg",
            "Post by someone.mp4",
            "Post by someone (1).mp4",
        ]
    )
    assert len(wrapper.last_output_files) == 4


def test_photo_download_does_not_overwrite_and_numbers_the_copy(tmp_path, server, downloader):
    ydl_class = _Instagram.ydl_class(_ig_single_photo(server.base))
    assert downloader(IG_URL, tmp_path, ydl_class)[0] is True
    ok, wrapper = downloader(IG_URL, tmp_path, ydl_class)
    assert ok is True
    assert _files(tmp_path) == ["Post by someone [FAKEPOST1] (1).jpg", "Post by someone [FAKEPOST1].jpg"]
    assert wrapper.last_output_files == [str(tmp_path / "Post by someone [FAKEPOST1] (1).jpg")]


def test_photo_download_without_numbering_skips_an_existing_file(tmp_path, server, downloader):
    ydl_class = _Instagram.ydl_class(_ig_single_photo(server.base))
    (tmp_path / "Post by someone [FAKEPOST1].jpg").write_bytes(b"mine")
    ok, _ = downloader(IG_URL, tmp_path, ydl_class, auto_number_duplicates=False)
    assert ok is True
    assert (tmp_path / "Post by someone [FAKEPOST1].jpg").read_bytes() == b"mine"
    assert _files(tmp_path) == ["Post by someone [FAKEPOST1].jpg"]


def test_photo_in_audio_mode_stays_a_photo(tmp_path, server, downloader):
    """Audio extraction and metadata embedding need ffmpeg (absent here); photos skip them."""
    ydl_class = _Instagram.ydl_class(_ig_single_photo(server.base))
    ok, wrapper = downloader(
        IG_URL, tmp_path, ydl_class, audio_only=True, download_metadata=True, download_thumbnail=True
    )
    assert ok is True, wrapper.last_error
    names = _files(tmp_path)
    assert "Post by someone [FAKEPOST1].jpg" in names
    assert not any(n.endswith((".mp3", ".m4a", ".opus")) for n in names)
    # Thumbnail on: the photo is the file, so no second image.
    assert sum(n.endswith(".jpg") for n in names) == 1


def test_subtitles_do_not_touch_a_photo(tmp_path, server, downloader):
    ydl_class = _Instagram.ydl_class(_ig_single_photo(server.base))
    ok, wrapper = downloader(IG_URL, tmp_path, ydl_class, download_subtitles=True, subtitle_languages="en")
    assert ok is True, wrapper.last_error
    assert _files(tmp_path) == ["Post by someone [FAKEPOST1].jpg"]


def test_photo_side_files_are_written_for_each_item(tmp_path, server, downloader):
    ydl_class = _Instagram.ydl_class(_ig_carousel(server.base, ["photo", "photo"]))
    ok, wrapper = downloader(IG_URL, tmp_path, ydl_class, download_metadata=True)
    assert ok is True, wrapper.last_error
    names = _files(tmp_path)
    for item in ("ITEM1", "ITEM2"):
        base = f"Post by someone [{item}]"
        assert f"{base}.jpg" in names
        assert f"{base}_metadata.txt" in names
        assert f"{base}_description.txt" in names
        assert f"{base}.info.json" in names
    text = (tmp_path / "Post by someone [ITEM1]_metadata.txt").read_text(encoding="utf-8")
    assert "IMAGE METADATA" in text
    assert "Image ID: ITEM1" in text
    assert "Resolution: 1080x1350" in text
    # Nothing that is true of a video only.
    for word in ("VIDEO QUALITY", "FPS", "Video Codec", "Audio Codec", "[DURATION]", "VIDEO METADATA"):
        assert word not in text


def test_photo_comments_file_does_not_say_video(tmp_path):
    from src.backend.side_files import write_comments_file

    data = {
        "id": "a",
        "title": "A post",
        "format_id": IMAGE_FORMAT_ID,
        "comments": [{"author": "x", "text": "hi", "timestamp": 1}],
    }
    path = tmp_path / "Post [a].info.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    write_comments_file(str(path), remove_json=False)
    text = (tmp_path / "Post [a] Comments.txt").read_text(encoding="utf-8")
    assert "POST COMMENTS" in text
    assert "Post Title: A post" in text
    assert "VIDEO" not in text


def test_video_metadata_text_is_unchanged(tmp_path):
    data = {"id": "v", "title": "A video", "width": 1280, "height": 720, "fps": 30, "duration": 65}
    path = tmp_path / "Clip.info.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    write_metadata_files(str(path))
    text = (tmp_path / "Clip_metadata.txt").read_text(encoding="utf-8")
    assert "VIDEO METADATA" in text
    assert "VIDEO QUALITY" in text
    assert "[DURATION]" in text
    assert "Video ID: v" in text


def test_video_only_post_processors_pass_a_photo_item(tmp_path, server, downloader):
    """The wrapped post-processors skip photos and still run for videos."""
    from yt_dlp.postprocessor import FFmpegMetadataPP

    seen = []

    class Recorder(mod.YoutubeDL):
        def __init__(self, params=None, auto_init=True):
            super().__init__(params, auto_init)

    ydl_class = Recorder
    options = DownloadOptions(IG_URL, str(tmp_path), "best", download_metadata=True)
    with ydl_class(build_ydl_opts(options)) as ydl:
        mod._skip_video_pps_for_images(ydl)
        pps = [pp for pp in ydl._pps["post_process"] if isinstance(pp, FFmpegMetadataPP)]
        assert len(pps) == 1
        pp = pps[0]
        photo = {"format_id": IMAGE_FORMAT_ID, "filepath": "x.jpg"}
        assert pp.run(photo) == ([], photo)
        # A video item reaches the real post-processor (which needs ffmpeg and fails here).
        try:
            pp.run({"format_id": "1", "filepath": str(tmp_path / "missing.mp4")})
        except Exception as error:
            seen.append(type(error).__name__)
    assert seen, "the video path must still reach the real post-processor"


def test_photo_without_any_image_fails_with_a_clear_message(tmp_path, server, downloader):
    bare = {**_ig_single_photo(server.base), "thumbnails": []}
    ydl_class = _Instagram.ydl_class(bare)
    ok, wrapper = downloader(IG_URL, tmp_path, ydl_class)
    assert ok is False
    assert _files(tmp_path) == []
    assert wrapper.last_error == tr("error_no_media_in_post")


def test_failed_image_download_is_a_failed_download(tmp_path, server, downloader):
    result = _ig_single_photo(server.base)
    result["thumbnails"] = [{"url": "http://127.0.0.1:9/never.jpg", "width": 10, "height": 10}]
    ok, wrapper = downloader(IG_URL, tmp_path, _Instagram.ydl_class(result))
    assert ok is False
    assert wrapper.last_error
    assert _files(tmp_path) == []


def test_video_lookup_marks_a_photo_post(server, monkeypatch):
    monkeypatch.setattr(mod, "YoutubeDL", _Instagram.ydl_class(_ig_single_photo(server.base)))
    info = mod.YtDlpWrapper().get_video_info(IG_URL)
    assert info is not None
    assert info.is_photo is True
    assert info.title == "Post by someone"


# ---------- X ----------


def _x_run(tmp_path, server, downloader, monkeypatch, status_file, url, **kwargs):
    status = _x_status(status_file, server.base)
    monkeypatch.setattr(make_twitter_photo_ie(), "_extract_status", lambda self, twid: status)
    return downloader(url, tmp_path, mod.YoutubeDL, **kwargs)


def test_x_post_with_four_photos_downloads_four_files(tmp_path, server, downloader, monkeypatch):
    ok, wrapper = _x_run(tmp_path, server, downloader, monkeypatch, "x_status_photos_only.json", X_PHOTOS_URL)
    assert ok is True, wrapper.last_error
    names = _files(tmp_path)
    assert len(names) == 4
    assert all(n.endswith(".jpg") for n in names)
    assert all("[" in n for n in names)  # the media id keeps them apart
    assert sorted(server.hits) == sorted(
        f"/x/{n}.jpg?name=orig" for n in ("DGghkJwUwAAM42D", "DGghkJwVYAA8UFT", "DGghkJ8UAAAHrSH", "DGghkJ8VYAAE87W")
    )


def test_x_post_with_photo_and_video_downloads_both(tmp_path, server, downloader, monkeypatch):
    ok, wrapper = _x_run(
        tmp_path,
        server,
        downloader,
        monkeypatch,
        "x_status_photo_and_video.json",
        X_MIXED_URL,
        download_thumbnail=False,
    )
    assert ok is True, wrapper.last_error
    names = _files(tmp_path)
    assert sum(n.endswith(".jpg") for n in names) == 1
    assert sum(n.endswith(".mp4") for n in names) == 1
    assert len(wrapper.last_output_files) == 2


def test_x_photo_index_url_downloads_that_photo_only(tmp_path, server, downloader, monkeypatch):
    ok, wrapper = _x_run(
        tmp_path, server, downloader, monkeypatch, "x_status_photos_only.json", X_PHOTOS_URL + "/photo/2"
    )
    assert ok is True, wrapper.last_error
    assert server.hits == ["/x/DGghkJwVYAA8UFT.jpg?name=orig"]
    assert len(_files(tmp_path)) == 1


def test_x_photo_metadata_and_description(tmp_path, server, downloader, monkeypatch):
    ok, wrapper = _x_run(
        tmp_path, server, downloader, monkeypatch, "x_status_photos_only.json", X_PHOTOS_URL, download_metadata=True
    )
    assert ok is True, wrapper.last_error
    names = _files(tmp_path)
    assert sum(n.endswith("]_metadata.txt") for n in names) == 4
    assert sum(n.endswith("]_description.txt") for n in names) == 4


# ---------- the X extractor on recorded statuses (fails loudly if the engine changes) ----------


def _extract_x(status_file, url, monkeypatch):
    # Only the extraction runs; the media URLs point to this computer and are never opened.
    status = _x_status(status_file, "http://127.0.0.1:9")
    monkeypatch.setattr(make_twitter_photo_ie(), "_extract_status", lambda self, twid: status)
    opts = {"skip_download": True, "ignore_no_formats_error": True, "quiet": True, "noplaylist": True}
    with mod.YoutubeDL(opts) as ydl:
        mod._register_photo_extractor(ydl, url)
        return ydl.extract_info(url, download=False)


def test_x_extractor_keeps_the_engines_key_and_replaces_it_in_place(monkeypatch):
    from yt_dlp.extractor.twitter import TwitterIE

    ie_class = make_twitter_photo_ie()
    assert ie_class.ie_key() == TwitterIE.ie_key() == "Twitter"
    assert ie_class.IE_NAME == TwitterIE.IE_NAME
    with mod.YoutubeDL({"quiet": True}) as ydl:
        order_before = list(ydl._ies)
        mod._register_photo_extractor(ydl, X_PHOTOS_URL)
        assert list(ydl._ies) == order_before
        assert isinstance(ydl.get_info_extractor("Twitter"), ie_class)
        assert ydl._ies["Twitter"].suitable(X_PHOTOS_URL)
    with mod.YoutubeDL({"quiet": True}) as ydl:
        mod._register_photo_extractor(ydl, "https://www.instagram.com/p/x/")
        assert not isinstance(ydl.get_info_extractor("Twitter"), ie_class)


def test_x_fixture_photos_only(monkeypatch):
    info = _extract_x("x_status_photos_only.json", X_PHOTOS_URL, monkeypatch)
    assert info["_type"] == "playlist"
    assert [e["id"] for e in info["entries"]] == [
        "894001431010656256",
        "894001431010697216",
        "894001431060938752",
        "894001431061028864",
    ]
    for number, entry in enumerate(info["entries"], 1):
        assert entry["title"].endswith(f" #{number}")
        assert entry["display_id"] == "894001459754180609"
        assert entry["uploader_id"] == "perrypumas"
        assert not entry["formats"]
        (thumb,) = entry["thumbnails"]
        assert thumb["url"].startswith("http://127.0.0.1:9/x/") and thumb["url"].endswith("?name=orig")
        assert looks_like_image_item(entry)
    assert info["entries"][0]["thumbnails"][0]["width"] > 0


def test_x_fixture_photo_and_video(monkeypatch):
    info = _extract_x("x_status_photo_and_video.json", X_MIXED_URL, monkeypatch)
    assert info["_type"] == "playlist"
    video, photo = info["entries"]
    assert video["formats"]
    assert not photo["formats"]
    assert looks_like_image_item(photo)
    assert video["title"].endswith("#1")
    assert photo["title"].endswith("#2")


def test_x_fixture_without_photos_is_left_to_the_engine(monkeypatch):
    status = _x_status("x_status_photo_and_video.json", "http://127.0.0.1:9")
    status["extended_entities"]["media"] = [m for m in status["extended_entities"]["media"] if m["type"] != "photo"]
    monkeypatch.setattr(make_twitter_photo_ie(), "_extract_status", lambda self, twid: status)
    with mod.YoutubeDL({"skip_download": True, "quiet": True, "noplaylist": True}) as ydl:
        mod._register_photo_extractor(ydl, X_MIXED_URL)
        info = ydl.extract_info(X_MIXED_URL, download=False)
    assert info.get("_type", "video") == "video"
    assert info["formats"]


def test_x_fixtures_still_have_the_shape_the_extractor_reads():
    """If this fails, the fixtures or the engine's status shape changed: check twitter_photos.py."""
    for name in ("x_status_photos_only.json", "x_status_photo_and_video.json"):
        status = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
        media = status["extended_entities"]["media"]
        assert media
        for item in media:
            assert item["type"] in {"photo", "video", "animated_gif"}
            assert item["id_str"]
            assert item["media_url_https"].startswith("https://")
            if item["type"] == "photo":
                assert item["original_info"]["width"] and item["original_info"]["height"]
        assert status["user"]["screen_name"]
        assert status["full_text"]


# ---------- messages ----------


@pytest.mark.parametrize(
    "url",
    [IG_URL, X_PHOTOS_URL, "https://x.com/a/status/1"],
)
def test_instagram_and_x_without_media_say_so(url):
    for text in ("There is no video in this post", "No video could be found in this tweet", "No video formats found!"):
        assert explain_download_error([text], url=url) == tr("error_no_media_in_post")


def test_facebook_photo_posts_are_said_to_be_unsupported():
    english = tr("error_no_video_in_post")
    assert "Facebook" in english
    assert "not supported" in english
    assert "later version" not in english
    url = "https://www.facebook.com/photo/?fbid=10160743390456729"
    assert explain_download_error(["ERROR: Unsupported URL: " + url], url=url) == english
    assert (
        explain_download_error(["There is no video in this post"], url="https://www.facebook.com/x/posts/1") == english
    )


def test_messages_exist_in_both_languages():
    from src.utils.translations import get_translation_manager

    english = {k: tr(k) for k in ("error_no_video_in_post", "error_no_media_in_post")}
    get_translation_manager().set_language("he")
    try:
        hebrew = {k: tr(k) for k in english}
    finally:
        get_translation_manager().set_language("en")
    for key, text in hebrew.items():
        assert text != key
        assert text != english[key]
        assert "\u2014" not in text and "\u2013" not in text
