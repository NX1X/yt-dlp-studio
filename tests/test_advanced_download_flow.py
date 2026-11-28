"""The 0.5.0 download options through the app: config, worker, wrapper, UI.

YoutubeDL is replaced by a recording fake; no network is used.
"""

from __future__ import annotations

import json
import logging
import os
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QMessageBox

from src.backend import download_preferences as prefs_mod
from src.backend import playlist_fetcher as playlist_mod
from src.backend import yt_dlp_wrapper as mod
from src.backend.config_manager import ConfigManager
from src.backend.download_options import DownloadOptions
from src.backend.download_preferences import DownloadPreferences, get_download_preferences
from src.backend.download_worker import DownloadWorker, download_options_for
from src.models.download_task import DownloadTask, TaskStatus
from src.ui.settings_tab import SettingsTab
from src.utils.constants import QUALITY_OPTIONS
from src.utils.translations import TRANSLATIONS, get_translation_manager, tr

URL = "https://www.youtube.com/watch?v=abc123"
SECRET_PROXY = "socks5://alice:hunter2@proxy.local:1080"
PROFILE = "/home/alice/.mozilla/firefox/secret.default"


@pytest.fixture(autouse=True)
def english():
    get_translation_manager().set_language("en")


class _FakeYDL:
    runs: list[dict] = []
    extract = None

    def __init__(self, params=None):
        self.params = params or {}
        self.added = []
        self._write_subtitles = lambda info, filename: []
        type(self).runs.append({"ydl": self, "params": self.params})

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
            return {"id": "abc123", "title": "Probe", "subtitles": {"en": []}, "_type": "playlist", "entries": []}
        return type(self).extract(self, url)


def _write_output(ydl, name="Clip.mp4"):
    folder = os.path.dirname(ydl.params["outtmpl"])
    path = os.path.join(folder, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write("data")
    return {"id": "abc123", "title": "Clip", "requested_downloads": [{"filepath": path}]}


@pytest.fixture
def fake_ydl(monkeypatch):
    _FakeYDL.runs = []
    _FakeYDL.extract = staticmethod(lambda ydl, url: _write_output(ydl))
    monkeypatch.setattr(mod, "YoutubeDL", _FakeYDL)
    monkeypatch.setattr(playlist_mod, "YoutubeDL", _FakeYDL)
    monkeypatch.setattr(mod.YtDlpWrapper, "_get_ffmpeg_location", lambda self: None)
    monkeypatch.setattr(mod.YtDlpWrapper, "_get_deno_location", lambda self: None)
    yield _FakeYDL
    assert not mod._reserved_outputs


@pytest.fixture
def no_sound(monkeypatch):
    import sys

    monkeypatch.setitem(sys.modules, "winsound", None)
    from PySide6.QtWidgets import QApplication

    monkeypatch.setattr(QApplication, "beep", staticmethod(lambda: None))


_PREFS = DownloadPreferences(
    cookies_browser="firefox",
    cookies_profile=PROFILE,
    proxy=SECRET_PROXY,
    filename_preset="uploader_title",
    video_codec="h264",
    audio_codec="aac",
)


# ---------- config: persisted and published ----------


@pytest.fixture
def config_manager(tmp_path):
    out_dir = tmp_path / "downloads"
    out_dir.mkdir()
    manager = ConfigManager(config_path=tmp_path / "config.json")
    manager.load_config()
    manager.update_config(output_directory=str(out_dir))
    return manager


def test_saving_the_config_publishes_the_preferences(config_manager):
    assert get_download_preferences() == DownloadPreferences()
    config_manager.update_config(proxy_url="http://proxy.local:3128", cookies_browser="firefox")
    current = get_download_preferences()
    assert current.proxy == "http://proxy.local:3128"
    assert current.cookies_browser == "firefox"


def test_loading_the_config_publishes_the_preferences(config_manager, tmp_path):
    config_manager.update_config(video_codec_preference="vp9", custom_format="bestaudio")
    prefs_mod.set_download_preferences(DownloadPreferences())
    ConfigManager(config_path=tmp_path / "config.json").load_config()
    assert get_download_preferences().video_codec == "vp9"
    assert get_download_preferences().custom_format == "bestaudio"


def test_new_fields_round_trip_through_the_file(config_manager, tmp_path):
    config_manager.update_config(
        cookies_browser="firefox",
        cookies_profile="work",
        proxy_url="socks5://127.0.0.1:1080",
        filename_template_preset="custom",
        custom_filename_template="%(id)s.%(ext)s",
        video_codec_preference="av1",
        audio_codec_preference="opus",
        custom_format="best",
    )
    saved = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert saved["proxy_url"] == "socks5://127.0.0.1:1080"
    config = ConfigManager(config_path=tmp_path / "config.json").load_config()
    assert (config.cookies_profile, config.custom_filename_template, config.audio_codec_preference) == (
        "work",
        "%(id)s.%(ext)s",
        "opus",
    )


def test_update_config_log_masks_the_proxy_password(config_manager, caplog):
    with caplog.at_level(logging.DEBUG, logger="YT-DLP Studio"):
        config_manager.update_config(proxy_url="http://bob:p4ssw0rd@proxy.local:3128")
    assert "p4ssw0rd" not in caplog.text
    assert "http://***@proxy.local:3128" in caplog.text


# ---------- the worker fills DownloadOptions ----------


def test_download_options_for_uses_the_preferences(tmp_path):
    task = DownloadTask(url=URL, output_directory=str(tmp_path), quality="720p (HD)")
    options = download_options_for(task, _PREFS)
    assert (options.cookies_browser, options.cookies_profile, options.proxy) == ("firefox", PROFILE, SECRET_PROXY)
    assert (options.filename_preset, options.video_codec, options.audio_codec) == ("uploader_title", "h264", "aac")
    assert options.format_string == QUALITY_OPTIONS["720p (HD)"]


def test_download_options_for_reads_the_current_preferences(tmp_path):
    prefs_mod.set_download_preferences(DownloadPreferences(custom_format="bestaudio[ext=m4a]"))
    task = DownloadTask(url=URL, output_directory=str(tmp_path), quality="Best Quality")
    assert download_options_for(task).custom_format == "bestaudio[ext=m4a]"


def test_worker_sends_proxy_and_cookies_to_info_and_download(tmp_path, fake_ydl, no_sound):
    prefs_mod.set_download_preferences(_PREFS)
    task = DownloadTask(url=URL, output_directory=str(tmp_path), quality="Best Quality", download_thumbnail=False)
    DownloadWorker(task).run()
    assert task.status == TaskStatus.COMPLETED
    probe, run = fake_ydl.runs
    for params in (probe["params"], run["params"]):
        assert params["proxy"] == SECRET_PROXY
        assert params["cookiesfrombrowser"] == ("firefox", PROFILE, None, None)
    assert run["params"]["format_sort"] == ["vcodec:h264", "acodec:aac"]
    assert run["params"]["outtmpl"] == os.path.join(str(tmp_path), "%(uploader)s - %(title)s.%(ext)s")


def test_worker_uses_one_snapshot(tmp_path, fake_ydl, no_sound):
    """A save in Settings during a download does not change that download."""
    prefs_mod.set_download_preferences(DownloadPreferences(proxy="http://first:1"))

    def extract(ydl, url):
        prefs_mod.set_download_preferences(DownloadPreferences(proxy="http://second:2"))
        return _write_output(ydl)

    fake_ydl.extract = staticmethod(extract)
    task = DownloadTask(url=URL, output_directory=str(tmp_path), quality="Best Quality", download_thumbnail=False)
    DownloadWorker(task).run()
    assert [r["params"]["proxy"] for r in fake_ydl.runs] == ["http://first:1", "http://first:1"]


def test_subtitle_and_playlist_lookups_use_the_network_options(fake_ydl):
    prefs_mod.set_download_preferences(_PREFS)
    mod.YtDlpWrapper().get_available_subtitles(URL)
    playlist_mod.PlaylistFetcher.fetch_playlist_quick(URL + "&list=PL1")
    playlist_mod.PlaylistFetcher.fetch_playlist_info(URL + "&list=PL1")
    assert len(fake_ydl.runs) == 3
    for run in fake_ydl.runs:
        assert run["params"]["proxy"] == SECRET_PROXY
        assert run["params"]["cookiesfrombrowser"][0] == "firefox"


def test_lookups_without_settings_add_nothing(fake_ydl):
    mod.YtDlpWrapper().get_video_info(URL)
    playlist_mod.PlaylistFetcher.fetch_playlist_quick(URL)
    for run in fake_ydl.runs:
        assert "proxy" not in run["params"]
        assert "cookiesfrombrowser" not in run["params"]


# ---------- secrets stay out of the log ----------


def test_download_log_has_no_proxy_password_or_profile(tmp_path, fake_ydl, caplog):
    options = DownloadOptions(
        URL,
        str(tmp_path),
        "best",
        proxy=SECRET_PROXY,
        cookies_browser="firefox",
        cookies_profile=PROFILE,
        download_thumbnail=False,
    )
    with caplog.at_level(logging.DEBUG, logger="YT-DLP Studio"):
        assert mod.YtDlpWrapper().download(options) is True
    assert "hunter2" not in caplog.text
    assert PROFILE not in caplog.text
    assert "socks5://***@proxy.local:1080" in caplog.text
    assert "Cookies From Browser: firefox" in caplog.text
    # yt-dlp itself still gets the real values.
    assert fake_ydl.runs[0]["params"]["proxy"] == SECRET_PROXY


# ---------- cookies never land in the info JSON ----------


def test_cookie_strip_hook_only_with_cookies_and_info_json(tmp_path, fake_ydl):
    def added(**kwargs):
        fake_ydl.runs = []
        options = DownloadOptions(URL, str(tmp_path), "best", download_thumbnail=False, **kwargs)
        mod.YtDlpWrapper().download(options)
        return [(type(pp).__name__, when) for pp, when in fake_ydl.runs[0]["ydl"].added]

    strip = ("_StripInfoJsonCookiesPP", "before_dl")
    assert strip in added(cookies_browser="firefox", download_metadata=True)
    assert strip in added(cookies_browser="firefox", download_comments=True)
    assert strip not in added(cookies_browser="firefox")
    assert strip not in added(download_metadata=True)


def test_strip_cookies_from_info_json(tmp_path):
    path = tmp_path / "Clip.info.json"
    data = {
        "title": "Clip",
        "cookies": "SID=secret; Domain=.youtube.com",
        "formats": [{"format_id": "18", "cookies": "SID=secret", "http_headers": {"User-Agent": "x"}}],
        "requested_formats": [{"format_id": "18", "cookies": "SID=secret"}],
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    assert mod.strip_cookies_from_info_json(str(path)) is True
    cleaned = json.loads(path.read_text(encoding="utf-8"))
    assert "secret" not in path.read_text(encoding="utf-8")
    assert cleaned["formats"] == [{"format_id": "18", "http_headers": {"User-Agent": "x"}}]
    assert cleaned["title"] == "Clip"
    # Nothing to remove: the file is left as it was.
    before = path.read_text(encoding="utf-8")
    assert mod.strip_cookies_from_info_json(str(path)) is False
    assert path.read_text(encoding="utf-8") == before


def test_strip_hook_runs_on_the_written_file(tmp_path):
    path = tmp_path / "Clip.info.json"
    path.write_text(json.dumps({"formats": [{"cookies": "SID=secret"}]}), encoding="utf-8")
    pp = mod._StripInfoJsonCookiesPP(None)
    files, info = pp.run({"infojson_filename": str(path)})
    assert files == []
    assert "secret" not in path.read_text(encoding="utf-8")
    # A missing or broken file does not fail the download.
    pp.run({"infojson_filename": str(tmp_path / "gone.info.json")})
    path.write_text("{broken", encoding="utf-8")
    pp.run({"infojson_filename": str(path)})


# ---------- clear messages instead of yt-dlp's text ----------


def test_app_bound_cookie_error_is_explained(tmp_path, fake_ydl, no_sound):
    def extract(ydl, url):
        ydl.params["logger"].error(
            "ERROR: Failed to decrypt with DPAPI. See  https://github.com/yt-dlp/yt-dlp/issues/10927  for more info"
        )
        raise RuntimeError("failed to load cookies")

    fake_ydl.extract = staticmethod(extract)
    prefs_mod.set_download_preferences(DownloadPreferences(cookies_browser="firefox"))
    task = DownloadTask(url=URL, output_directory=str(tmp_path), quality="Best Quality")
    worker = DownloadWorker(task)
    failed = []
    worker.download_failed.connect(failed.append)
    worker.run()
    expected = tr("cookies_error_app_bound", browser="Firefox")
    assert worker.wrapper.user_error == expected
    assert worker.wrapper.last_error == expected
    assert failed == [expected]
    assert task.error_message == expected


def test_sign_in_error_without_cookies_gets_a_hint(tmp_path, fake_ydl):
    def extract(ydl, url):
        ydl.params["logger"].error("ERROR: [youtube] abc123: Sign in to confirm your age. Use --cookies-from-browser")
        return None

    fake_ydl.extract = staticmethod(extract)
    wrapper = mod.YtDlpWrapper()
    assert wrapper.download(DownloadOptions(URL, str(tmp_path), "best")) is False
    assert wrapper.user_error == tr("cookies_hint_sign_in")


def test_other_failures_keep_the_old_message(tmp_path, fake_ydl, no_sound):
    fake_ydl.extract = staticmethod(lambda ydl, url: None)
    task = DownloadTask(url=URL, output_directory=str(tmp_path), quality="Best Quality")
    worker = DownloadWorker(task)
    worker.run()
    assert worker.wrapper.user_error is None
    assert task.error_message == "Download failed"


def test_next_download_clears_the_user_error(tmp_path, fake_ydl):
    wrapper = mod.YtDlpWrapper()
    fake_ydl.extract = staticmethod(lambda ydl, url: (_ for _ in ()).throw(RuntimeError("failed to load cookies")))
    wrapper.download(DownloadOptions(URL, str(tmp_path), "best", cookies_browser="firefox"))
    assert wrapper.user_error
    fake_ydl.extract = staticmethod(lambda ydl, url: _write_output(ydl))
    assert wrapper.download(DownloadOptions(URL, str(tmp_path), "best")) is True
    assert wrapper.user_error is None


# ---------- Settings tab ----------


@pytest.fixture
def settings_tab(qtbot, config_manager):
    tab = SettingsTab(config_manager)
    qtbot.addWidget(tab)
    return tab


def test_section_starts_collapsed_and_toggles(settings_tab):
    adv = settings_tab.advanced_options
    assert adv.group.isHidden()
    assert adv.toggle_button.text() == tr("button_show_advanced_download")
    adv.toggle_button.setChecked(True)
    assert not adv.group.isHidden()
    assert adv.toggle_button.text() == tr("button_hide_advanced_download")


def test_fields_are_labelled_for_screen_readers(settings_tab):
    adv = settings_tab.advanced_options
    for field in (adv.cookies_combo, adv.proxy_input, adv.filename_combo, adv.custom_format_input):
        assert field.accessibleName()
        assert field.toolTip()


def test_cookie_choices_on_this_platform(settings_tab):
    combo = settings_tab.advanced_options.cookies_combo
    values = [combo.itemData(i) for i in range(combo.count())]
    assert values == ["", *prefs_mod.cookie_browsers()]


def test_dependent_fields_enable(settings_tab):
    adv = settings_tab.advanced_options
    assert not adv.cookies_profile_input.isEnabled()
    assert not adv.custom_template_input.isEnabled()
    adv.cookies_combo.setCurrentIndex(adv.cookies_combo.findData("firefox"))
    adv.filename_combo.setCurrentIndex(adv.filename_combo.findData("custom"))
    assert adv.cookies_profile_input.isEnabled()
    assert adv.custom_template_input.isEnabled()
    adv.custom_format_input.setText("best")
    assert not adv.video_codec_combo.isEnabled()
    assert not adv.audio_codec_combo.isEnabled()


def test_save_persists_and_publishes(settings_tab, config_manager):
    adv = settings_tab.advanced_options
    adv.cookies_combo.setCurrentIndex(adv.cookies_combo.findData("firefox"))
    adv.cookies_profile_input.setText(" work ")
    adv.proxy_input.setText("socks5://127.0.0.1:1080")
    adv.filename_combo.setCurrentIndex(adv.filename_combo.findData("date_title"))
    adv.video_codec_combo.setCurrentIndex(adv.video_codec_combo.findData("h265"))
    adv.audio_codec_combo.setCurrentIndex(adv.audio_codec_combo.findData("opus"))
    with patch.object(QMessageBox, "information"), patch.object(QMessageBox, "warning") as warning:
        settings_tab._save_settings()
    warning.assert_not_called()
    config = config_manager.get_config()
    assert (config.cookies_browser, config.cookies_profile, config.proxy_url) == (
        "firefox",
        "work",
        "socks5://127.0.0.1:1080",
    )
    assert (config.filename_template_preset, config.video_codec_preference, config.audio_codec_preference) == (
        "date_title",
        "h265",
        "opus",
    )
    assert get_download_preferences().filename_preset == "date_title"


@pytest.mark.parametrize(
    ("field", "value", "key"),
    [
        ("proxy_input", "ftp://host:21", "error_proxy_scheme"),
        ("custom_template_input", "../%(title)s.%(ext)s", "error_template_path"),
        ("custom_template_input", "%(title)s", "error_template_ext"),
        ("custom_format_input", "best][", "error_format_syntax"),
    ],
)
def test_invalid_value_blocks_the_save(settings_tab, config_manager, field, value, key):
    adv = settings_tab.advanced_options
    adv.filename_combo.setCurrentIndex(adv.filename_combo.findData("custom"))
    adv.custom_template_input.setText("%(title)s.%(ext)s")
    getattr(adv, field).setText(value)
    with patch.object(QMessageBox, "information"), patch.object(QMessageBox, "warning") as warning:
        settings_tab._save_settings()
    warning.assert_called_once()
    assert warning.call_args.args[1:] == (tr("error_invalid_advanced_settings"), tr(key))
    assert not adv.group.isHidden()  # opened, so the user sees the field
    assert config_manager.get_config().filename_template_preset == "title_quality"


def test_load_shows_saved_values_and_reset_clears_them(settings_tab, config_manager):
    config_manager.update_config(
        proxy_url="http://proxy.local:3128", custom_format="bestaudio", filename_template_preset="custom"
    )
    settings_tab._load_settings()
    adv = settings_tab.advanced_options
    assert adv.proxy_input.text() == "http://proxy.local:3128"
    assert adv.custom_format_input.text() == "bestaudio"
    assert adv.filename_combo.currentData() == "custom"
    with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes), patch.object(QMessageBox, "information"):
        settings_tab._reset_defaults()
    assert adv.proxy_input.text() == ""
    assert adv.filename_combo.currentData() == "title_quality"
    assert get_download_preferences() == DownloadPreferences()


def test_new_strings_exist_in_both_languages():
    keys = [k for k in TRANSLATIONS["en"] if k.startswith(("cookies_", "proxy_", "filename_preset_", "codec_"))]
    keys += ["settings_advanced_download", "label_custom_format", "text_cookies_privacy", "text_advanced_applies"]
    for key in keys:
        assert TRANSLATIONS["he"].get(key), key
        assert chr(0x2014) not in TRANSLATIONS["en"][key]
        assert chr(0x2013) not in TRANSLATIONS["en"][key]
