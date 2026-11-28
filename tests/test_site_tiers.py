"""Tests for the site tiers (src/utils/site_tiers.py) and the label in the Download tab."""

import pytest

import src.utils.translations as tr_module
from src.ui.site_tier_label import SiteTierLabel
from src.ui.theme import ModernTheme, ThemeMode
from src.utils.site_tiers import TESTED_SITES, SiteTier, classify_url, tested_site_name
from src.utils.translations import TRANSLATIONS

TESTED_URLS = [
    ("https://www.youtube.com/watch?v=jNQXAC9IVRw", "YouTube"),
    ("https://youtube.com/watch?v=jNQXAC9IVRw", "YouTube"),
    ("https://m.youtube.com/watch?v=jNQXAC9IVRw", "YouTube"),
    ("https://music.youtube.com/watch?v=abc", "YouTube"),
    ("https://youtu.be/jNQXAC9IVRw", "YouTube"),
    ("https://www.youtube.com/playlist?list=PL123", "YouTube"),
    ("https://www.instagram.com/reel/abc/", "Instagram"),
    ("https://instagram.com/p/abc/", "Instagram"),
    ("https://www.tiktok.com/@user/video/123", "TikTok"),
    ("https://tiktok.com/@user/video/123", "TikTok"),
    ("https://vm.tiktok.com/ZMabc/", "TikTok"),
    ("https://www.facebook.com/watch/?v=123", "Facebook"),
    ("https://facebook.com/user/videos/123", "Facebook"),
    ("https://m.facebook.com/watch/?v=123", "Facebook"),
    ("https://fb.watch/abc/", "Facebook"),
    ("https://x.com/user/status/123", "X"),
    ("https://twitter.com/user/status/123", "X"),
    ("https://mobile.twitter.com/user/status/123", "X"),
    ("http://www.youtube.com/watch?v=abc", "YouTube"),
]


class TestClassifier:
    @pytest.mark.parametrize(("url", "site"), TESTED_URLS)
    def test_tested_sites(self, url, site):
        assert classify_url(url) is SiteTier.TESTED
        assert tested_site_name(url) == site

    @pytest.mark.parametrize(
        "url",
        [
            "https://vimeo.com/123",
            "https://www.dailymotion.com/video/x8abc",
            "https://soundcloud.com/artist/track",
            "https://example.com/video.mp4",
            "http://192.168.1.10/video.mp4",
            "http://localhost:8080/v",
        ],
    )
    def test_other_sites_are_experimental(self, url):
        assert classify_url(url) is SiteTier.EXPERIMENTAL
        assert tested_site_name(url) is None

    @pytest.mark.parametrize(
        "url",
        [
            "https://evil-youtube.com/watch?v=abc",
            "https://youtube.com.evil.example/watch?v=abc",
            "https://notyoutube.com/watch",
            "https://youtube.co/watch",
            "https://www.youtube.com.example.org/",
            "https://fakeinstagram.com/p/abc",
            "https://instagram.com.evil.example/p/abc",
            "https://tiktok.co/@user",
            "https://facebook.com-video.example/watch",
            "https://xx.com/user/status/1",
            "https://twitter.co/user",
            "https://youtube.com@evil.example/watch?v=abc",  # user info, real host is evil.example
            "https://evil.example/?u=https://www.youtube.com/watch",
            "https://evil.example/youtube.com",
            "https://gaming.youtube.com/watch?v=abc",  # no subdomain matching
            "https://www.уoutube.com/watch?v=abc",  # Cyrillic "у"
        ],
    )
    def test_lookalike_hosts_are_not_tested(self, url):
        assert classify_url(url) is SiteTier.EXPERIMENTAL
        assert tested_site_name(url) is None

    @pytest.mark.parametrize(
        "url",
        [
            "https://www.youtube.com:443/watch?v=abc",
            "http://youtube.com:80/watch?v=abc",
            "https://youtu.be:8443/abc",
        ],
    )
    def test_ports_are_ignored(self, url):
        assert classify_url(url) is SiteTier.TESTED

    @pytest.mark.parametrize("url", ["https://youtube.com:abc/watch", "https://youtube.com:99999/watch"])
    def test_invalid_port_is_invalid(self, url):
        assert classify_url(url) is SiteTier.INVALID

    @pytest.mark.parametrize(
        "url",
        ["HTTPS://WWW.YOUTUBE.COM/watch?v=abc", "https://YouTu.Be/abc", "Https://X.com/u/status/1"],
    )
    def test_uppercase(self, url):
        assert classify_url(url) is SiteTier.TESTED

    def test_surrounding_spaces_and_trailing_dot(self):
        assert classify_url("  https://www.youtube.com/watch?v=abc \n") is SiteTier.TESTED
        assert classify_url("https://www.youtube.com./watch?v=abc") is SiteTier.TESTED

    @pytest.mark.parametrize(
        "url",
        [
            "youtube.com/watch?v=abc",  # missing scheme
            "www.youtube.com/watch?v=abc",
            "//www.youtube.com/watch?v=abc",
            "ftp://youtube.com/video",
            "javascript:alert(1)",
            "file:///home/user/video.mp4",
            "https://",
            "https:///watch",
            "https://evil.example\\@youtube.com/",
            "",
            "   ",
            "not a url",
            None,
            42,
        ],
    )
    def test_invalid(self, url):
        assert classify_url(url) is SiteTier.INVALID
        assert tested_site_name(url) is None

    def test_tested_site_list(self):
        assert sorted(TESTED_SITES) == ["Facebook", "Instagram", "TikTok", "X", "YouTube"]
        for hosts in TESTED_SITES.values():
            for host in hosts:
                assert host == host.lower() and "/" not in host and ":" not in host


@pytest.fixture
def english():
    manager = tr_module.get_translation_manager()
    before = manager.get_language()
    manager.set_language("en")
    yield manager
    manager.set_language(before)


class TestSiteTierLabel:
    def test_hidden_at_start(self, qapp):
        label = SiteTierLabel()
        assert label.isHidden()
        assert label.objectName() == "siteTierLabel"

    def test_tested(self, qapp, english):
        label = SiteTierLabel()
        assert label.update_for_url("https://youtu.be/abc") is SiteTier.TESTED
        assert not label.isHidden()
        assert label.text() == "Tested site"
        assert label.property("siteTier") == "tested"
        assert "before every release" in label.toolTip()
        assert label.accessibleName() == "Tested site"
        assert label.accessibleDescription() == label.toolTip()

    def test_experimental(self, qapp, english):
        label = SiteTierLabel()
        assert label.update_for_url("https://vimeo.com/123") is SiteTier.EXPERIMENTAL
        assert not label.isHidden()
        assert label.text() == "Experimental site: may not work"
        assert label.property("siteTier") == "experimental"
        assert "does not test this site" in label.toolTip()
        assert label.accessibleName() == label.text()

    @pytest.mark.parametrize("url", ["", "youtube.com/watch", "garbage"])
    def test_invalid_hides_label(self, qapp, english, url):
        label = SiteTierLabel()
        label.update_for_url("https://vimeo.com/123")
        assert label.update_for_url(url) is SiteTier.INVALID
        assert label.isHidden()
        assert label.text() == ""
        assert label.toolTip() == ""
        assert label.accessibleName() == ""

    def test_switches_between_tiers(self, qapp, english):
        label = SiteTierLabel()
        label.update_for_url("https://vimeo.com/123")
        label.update_for_url("https://x.com/u/status/1")
        assert label.text() == "Tested site"
        assert label.property("siteTier") == "tested"

    def test_hebrew(self, qapp, english):
        english.set_language("he")
        label = SiteTierLabel()
        label.update_for_url("https://youtu.be/abc")
        # tr() adds an RLM after a final ")", ":" or "." in Hebrew.
        from src.utils.translations import _end_rtl_paren

        def shown(key: str) -> str:
            return _end_rtl_paren(key, TRANSLATIONS["he"][key])

        assert label.text() == shown("site_tier_tested")
        label.update_for_url("https://vimeo.com/1")
        assert label.text() == shown("site_tier_experimental")
        assert label.toolTip() == shown("tooltip_site_tier_experimental")

    def test_follows_line_edit(self, qapp, english):
        from PySide6.QtWidgets import QLineEdit

        line_edit = QLineEdit()
        label = SiteTierLabel()
        line_edit.textChanged.connect(label.update_for_url)
        line_edit.setText("https://www.instagram.com/reel/abc/")
        assert label.text() == "Tested site"
        line_edit.clear()
        assert label.isHidden()


class TestTranslationsAndTheme:
    KEYS = ("site_tier_tested", "site_tier_experimental", "tooltip_site_tier_tested", "tooltip_site_tier_experimental")

    @pytest.mark.parametrize("language", ["en", "he"])
    def test_every_string_is_translated(self, language):
        for key in self.KEYS:
            assert TRANSLATIONS[language][key].strip()
            # No em dash or en dash in user-facing text
            assert chr(0x2014) not in TRANSLATIONS[language][key]
            assert chr(0x2013) not in TRANSLATIONS[language][key]

    def test_hebrew_differs_from_english(self):
        for key in ("site_tier_tested", "site_tier_experimental"):
            assert TRANSLATIONS["he"][key] != TRANSLATIONS["en"][key]

    @pytest.mark.parametrize(
        ("mode", "tested", "experimental"),
        [(ThemeMode.DARK, "#4ec9b0", "#dcdcaa"), (ThemeMode.LIGHT, "#047857", "#b45309")],
    )
    def test_theme_colors(self, mode, tested, experimental):
        qss = ModernTheme.get_stylesheet(mode)
        assert f'QLabel#siteTierLabel[siteTier="tested"] {{\n    color: {tested};' in qss
        assert f'QLabel#siteTierLabel[siteTier="experimental"] {{\n    color: {experimental};' in qss


class TestDownloadTabWiring:
    def test_label_follows_url_field_and_video_info(self, qapp, english, tmp_path):
        from unittest.mock import patch

        from src.backend.config_manager import ConfigManager
        from src.backend.queue_manager import QueueManager
        from src.models.video_info import VideoInfo
        from src.ui.download_tab import DownloadTab

        config_manager = ConfigManager(tmp_path / "config.json")
        config_manager.load_config()
        with patch.object(DownloadTab, "_auto_detect_clipboard_url"):
            tab = DownloadTab(config_manager, QueueManager())

        assert tab.site_tier_label.isHidden()  # empty URL field
        tab.url_input.setText("https://vimeo.com/123")
        assert tab.site_tier_label.text() == "Experimental site: may not work"
        tab.url_input.setText("https://youtu.be/abc")
        assert tab.site_tier_label.text() == "Tested site"

        # The page URL from yt-dlp updates the label (no dialog in the test).
        tab.url_input.setText("https://short.example/abc")
        with patch("src.ui.download_tab.VideoInfoDialog"):
            tab._on_info_fetched(VideoInfo(title="t", url="https://www.youtube.com/watch?v=abc"))
        assert tab.site_tier_label.property("siteTier") == "tested"
