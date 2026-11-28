"""Tests for the 0.5.0 download options: cookies, proxy, file names, formats.

Pure tests of ``build_ydl_opts`` and the validators, plus the file names that
yt-dlp itself makes from each preset (no network).
"""

from __future__ import annotations

import os

import pytest

from src.backend import yt_dlp_wrapper as wrapper_mod
from src.backend.download_options import (
    AUDIO_FILENAME_TEMPLATE,
    DATE_TITLE_TEMPLATE,
    FILENAME_PRESET_CUSTOM,
    FILENAME_PRESET_DATE_TITLE,
    FILENAME_PRESET_TITLE_QUALITY,
    FILENAME_PRESET_UPLOADER_TITLE,
    FILENAME_PRESETS,
    UPLOADER_TITLE_TEMPLATE,
    VIDEO_FILENAME_TEMPLATE,
    DownloadOptions,
    build_ydl_opts,
    mask_proxy_url,
    network_opts,
    redact_ydl_opts,
)
from src.backend.download_preferences import (
    PROXY_SCHEMES,
    DownloadPreferences,
    cookie_browsers,
    explain_download_error,
    validate_cookies_profile,
    validate_custom_format,
    validate_filename_template,
    validate_proxy_url,
)
from src.models.app_config import AppConfig
from src.utils.secret_scrub import scrub_secrets
from src.utils.translations import get_translation_manager, tr

OUT = os.path.join("downloads", "here")
NEW_KEYS = ("format_sort", "proxy", "cookiesfrombrowser")


def _opts(**kwargs):
    return DownloadOptions("https://example.com/v", OUT, "bestvideo+bestaudio/best", **kwargs)


@pytest.fixture(autouse=True)
def english():
    get_translation_manager().set_language("en")


# ---------- defaults ----------


def test_new_options_are_off_by_default():
    o = _opts()
    assert (o.cookies_browser, o.cookies_profile, o.proxy) == ("", "", "")
    assert (o.filename_preset, o.custom_filename_template) == (FILENAME_PRESET_TITLE_QUALITY, "")
    assert (o.video_codec, o.audio_codec, o.custom_format) == ("any", "any", "")
    ydl_opts = build_ydl_opts(o)
    assert not any(key in ydl_opts for key in NEW_KEYS)


# ---------- browser cookies ----------


def test_cookies_from_firefox():
    ydl_opts = build_ydl_opts(_opts(cookies_browser="firefox"))
    assert ydl_opts["cookiesfrombrowser"] == ("firefox", None, None, None)


def test_cookies_with_profile():
    ydl_opts = build_ydl_opts(_opts(cookies_browser="firefox", cookies_profile="work"))
    assert ydl_opts["cookiesfrombrowser"] == ("firefox", "work", None, None)


def test_profile_without_browser_is_ignored():
    assert "cookiesfrombrowser" not in build_ydl_opts(_opts(cookies_profile="work"))


@pytest.mark.parametrize(
    ("platform", "expected"),
    [
        ("linux", ("firefox",)),
        ("win32", ("firefox", "chrome", "edge", "brave")),
        ("darwin", ("firefox",)),
    ],
)
def test_cookie_browsers_by_platform(platform, expected):
    assert cookie_browsers(platform) == expected


def test_no_banned_or_unreadable_browsers_offered():
    """Opera (owner from a banned country) and Chromium on Linux (needs secretstorage) stay out."""
    for platform in ("linux", "win32"):
        assert "opera" not in cookie_browsers(platform)
    assert not set(cookie_browsers("linux")) & {"chrome", "chromium", "edge", "brave", "vivaldi"}


# ---------- proxy ----------


def test_proxy_option():
    assert build_ydl_opts(_opts(proxy="socks5://127.0.0.1:1080"))["proxy"] == "socks5://127.0.0.1:1080"


def test_network_opts_alone():
    assert network_opts("", "") == {}
    assert network_opts("http://p:3128", "firefox", "") == {
        "proxy": "http://p:3128",
        "cookiesfrombrowser": ("firefox", None, None, None),
    }


@pytest.mark.parametrize(
    "url",
    [
        "",
        "http://proxy.local:3128",
        "https://proxy.local",
        "socks5://127.0.0.1:1080",
        "socks5h://127.0.0.1:1080/",
        "http://user:p%40ss@proxy.local:8080",
        "SOCKS5://Host:1080",
        "http://[::1]:8080",
    ],
)
def test_valid_proxies(url):
    assert validate_proxy_url(url) is None


@pytest.mark.parametrize(
    ("url", "key"),
    [
        ("ftp://proxy.local:21", "error_proxy_scheme"),
        ("socks4://proxy.local:1080", "error_proxy_scheme"),
        ("proxy.local:3128", "error_proxy_scheme"),
        ("http://", "error_proxy_invalid"),
        ("http://proxy.local:99999", "error_proxy_invalid"),
        ("http://proxy.local:0", "error_proxy_invalid"),
        ("http://proxy.local:port", "error_proxy_invalid"),
        ("http://proxy.local/path", "error_proxy_invalid"),
        ("http://proxy.local?x=1", "error_proxy_invalid"),
        ("http://proxy.local:80\n", "error_proxy_invalid"),
        ("http://pro xy:80", "error_proxy_invalid"),
    ],
)
def test_invalid_proxies(url, key):
    assert validate_proxy_url(url) == key


def test_supported_proxy_schemes():
    assert PROXY_SCHEMES == ("http", "https", "socks5", "socks5h")


@pytest.mark.parametrize(
    ("url", "masked"),
    [
        ("", ""),
        ("socks5://127.0.0.1:1080", "socks5://127.0.0.1:1080"),
        ("http://alice:hunter2@proxy:3128", "http://***@proxy:3128"),
        ("socks5h://token@proxy:1080", "socks5h://***@proxy:1080"),
        ("http://a:b@c@proxy:1", "http://***@proxy:1"),
    ],
)
def test_mask_proxy_url(url, masked):
    assert mask_proxy_url(url) == masked


def test_log_scrubber_catches_socks_credentials():
    out = scrub_secrets("Unable to connect to socks5://alice:hunter2@proxy:1080")
    assert "hunter2" not in out
    assert "socks5://" in out


# ---------- the options log ----------


def test_redacted_options_hide_secrets():
    ydl_opts = build_ydl_opts(
        _opts(proxy="http://alice:hunter2@proxy:3128", cookies_browser="firefox", cookies_profile="/home/a/ff"),
        progress_hooks=[lambda d: None],
    )
    safe = redact_ydl_opts(ydl_opts)
    assert "progress_hooks" not in safe
    assert safe["proxy"] == "http://***@proxy:3128"
    assert safe["cookiesfrombrowser"] == ["firefox", "***"]
    assert "hunter2" not in repr(safe) and "/home/a/ff" not in repr(safe)
    # The real options are not changed.
    assert ydl_opts["proxy"] == "http://alice:hunter2@proxy:3128"


def test_redacted_options_without_profile():
    safe = redact_ydl_opts(build_ydl_opts(_opts(cookies_browser="firefox")))
    assert safe["cookiesfrombrowser"] == ["firefox", None]


# ---------- format options ----------


@pytest.mark.parametrize(
    ("codec", "field"),
    [("h264", "vcodec:h264"), ("h265", "vcodec:h265"), ("vp9", "vcodec:vp9"), ("av1", "vcodec:av01")],
)
def test_video_codec_preference(codec, field):
    assert build_ydl_opts(_opts(video_codec=codec))["format_sort"] == [field]


@pytest.mark.parametrize(
    ("codec", "field"),
    [("aac", "acodec:aac"), ("opus", "acodec:opus"), ("vorbis", "acodec:vorbis")],
)
def test_audio_codec_preference(codec, field):
    assert build_ydl_opts(_opts(audio_codec=codec))["format_sort"] == [field]


def test_both_codecs_and_the_quality_preset_stay():
    ydl_opts = build_ydl_opts(_opts(video_codec="h264", audio_codec="aac"))
    assert ydl_opts["format_sort"] == ["vcodec:h264", "acodec:aac"]
    assert ydl_opts["format"] == "bestvideo+bestaudio/best"


def test_unknown_codec_is_ignored():
    assert "format_sort" not in build_ydl_opts(_opts(video_codec="mpeg2", audio_codec="?"))


def test_audio_only_has_no_codec_preference():
    assert "format_sort" not in build_ydl_opts(_opts(audio_only=True, video_codec="h264", audio_codec="opus"))


def test_custom_format_replaces_quality_and_codecs():
    ydl_opts = build_ydl_opts(_opts(custom_format="bestaudio[ext=m4a]", video_codec="h264", audio_codec="aac"))
    assert ydl_opts["format"] == "bestaudio[ext=m4a]"
    assert "format_sort" not in ydl_opts


def test_custom_format_also_for_audio_only():
    assert (
        build_ydl_opts(_opts(audio_only=True, custom_format="bestaudio[ext=webm]"))["format"] == "bestaudio[ext=webm]"
    )


def test_codec_preferences_pick_the_format(tmp_path):
    """yt-dlp's own sorter picks the preferred codecs from a format list."""
    formats = [
        {"format_id": "av1", "vcodec": "av01.0.08M.08", "acodec": "none", "height": 1080},
        {"format_id": "vp9", "vcodec": "vp9", "acodec": "none", "height": 1080},
        {"format_id": "h264", "vcodec": "avc1.640028", "acodec": "none", "height": 1080},
        {"format_id": "h264_480", "vcodec": "avc1.4d401e", "acodec": "none", "height": 480},
        {"format_id": "opus", "vcodec": "none", "acodec": "opus", "abr": 130},
        {"format_id": "aac", "vcodec": "none", "acodec": "mp4a.40.2", "abr": 128},
    ]

    def pick(**kwargs):
        ydl_opts = build_ydl_opts(_opts(**kwargs))
        ydl = wrapper_mod.YoutubeDL({"quiet": True, "format_sort": ydl_opts.get("format_sort", [])})
        info = {"id": "x", "formats": [dict(f, url="https://example.com", ext="mp4") for f in formats]}
        ydl.sort_formats(info)
        selector = ydl.build_format_selector(ydl_opts["format"])
        ctx = {"formats": info["formats"], "has_merged_format": False, "incomplete_formats": False}
        return [f["format_id"] for f in selector(ctx)]

    assert pick() == ["av1+opus"]
    assert pick(video_codec="h264", audio_codec="aac") == ["h264+aac"]
    assert pick(video_codec="vp9") == ["vp9+opus"]


@pytest.mark.parametrize("value", ["", "best", "bestaudio[ext=m4a]", "bv*[vcodec^=avc]+ba[acodec^=mp4a]/b"])
def test_valid_custom_formats(value):
    assert validate_custom_format(value) is None


@pytest.mark.parametrize(
    ("value", "key"),
    [
        ("best\nrm -rf /", "error_format_invalid_char"),
        ("best\r", "error_format_invalid_char"),
        ("best\x00", "error_format_invalid_char"),
        ("   ", "error_format_syntax"),
        ("best[height<=720", "error_format_syntax"),
        ("(bv+ba", "error_format_syntax"),
        ("b" * 501, "error_format_too_long"),
    ],
)
def test_invalid_custom_formats(value, key):
    assert validate_custom_format(value) == key


def test_yt_dlp_parses_the_custom_format():
    assert wrapper_mod.YtDlpWrapper.format_selector_error("bestaudio[ext=m4a]") is None
    assert "Invalid format specification" in wrapper_mod.YtDlpWrapper.format_selector_error("best][")


# ---------- file name templates ----------


@pytest.mark.parametrize(
    ("preset", "video", "audio"),
    [
        (FILENAME_PRESET_TITLE_QUALITY, VIDEO_FILENAME_TEMPLATE, AUDIO_FILENAME_TEMPLATE),
        (FILENAME_PRESET_UPLOADER_TITLE, UPLOADER_TITLE_TEMPLATE, UPLOADER_TITLE_TEMPLATE),
        (FILENAME_PRESET_DATE_TITLE, DATE_TITLE_TEMPLATE, DATE_TITLE_TEMPLATE),
    ],
)
def test_preset_templates(preset, video, audio):
    assert _opts(filename_preset=preset).filename_template == video
    assert _opts(filename_preset=preset, audio_only=True).filename_template == audio
    assert build_ydl_opts(_opts(filename_preset=preset))["outtmpl"] == os.path.join(OUT, video)


def test_custom_template():
    o = _opts(filename_preset=FILENAME_PRESET_CUSTOM, custom_filename_template="%(id)s.%(ext)s")
    assert o.output_template == os.path.join(OUT, "%(id)s.%(ext)s")


@pytest.mark.parametrize("preset", [FILENAME_PRESET_CUSTOM, "nonsense"])
def test_custom_without_template_or_unknown_preset_falls_back(preset):
    assert _opts(filename_preset=preset).filename_template == VIDEO_FILENAME_TEMPLATE


_INFO = {
    "id": "jNQXAC9IVRw",
    "title": 'Me at the zoo: a/b "test"?',
    "uploader": "jawed",
    "upload_date": "20050424",
    "ext": "mp4",
    "height": 240,
    "quality": 3.0,
}


@pytest.mark.parametrize(
    ("preset", "template", "plain", "numbered"),
    [
        (FILENAME_PRESET_TITLE_QUALITY, "", "Me at the zoo_240p.mp4", "Me at the zoo_240p (1).mp4"),
        (FILENAME_PRESET_UPLOADER_TITLE, "", "jawed - Me at the zoo.mp4", "jawed - Me at the zoo (1).mp4"),
        (FILENAME_PRESET_DATE_TITLE, "", "2005-04-24 - Me at the zoo.mp4", "2005-04-24 - Me at the zoo (1).mp4"),
        (FILENAME_PRESET_CUSTOM, "%(id)s.%(ext)s", "jNQXAC9IVRw.mp4", "jNQXAC9IVRw (1).mp4"),
    ],
)
def test_yt_dlp_names_and_duplicate_numbering(preset, template, plain, numbered):
    """Each preset gives a Windows-safe name, and duplicate numbering still works."""
    o = _opts(filename_preset=preset, custom_filename_template=template)
    ydl = wrapper_mod.YoutubeDL({"quiet": True, "windowsfilenames": True, "outtmpl": o.output_template})
    title_info = dict(_INFO, title="Me at the zoo")
    assert os.path.basename(ydl.prepare_filename(title_info)) == plain
    numbered_template = wrapper_mod._numbered_template(o.output_template, 1)
    assert os.path.basename(ydl.prepare_filename(title_info, outtmpl=numbered_template)) == numbered
    # Characters Windows does not allow are replaced, never used as folders.
    name = os.path.basename(ydl.prepare_filename(_INFO))
    assert not set(name) & set('<>:"/\\|?*')


@pytest.mark.parametrize(
    "template",
    [
        "%(title)s.%(ext)s",
        "%(uploader)s - %(title)s [%(id)s].%(ext)s",
        "%(upload_date>%Y-%m-%d)s %(title)s.%(ext)s",
        "%(playlist_index)03d - %(title)s.%(ext)s",
        "%(uploader,channel|Unknown)s - %(title)s.%(ext)s",
        "%(title).80s.%(ext)s",
        "100%% %(title)s.%(ext)s",
        "video.%(ext)s",
        "%(title)s_%(height)sp.%(ext)s",
    ],
)
def test_valid_templates(template):
    assert validate_filename_template(template) is None


@pytest.mark.parametrize(
    ("template", "key"),
    [
        ("", "error_template_empty"),
        ("   ", "error_template_empty"),
        ("%(title)s", "error_template_ext"),
        ("%(title)s.mp4", "error_template_ext"),
        ("%(title)s.%(ext)s.bak", "error_template_ext"),
        (".%(ext)s", "error_template_ext"),
        ("../%(title)s.%(ext)s", "error_template_path"),
        ("..%(title)s.%(ext)s", "error_template_path"),
        ("%(title)s/..%(ext)s", "error_template_path"),
        ("sub/%(title)s.%(ext)s", "error_template_path"),
        ("sub\\%(title)s.%(ext)s", "error_template_path"),
        ("/etc/%(title)s.%(ext)s", "error_template_path"),
        ("C:%(title)s.%(ext)s", "error_template_path"),
        ("~%(title)s.%(ext)s", "error_template_path"),
        ("%(title)s\n.%(ext)s", "error_template_invalid_char"),
        ("%(title)s?.%(ext)s", "error_template_invalid_char"),
        ("$HOME %(title)s.%(ext)s", "error_template_invalid_char"),
        ("ab:c %(title)s.%(ext)s", "error_template_invalid_char"),
        ("%(description)s.%(ext)s", "error_template_unknown_field"),
        ("%(title,filepath)s.%(ext)s", "error_template_unknown_field"),
        ("%(__class__)s.%(ext)s", "error_template_unknown_field"),
        ("%(title.0)s.%(ext)s", "error_template_field_syntax"),
        ("%(title)z.%(ext)s", "error_template_field_syntax"),
        ("%title.%(ext)s", "error_template_field_syntax"),
        ("100% %(title)s.%(ext)s", "error_template_field_syntax"),
        ("%(title|a/b)s.%(ext)s", "error_template_path"),
        ("x" * 195 + ".%(ext)s", "error_template_too_long"),
    ],
)
def test_rejected_templates(template, key):
    assert validate_filename_template(template) == key


def test_every_validation_key_has_both_translations():
    from src.utils.translations import TRANSLATIONS

    keys = {
        "error_template_empty",
        "error_template_too_long",
        "error_template_invalid_char",
        "error_template_path",
        "error_template_ext",
        "error_template_field_syntax",
        "error_template_unknown_field",
        "error_proxy_invalid",
        "error_proxy_scheme",
        "error_format_too_long",
        "error_format_invalid_char",
        "error_format_syntax",
        "error_cookies_profile",
    }
    for lang in ("en", "he"):
        assert keys <= set(TRANSLATIONS[lang])


def test_presets_list():
    assert FILENAME_PRESETS == ("title_quality", "uploader_title", "date_title", "custom")


# ---------- preferences from the config ----------


def test_preferences_from_config():
    config = AppConfig(
        output_directory="/tmp",
        cookies_browser="firefox",
        cookies_profile=" default-release ",
        proxy_url="socks5://127.0.0.1:1080",
        filename_template_preset="custom",
        custom_filename_template="%(id)s.%(ext)s",
        video_codec_preference="h264",
        audio_codec_preference="aac",
        custom_format="bestaudio",
    )
    prefs = DownloadPreferences.from_config(config)
    assert prefs == DownloadPreferences(
        cookies_browser="firefox",
        cookies_profile="default-release",
        proxy="socks5://127.0.0.1:1080",
        filename_preset="custom",
        custom_filename_template="%(id)s.%(ext)s",
        video_codec="h264",
        audio_codec="aac",
        custom_format="bestaudio",
    )
    assert prefs.rejected == ()
    assert prefs.network_opts() == {
        "proxy": "socks5://127.0.0.1:1080",
        "cookiesfrombrowser": ("firefox", "default-release", None, None),
    }


def test_bad_values_in_the_config_fall_back(caplog):
    config = AppConfig(
        output_directory="/tmp",
        cookies_browser="opera",
        proxy_url="ftp://user:secret@host",
        filename_template_preset="custom",
        custom_filename_template="../%(title)s.%(ext)s",
        video_codec_preference="mpeg2",
        audio_codec_preference=7,  # type: ignore[arg-type]
        custom_format="best\nworst",
    )
    with caplog.at_level("WARNING"):
        prefs = DownloadPreferences.from_config(config)
    assert prefs == DownloadPreferences(filename_preset="custom")
    assert set(prefs.rejected) == {
        "cookies_browser",
        "proxy",
        "custom_filename_template",
        "video_codec",
        "audio_codec",
        "custom_format",
    }
    assert "secret" not in caplog.text


def test_old_config_without_new_fields():
    """A 0.4.x config file has none of the new keys; the defaults apply."""
    data = AppConfig(output_directory="/tmp").to_dict()
    for key in (
        "cookies_browser",
        "cookies_profile",
        "proxy_url",
        "filename_template_preset",
        "custom_filename_template",
        "video_codec_preference",
        "audio_codec_preference",
        "custom_format",
    ):
        del data[key]
    assert DownloadPreferences.from_config(AppConfig.from_dict(data)) == DownloadPreferences()


@pytest.mark.parametrize(("profile", "ok"), [("", True), ("default", True), ("C:\\Profiles\\x", True), ("a\nb", False)])
def test_cookies_profile_check(profile, ok):
    assert (validate_cookies_profile(profile) is None) is ok


# ---------- clear error messages ----------


@pytest.mark.parametrize(
    ("message", "key"),
    [
        (
            "ERROR: Failed to decrypt with DPAPI. See  https://github.com/yt-dlp/yt-dlp/issues/10927  for more info",
            "cookies_error_app_bound",
        ),
        (
            "ERROR: Could not copy Chrome cookie database. See  https://github.com/yt-dlp/yt-dlp/issues/7271",
            "cookies_error_locked",
        ),
        ("ERROR: could not find firefox cookies database in '/x'", "cookies_error_not_found"),
        ("failed to load cookies", "cookies_error_generic"),
    ],
)
def test_cookie_errors_get_a_clear_message(message, key):
    assert explain_download_error([message], cookies_browser="chrome") == tr(key, browser="Chrome")


def test_cookie_error_without_cookies_is_not_explained():
    assert explain_download_error(["failed to load cookies"]) is None


def test_sign_in_hint():
    message = "ERROR: [youtube] x: Sign in to confirm your age. Use --cookies-from-browser or --cookies"
    assert explain_download_error([message]) == tr("cookies_hint_sign_in")
    assert explain_download_error([message], cookies_browser="firefox") == tr(
        "cookies_hint_signed_in_browser", browser="Firefox"
    )


def test_proxy_hint_only_with_a_proxy():
    message = "ERROR: Unable to download webpage: Unable to connect to proxy"
    assert explain_download_error([message]) is None
    assert explain_download_error([message], proxy="socks5://h:1") == tr("proxy_error_connect")


def test_other_errors_are_left_alone():
    assert explain_download_error([None, "ERROR: Requested format is not available"], cookies_browser="firefox") is None
    assert explain_download_error([]) is None


def test_hebrew_messages():
    get_translation_manager().set_language("he")
    try:
        text = explain_download_error(["failed to load cookies"], cookies_browser="firefox")
        assert "Firefox" in text and text != tr("cookies_error_generic")
        assert text.startswith("לא")
    finally:
        get_translation_manager().set_language("en")
