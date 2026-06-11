# Changelog

All notable changes to YT-DLP Studio will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Note.** YT-DLP Studio was developed privately from October 2024 through
> April 2026, reaching internal version 0.9.2. In May 2026 we reset the public
> version to **0.1.0** to mark the first public beta. The earlier development
> changelog is archived at
> [`docs-internal/OLD_CHANGELOG.md`](docs-internal/OLD_CHANGELOG.md). Rationale and
> the version management pipeline are documented in
> [`docs-internal/VERSIONING.md`](docs-internal/VERSIONING.md).

---

## [Unreleased]

### Added
- **Per-playlist subtitle picker.** The playlist viewer dialog gained a new "Subtitles" section with a master toggle (off by default) plus per-language checkboxes (Hebrew, English, Arabic, Spanish, French, Russian, German) and a free-form text field for any other ISO code (e.g. `pt, it, zh-Hans`). Ticking Hebrew expands to both `he` and `iw` because YouTube serves Hebrew subtitles under either ISO code depending on the upload year. When the picker is engaged it overrides the main download tab's subtitle settings for that playlist; when it is off the playlist inherits the tab's settings as before. Both English and Hebrew translation dictionaries gained the new strings.
- New dependency: `yt-dlp-ejs>=0.8.0`. yt-dlp 2026.06.09 needs the EJS (External JavaScript) solver package to handle YouTube's JS challenges. Without it, the vendored Deno-only fallback uses a 245-byte stub lib script that often fails to solve challenges and silently drops formats. The package is ~53KB on PyPI, ships from the same maintainers as yt-dlp, and is automatically picked up at runtime via `from yt_dlp.dependencies import yt_dlp_ejs`. Wired into both the runtime `dependencies` list in `pyproject.toml` and the PyInstaller `hiddenimports` in `packaging/build.spec`.
- New dependency: `curl_cffi>=0.15.0`. Provides browser TLS/JA3 impersonation via libcurl-impersonate. Without it, YouTube's subtitle and comments endpoints return HTTP 429 on any client that does not look like a real browser, which (combined with how yt-dlp surfaces subtitle errors) would silently abort entire video downloads. The wrapper now sets `impersonate=ImpersonateTarget('chrome')` on every yt-dlp invocation when curl_cffi is present, and degrades gracefully (logged warning, no impersonate option) when it is not. The Windows AMD64 wheel is `cp310-abi3` and ~1.7 MB; PyInstaller's `collect_all('curl_cffi')` pulls in the native libcurl-impersonate binaries and the bundled `cacert.pem`.
- Global crash handler (`src/utils/crash_handler.py`). Installs `sys.excepthook` and `threading.excepthook` from `launcher.py` before app construction; unhandled exceptions in the main thread or any worker thread now write a structured JSON crash report to `%APPDATA%\YT-DLP Studio\crashes\` (Windows) or `~/.config/YT-DLP Studio/crashes/` (Linux). Reports include app version, yt-dlp version, Python version, platform, full traceback, and the last 200 log lines. Capped at 20 files; `KeyboardInterrupt` still falls through to the default hook so Ctrl+C kills the dev run cleanly.

### Fixed
- **Subtitles now actually download when combined with comments/metadata.** Browser impersonation alone was not enough: YouTube's per-IP rate limiter fills up during the ~60+ comment API requests, so by the time the subtitle download fires it gets HTTP 429 even with a Chrome JA3 fingerprint. The wrapper now sets `sleep_interval_requests=1` when `download_subtitles` is on AND (`download_comments` OR `download_metadata`) is on, which spaces every API request by 1s. Cost: ~10-30s extra per video during the comment phase. Benefit: the `.srt` file actually lands. Single-flag scenarios (subs alone, comments alone) skip the slowdown.
- **Subtitle 429 errors no longer abort the video download.** YouTube aggressively rate-limits subtitle requests (HTTP 429) on clients that do not impersonate a real browser. yt-dlp's `_write_subtitles` raises `DownloadError` on subtitle failure unless `ignoreerrors` is literally `True` - and our default of `"only_download"` does NOT count. Result: with subtitles enabled, a single 429 on any subtitle silently aborted that whole video, leaving the user with zero video files and a misleading "Download complete" log line. Two fixes:
  1. **Add `sleep_interval_subtitles=2`** when subtitle download is enabled, which spaces requests apart and prevents most 429s in the first place.
  2. **Wrap `_write_subtitles`** on the YoutubeDL instance so a subtitle failure becomes a warning and returns `[]` instead of raising. The video download proceeds. Real video download errors still surface normally (we did NOT set `ignoreerrors=True`).

### Changed
- **yt-dlp engine bumped from 2026.02.04 to 2026.06.09** (vendored at `vendor/yt_dlp_engine/`). Brings months of extractor fixes and three CVE fixes upstream.

### Security
- Picks up upstream yt-dlp CVE fixes (advisory IDs are reserved at the time of writing):
  - File downloader cookie leak with `curl` (not exposed by Studio - we use the native downloader).
  - Dangerous file type creation via insufficient filename sanitization (`.desktop`, `.url`, `.webloc` are now restricted to `--write-link` context).
  - Arbitrary code execution via manifest downloads with `aria2c` (not exposed by Studio - we use the native downloader and never enable HLS/DASH via aria2c).
- Studio is unaffected by all three CVEs in practice because it does not expose the vulnerable downloader options to the user, but it inherits the hardened upstream code regardless.

### Notes for maintainer
- yt-dlp 2026.06.09 ships its own PyInstaller hook at `yt_dlp/__pyinstaller/hook-yt_dlp.py`. Our `packaging/hook-yt_dlp.py` remains complementary (it only adds stdlib hidden imports PyInstaller misses on Python 3.13+).
- Bundled Deno (v2.6.10) remains above the new yt-dlp minimum of v2.3.0; no Deno change required.
- Bun is now deprecated upstream and Studio does not use it.

---

## [0.1.1] - 2026-05-16

**Bug-fix release.** The 0.1.0 Windows executable failed to start; this release fixes that.

### Fixed
- Windows executable crashed on launch with `ModuleNotFoundError: No module named 'yt_dlp'`. The bundled yt-dlp engine path was only resolved for source runs, not inside the PyInstaller bundle, so the frozen app could never import yt-dlp. Both the main download path and the playlist fetcher are fixed.

### Security
- Downloaded Deno binary is now created with `0o700` (owner-only) permissions instead of being world-accessible.

### Changed
- CI tooling (ruff, black, pip-audit, zizmor) is now hash-pinned, and supplementary security scanners were added. No user-facing change.

---

## [0.1.0] - 2026-05-10

**First public beta of YT-DLP Studio.**

The application is functional for daily use, but is published as a beta because UI bugs, polish items, and additional UI options are still being worked on. Backwards-compatibility commitments for config and history file formats begin at v1.0.0 - see [`ROADMAP.md`](ROADMAP.md).

### Added
- User-friendly Windows desktop GUI for [yt-dlp](https://github.com/yt-dlp/yt-dlp), no command line required
- Quality selection: Best Quality (automatic), 8K, 4K, 2K, 1080p, 720p, 480p, 360p
- Audio-only downloads with bitrate selection: Best Quality (VBR), 320 / 256 / 192 / 128 kbps
- Audio format selector: MP3, M4A/AAC, OPUS, FLAC, WAV, Vorbis/OGG
- Video container selector: MP4, MKV, WebM, Auto
- Subtitle download with per-language selection (auto-generated and manual)
- Comment download - saves video comments to a `.txt` file
- Thumbnail download (opt-in)
- Metadata download (`.info.json`)
- Playlist support with per-video selection
- Channel download support
- Download queue with up to 3 concurrent downloads, conflict detection, and auto-numbering for duplicate filenames
- Download history tracking
- Download speed limiting
- Update checker (in-app, points to GitHub releases of `NX1X/yt-dlp-studio`)
- Bundled FFmpeg (no separate install required)
- Bundled Deno v2.6.10 JS runtime (required for YouTube JS challenge solving)
- Multi-language support: English and Hebrew, with full RTL layout
- Dark / Light theme toggle, persisted across sessions
- Comprehensive keyboard shortcuts
- About tab with credits and developer info
- System tray notifications and audio alerts on download complete / error
- Apache 2.0 license

### Build & release infrastructure
- PyInstaller-based single-file Windows EXE build (Windows 10 / 11, 64-bit)
- Authenticode-style EXE metadata (ProductName, FileVersion, ProductVersion)
- GitHub Actions CI: lint (ruff, black), tests (pytest, 351+ tests), Windows build with provenance attestation
- GitHub Actions release workflow: auto-tags on `__version__` bump, validates CHANGELOG entry, syncs version metadata, publishes Windows release artifacts, marks `0.x` releases as pre-release
- Single source of truth for the version number in `src/__init__.py` (`__version__`), with `pyproject.toml` reading it dynamically via Hatch and `scripts/sync_version.py` propagating it to the Windows EXE metadata file

### Known limitations
- Windows only - Linux desktop build is on the roadmap for v1.1.0 (see `ROADMAP.md`)
- Some UI bugs and missing UI options being tracked for v0.2.0 stabilization release
- Resume of interrupted downloads not yet supported - planned for a future 0.x release
