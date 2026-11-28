"""Tests for the links to the online guide (F1, Help buttons)."""

import pytest
from PySide6.QtWidgets import QMessageBox, QPushButton

from src.ui import help_links
from src.ui.advanced_download_options import AdvancedDownloadOptions
from src.ui.error_dialog import build_download_error_dialog
from src.ui.help_links import TAB_ANCHORS, anchor_for_tab, guide_url, make_help_button, open_guide
from src.utils.constants import APP_GUIDE_URL


@pytest.fixture
def opened(monkeypatch):
    urls: list[str] = []
    monkeypatch.setattr(help_links.QDesktopServices, "openUrl", lambda url: urls.append(url.toString()) or True)
    return urls


class TestGuideUrl:
    def test_base_url_is_https(self):
        assert APP_GUIDE_URL.startswith("https://")

    def test_no_anchor_is_the_guide_top(self):
        assert guide_url() == APP_GUIDE_URL

    def test_anchor_is_added(self):
        assert guide_url("queue") == f"{APP_GUIDE_URL}#queue"


class TestTabAnchors:
    @pytest.mark.parametrize(
        ("tab", "anchor"),
        [("download", "download"), ("queue", "queue"), ("history", "history"), ("settings", "settings"), ("about", "")],
    )
    def test_each_tab_has_its_anchor(self, tab, anchor):
        assert anchor_for_tab(tab) == anchor

    def test_unknown_tab_gives_the_top(self):
        assert anchor_for_tab("nope") == ""

    def test_every_tab_is_mapped(self):
        assert set(TAB_ANCHORS) == {"download", "queue", "history", "settings", "about"}


class TestOpenGuide:
    def test_opens_the_url(self, opened):
        assert open_guide("history") is True
        assert opened == [guide_url("history")]

    def test_refuses_a_link_that_is_not_https(self, opened, monkeypatch):
        monkeypatch.setattr(help_links, "APP_GUIDE_URL", "http://example.com/guide.html")
        assert open_guide("x") is False
        assert opened == []

    def test_reports_a_failed_open(self, monkeypatch):
        monkeypatch.setattr(help_links.QDesktopServices, "openUrl", lambda url: False)
        assert open_guide() is False


class TestHelpButtons:
    def test_button_opens_its_anchor(self, qtbot, opened):
        button = make_help_button("cookies")
        qtbot.addWidget(button)
        assert button.property("buttonStyle") == "link"
        button.click()
        assert opened == [guide_url("cookies")]

    def test_advanced_options_help_opens_advanced_options(self, qtbot, opened):
        widget = AdvancedDownloadOptions()
        qtbot.addWidget(widget)
        buttons = [b for b in widget.findChildren(QPushButton) if b.property("buttonStyle") == "link"]
        assert len(buttons) == 1
        buttons[0].click()
        assert opened == [guide_url("advanced-options")]

    def test_error_dialog_help_opens_download_failed_and_stays_open(self, qtbot, opened):
        box = build_download_error_dialog(None, "boom")
        qtbot.addWidget(box)
        help_button = next(b for b in box.buttons() if box.buttonRole(b) == QMessageBox.ButtonRole.HelpRole)
        box.show()
        help_button.click()
        assert opened == [guide_url("download-failed")]
        assert box.isVisible()
