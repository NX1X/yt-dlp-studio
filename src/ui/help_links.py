"""
Links to the online guide (https://studio.nx1xlab.dev/guide.html).

F1 opens the guide at the section of the current tab. The "Help" links in
the About tab, the Advanced Download Options and the download error dialog
open one anchor each. Only https links are opened, with ``QDesktopServices``.
"""

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QPushButton

from ..utils.constants import APP_GUIDE_URL
from ..utils.logger import get_logger
from ..utils.translations import tr

logger = get_logger()

# Anchors in the guide page. The empty anchor is the top of the page.
ANCHOR_TOP = ""
ANCHOR_ADVANCED_OPTIONS = "advanced-options"
ANCHOR_DOWNLOAD_FAILED = "download-failed"

# Tab key -> anchor, for F1. The About tab has no section of its own.
TAB_ANCHORS: dict[str, str] = {
    "download": "download",
    "queue": "queue",
    "history": "history",
    "settings": "settings",
    "about": ANCHOR_TOP,
}


def guide_url(anchor: str = ANCHOR_TOP) -> str:
    """The guide URL, with ``#anchor`` when an anchor is given."""
    return f"{APP_GUIDE_URL}#{anchor}" if anchor else APP_GUIDE_URL


def anchor_for_tab(tab_key: str) -> str:
    """The guide anchor for a tab key. An unknown tab gives the top of the guide."""
    return TAB_ANCHORS.get(tab_key, ANCHOR_TOP)


def open_guide(anchor: str = ANCHOR_TOP) -> bool:
    """
    Open the guide in the default browser.

    Returns:
        True if the browser was started
    """
    url = guide_url(anchor)
    if not url.startswith("https://"):
        logger.warning(f"Refused to open a link that is not https: {url}")
        return False
    if not QDesktopServices.openUrl(QUrl(url)):
        logger.warning(f"Could not open the online guide: {url}")
        return False
    return True


def make_help_button(anchor: str) -> QPushButton:
    """A small "Help" link button that opens the guide at ``anchor``."""
    button = QPushButton(tr("button_help"))
    button.setProperty("buttonStyle", "link")
    button.setCursor(Qt.PointingHandCursor)
    button.setToolTip(tr("tooltip_help_guide"))
    button.clicked.connect(lambda: open_guide(anchor))
    return button
