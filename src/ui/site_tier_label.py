"""
Label next to the URL field that shows the site tier.

"Tested site" for the sites checked before every release, "Experimental
site: may not work" for every other http(s) URL, and nothing for an empty or
invalid URL. The label only informs: it never blocks a download.

The colors come from the theme stylesheet (``QLabel#siteTierLabel`` in
src/ui/theme.py), so they follow the dark and light modes.
"""

from PySide6.QtWidgets import QLabel, QWidget

from ..utils.site_tiers import SiteTier, classify_url
from ..utils.translations import tr

# (text key, tooltip key) per visible tier
_TIER_TEXT = {
    SiteTier.TESTED: ("site_tier_tested", "tooltip_site_tier_tested"),
    SiteTier.EXPERIMENTAL: ("site_tier_experimental", "tooltip_site_tier_experimental"),
}


class SiteTierLabel(QLabel):
    """Shows the tier of the site of the current URL."""

    OBJECT_NAME = "siteTierLabel"
    # Dynamic property that the theme stylesheet selects on
    TIER_PROPERTY = "siteTier"

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName(self.OBJECT_NAME)
        self.tier = SiteTier.INVALID
        self.setVisible(False)

    def update_for_url(self, url: str) -> SiteTier:
        """
        Show the tier for ``url``, or hide the label if the URL is invalid.

        Returns:
            The tier that is shown
        """
        tier = classify_url(url)
        self.tier = tier
        keys = _TIER_TEXT.get(tier)
        if keys is None:
            self.clear()
            self.setToolTip("")
            self.setAccessibleName("")
            self.setAccessibleDescription("")
            self.setVisible(False)
            return tier

        text, tooltip = tr(keys[0]), tr(keys[1])
        self.setText(text)
        self.setToolTip(tooltip)
        # Screen readers read the text and the explanation, not only a color.
        self.setAccessibleName(text)
        self.setAccessibleDescription(tooltip)
        if self.property(self.TIER_PROPERTY) != tier.value:
            self.setProperty(self.TIER_PROPERTY, tier.value)
            # Apply the stylesheet rule for the new property value.
            self.style().unpolish(self)
            self.style().polish(self)
        self.setVisible(True)
        return tier
