"""Check that the vendored yt-dlp can still read the officially tested sites.

YouTube and TikTok are checked (see README.md). This script calls the
vendored yt-dlp through the app's own code paths, with no download.

``--site youtube`` (the default) runs three checks:

1. ``ensure_deno_installed()`` gets Deno the way a source run does (the
   pinned version, checked by SHA-256). yt-dlp needs Deno to solve
   YouTube's JavaScript challenges.
2. ``YtDlpWrapper.get_video_info()`` reads one public video. It must
   return at least one real format (storyboard images do not count).
3. ``PlaylistFetcher.fetch_playlist_info()`` reads one public playlist.
   It must return at least ``MIN_PLAYLIST_ENTRIES`` entries.

``--site tiktok`` reads the info of one public TikTok video (no download).
It runs only on GitHub Actions (``GITHUB_ACTIONS=true``) and refuses to
run anywhere else, so a developer machine never contacts TikTok by
accident. Tests use fakes and send no request.

YouTube sometimes answers a cloud IP address (such as a GitHub runner)
with "Sign in to confirm you're not a bot". TikTok answers with a block
("Your IP address is blocked", login required, HTTP 403 or 429). That
says nothing about the engine, so such a check is "blocked"
(inconclusive), not failed.

Exit codes:
    0  every check passed
    1  at least one check failed
    2  no check failed, but at least one was blocked by the site
    3  ``--site tiktok`` outside GitHub Actions (nothing was run)

A short Markdown report goes to stdout and, with ``--report``, to
``extractor-report.md`` (YouTube) or ``extractor-report-tiktok.md`` in the
current folder. The weekly workflow (.github/workflows/extractor-check.yml)
puts the report in an issue when a check fails.

Run from the project root:

    python scripts/check_extractors.py [--site youtube] [--report]

This script needs network access to youtube.com and github.com.
"""

from __future__ import annotations

import argparse
import contextlib
import logging
import os
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
TIKTOK_REPORT_FILE = "extractor-report-tiktok.md"

# A public test video from yt-dlp's own tests (_TESTS of TikTokIE in
# vendor/yt_dlp_engine/yt_dlp/extractor/tiktok.py, a test that is not
# only_matching). Only its info is read, nothing is downloaded. The web page
# gives this video as audio only (a FIXME in yt-dlp's test); that is enough,
# the check needs one real format.
TIKTOK_VIDEO_URL = "https://www.tiktok.com/@tatemcrae/video/7107337212743830830"

YOUTUBE, TIKTOK = "youtube", "tiktok"

DENO_CHECK = "Deno"
VIDEO_CHECK = "YouTube video"
PLAYLIST_CHECK = "YouTube playlist"
TIKTOK_CHECK = "TikTok video"

# Stable part of YouTube's "Sign in to confirm you're not a bot" message.
BOT_CHECK_MARKER = "confirm you"
BOT_CHECK_MARKER_2 = "not a bot"
BLOCKED_DETAIL = (
    "YouTube asked this runner to sign in to confirm it is not a bot. "
    "This depends on the runner's IP address, not on the engine, so the result is inconclusive."
)

# Stable parts of the errors TikTok gives when it blocks a request. Compared
# in lower case. "your ip address is blocked" is yt-dlp's own text for status
# 10204; the login texts come from raise_login_required and the /login
# redirect; the rest is HTTP and bot-check wording.
TIKTOK_BLOCK_MARKERS = (
    "ip address is blocked",
    "requiring login",
    "login required",
    "log into an account",
    "use --cookies",
    "http error 403",
    "http error 429",
    "too many requests",
    "captcha",
    "not a bot",
    "verify to continue",
)
TIKTOK_BLOCKED_DETAIL = (
    "TikTok blocked this runner (IP address blocked, login required, bot check, or HTTP 403 or 429). "
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


def _is_tiktok_block(log_lines: list[str]) -> bool:
    text = "\n".join(log_lines).lower()
    return any(marker in text for marker in TIKTOK_BLOCK_MARKERS)


def _extraction_failed(name: str, url: str, log_lines: list[str], site: str = YOUTUBE) -> Result:
    if site == TIKTOK:
        if _is_tiktok_block(log_lines):
            return Result(name, url, BLOCKED, TIKTOK_BLOCKED_DETAIL)
    elif _is_bot_check(log_lines):
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


def check_tiktok_video(url: str) -> Result:
    """Read the info of one public TikTok video. Never runs outside GitHub Actions."""
    if not _on_github_actions():
        raise RuntimeError("The TikTok check runs only on GitHub Actions (GITHUB_ACTIONS=true).")
    from src.backend.yt_dlp_wrapper import YtDlpWrapper

    name = TIKTOK_CHECK
    with _captured_app_log() as log_lines:
        info = YtDlpWrapper().get_video_info(url)
    if info is None:
        return _extraction_failed(name, url, log_lines, TIKTOK)
    real = [f for f in info.formats if _is_real_format(f)]
    if not real:
        return Result(name, url, FAIL, f"Extraction returned no real formats ({len(info.formats)} formats in total).")
    return Result(name, url, PASS, f"'{info.title}': {len(real)} formats.")


def _on_github_actions() -> bool:
    return os.environ.get("GITHUB_ACTIONS") == "true"


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
    parser.add_argument(
        "--site",
        choices=(YOUTUBE, TIKTOK),
        default=YOUTUBE,
        help="which site to check (tiktok runs only on GitHub Actions)",
    )
    parser.add_argument("--report", action="store_true", help="also write the Markdown report to a file")
    args = parser.parse_args(argv)

    if args.site == TIKTOK:
        if not _on_github_actions():
            print("The TikTok check runs only on GitHub Actions. Nothing was run.", file=sys.stderr)
            return 3
        results = [_run(TIKTOK_CHECK, TIKTOK_VIDEO_URL, lambda: check_tiktok_video(TIKTOK_VIDEO_URL))]
        report_file = TIKTOK_REPORT_FILE
    else:
        results = [_run(DENO_CHECK, "-", check_deno)]
        results.append(_run(VIDEO_CHECK, VIDEO_URL, lambda: check_video(VIDEO_URL)))
        results.append(_run(PLAYLIST_CHECK, PLAYLIST_URL, lambda: check_playlist(PLAYLIST_URL)))
        report_file = REPORT_FILE

    try:
        from src.backend.yt_dlp_wrapper import YtDlpWrapper

        engine_version = YtDlpWrapper.get_ytdlp_version()
    except Exception:  # noqa: BLE001
        engine_version = "unknown"

    report = render(results, engine_version)
    print(report)
    if args.report:
        Path(report_file).write_text(report, encoding="utf-8")

    return exit_code(results)


if __name__ == "__main__":
    sys.exit(main())
