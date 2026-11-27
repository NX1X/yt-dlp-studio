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

The exit code is 0 only if every check passes. A short Markdown report
goes to stdout and, with ``--report FILE``, to that file. The weekly
workflow (.github/workflows/extractor-check.yml) puts the report in an
issue when a check fails.

Run from the project root:

    python scripts/check_extractors.py [--report extractor-report.md]

This script needs network access to youtube.com and github.com.
"""

from __future__ import annotations

import argparse
import sys
import traceback
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


@dataclass
class Result:
    name: str
    url: str
    ok: bool
    detail: str


def _is_real_format(fmt: dict) -> bool:
    """False for storyboard image formats, which every video has."""
    return fmt.get("ext") != "mhtml" and "storyboard" not in str(fmt.get("format_note", "")).lower()


def check_deno() -> Result:
    from src.backend.yt_dlp_wrapper import YtDlpWrapper
    from src.utils.deno_installer import DENO_VERSION, ensure_deno_installed

    ensure_deno_installed()
    YtDlpWrapper.reset_deno_cache()
    path = YtDlpWrapper()._get_deno_location()
    if path is None:
        return Result("Deno", "-", False, f"Deno {DENO_VERSION} was not found and the download failed.")
    return Result("Deno", "-", True, f"Deno found at {path}")


def check_video(url: str) -> Result:
    from src.backend.yt_dlp_wrapper import YtDlpWrapper

    info = YtDlpWrapper().get_video_info(url)
    if info is None:
        return Result("YouTube video", url, False, "Extraction failed. See the log above.")
    real = [f for f in info.formats if _is_real_format(f)]
    if not real:
        return Result(
            "YouTube video",
            url,
            False,
            f"Extraction returned no real formats ({len(info.formats)} formats in total).",
        )
    video = sum(1 for f in real if f.get("vcodec") not in (None, "none"))
    audio = sum(1 for f in real if f.get("acodec") not in (None, "none"))
    return Result(
        "YouTube video",
        url,
        True,
        f"'{info.title}': {len(real)} formats ({video} with video, {audio} with audio).",
    )


def check_playlist(url: str) -> Result:
    from src.backend.playlist_fetcher import PlaylistFetcher

    info = PlaylistFetcher.fetch_playlist_info(url)
    if info is None:
        return Result("YouTube playlist", url, False, "Extraction failed. See the log above.")
    count = len(info.videos)
    if count < MIN_PLAYLIST_ENTRIES:
        return Result(
            "YouTube playlist",
            url,
            False,
            f"'{info.title}': {count} entries, expected at least {MIN_PLAYLIST_ENTRIES}.",
        )
    return Result("YouTube playlist", url, True, f"'{info.title}': {count} entries.")


def _run(name: str, url: str, func) -> Result:
    try:
        return func()
    except Exception:  # noqa: BLE001 - every failure must end up in the report
        return Result(name, url, False, "Unexpected error:\n" + traceback.format_exc())


def render(results: list[Result], engine_version: str) -> str:
    lines = [
        f"Vendored yt-dlp engine: `{engine_version}`",
        "",
        "| Check | Result | Details |",
        "| --- | --- | --- |",
    ]
    for r in results:
        status = "pass" if r.ok else "FAIL"
        detail = r.detail.strip().splitlines()[0] if r.detail.strip() else ""
        target = r.name if r.url == "-" else f"{r.name} ({r.url})"
        lines.append(f"| {target} | {status} | {detail.replace('|', '/')} |")
    for r in results:
        if not r.ok and "\n" in r.detail.strip():
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--report", type=Path, help="also write the Markdown report to this file")
    args = parser.parse_args(argv)

    results = [_run("Deno", "-", check_deno)]
    results.append(_run("YouTube video", VIDEO_URL, lambda: check_video(VIDEO_URL)))
    results.append(_run("YouTube playlist", PLAYLIST_URL, lambda: check_playlist(PLAYLIST_URL)))

    try:
        from src.backend.yt_dlp_wrapper import YtDlpWrapper

        engine_version = YtDlpWrapper.get_ytdlp_version()
    except Exception:  # noqa: BLE001
        engine_version = "unknown"

    report = render(results, engine_version)
    print(report)
    if args.report:
        args.report.write_text(report, encoding="utf-8")

    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
