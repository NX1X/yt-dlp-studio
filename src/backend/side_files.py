"""
Readable side files for a finished download.

When metadata or comments are on, yt-dlp writes a ``.info.json`` file next to
the video. These helpers turn it into text files people can read:

- metadata: ``<base>_metadata.txt``, the ``.description`` file renamed to
  ``<base>_description.txt``, and the JSON rewritten with indentation;
- comments: ``<base> Comments.txt``. The JSON is removed again if metadata
  is off.

``<base>`` is the JSON path without its last extension, so it ends in
``.info`` (``name.info_metadata.txt``). That is how it has always worked; the
description file is therefore only renamed if ``name.info.description``
exists.

A failure here is logged and never fails the download.
"""

from __future__ import annotations

import glob
import json
import os
import time
from datetime import datetime
from typing import IO, Any

from ..utils.logger import get_logger

logger = get_logger()

_RULE = "=" * 80
# How recent an .info.json must be to belong to this download, in seconds.
_METADATA_MAX_AGE = 60
_COMMENTS_MAX_AGE = 120


def write_side_files(output_dir: str, info_dict: dict[str, Any] | None, *, metadata: bool, comments: bool) -> None:
    """Write the readable metadata and comments files that are switched on."""
    if metadata and info_dict:
        _safely(write_metadata_files, output_dir, message="Error post-processing metadata files")
    if comments and info_dict:
        _safely(write_comments_file, output_dir, not metadata, message="Error extracting comments to TXT")


def _safely(func, *args, message: str) -> None:
    try:
        func(*args)
    except Exception:
        logger.exception(message)


def _newest_info_json(output_dir: str, max_age: float) -> str | None:
    """Return the newest ``*.info.json`` changed in the last ``max_age`` seconds."""
    json_files = glob.glob(os.path.join(output_dir, "*.info.json"))
    recent = [f for f in json_files if time.time() - os.path.getmtime(f) < max_age]
    return max(recent, key=os.path.getmtime) if recent else None


def _read_json(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------- metadata ----------


def write_metadata_files(output_dir: str) -> None:
    """Write ``_metadata.txt``, rename the description, indent the JSON."""
    json_file = _newest_info_json(output_dir, _METADATA_MAX_AGE)
    if not json_file:
        logger.warning("Could not find recently created JSON metadata file")
        return
    base_filename = os.path.splitext(json_file)[0]
    logger.info(f"Post-processing metadata files for: {os.path.basename(base_filename)}")

    data = _read_json(json_file)

    metadata_txt = f"{base_filename}_metadata.txt"
    with open(metadata_txt, "w", encoding="utf-8") as f:
        _write_metadata_text(f, data)
    logger.info(f"✓ Created human-readable metadata: {os.path.basename(metadata_txt)}")

    # Rename .description to .txt for better Windows compatibility.
    desc_file = f"{base_filename}.description"
    desc_txt_file = f"{base_filename}_description.txt"
    if os.path.exists(desc_file):
        os.rename(desc_file, desc_txt_file)
        logger.info(f"✓ Renamed description file to: {os.path.basename(desc_txt_file)}")

    # Keep the JSON for technical users, but make it readable.
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info("✓ Formatted JSON file with 2-space indentation")


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


def write_comments_file(output_dir: str, remove_json: bool) -> None:
    """Write ``<base> Comments.txt`` from the info JSON. Remove the JSON if asked."""
    logger.info("Post-processing comments to .txt file...")
    # Give yt-dlp a moment to finish writing the JSON file.
    time.sleep(1)

    json_file = _newest_info_json(output_dir, _COMMENTS_MAX_AGE)
    if not json_file:
        logger.warning("Could not find recently created JSON file for comments")
        return
    logger.info(f"Found JSON file: {os.path.basename(json_file)}")
    base_filename = os.path.splitext(json_file)[0]

    data = _read_json(json_file)
    comments_list = data.get("comments", [])
    logger.info(f"Found {len(comments_list)} comments in JSON file")
    if not comments_list:
        logger.warning("⚠ No comments found in video (comments may be disabled)")
        return

    comments_txt = f"{base_filename} Comments.txt"
    with open(comments_txt, "w", encoding="utf-8") as f:
        f.write(f"{_RULE}\nVIDEO COMMENTS\n{_RULE}\n\n")
        f.write(f"Video Title: {data.get('title', 'N/A')}\n")
        f.write(f"Total Comments: {len(comments_list):,}\n")
        f.write(f"{_RULE}\n\n")
        for i, comment in enumerate(comments_list, 1):
            _write_comment(f, i, comment)
    logger.info(f"✓ Comments saved to: {os.path.basename(comments_txt)} ({len(comments_list):,} comments)")

    if remove_json:
        try:
            os.remove(json_file)
            logger.info("✓ Cleaned up temporary JSON file")
        except OSError as cleanup_error:
            logger.debug(f"Could not remove temporary JSON file: {cleanup_error}")


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
    likes = comment.get("like_count", 0)
    f.write(f"[Comment #{number}]\n")
    f.write(f"Author: {comment.get('author', 'Unknown')}\n")
    if time_str:
        f.write(f"Date: {time_str}\n")
    if likes > 0:
        f.write(f"Likes: {likes:,}\n")
    f.write(f"\n{comment.get('text', '')}\n")
    f.write("-" * 80 + "\n\n")
