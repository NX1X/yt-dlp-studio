"""
Photos of an X post.

yt-dlp's X extractor (``TwitterIE``) drops every media item of type
``photo``, so a post with photos only fails with "No video could be found in
this tweet", and the photos of a mixed post are lost. ``make_twitter_photo_ie``
builds a subclass with the same ``ie_key`` that adds one entry per photo. Each
entry has the photo as ``thumbnails`` and no formats, the same shape as a
photo item of an Instagram carousel, so one code path downloads both (see
``utils/photo_posts.py``).

The subclass depends on one private method of the engine, ``_extract_status``
(the status JSON of the post), and on the shape of that JSON. A fixture test
(``tests/test_photo_posts.py``) runs it on a recorded status, so an engine
update that changes the shape fails the test loudly.

The engine is imported inside the function: only ``yt_dlp_wrapper`` puts the
vendored engine on ``sys.path``, and it does that before it calls this.
"""

from __future__ import annotations

import re
from typing import Any

_ie_class: type | None = None


def make_twitter_photo_ie() -> type:
    """Return the ``TwitterIE`` subclass that also reads photos (built once)."""
    global _ie_class
    if _ie_class is None:
        _ie_class = _build_ie_class()
    return _ie_class


def _build_ie_class() -> type:
    from yt_dlp.extractor.twitter import TwitterIE
    from yt_dlp.utils import (
        ExtractorError,
        format_field,
        int_or_none,
        str_or_none,
        traverse_obj,
        truncate_string,
        unified_timestamp,
        update_url_query,
    )

    class TwitterPhotoIE(TwitterIE):
        """``TwitterIE`` that adds the photos of a post as image entries."""

        # The class name would give another key; the key must stay "Twitter"
        # so this class replaces the engine's one in the YoutubeDL instance.
        @classmethod
        def ie_key(cls) -> str:
            return TwitterIE.ie_key()

        IE_NAME = TwitterIE.IE_NAME

        _status_cache: tuple[str, dict[str, Any]] | None = None

        def _extract_status(self, twid):
            # Read the status once for this class and for the engine's code.
            if self._status_cache and self._status_cache[0] == twid:
                return self._status_cache[1]
            status = super()._extract_status(twid)
            self._status_cache = (twid, status)
            return status

        def _real_extract(self, url):
            twid, selected_index = self._match_valid_url(url).group("id", "index")
            try:
                return self._extract_with_photos(url, twid, selected_index)
            finally:
                self._status_cache = None

        # ----- extraction -----

        def _all_media(self, status):
            return traverse_obj(status, ((None, "quoted_status"), "extended_entities", "media", ..., {dict})) or []

        def _extract_with_photos(self, url, twid, selected_index):
            status = self._extract_status(twid)
            media = self._all_media(status)
            photos = [m for m in media if m.get("type") == "photo"]
            if not photos:
                return super()._real_extract(url)

            info = self._post_info(twid, status)
            if selected_index and not self._yes_playlist(
                twid, selected_index, video_label="URL-specified media number"
            ):
                desired = media[int(selected_index) - 1] if 0 < int(selected_index) <= len(media) else None
                if desired is None:
                    raise ExtractorError(f"Media #{selected_index} is unavailable", expected=True)
                if desired.get("type") == "photo":
                    return self._photo_entry(info, twid, desired)
                return super()._real_extract(url)

            others = [m for m in media if m.get("type") != "photo"]
            base = None
            if others or status.get("card"):
                try:
                    base = super()._real_extract(url)
                except ExtractorError:
                    base = None  # photos only
            entries = self._entries_of(base)
            photo_entries = [self._photo_entry(info, twid, m) for m in photos]
            if not entries and len(photo_entries) == 1:
                return photo_entries[0]
            return self._merge(info, base, entries, photo_entries)

        @staticmethod
        def _entries_of(result):
            if not result:
                return []
            if result.get("_type") == "playlist":
                return list(result.get("entries") or [])
            return [result]

        def _merge(self, info, base, entries, photo_entries):
            if base is not None and base.get("_type") != "playlist" and entries:
                # A single video: number it, as the engine does for several.
                entries[0] = {**entries[0], "title": f"{entries[0].get('title') or info['title']} #1"}
            for number, entry in enumerate(photo_entries, len(entries) + 1):
                entry["title"] = f"{entry['title']} #{number}"
            return self.playlist_result([*entries, *photo_entries], **info)

        def _post_info(self, twid, status):
            """The fields every entry of the post shares (as the engine builds them)."""
            title = description = (
                traverse_obj(status, (("full_text", "text"), {lambda x: x.replace("\n", " ")}), get_all=False) or ""
            )
            title = truncate_string(self._strip_links(title), left=72)
            user = status.get("user") or {}
            uploader = user.get("name")
            if uploader:
                title = f"{uploader} - {title}"
            uploader_id = user.get("screen_name")
            return {
                "id": twid,
                "title": title,
                "description": description,
                "uploader": uploader,
                "timestamp": unified_timestamp(status.get("created_at")),
                "channel_id": str_or_none(status.get("user_id_str")) or str_or_none(user.get("id_str")),
                "uploader_id": uploader_id,
                "uploader_url": format_field(uploader_id, None, "https://twitter.com/%s"),
                "view_count": int_or_none(status.get("view_count")),
                "like_count": int_or_none(status.get("favorite_count")),
                "repost_count": int_or_none(status.get("retweet_count")),
                "comment_count": int_or_none(status.get("reply_count")),
                "age_limit": 18 if status.get("possibly_sensitive") else 0,
                "tags": traverse_obj(status, ("entities", "hashtags", ..., "text")),
            }

        @staticmethod
        def _strip_links(text):
            # Drop 'https://t.co/...' links from file names, as the engine does.
            return re.sub(r"\s+(https?://[^ ]+)", "", text)

        def _photo_entry(self, info, twid, media):
            media_id = traverse_obj(media, "id_str", "id", expected_type=str_or_none) or twid
            media_url = media.get("media_url_https") or media.get("media_url")
            size = media.get("original_info") or {}
            thumbnails = []
            if media_url:
                thumbnails.append(
                    {
                        "id": "orig",
                        "url": update_url_query(media_url, {"name": "orig"}),
                        "width": int_or_none(size.get("width") or size.get("w")),
                        "height": int_or_none(size.get("height") or size.get("h")),
                    }
                )
            return {**info, "id": media_id, "display_id": twid, "formats": [], "thumbnails": thumbnails}

    return TwitterPhotoIE
