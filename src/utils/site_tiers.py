"""
Site tiers: which sites YT-DLP Studio tests.

- **Tested:** the sites checked before every release (YouTube, Instagram,
  TikTok, Facebook, X). Only YouTube is also checked every week in CI
  (``.github/workflows/extractor-check.yml``); the others are checked by
  hand before each release.
- **Experimental:** every other http or https URL. yt-dlp supports more than
  1000 sites, but YT-DLP Studio does not test them. Downloads are allowed.
- **Invalid:** not an http or https URL with a host name.

The tier comes from the host name of the parsed URL, with exact matches
only: ``myyoutube.example`` and ``youtube.com.example.net`` are not YouTube.
"""

from enum import Enum
from urllib.parse import urlsplit


class SiteTier(Enum):
    """How well a site is tested."""

    TESTED = "tested"
    EXPERIMENTAL = "experimental"
    INVALID = "invalid"


# Exact host names of the tested sites, by site name. Add the "www." form
# explicitly: there is no subdomain matching.
TESTED_SITES: dict[str, frozenset[str]] = {
    "YouTube": frozenset(
        {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"},
    ),
    "Instagram": frozenset({"instagram.com", "www.instagram.com"}),
    "TikTok": frozenset({"tiktok.com", "www.tiktok.com", "vm.tiktok.com"}),
    "Facebook": frozenset({"facebook.com", "www.facebook.com", "m.facebook.com", "fb.watch"}),
    "X": frozenset({"x.com", "www.x.com", "twitter.com", "www.twitter.com", "mobile.twitter.com"}),
}

_HOST_TO_SITE = {host: site for site, hosts in TESTED_SITES.items() for host in hosts}

_SCHEMES = ("http", "https")


def _host_of(url: str) -> str | None:
    """Return the lower-case host name of an http(s) URL, or None if there is none."""
    if not isinstance(url, str):
        return None
    try:
        parts = urlsplit(url.strip())
        host = parts.hostname  # lower case, without user info and port
        _ = parts.port  # raises ValueError for a port that is not a number
    except ValueError:
        return None
    if parts.scheme.lower() not in _SCHEMES or not host:
        return None
    # Browsers read "\" as "/", so in "https://other.example\@youtube.com" the
    # real host is other.example, but urlsplit says youtube.com. Refuse it.
    if "\\" in parts.netloc:
        return None
    # "youtube.com." (fully qualified) is the same host as "youtube.com".
    return host[:-1] if host.endswith(".") else host


def tested_site_name(url: str) -> str | None:
    """
    Return the name of the tested site for a URL.

    Returns:
        "YouTube", "Instagram", "TikTok", "Facebook" or "X", or None if the
        URL is not on a tested site
    """
    host = _host_of(url)
    return _HOST_TO_SITE.get(host) if host else None


def classify_url(url: str) -> SiteTier:
    """
    Return the site tier of a URL.

    Args:
        url: URL as the user entered it (surrounding spaces are ignored).
            A URL without ``http://`` or ``https://`` is invalid, the same
            as for the download itself.

    Returns:
        SiteTier.TESTED, SiteTier.EXPERIMENTAL or SiteTier.INVALID
    """
    host = _host_of(url)
    if host is None:
        return SiteTier.INVALID
    return SiteTier.TESTED if host in _HOST_TO_SITE else SiteTier.EXPERIMENTAL
