"""
Photo posts: image-only posts and the photo items of a carousel.

yt-dlp has no download for a post item that holds a photo. For such an item
the extractor gives no formats, only ``thumbnails`` (Instagram: 13 sizes of
the photo; the X extractor of this app does the same, see
``backend/twitter_photos.py``). The app turns the item into a plain file
download of the largest image, so yt-dlp's own downloader does the work and
the proxy, the cookies and the request headers apply as for a video.

This module is pure Python (no yt-dlp import), so the models, the side files
and the options can use it.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import unquote, urlsplit

# Sites whose photo posts download. Other sites keep the plain behavior.
PHOTO_HOSTS = ("instagram.com", "instagr.am", "twitter.com", "x.com")
# The part of the PHOTO_HOSTS that needs the X photo extractor.
TWITTER_HOSTS = ("twitter.com", "x.com")

# Marks an item that the app turned into an image download. Set in
# ``image_item_update`` and read by the post-processor skips, the file name
# and the metadata text.
IMAGE_FORMAT_ID = "photo"

# Extensions kept for a photo. Anything else is saved as .jpg.
IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "webp", "gif", "heic", "avif")
DEFAULT_IMAGE_EXTENSION = "jpg"


def host_matches(url: str, hosts: tuple[str, ...]) -> bool:
    """True if the host of ``url`` is one of ``hosts`` or a subdomain of one."""
    try:
        host = (urlsplit(url).hostname or "").lower()
    except ValueError:
        return False
    return any(host == h or host.endswith("." + h) for h in hosts)


def supports_photo_posts(url: str) -> bool:
    """True if photo posts of the site of ``url`` download."""
    return host_matches(url, PHOTO_HOSTS)


def needs_twitter_photos(url: str) -> bool:
    """True if ``url`` is on X and needs the extractor that reads photos."""
    return host_matches(url, TWITTER_HOSTS)


def is_image_item(info: dict[str, Any] | None) -> bool:
    """True if the item was turned into an image download."""
    return isinstance(info, dict) and info.get("format_id") == IMAGE_FORMAT_ID


# A size in an image URL: "s640x640" or "p1080x1350" after "_", "/" or "=".
_URL_SIZE = re.compile(r"(?<![A-Za-z0-9])[sp](\d{2,5})x(\d{2,5})(?!\d)")
# An image URL with no size at all is the unscaled original (Instagram). It
# ranks above every sized one.
_UNSCALED = 1 << 60


def _number(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _thumbnail_area(thumbnail: dict[str, Any]) -> int:
    """Pixel count of a thumbnail: its width and height, else the size in its URL.

    Instagram gives no width or height in the engine's result. The size is
    in the URL (``..._s640x640_...``), and the unscaled original has none.
    """
    area = _number(thumbnail.get("width")) * _number(thumbnail.get("height"))
    if area:
        return area
    match = _URL_SIZE.search(unquote(thumbnail.get("url") or ""))
    if match:
        return int(match.group(1)) * int(match.group(2))
    return _UNSCALED


def _thumbnail_size(thumbnail: dict[str, Any]) -> tuple[int, int]:
    return _number(thumbnail.get("preference")), _thumbnail_area(thumbnail)


def best_image(info: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return the largest thumbnail with a URL, or None.

    The order of the list is not trusted: yt-dlp sorts thumbnails without a
    size by URL text. Of equal ones, the first in the list wins.
    """
    if not isinstance(info, dict):
        return None
    candidates = [t for t in info.get("thumbnails") or [] if isinstance(t, dict) and t.get("url")]
    if not candidates:
        return None
    return max(candidates, key=_thumbnail_size)


def looks_like_image_item(info: dict[str, Any] | None) -> bool:
    """True if an item has no video to download but has an image.

    That is the shape of a photo item: no formats, no direct URL, and
    thumbnails. Items that were already turned into an image count too.
    """
    if not isinstance(info, dict):
        return False
    if is_image_item(info):
        return True
    if info.get("formats") or info.get("url") or info.get("entries"):
        return False
    return best_image(info) is not None


def is_photo_post(info: dict[str, Any] | None) -> bool:
    """True if a result (an item, or a post with items) holds only photos."""
    if not isinstance(info, dict):
        return False
    entries = [e for e in info.get("entries") or [] if isinstance(e, dict)]
    if entries:
        return all(is_photo_post(e) for e in entries)
    return looks_like_image_item(info)


def image_extension(url: str) -> str:
    """The extension of an image URL (query ignored), or ``jpg``."""
    path = urlsplit(url).path
    ext = path.rpartition(".")[2].lower() if "." in path.rpartition("/")[2] else ""
    return ext if ext in IMAGE_EXTENSIONS else DEFAULT_IMAGE_EXTENSION


def image_item_update(info: dict[str, Any]) -> dict[str, Any] | None:
    """Return the fields that turn a photo item into a plain image download.

    Args:
        info: The item as yt-dlp holds it just before the download.

    Returns:
        The fields to merge into ``info``, or None if the item is not a photo
        item (or was turned already).
    """
    if is_image_item(info) or not looks_like_image_item(info):
        return None
    best = best_image(info)
    if best is None:
        return None
    url = best["url"]
    update: dict[str, Any] = {
        "url": url,
        "ext": image_extension(url),
        "protocol": "https",
        "format_id": IMAGE_FORMAT_ID,
        "format": IMAGE_FORMAT_ID,
        "vcodec": "none",
        "acodec": "none",
        # The image is the file itself, so no extra thumbnail is written.
        "thumbnail": url,
        "thumbnails": [],
    }
    if _number(best.get("width")) and _number(best.get("height")):
        update["width"] = best["width"]
        update["height"] = best["height"]
    title = info.get("title")
    if isinstance(title, str) and title.startswith("Video by "):
        # Instagram names every item "Video by <user>", also a photo.
        update["title"] = "Photo by " + title[len("Video by ") :]
    headers = {**(info.get("http_headers") or {}), **(best.get("http_headers") or {})}
    if headers:
        update["http_headers"] = headers
    return update
