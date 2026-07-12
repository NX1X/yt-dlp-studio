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

_(no entries yet)_

---

## [0.2.0] - 2026-07-11

### Linux (Ubuntu) desktop support

First release with an officially built and published Linux desktop package,
alongside the existing Windows EXE. The Linux build is a self-contained
PyInstaller binary that relies on a system-installed FFmpeg and auto-downloads
Deno on first run.

### Added

- **Linux desktop integration package.** The Linux release archive
  (`yt-dlp-studio-<version>-Linux.tar.gz`) now ships an `install.sh` /
  `uninstall.sh` pair plus hicolor icons (32-256px) and a `.desktop` launcher
  (`packaging/linux/`). `install.sh` installs the executable, icons, and
  launcher into the per-user XDG locations (`~/.local/bin`,
  `~/.local/share/icons/hicolor`, `~/.local/share/applications`) with no root
  required, so YT-DLP Studio appears in the Ubuntu application menu / dock.
- **PNG application icon** rendered from the source SVG and bundled at
  `src/resources/icons/favicon.png` so the window icon renders reliably in a
  frozen build even without the Qt SVG image plugin.
- **Linux build in CI.** `.github/workflows/build.yml` now has a `build-linux`
  job that builds the PyInstaller Linux binary on every PR and push to
  `main`/`dev`, mirroring the existing Windows build so Linux-only bundle
  regressions surface before merge.
- **Runtime smoke-test of the Linux binary in CI.** Both the CI and release
  Linux builds now launch the frozen binary headless (offscreen Qt) and assert
  it reaches the "started successfully" milestone before uploading/publishing.
  This runtime-tests the bundle - catching missing hidden imports and Qt/plugin
  gaps that a build-only check misses.

### Changed

- **The release pipeline now builds and publishes the Linux artifact.** The
  previously-disabled `build-linux` job in `.github/workflows/release.yml` is
  enabled, produces a Sigstore-signed SLSA provenance attestation (matching the
  Windows job), packages the full desktop bundle, and is wired into
  `create-release` so the Linux `.tar.gz` is attached to every GitHub Release.
- **Wide Linux distribution support, not just Debian/Ubuntu.** The Linux binary
  is now built on `ubuntu-22.04` (glibc 2.35) instead of `ubuntu-latest` (24.04,
  glibc 2.39). A PyInstaller binary cannot run on a glibc older than its build
  host's, so this lowers the compatibility floor to cover Ubuntu 22.04+,
  Debian 12+, Fedora 36+, Linux Mint 21+, Arch, and most 2022-and-later
  distributions. `install.sh` now detects the system package manager
  (apt/dnf/pacman/zypper/apk/...) and prints the correct FFmpeg install command,
  and the docs list per-distro instructions.
- **FFmpeg and Deno lookup is now platform-aware.** `yt_dlp_wrapper` resolves
  `ffmpeg`/`deno` (no `.exe`) on Linux/macOS and finds the auto-installed Deno
  binary in the project-local `deno/` folder on every platform.
- **The in-app updater is Linux-aware.** On Linux it selects the Linux archive
  asset (never a Windows `.exe`), names the download with the correct
  extension, and - since a `.tar.gz` is not a self-running installer - reveals
  the downloaded archive in the file manager instead of trying to execute it.
- On Linux the app sets its Qt desktop file name (`yt-dlp-studio`) so
  GNOME/Wayland associates the window with the installed launcher and shows the
  correct dock icon.

### Fixed

- **`NameError` on a frozen Linux build when Deno was absent.** The module-level
  project-root path used by the Deno lookup was only defined in the
  run-from-source branch; on a frozen Linux build (which does not bundle Deno)
  the lookup could reference an undefined name. The project root is now resolved
  unconditionally.
- **Missing hidden imports in the Linux PyInstaller spec.** `build_linux.spec`
  was missing `concurrent` / `concurrent.futures` (yt-dlp's fragment downloader)
  and the `yt_dlp_ejs` JS-challenge solver that `build.spec` (Windows) already
  listed. Because the vendored engine is bundled as data (not analysed for
  imports), these were dropped from the Linux binary - it happened to work on
  Python 3.11 (pulled in transitively) but failed with
  `ModuleNotFoundError: No module named 'concurrent'` on 3.10, and YouTube JS
  challenges could silently lose formats without the solver. Both are now listed
  explicitly. Surfaced by the new runtime smoke-test.
- **Restored Python 3.10 support (run-from-source).** The code imported
  `datetime.UTC`, which only exists on Python 3.11+, despite
  `requires-python = ">=3.10"` and a 3.10 classifier - so running from source on
  Python 3.10 (e.g. stock Ubuntu 22.04, whose system Python is 3.10) crashed at
  import. Switched to `datetime.timezone.utc` (works on 3.2+) across
  `main_window`, `settings_tab`, `crash_handler`, and `scripts/sync_version.py`,
  and set the ruff/black `target-version` to `py310` so 3.11-only idioms can't
  slip back in.
- **`test_queue_tab.py` is no longer flaky / excluded from CI.** It asserted
  English UI strings but never pinned the language, so the translation
  singleton's state (mutated by other test modules) or the CI runner's locale
  could render the labels in Hebrew and fail 6 assertions. It now forces English
  in a fixture, so the full suite runs deterministically under any locale; the
  `--ignore=tests/test_queue_tab.py` exclusion has been removed.
- **CodeQL and the Scorecard/Security workflow egress.** Added
  `release-assets.githubusercontent.com` to the CodeQL harden-runner allowlist -
  GitHub moved release-asset downloads (the CodeQL CLI bundle) to that host, and
  block-mode egress was refusing it, failing "Initialize CodeQL" with
  ECONNREFUSED.

---

## [0.1.3] - 2026-07-11

### Maintenance release focused on supply-chain hardening. No user-facing feature changes; the Windows EXE built from this tag is functionally identical to `0.1.2` and only differs in the hardened CI + dependency posture that produced it.

### Changed

- **Renovate cooldown bumped from 7 days to 14 days across all package rules.** Rationale is documented in the file header of `.github/renovate.json5`: this project ships as a signed PyInstaller EXE to end users, so the supply-chain threat model outweighs the CVE-patch-latency concern (no live service under attack). A two-week observation window catches typical time-to-postmortem for a bad release before a hijacked package can be merged into main. `vulnerabilityAlerts.minimumReleaseAge` deliberately matches the base cooldown - shortening the security override would widen the window in which a malicious release masquerading as a CVE patch could slip in and land inside the signed EXE. The `yt-dlp/yt-dlp` engine cooldown was bumped from 5 to 7 days (still shorter than the base because upstream ships almost daily and extractor breakage is the most visible user-facing regression).
- **Pip is now version-pinned in every workflow.** All five `python -m pip install --upgrade pip` sites across `.github/workflows/build.yml` (Tests + Windows Build) and `.github/workflows/release.yml` (Tests + Windows Build + Linux Build) now use `pip==26.1.2` instead of the bare upgrade. Fixes Scorecard's `PinnedDependenciesID` regression source and gives Renovate something concrete to update on a schedule.
- **PyInstaller is now version-pinned in the Linux release build.** Replaced the bare `pip install pyinstaller` in `.github/workflows/release.yml` with `pip install pyinstaller==6.21.0`. The Windows build path continues to pull PyInstaller through `pip install -e .[build]` for now; a follow-up PR will refactor the `.[dev]` / `.[build]` editable-install sites to `pip install --no-deps -e .` plus explicit hash-pinned tool installs once the runtime lockfile has been regenerated to include the dev + build extras.

### Fixed

- **`.github/renovate.json5` schema-validation warning cleared.** The `vulnerabilityAlerts` block used to include `"prPriority": 10`, which Renovate's schema only permits inside `packageRules`. The property was silently ignored at runtime, but every scheduled Renovate run reported "Repository Problems / Found renovate config warnings" on the Dependency Dashboard. Removed. `npx --package=renovate -- renovate-config-validator .github/renovate.json5` now reports `Config validated successfully`.

### Added

- **New Renovate custom manager** for the pinned pip version. Regex-tracks `pip install --upgrade pip==X.Y.Z` occurrences in `.github/workflows/*.yml` and bumps them via the standard PyPI datasource under the 14-day cooldown, so the pin does not silently rot.

### Security

- The msgpack `1.1.2 -> 1.2.1` bump for **GHSA-6v7p-g79w-8964** (Out-of-bounds read / crash on Unpacker reuse after a caught exception, upstream advisory rated High) landed via Dependabot PR #24 alongside this release.

### Notes for maintainer

- The `pip install -e .[dev]` and `pip install -e .[build]` editable-install sites still exist and are still flagged by Scorecard's `PinnedDependenciesID` rule. The rewrite pattern is documented in the follow-up PR: (a) regenerate `requirements/lock.txt` with the `[dev]` and `[build]` optional-dependencies included, (b) change each site to `pip install --no-deps -e .` (project only, no transitive re-install), (c) add explicit `pip install <tool>==<pin>` lines for anything the removed extras used to pull that isn't already in the lockfile. Deferred out of `0.1.3` to keep the release surface tight; the current Scorecard alerts for these sites have been dismissed with a follow-up-PR-tracked rationale.
- Follow-up items already scheduled: refactor the `-e .[extras]` sites (see above), regenerate `requirements/lock.txt` to cover dev+build extras, revisit branch protection for `main` (the "no merge commits" rule flagged an ancestor-of-main squash commit on this branch's push and required a bypass - either loosen the rule or accept bypasses on release branches).

---

## [0.1.2] - 2026-06-12

### Added

- **Per-playlist subtitle picker** in the Playlist Viewer dialog. Master toggle (off by default) plus per-language checkboxes (Hebrew, English, Arabic, Spanish, French, Russian, German) and a free-form text field for any other ISO code (e.g. `pt, it, zh-Hans`). Ticking Hebrew expands to both `he` and `iw` because YouTube serves Hebrew subtitles under either ISO code depending on upload year. When engaged, the picker overrides the main Download tab's subtitle settings for that playlist; when off, the playlist inherits the tab's settings.
- **System Information** group on the About tab consolidating yt-dlp engine version, FFmpeg version, Python runtime, and PySide6 (Qt) version. Moved here from the Settings tab.
- **Storage** group on the Settings tab surfacing the log file path, crash reports directory, and config file path with "Copy" buttons that put each path on the clipboard for easy bug-report attachment.
- **Empty-state placeholders** on the Queue and History tabs. Previously-declared `queue_empty` / `history_empty` translation keys are now rendered (plus new `_hint` companions) via a `QStackedLayout` that swaps the table for a centered placeholder when there are no rows.
- **Native crash dialog.** When the global crash handler captures an unhandled exception on the Qt main thread, the user now sees a translated `QMessageBox` with the path of the JSON report and a link to GitHub issues, rather than the app closing silently.
- New runtime dependency: **`yt-dlp-ejs>=0.8.0`**. yt-dlp 2026.06.09 needs the EJS (External JavaScript) solver package to handle YouTube's JS challenges; without it, the vendored Deno-only fallback uses a 245-byte stub lib script that silently drops formats. Wheel is ~53 KB.
- New runtime dependency: **`curl_cffi>=0.15.0`**. Browser TLS/JA3 impersonation via libcurl-impersonate. The wrapper now sets `impersonate=ImpersonateTarget('chrome')` on every yt-dlp invocation when curl_cffi is present, and degrades gracefully (logged warning, no `impersonate` option) when it is not. PyInstaller's `collect_all('curl_cffi')` bundles the native libcurl-impersonate binaries and `cacert.pem` into the EXE.
- New module: **`src/utils/crash_handler.py`**. Installs `sys.excepthook` and `threading.excepthook` from `launcher.py` before app construction. Writes structured JSON reports to `%APPDATA%\YT-DLP Studio\crashes\` (Windows) or `~/.config/YT-DLP Studio/crashes/` (Linux). Includes app version, yt-dlp version, Python version, platform, full traceback, and the last 200 log lines. Capped at 20 files; `KeyboardInterrupt` still falls through to the default handler.
- New module: **`src/backend/subtitle_list_worker.py`**. `SubtitleListWorker` `QThread` that enumerates available subtitles off the UI thread, restoring responsiveness during the 2-10 second yt-dlp probe that previously froze the entire Qt event loop.
- New developer workflow: **`.github/workflows/bump-yt-dlp-engine.yml`** (`workflow_dispatch`-only). Validates the requested version format, downloads `yt-dlp.tar.gz` and its `SHA2-256SUMS`, verifies a GPG signature on the sums file against the bundled trust anchor (Simon Sawicki / yt-dlp release key), confirms the tarball hash matches, swaps `vendor/yt_dlp_engine/`, runs `check_imports.py` + pytest, and opens a PR. Complements - does not bypass - the Renovate 7-day cooldown.

### Changed

- **yt-dlp engine bumped from 2026.02.04 to 2026.06.09** (vendored at `vendor/yt_dlp_engine/`). Brings months of extractor fixes and three CVE fixes upstream.
- **Hebrew / RTL parity pass.** Every previously-hardcoded English string surfaced in Hebrew sessions is now routed through `tr()`: Download Type label and combo items, Video Format / Audio Format labels, Best Quality / Audio Xkbps combo items, Select Subs button + "Fetching" state, the No Subtitles dialog, Queue tab Actions column, Playlist Viewer table headers (Select, #, Title, Duration, Uploader), Add to Queue button. The Download Type and Quality combos now use `addItem(label, internal_key)` so the stable English key flows through `QUALITY_OPTIONS` / `AUDIO_QUALITY_MAP` via `currentData()` regardless of UI language; three `currentText() == "Audio Only"` string-equality checks were replaced with a `_is_audio_mode` boolean attribute. The Hebrew and English translation dictionaries gained ~70 new keys across these flows.
- **About tab rewrite.** Full i18n pass (Details, About the Developer, Credits, Shortcuts sections), new System Information group (moved from Settings), GitHub button activated, every QTextBrowser swapped for QLabel so the tab is a single scroll region rather than nested scrollbars. RTL-aware alignment so multi-line blocks anchor at the top instead of vertical-centering. Dark-theme-only inline colors (`#ccc`, `#888`, `#58a6ff`, `#1a1a1a`) replaced with palette defaults and a single high-contrast accent (`#1976d2`) visible on both themes.
- **Settings tab cleanup.** Theme-toggle, Check-for-Updates, and Save buttons stripped of their hardcoded inline stylesheets; they now use `buttonStyle="secondary"` (or the default primary style for Save) so theme.py picks the right shade for both light and dark. Removed the unused `_get_ffmpeg_version` helper and `subprocess` import.
- **Honest auto-update microcopy.** The setting previously labelled "Check for Updates on Startup" now reads "Notify me about new versions on startup" with a tooltip making explicit that the action is notification only, not auto-install. Matches the deferred installer-UX decision documented in `docs/UPDATE_SERVICE_NOTES.md`.
- **Single command for version bumps.** `scripts/sync_version.py` now also stamps `## [Unreleased]` in `CHANGELOG.md` as `## [<version>] - <YYYY-MM-DD>` and prepends a fresh empty Unreleased section. Bumping a release is now one edit (`__version__` in `src/__init__.py`) plus one command.

### Fixed

- **Subtitles now actually download when combined with comments/metadata.** Browser impersonation alone was not enough: YouTube's per-IP rate limiter fills up during the ~60+ comment API requests, so by the time the subtitle download fires it gets HTTP 429 even with a Chrome JA3 fingerprint. The wrapper now sets `sleep_interval_requests=1` when `download_subtitles` is on AND (`download_comments` OR `download_metadata`) is on, which spaces every API request by 1s. Cost: ~10-30 s extra per video during the comment phase. Benefit: the `.srt` file actually lands.
- **Subtitle 429 errors no longer abort the video download.** YouTube aggressively rate-limits subtitle requests on clients that do not impersonate a real browser. yt-dlp's `_write_subtitles` raises `DownloadError` on subtitle failure unless `ignoreerrors` is literally `True`, and our default of `"only_download"` does NOT count. Two fixes:
  1. **Add `sleep_interval_subtitles=2`** when subtitle download is enabled, which spaces requests apart and prevents most 429s in the first place.
  2. **Wrap `_write_subtitles`** on the YoutubeDL instance so a subtitle failure becomes a warning and returns `[]` instead of raising. The video download proceeds. Real video download errors still surface normally (we did NOT set `ignoreerrors=True`).
- **No more UI freeze on the Select Subs button.** The 2-10 s yt-dlp probe was running synchronously on the UI thread, freezing the entire Qt event loop. Replaced with a `SubtitleListWorker` `QThread` dispatch; the button shows the translated "Fetching…" label and remains disabled until results arrive.

### Security

- Picks up upstream yt-dlp CVE fixes in the engine bump:
  - File downloader cookie leak with `curl` (not exposed by Studio - we use the native downloader).
  - Dangerous file type creation via insufficient filename sanitization (`.desktop`, `.url`, `.webloc` are now restricted to `--write-link` context).
  - Arbitrary code execution via manifest downloads with `aria2c` (not exposed by Studio - we use the native downloader and never enable HLS/DASH via aria2c).
- Dependency security bumps preempting Renovate PRs #8, #9, #10:
  - `requests` `>=2.31.0` → `>=2.33.0` (CVE-2024-35195 Session ignores `verify=False` on subsequent requests; CVE-2024-47081 `.netrc` credential leak via crafted URL; CVE-2026-25645 insecure temp-file reuse in `extract_zipped_paths`).
  - `pytest` (dev) `>=7.4.0` → `>=9.0.3` (CVE-2025-71176 vulnerable tmpdir handling).
  - `idna` `3.13` → `3.18` via regenerated `requirements/lock.txt` (CVE-2026-45409 IDN handling, transitive via `requests`).
- **Crash reports now scrub credentials before write.** New `_scrub_secrets()` in `src/utils/crash_handler.py` replaces URL userinfo (`https://user:pass@host`), `Authorization: Bearer <token>` and `Basic <token>` patterns, `api_key=` / `password=` / `token=` / `cookie=` / `authorization=` key-value pairs (both `:` and `=` separators), and AWS access key IDs (`AKIA…`) with `[REDACTED]`. Applied to the exception message, the full traceback, and every line of the rolling log tail before the JSON file is written, so a user attaching a crash report to a GitHub issue cannot accidentally leak credentials.
- **Workflow hardening (`bump-yt-dlp-engine.yml`).** New "Validate workflow inputs" step: `base_branch` must match `^[A-Za-z0-9][A-Za-z0-9._/-]{0,99}$` to reject `refs/pull/*/head` and other non-branch refs; `version` (when supplied) must match `^[0-9]{4}\.[0-9]{2}\.[0-9]{2}$`, which also doubles as a Python-string-injection guard for the `constants.py` rewrite step. The resolved version (from `gh release view`) is re-validated against the same regex before being interpolated into Python. The SHA-256 verification step now fails explicitly when `SHA2-256SUMS` does not contain a `yt-dlp.tar.gz` line, or when the parsed hash is not 64 hex chars - the old behavior relied on `test "" = "<hex>"` being false, which worked but was opaque.

### Removed

- **`osv-scanner` job removed from `.github/workflows/security.yml`.** Its advisory coverage substantially overlaps `pip-audit` (lockfile CVEs) and Socket Security (malicious / behavioral package risk), and Renovate's OSV vulnerability alerts already surface OSV advisories on this repo independently. Additionally, `google/osv-scanner-action` v2.3.5+ ships as a reusable workflow whose `action.yml` lacks a `runs:` block, so calling it as a step (which preserved our per-job `harden-runner` egress allowlist) was no longer possible without losing the egress lock. Dropping the scanner is a duplication cleanup, not a coverage regression.

### CI / tooling

- All ruff and black checks pass on the lint + format job, including the four `F601` duplicate-key violations introduced in earlier i18n passes (`button_view_on_github`, `tooltip_select_subs`) which have been resolved.
- `tests/test_crash_handler.py` contains synthetic strings (fake GitHub tokens, fake AWS access keys, URLs with fake passwords) that drive the `_scrub_secrets()` test fixtures. New `.gitguardian.yml` excludes that single file from scanning so the GitGuardian "Pull Request Alerts" check stops failing on every push without disabling the scanner anywhere else in the repo.
- New `sonar-project.properties` excludes `vendor/`, `docs-internal/`, `venv/`, `build/`, `dist/` from SonarCloud analysis. Without it, SonarCloud scanned the entire vendored yt-dlp tree and reported ~260 issues we cannot act on (mostly `python:S1192` string-duplication across 1000+ upstream extractors). After the exclusion, only ~14 findings on code we actually own remain, and those are addressed below.
- `.gitguardian.yml` `ignored-paths` key migrated to `ignored_paths` (hyphenated form is deprecated in ggshield 1.51.0).
- Fixed seven actionable SonarCloud findings:
  - `python:S8572` in `src/utils/crash_handler.py` (×2), `src/ui/about_tab.py`, and `src/ui/update_dialog.py`: `logger.error(f"...{e}")` inside `except` blocks replaced with `logger.exception("...")` so the traceback is captured automatically.
  - `python:S5869` in `src/utils/crash_handler.py:69`: the Bearer/Basic-token character class `[A-Za-z0-9._\-+/=]` rewritten as `[A-Za-z0-9._+/=-]` (literal `-` at the end, no escape) so Sonar's regex parser stops flagging `_\-+` as an overlap candidate. Identical char set, cleaner notation.
  - `python:S7494` in `tests/test_playlist_subtitle_picker.py:97`: `dict((k, v) for ...)` → `{k: v for ...}`.
  - `python:S7498` in `tests/test_yt_dlp_wrapper.py:310`: `dict(url=..., output_dir=..., ...)` constructor → `{"url": ..., "output_dir": ..., ...}` literal.
- Defused six SonarCloud `python:S5443` warnings on `/tmp/...` mock paths in `tests/test_yt_dlp_wrapper.py` by changing the test data to relative paths (`video.mp4`, `video.en.srt`). The values are opaque mock arguments to a monkey-patched `_write_subtitles`, never touch the filesystem; `/tmp` was a stylistic choice that tripped Sonar's publicly-writable-directory heuristic.
- One remaining `python:S2068` finding in `tests/test_crash_handler.py:216` (the `"https://alice:hunter2@example.com/data"` test fixture) suppressed inline with `# NOSONAR` plus an explanatory comment - the URL is the regression input for the secret-scrubber's userinfo-in-URL pattern and cannot be changed without defeating the test.
- **Closed five CodeQL "Clear-text storage/logging of sensitive information" findings** at `src/utils/crash_handler.py:179, 209, 211, 212, 216`. CodeQL's taint tracker followed `str(exc_value)` into `report["exception_message"]`, then into the JSON write and the `logger.critical(...)` call, and did not recognise `_scrub_secrets` as a sanitiser. Rather than dismiss the alerts, the underlying concern is now genuinely addressed:
  - `scrub_secrets` was extracted from `crash_handler.py` into a new shared module `src/utils/secret_scrub.py` (still re-exported as `crash_handler._scrub_secrets` for backward compatibility with existing tests).
  - `src/utils/logger.py` gained a new `SecretScrubbingFormatter(logging.Formatter)` that runs every formatted log record - including any `exc_info=` traceback - through `scrub_secrets` before the record reaches a handler. Both the rolling file handler and the console handler use it. Result: the log file at `%APPDATA%\YT-DLP Studio\yt-dlp-studio.log` (which a user can now also surface easily via the new Settings -> Storage Copy buttons) cannot leak URL userinfo, Bearer/Basic tokens, `api_key=` / `password=` / `token=` / `cookie=` / `authorization=` patterns, or AWS-style access key IDs even when `logger.exception()` writes an unscrubbed traceback. New file `tests/test_log_scrubbing.py` adds 7 tests covering URL userinfo, kv pairs, Bearer tokens, AKIA keys, exc_info tracebacks, clean text pass-through, and `%`-args interpolation.

### Notes for maintainer

- yt-dlp 2026.06.09 ships its own PyInstaller hook at `yt_dlp/__pyinstaller/hook-yt_dlp.py`. Our `packaging/hook-yt_dlp.py` remains complementary - it only adds stdlib hidden imports PyInstaller misses on Python 3.13+.
- Bundled Deno (v2.6.10) remains above the new yt-dlp minimum of v2.3.0; no Deno change required.
- Bun support is now deprecated upstream and Studio does not use it.

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
