"""Check that the vendored yt-dlp can still read the officially tested sites.

YouTube is the only officially tested site (see README.md). This script
calls the vendored yt-dlp through the app's own code paths, with no
download:

1. ``ensure_deno_installed()`` gets Deno the way a source run does (the
   pinned version, checked by SHA-256). yt-dlp needs Deno to solve
   YouTube's JavaScript challenges.
2. ``YtDlpWrapper.get_video_info()`` reads one public video. It must
   return at least one real format (storyboard images do not count).
3. ``PlaylistFetcher.fetch_playlist_info()`` reads one public playlist.
   It must return at least ``MIN_PLAYLIST_ENTRIES`` entries.

YouTube sometimes answers a cloud IP address (such as a GitHub runner)
with "Sign in to confirm you're not a bot". That says nothing about the
engine, so such a check is "blocked" (inconclusive), not failed.

Exit codes:
    0  every check passed
    1  at least one check failed
    2  no check failed, but at least one was blocked by the bot check

A short Markdown report goes to stdout and, with ``--report``, to
``extractor-report.md`` in the current folder. The weekly workflow (.github/workflows/extractor-check.yml)
puts the report in an issue when a check fails.

Run from the project root:

    python scripts/check_extractors.py [--report]

This script needs network access to youtube.com and github.com.
"""

from __future__ import annotations

import argparse
import contextlib
import logging
import sys
import traceback
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# "Me at the zoo", the first video uploaded to YouTube (2005).
VIDEO_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
# "29C3: Not my department", a public playlist of 96 entries that the
# upstream yt-dlp test suite also uses (extractor/youtube/_tab.py).
PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLwP_SiAcdui0KVebT0mU9Apz359a4ubsC"
MIN_PLAYLIST_ENTRIES = 10
REPORT_FILE = "extractor-report.md"

DENO_CHECK = "Deno"
VIDEO_CHECK = "YouTube video"
PLAYLIST_CHECK = "YouTube playlist"

# Stable part of YouTube's "Sign in to confirm you're not a bot" message.
BOT_CHECK_MARKER = "confirm you"
BOT_CHECK_MARKER_2 = "not a bot"
BLOCKED_DETAIL = (
    "YouTube asked this runner to sign in to confirm it is not a bot. "
    "This depends on the runner's IP address, not on the engine, so the result is inconclusive."
)

PASS, FAIL, BLOCKED = "pass", "FAIL", "blocked"


@dataclass
class Result:
    name: str
    url: str
    status: str
    detail: str

    @property
    def ok(self) -> bool:
        return self.status == PASS


def _is_real_format(fmt: dict) -> bool:
    """False for storyboard image formats, which every video has."""
    return fmt.get("ext") != "mhtml" and "storyboard" not in str(fmt.get("format_note", "")).lower()


class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.DEBUG)
        self.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(self.format(record))


@contextlib.contextmanager
def _captured_app_log() -> Iterator[list[str]]:
    """Collect what the app logger writes, tracebacks included.

    The wrapper and the playlist fetcher return None on an error and log
    the reason. This is how the script learns that reason.
    """
    from src.utils.logger import get_logger

    app_logger = get_logger()
    handler = _ListHandler()
    app_logger.addHandler(handler)
    try:
        yield handler.lines
    finally:
        app_logger.removeHandler(handler)


def _is_bot_check(log_lines: list[str]) -> bool:
    text = "\n".join(log_lines)
    return BOT_CHECK_MARKER in text and BOT_CHECK_MARKER_2 in text


def _extraction_failed(name: str, url: str, log_lines: list[str]) -> Result:
    if _is_bot_check(log_lines):
        return Result(name, url, BLOCKED, BLOCKED_DETAIL)
    return Result(name, url, FAIL, "Extraction failed. See the log above.")


def check_deno() -> Result:
    from src.backend.yt_dlp_wrapper import YtDlpWrapper
    from src.utils.deno_installer import DENO_VERSION, ensure_deno_installed

    ensure_deno_installed()
    YtDlpWrapper.reset_deno_cache()
    path = YtDlpWrapper()._get_deno_location()
    if path is None:
        return Result(DENO_CHECK, "-", FAIL, f"Deno {DENO_VERSION} was not found and the download failed.")
    return Result(DENO_CHECK, "-", PASS, f"Deno found at {path}")


def check_video(url: str) -> Result:
    from src.backend.yt_dlp_wrapper import YtDlpWrapper

    name = VIDEO_CHECK
    with _captured_app_log() as log_lines:
        info = YtDlpWrapper().get_video_info(url)
    if info is None:
        return _extraction_failed(name, url, log_lines)
    real = [f for f in info.formats if _is_real_format(f)]
    if not real:
        return Result(name, url, FAIL, f"Extraction returned no real formats ({len(info.formats)} formats in total).")
    video = sum(1 for f in real if f.get("vcodec") not in (None, "none"))
    audio = sum(1 for f in real if f.get("acodec") not in (None, "none"))
    return Result(name, url, PASS, f"'{info.title}': {len(real)} formats ({video} with video, {audio} with audio).")


def check_playlist(url: str) -> Result:
    from src.backend.playlist_fetcher import PlaylistFetcher

    name = PLAYLIST_CHECK
    with _captured_app_log() as log_lines:
        info = PlaylistFetcher.fetch_playlist_info(url)
    if info is None:
        return _extraction_failed(name, url, log_lines)
    count = len(info.videos)
    if count < MIN_PLAYLIST_ENTRIES:
        return Result(name, url, FAIL, f"'{info.title}': {count} entries, expected at least {MIN_PLAYLIST_ENTRIES}.")
    return Result(name, url, PASS, f"'{info.title}': {count} entries.")


def _run(name: str, url: str, func) -> Result:
    try:
        return func()
    except Exception:  # noqa: BLE001 - every failure must end up in the report
        return Result(name, url, FAIL, "Unexpected error:\n" + traceback.format_exc())


def render(results: list[Result], engine_version: str) -> str:
    lines = [
        f"Vendored yt-dlp engine: `{engine_version}`",
        "",
        "| Check | Result | Details |",
        "| --- | --- | --- |",
    ]
    for r in results:
        detail = r.detail.strip().splitlines()[0] if r.detail.strip() else ""
        target = r.name if r.url == "-" else f"{r.name} ({r.url})"
        lines.append(f"| {target} | {r.status} | {detail.replace('|', '/')} |")
    for r in results:
        if r.status == FAIL and "\n" in r.detail.strip():
            lines += [
                "",
                f"<details><summary>{r.name} traceback</summary>",
                "",
                "```",
                r.detail.strip(),
                "```",
                "",
                "</details>",
            ]
    return "\n".join(lines) + "\n"


def exit_code(results: list[Result]) -> int:
    if any(r.status == FAIL for r in results):
        return 1
    if any(r.status == BLOCKED for r in results):
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--report", action="store_true", help=f"also write the Markdown report to {REPORT_FILE}")
    args = parser.parse_args(argv)

    results = [_run(DENO_CHECK, "-", check_deno)]
    results.append(_run(VIDEO_CHECK, VIDEO_URL, lambda: check_video(VIDEO_URL)))
    results.append(_run(PLAYLIST_CHECK, PLAYLIST_URL, lambda: check_playlist(PLAYLIST_URL)))

    try:
        from src.backend.yt_dlp_wrapper import YtDlpWrapper

        engine_version = YtDlpWrapper.get_ytdlp_version()
    except Exception:  # noqa: BLE001
        engine_version = "unknown"

    report = render(results, engine_version)
    print(report)
    if args.report:
        Path(REPORT_FILE).write_text(report, encoding="utf-8")

    return exit_code(results)


if __name__ == "__main__":
    sys.exit(main())
