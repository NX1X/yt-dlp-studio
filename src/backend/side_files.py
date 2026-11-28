"""
Readable side files for a finished download.

When metadata or comments are on, yt-dlp writes a ``.info.json`` file next to
the video. These helpers turn it into text files people can read:

- metadata: ``<base>_metadata.txt``, the ``.description`` file renamed to
  ``<base>_description.txt``, and the JSON rewritten with indentation;
- comments: ``<base> Comments.txt``. The JSON is removed again if metadata
  is off.

``<base>`` is the JSON path without ``.info.json``, the same base yt-dlp
uses for the video and its ``.description`` file. So ``name.info.json`` gives
``name_metadata.txt``, ``name Comments.txt`` and ``name_description.txt``.
Up to 0.4.1 the base kept ``.info`` (``name.info_metadata.txt``), so the
description file was never found and never renamed.

The JSON of each item comes from the paths that yt-dlp reports in the info
dict, never from a look at the folder, so two downloads that run at once in
one folder cannot take each other's files. A post with several videos is a
playlist result, and each item gets its own set of files.

A failure here is logged and never fails the download.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from datetime import datetime
from typing import IO, Any

from ..utils.logger import get_logger

logger = get_logger()

_RULE = "=" * 80
_INFO_JSON_SUFFIX = ".info.json"


def iter_downloads(info_dict: dict[str, Any] | None) -> Iterator[dict[str, Any]]:
    """Yield each ``requested_downloads`` item of a result, entries included.

    A single video keeps ``requested_downloads`` at the top. A post with
    several videos is a playlist result that keeps it in each entry (and an
    entry may itself be a playlist).
    """
    if not isinstance(info_dict, dict):
        return
    for download in info_dict.get("requested_downloads") or []:
        if isinstance(download, dict):
            yield download
    for entry in info_dict.get("entries") or []:
        yield from iter_downloads(entry)


def info_json_paths(info_dict: dict[str, Any] | None) -> list[str]:
    """Return the info JSON paths of the downloads, in order, without repeats.

    Uses ``infojson_filename``, which yt-dlp sets when it writes the file.
    Without it, the path comes from the video file name (same base, extension
    ``.info.json``). Only paths of files that exist are returned.
    """
    found: dict[str, None] = {}
    for download in iter_downloads(info_dict):
        path = download.get("infojson_filename")
        if not path:
            filepath = download.get("filepath")
            path = os.path.splitext(filepath)[0] + _INFO_JSON_SUFFIX if filepath else None
        if path and os.path.exists(path):
            found[path] = None
    return list(found)


def write_side_files(
    info_dict: dict[str, Any] | None,
    *,
    metadata: bool,
    comments: bool,
    post_json: str | None = None,
) -> None:
    """Write the readable metadata and comments files that are switched on.

    Args:
        info_dict: The result of ``extract_info``.
        metadata: Write the metadata files.
        comments: Write the comments files.
        post_json: Path of the JSON that yt-dlp writes for the whole post
            when the result is a playlist, or None. With metadata on, its
            description is handled like an item's. With metadata off, the
            file is removed.
    """
    if not info_dict or not (metadata or comments):
        return
    for json_file in info_json_paths(info_dict):
        if metadata:
            _safely(write_metadata_files, json_file, message="Error post-processing metadata files")
        if comments:
            _safely(write_comments_file, json_file, not metadata, message="Error extracting comments to TXT")
    if post_json and os.path.exists(post_json):
        _safely(_finish_post_json, post_json, metadata, message="Error post-processing the post JSON file")


def _safely(func, *args, message: str) -> None:
    try:
        func(*args)
    except Exception:
        logger.exception(message)


def _finish_post_json(json_file: str, keep: bool) -> None:
    """Tidy the JSON of a whole post: keep it with metadata, else remove it."""
    if keep:
        _rename_description(_base_of(json_file))
        return
    os.remove(json_file)
    logger.info("✓ Cleaned up temporary JSON file of the post")


def _base_of(json_file: str) -> str:
    """The download's base path: ``name.info.json`` gives ``name``."""
    if json_file.endswith(_INFO_JSON_SUFFIX):
        return json_file[: -len(_INFO_JSON_SUFFIX)]
    return os.path.splitext(json_file)[0]


def _read_json(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------- metadata ----------


def write_metadata_files(json_file: str) -> None:
    """Write ``_metadata.txt``, rename the description, indent the JSON."""
    base_filename = _base_of(json_file)
    logger.info(f"Post-processing metadata files for: {os.path.basename(base_filename)}")

    data = _read_json(json_file)

    metadata_txt = f"{base_filename}_metadata.txt"
    with open(metadata_txt, "w", encoding="utf-8") as f:
        _write_metadata_text(f, data)
    logger.info(f"✓ Created human-readable metadata: {os.path.basename(metadata_txt)}")

    _rename_description(base_filename)

    # Keep the JSON for technical users, but make it readable.
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info("✓ Formatted JSON file with 2-space indentation")


def _rename_description(base_filename: str) -> None:
    """Rename ``.description`` to ``_description.txt``, or remove it if empty."""
    desc_file = f"{base_filename}.description"
    if not os.path.exists(desc_file):
        return
    with open(desc_file, encoding="utf-8", errors="replace") as f:
        has_text = bool(f.read().strip())
    if not has_text:
        # yt-dlp writes an empty file for an empty description.
        os.remove(desc_file)
        logger.info("✓ Removed the empty description file")
        return
    # Rename .description to .txt for better Windows compatibility.
    desc_txt_file = f"{base_filename}_description.txt"
    os.replace(desc_file, desc_txt_file)
    logger.info(f"✓ Renamed description file to: {os.path.basename(desc_txt_file)}")


def _write_metadata_text(f: IO[str], data: dict[str, Any]) -> None:
    f.write(f"{_RULE}\nVIDEO METADATA\n{_RULE}\n\n")
    _write_essentials(f, data)
    _write_upload_date(f, data.get("upload_date", ""))
    _write_duration(f, data.get("duration", 0))
    _write_statistics(f, data)
    _write_quality(f, data)
    _write_categories_and_tags(f, data)
    thumbnail = data.get("thumbnail", "")
    if thumbnail:
        f.write(f"[THUMBNAIL URL]\n{thumbnail}\n\n")
    f.write(f"{_RULE}\nEnd of Metadata\n{_RULE}\n")


def _write_essentials(f: IO[str], data: dict[str, Any]) -> None:
    f.write("[ESSENTIAL INFORMATION]\n")
    f.write(f"Title: {data.get('title', 'N/A')}\n")
    f.write(f"Uploader: {data.get('uploader', 'N/A')}\n")
    f.write(f"Channel: {data.get('channel', 'N/A')}\n")
    f.write(f"Channel ID: {data.get('channel_id', 'N/A')}\n")
    f.write(f"Video ID: {data.get('id', 'N/A')}\n")
    f.write(f"URL: {data.get('webpage_url', 'N/A')}\n\n")


def _write_upload_date(f: IO[str], upload_date: str) -> None:
    if not upload_date or len(upload_date) != 8:
        return
    try:
        formatted_date = datetime.strptime(upload_date, "%Y%m%d").strftime("%B %d, %Y")
        f.write(f"[UPLOAD DATE]\n{formatted_date}\n\n")
    except Exception:
        f.write(f"[UPLOAD DATE]\n{upload_date}\n\n")


def _write_duration(f: IO[str], duration: Any) -> None:
    if not duration:
        return
    minutes, seconds = divmod(int(duration), 60)
    hours, minutes = divmod(minutes, 60)
    duration_str = f"{hours}h {minutes}m {seconds}s" if hours > 0 else f"{minutes}m {seconds}s"
    f.write(f"[DURATION]\n{duration_str}\n\n")


def _write_statistics(f: IO[str], data: dict[str, Any]) -> None:
    f.write("[STATISTICS]\n")
    for label, key in (("Views", "view_count"), ("Likes", "like_count"), ("Comments", "comment_count")):
        value = data.get(key, 0)
        if value:
            f.write(f"{label}: {value:,}\n")
    f.write("\n")


def _write_quality(f: IO[str], data: dict[str, Any]) -> None:
    f.write("[VIDEO QUALITY]\n")
    f.write(f"Resolution: {data.get('width', 'N/A')}x{data.get('height', 'N/A')}\n")
    f.write(f"FPS: {data.get('fps', 'N/A')}\n")
    f.write(f"Format: {data.get('format', 'N/A')}\n")
    f.write(f"Video Codec: {data.get('vcodec', 'N/A')}\n")
    f.write(f"Audio Codec: {data.get('acodec', 'N/A')}\n\n")


def _write_categories_and_tags(f: IO[str], data: dict[str, Any]) -> None:
    categories = data.get("categories", [])
    if categories:
        f.write("[CATEGORIES]\n")
        f.write(", ".join(categories) + "\n\n")
    tags = data.get("tags", [])
    if tags:
        f.write("[TAGS]\n")
        # Four tags per line for readability
        for i in range(0, len(tags), 4):
            f.write(", ".join(tags[i : i + 4]) + "\n")
        f.write("\n")


# ---------- comments ----------


def write_comments_file(json_file: str, remove_json: bool) -> None:
    """Write ``<base> Comments.txt`` from the info JSON. Remove the JSON if asked."""
    logger.info("Post-processing comments to .txt file...")
    logger.info(f"Found JSON file: {os.path.basename(json_file)}")
    base_filename = _base_of(json_file)

    data = _read_json(json_file)
    comments_list = data.get("comments") or []
    expected = _comment_total(data)
    # X, Facebook and TikTok have no comment support in yt-dlp: the field is
    # missing, although some of them know the count.
    provided = data.get("comments") is not None
    logger.info(f"Found {len(comments_list)} comments in JSON file")
    if not comments_list:
        logger.warning(f"⚠ {_no_comments_reason(provided, expected)}")
    else:
        comments_txt = f"{base_filename} Comments.txt"
        with open(comments_txt, "w", encoding="utf-8") as f:
            _write_comments_header(f, data, len(comments_list), expected)
            for i, comment in enumerate(comments_list, 1):
                _write_comment(f, i, comment)
        logger.info(f"✓ Comments saved to: {os.path.basename(comments_txt)} ({len(comments_list):,} comments)")

    # With comments only, the JSON is a temporary file. It goes also when
    # there were no comments to write.
    if remove_json:
        try:
            os.remove(json_file)
            logger.info("✓ Cleaned up temporary JSON file")
        except OSError as cleanup_error:
            logger.debug(f"Could not remove temporary JSON file: {cleanup_error}")


def _comment_total(data: dict[str, Any]) -> int | None:
    """The number of comments the post has, or None if the site gave no count."""
    value = data.get("comment_count")
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _no_comments_reason(provided: bool, expected: int | None) -> str:
    """Log text for a post that gave no comments.

    ``provided`` is False if the site gave no comments field at all.
    """
    if not provided:
        return "This site does not provide comments for this post"
    if not expected:
        return "No comments found: the post has none, or comments are turned off"
    return f"The site returned none of the {int(expected):,} comments of this post"


def _write_comments_header(f: IO[str], data: dict[str, Any], count: int, expected: int | None) -> None:
    f.write(f"{_RULE}\nVIDEO COMMENTS\n{_RULE}\n\n")
    f.write(f"Video Title: {data.get('title', 'N/A')}\n")
    if expected is not None and expected > count:
        # Instagram without a login returns about a dozen of the comments.
        f.write(f"Total Comments: {count:,} of {expected:,}\n")
        f.write(f"Note: this file holds only the comments the site returned ({count:,} of {expected:,}).\n")
    else:
        f.write(f"Total Comments: {count:,}\n")
    f.write(f"{_RULE}\n\n")


def _comment_time(timestamp: Any) -> str:
    """Local date and time of a comment, or "" without a timestamp."""
    if not timestamp:
        return ""
    try:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(timestamp)


def _write_comment(f: IO[str], number: int, comment: dict[str, Any]) -> None:
    time_str = _comment_time(comment.get("timestamp", 0))
    likes = comment.get("like_count") or 0
    f.write(f"[Comment #{number}]\n")
    f.write(f"Author: {comment.get('author', 'Unknown')}\n")
    if time_str:
        f.write(f"Date: {time_str}\n")
    if likes > 0:
        f.write(f"Likes: {likes:,}\n")
    f.write(f"\n{comment.get('text', '')}\n")
    f.write("-" * 80 + "\n\n")
