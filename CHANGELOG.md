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

### Fixed

- **No console window flash at launch on Windows.** The About tab ran `ffmpeg -version` while the window was built, and Windows opened a console window for it. FFmpeg now starts without a window, only when the About tab is first shown or from a background thread at startup, and at most once per run.
- **The About tab shows the FFmpeg the downloader uses.** It used to run whatever `ffmpeg` was first on PATH. It now asks the same FFmpeg that downloads use, which is the bundled copy in the Windows EXE.

### Changed

- **One Environment line in the startup log.** Right after "started successfully" the log shows the app, engine, FFmpeg and Deno versions, Python, Qt and the install kind. This helps with bug reports. A failed lookup shows "unknown" and never stops startup.
- **The impersonation warning is quiet.** yt-dlp warns "no impersonate target is available" on some sites because curl_cffi is not shipped. Downloads still work, so this one message now goes to the log at DEBUG. Other warnings stay at WARNING.

---

## [0.3.1] - 2026-10-31

### Linux packages: an AppImage, a `.deb` and an `.rpm` beside the `.tar.gz`, updates that match how you installed, and a working notifications setting.

### Added

- **Linux packages.** Each release now ships an AppImage, a `.deb` and an `.rpm` beside the `.tar.gz`. All four wrap the same PyInstaller binary. The `.deb` and `.rpm` install into `/opt/yt-dlp-studio`, pull in FFmpeg and add a menu entry. Removing or purging them keeps settings and history in `~/.config/YT-DLP Studio`.
- **Updates match the install.** The updater offers an AppImage copy the new AppImage, a `.deb` install the new `.deb` and an `.rpm` install the new `.rpm`. The `.tar.gz` copy still gets the archive. Each kind shows its own next step.
- **CI tests every Linux package.** CI launches the AppImage headless. It installs the `.deb` with apt, launches it and purges it, then checks that user data survives. It extracts the `.rpm` and launches its payload. Every payload must match the built binary byte for byte.

### Fixed

- **"Enable Desktop Notifications" now works.** The Settings checkbox did nothing. It is now saved in the config (`notifications_enabled`, default on) and applied when you save, when you reset to defaults, and at startup.
- **The tray menu is translated.** "Show Window" and "Quit" now come from the translation tables, in English and Hebrew.
- **`docs/ROADMAP.md` is no longer stale.** It no longer says the removed bandwidth, video player and filter modules exist. It marks notifications and in-place updates as shipped and points to `ROADMAP.md` for the current plan.

### Removed

- **`plyer` dependency.** The frozen build could not use it. Notifications use the tray icon, then `notify-send` on Linux. The lock files lost only the `plyer==2.1.0` entries.
- **122 unused translation keys**, in both English and Hebrew. Nothing in `src/` or `tests/` used them. Most belonged to removed or replaced UI: the bandwidth, filter and video player modules (#60), an old batch dialog, an old subtitle picker, and an old menu bar.

### Not verified

- The `.rpm` is built and checked on Ubuntu, but no CI job installs it on Fedora or openSUSE. A real `dnf install` is still to be tested.
- The AppImage runs on the Ubuntu 22.04 runner without FUSE (extract-and-run). A double-click launch on a desktop with FUSE is still to be tested.

---

## [0.3.0] - 2026-10-31

### Installable: a real Windows installer that updates itself in place, a download queue that survives a restart, and working notifications and history.

### Added

- **Windows installer** (#61). `YT-DLP-Studio-Setup-<version>.exe` installs per user, with no admin rights, into `%LOCALAPPDATA%\Programs\YT-DLP Studio`. It adds a Start-menu shortcut and an optional desktop shortcut, in English or Hebrew. It installs the same one-file EXE as the portable download, so the two cannot drift. The portable EXE and ZIP stay available.
  - **Uninstall keeps your data.** Settings, download history and logs in `%APPDATA%\YT-DLP Studio` stay. Deleting them needs a Yes in a box that defaults to No, or `/PURGEDATA=yes` for unattended use.
  - **Tested on a real Windows runner in CI**, on every PR and release: silent install, launch of the installed app until it logs "started successfully", silent uninstall with user data kept, then reinstall and uninstall with `/PURGEDATA=yes`.
  - The app now sets the same taskbar identity (AppUserModelID) as its shortcuts, so its window groups with the pinned icon.
- **In-place updates** (#64). An installed copy downloads the new installer, checks its SHA-256 against the published digest, runs it silently and starts again. A portable copy downloads the new portable EXE and says plainly that it is a separate copy that does not replace the running one.
  - Security hardening from a review of this feature: the file is checked again right before it runs; downloads are written to `<name>.part` until verified; only https downloads from GitHub release hosts are accepted, also after redirects; downloads larger than the published size are stopped; the file name from the GitHub API must be a plain name inside the Downloads folder. A ZIP or an unknown file is shown in Explorer, never run.
- **The download queue survives a restart** (#63). Pending, running and failed tasks are saved to `download_queue.json` (with a format version) next to the history file, and restored on the next start. A paused queue stays paused. A damaged file never stops the app from starting; it is kept as `download_queue.json.bad`.
- **Retry failed downloads** (#63): a Retry button per task, a "Retry All Failed" button, and one automatic retry for network errors only (never for private, geo-blocked, removed or copyrighted videos).

### Changed

- **Bundled yt-dlp engine 2026.08.19 -> 2026.10.26.** Tarball SHA-256 `21f942d258d25cc4e60b4982a25c423460f0bebb835f38e6dfd1fcb140087f95`, matching the `SHA2-256SUMS` file signed by the pinned yt-dlp release key (`AC0CBBE6848D6A873464AF4E57CF65933B5A7581`, GPG "Good signature"). Includes the 2026.10.21 YouTube fixes (a new default `tv_samsung` client, a fix for initial data extraction, clearer error messages). Still uses `yt-dlp-ejs==0.8.0`, unchanged.
- **Deno 2.9.6 -> 2.9.8** in `deno_installer.py`, `build.yml` and `release.yml`. SHA-256 `cba84b26e0df5ae7f74fc66b86a95b866872a86292ebd84fa1e959927edd93bf`, the same in the publisher's sidecar file, the downloaded asset and the GitHub release digest.
- **FFmpeg 8.1.2 -> 9.0.2** in `build.yml` and `release.yml` (SHA-256 `4d2060a8b34a940aa47d785142055bb92a63053781e55f2ace4546edd519a8f5`, the same in the download and the GitHub digest). This is a major version: every library file name changed (`avcodec-63`, `avdevice-63`, `avfilter-12`, `avformat-63`, `avutil-61`, `swresample-7`, `swscale-10`, read from the real 9.0.2 archive). `packaging/build.spec` and the CI bundle check were updated to match.
- **Cooldown override, by decision.** yt-dlp 2026.10.26 (4 days old) and Deno 2.9.8 (9 days old) were taken inside the project's cooldown window (7 and 14 days) because the maintainer asked for the latest versions. yt-dlp's GPG signature check against the pinned key still guards against a hijacked release.
- **Running from source now needs Python 3.11 or newer** (was 3.10). yt-dlp 2026.10.26 dropped Python 3.10. `requires-python`, the lint targets and the lock files moved to 3.11; the relock only removed packages that 3.10 alone needed. The Windows EXE and the Linux binary bundle their own Python, so they are not affected, and the Linux binary still runs on Ubuntu 22.04.

### Fixed

- **Desktop notifications never appeared** (#62). The app never created its tray icon, so every notification fell through to a library the EXE cannot use. Notifications now go through the tray icon, then `notify-send` on Linux. "Notification sent" is logged only when a notification really went out.
- **The real file name is shown and opened** (#65). Nothing recorded the downloaded file, so the Queue tab, notifications and the "Download complete" box said "video file", and "Open file" could not find the file. They now use the real name and title from yt-dlp.
- **The History tab never got new entries** (#66). Finished downloads are now recorded: completions, final failures with the real reason, and cancels. A failure that is about to be retried waits for its final result. The tab refreshes on its own.
- **The queue could run more than 3 downloads at once** (#63). After a restore or "Retry All", a running download could be lost track of when tasks were removed or reordered. Downloads are now tracked by task, threads are kept until they finish, and closing the app cancels running downloads and waits up to 4 seconds for them.
- **Release pipeline race** (#61). A release could fail to create its tag while its own test jobs were still running, which is what happened to the first v0.2.1 run. Release runs now queue, and the tag waits for the required checks.

### Not verified before release

These need a real Windows desktop, not a CI runner: the interactive installer wizard, the Yes/No box on uninstall, the desktop shortcut, and Windows toast notifications. The first real in-place update happens when 0.3.0 updates to a later release.

---

## [0.2.1] - 2026-10-30

### Maintenance release: removes curl_cffi, hash-pins every CI install, and makes CI check the contents of each built executable.

### Removed

- **`curl_cffi` (browser impersonation) is no longer a dependency or bundled.** It is banned by the project's software-origin policy. It was optional here: yt-dlp works without it. It is removed from `pyproject.toml`, from both PyInstaller specs, and from every lock file. It is also added to `excludes` in `packaging/build.spec` and `packaging/build_linux.spec`. The vendored yt-dlp loads `curl_cffi` automatically when it is installed, so the exclude keeps it out of the executable even if a build machine has it. Verified: a build made in a venv with `curl_cffi` 0.15.0 installed contains none of it.
  - **Effect on downloads, measured on 2026-10-14:** video, audio and English subtitle downloads work without it. yt-dlp now logs one warning: "the extractor specified to use impersonation ... no impersonate target is available". Auto-translated subtitles in other languages (`de`, `fr`, `es`) hit HTTP 429 on the same video **both with and without** Chrome impersonation, so removing it causes no measurable regression there. The existing subtitle sleep and the non-fatal subtitle handling still apply.
  - Guard tests fail if `curl_cffi` returns to `pyproject.toml`, to a lock file, or to a spec, or if the wrapper requests impersonation.
- **`sonar-project.properties` is removed.** The project uses SonarCloud Automatic Analysis, so the analysis scope and exclusions are set in the SonarCloud UI instead.

### Added

- **CI checks the contents of every built executable** (`scripts/check_bundle.py`). It runs right after PyInstaller in the Windows and Linux jobs of `build.yml` and `release.yml`, and fails the build when something critical is missing: the `yt_dlp_ejs` solver scripts, the vendored engine, the Qt extensions, and on Windows `ffmpeg.exe`, `ffprobe.exe`, `deno.exe` and the 7 FFmpeg DLLs. It also fails on any `curl_cffi` content, and when the bundled yt-dlp version differs from `YTDLP_VERSION`. v0.1.3 shipped without the solver scripts and every YouTube download failed; this check catches that. Proven both ways: it passes on a real Linux build, and it fails with exit code 1 on a build made without the solver scripts.
- **`requirements/dev.txt`**: a hash-pinned lock of runtime plus dev tools, constrained by `requirements/lock.txt`.
- **`scripts/relock.sh`** regenerates all three lock files the correct way (see Fixed).
- **`tests/test_lock_consistency.py`** fails when a lock pin no longer satisfies its bound in `pyproject.toml`, when `dev.txt` or `build-tools.txt` disagrees with `lock.txt`, or when `curl_cffi` appears in any lock.

### Fixed

- **The lock file had drifted from `pyproject.toml`.** Renovate raises version bounds but does not regenerate the locks. `requirements/lock.txt` pinned PySide6 6.11.0 while `pyproject.toml` required `>=6.11.2`. CI hid it, because the unhashed `pip install -e .[dev]` that followed upgraded past the lock. The locks are regenerated and now match, and the new consistency test catches this from now on.
- **`requirements/lock.txt` could not be installed on Python 3.10**, the `requires-python` floor. It was compiled on Python 3.14, which drops `tomli` (PySide6 needs it below 3.11), so `pip install --require-hashes` failed. All three lock files are now compiled with `uv pip compile --universal --python-version 3.10`, which keeps platform and Python-version markers. That also keeps Windows-only packages such as `colorama` in `dev.txt`. Verified: all three files install with zero errors on Python 3.14 and 3.10, and the full test suite passes on both.
- **The 14-day supply-chain cooldown now covers transitive dependencies too.** pip-compile picks the newest version that fits a bound, and Renovate's `minimumReleaseAge` covers only the direct dependencies it bumps. The first regeneration would have pulled 15 packages younger than 14 days, including PySide6 6.12.0 and its new `pyside6-webengine` dependency. Locks are now built with `--exclude-newer` set 14 days back (2026-10-16 for this release). Verified on 2026-10-30: 75 of the 79 unique pins are at least 14 days old. The other 4 are the security fixes listed under Security, which skip the cooldown on purpose.

### Security

- **Fixes for 20 Dependabot alerts, plus 11 `virtualenv` CVEs that only `pip-audit` reported.** The alerts close when this release merges to `main`. The locks pinned vulnerable versions of seven packages. All four lock files now pin the patched versions, and `pip-audit` finds no known vulnerabilities in any of them (checked 2026-10-30).

  | Package | Was | Now | Worst alert | Where |
  | :- | :- | :- | :- | :- |
  | `certifi` | 2026.4.22 | 2026.10.18 | critical, GHSA-6q48-6c7w-9gw2 (emSign root CAs) | app (`lock.txt`) and CI |
  | `urllib3` | 2.7.0 | 2.8.0 | high, GHSA-vxq7-64xx-v4gw, GHSA-8988-9cw3-xx77 | app (`lock.txt`) and CI |
  | `msgpack` | 1.2.1 | 1.2.3 | high, GHSA-j586-36cw-2gc2 | CI tools |
  | `black` | 26.3.1 | 26.10.1 | high, GHSA-cg8m-r9f2-5wm2 | CI tools |
  | `filelock` | 3.29.0 | 4.2.1 | high, GHSA-v4x8-3wr5-3wq8 (and 9 more) | CI and dev tools |
  | `setuptools` | 84.0.0 | 84.1.0 | low, GHSA-xmj3-9gf7-h52w | build tools |
  | `virtualenv` | 21.14.1 | 21.14.10 | 11 CVEs | dev tools |

  - **Security fixes no longer wait for the 14-day cooldown.** `certifi`, `filelock`, `setuptools` and `virtualenv` fixes were 10 to 13 days old. `scripts/relock.sh` now lets each one through up to a cutoff just after its patched release and no further, so newer releases of the same package still wait. Every other package keeps the 14-day cutoff (2026-10-16 for this release). Renovate follows the same rule: its security PRs now wait 0 days instead of 14 (`.github/renovate.json5`), and regular updates still wait 14 days.
  - **Known gap:** `dev.txt` keeps `filelock` 4.1.0 for the Python 3.10 CI test job, because `filelock` 4.2.1 needs Python 3.11 or later and no patched release supports 3.10. It is a dev tool only (`virtualenv` pulls it in) and never reaches the app.
  - **`requirements/ci-tools.txt` is now built by `scripts/relock.sh`** with the same cooldown, `--universal` and Python 3.11. Before, it was compiled by hand with `pip-compile` on Python 3.14 and had no cooldown. It now also pins `pip` itself, which `--require-hashes` needs.
  - Verified: each lock installs with `--require-hashes` on its target Python (`lock.txt` on 3.10 and 3.14, `dev.txt` and `build-tools.txt` on 3.10, `ci-tools.txt` on 3.11), and the full test suite passes (485 tests).
- **Every CI `pip install` is now hash-pinned.** The three `pip install -e .[dev]` steps (in `build.yml`, `release.yml` and `bump-yt-dlp-engine.yml`) become `pip install --require-hashes -r requirements/dev.txt --only-binary :all:`. The editable install is gone entirely: `conftest.py` already puts the repo on `sys.path`, and nothing reads the installed package metadata. This clears the 6 open OpenSSF Scorecard `PinnedDependenciesID` alerts and SonarCloud `githubactions:S8541` / `S8544`.
- **`update_checker.py` mounts its retry adapter for HTTPS only.** It no longer mounts one for `http://`, which nothing used (SonarCloud hotspot `python:S5332`).

### Also shipped in this release

Two changes merged a few seconds after #58 and were built into the published 0.2.1 (its tag points at `28dcfdf`):

- **LICENSE restored to the verbatim Apache-2.0 text, and a NOTICE file added** (#57). The committed license had drifted from the canonical text in two places. Third-party attribution moved to `NOTICE`.
- **Three unused UI modules removed** (#60): `video_player_widget.py`, `filter_dialog.py` and `bandwidth_widget.py`, 431 statements that nothing imported. Audio-only downloads are no longer labelled "video file" in the completion fallback.

### Dependencies

- `packaging>=26.3` (#52), `pre-commit>=4.6.2` (#39, #53), `pytest-qt>=4.5.0` (#43), `pyinstaller>=6.22.3` (#56). All four support Python 3.10 and were older than 14 days.
- Locked versions (selection): PySide6 6.11.2, requests 2.34.2, packaging 26.3, yt-dlp-ejs 0.8.0, PyInstaller 6.22.3, pytest 9.1.1.

---

## [0.2.0] - 2026-09-20

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
- **The in-app updater is Linux-aware.** On Linux it selects the Linux archive
  asset (never a Windows `.exe`), names the download with the correct
  extension, and - since a `.tar.gz` is not a self-running installer - reveals
  the downloaded archive in the file manager instead of trying to execute it.
- On Linux the app sets its Qt desktop file name (`yt-dlp-studio`) so
  GNOME/Wayland associates the window with the installed launcher and shows the
  correct dock icon.

### Fixed

- **Linux PyInstaller spec was missing runtime dependencies.**
  `build_linux.spec` did not bundle `curl_cffi`'s native impersonation library
  (downloads failed at `YoutubeDL` init with "Impersonate target 'chrome' is not
  available"), the `yt_dlp_ejs` solver `.js` data files (JS challenges could lose
  formats), or `concurrent.futures` (`ModuleNotFoundError` on Python 3.10). All
  are now bundled via `collect_all` / `collect_data_files` / hidden imports,
  matching the Windows spec. Surfaced by the new runtime smoke-test.
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
- **Sigstore egress for the Scorecard job.** Added
  `fulcio`/`rekor`/`tuf-repo-cdn.sigstore.dev` to the Scorecard harden-runner
  allowlist so `publish_results` can sign results; the Security workflow had been
  failing on every run.

> Note: the dependency, engine, and CodeQL/`release-assets` egress work that was
> staged on this branch shipped ahead of it in **0.1.4** (see below); 0.2.0
> carries only the Linux-desktop delta on top.

---

## [0.1.4] - 2026-09-19

### Hotfix release: downloads work again in the Windows EXE. Also refreshes the bundled yt-dlp engine, Deno and FFmpeg, and clears the open dependency and CI backlog.

### Fixed

- **YouTube downloads failing in the Windows EXE.** `packaging/build.spec` listed `yt_dlp_ejs` under `hiddenimports`, which bundles the package's Python modules but not its data files. The JS challenge solver scripts (`yt_dlp_ejs/yt/solver/core.min.js` and `lib.min.js`) were therefore missing from the frozen build, so YouTube's JS challenges could not be solved and downloads failed or lost formats. Running from source was unaffected because the scripts exist on disk in the venv. The spec now adds `collect_data_files('yt_dlp_ejs')` to `datas`. Verified with the new engine: yt-dlp logs `Using challenge solver lib/core script v0.8.0 (source: python package, variant: minified)` with no hash-mismatch warning.
- **Failed downloads were reported as successful.** With `ignoreerrors='only_download'`, a failed download does not raise: `extract_info` returns `None`, and the wrapper logged `DOWNLOAD COMPLETED SUCCESSFULLY` with nothing on disk. This is exactly what v0.1.3 users saw, completing in about two seconds with no file. The wrapper now counts a download as successful only when the files yt-dlp reports in `requested_downloads` exist, and otherwise fails with yt-dlp's own error, which the UI displays. yt-dlp's warnings and errors are also routed into the app log through a `logger` bridge; previously they went to stdout/stderr, which the windowed EXE discards.
- **Playlist dialog crash on float durations.** yt-dlp reports `duration` as a float (e.g. `245.0`), and the `:02d` format in `PlaylistVideoInfo` raised `ValueError`, closing the dialog. The duration is now normalised to `int` first. Covered by new tests in `tests/test_playlist_fetcher.py`.
- **`bump-yt-dlp-engine.yml` never passed its checksum step.** The `SHA2-256SUMS` lookup allowed exactly one space between hash and filename, but `sha256sum` emits two, so the pattern matched no upstream release (tested back to `2026.02.04`) and the workflow always exited at "yt-dlp.tar.gz hash not found". The pattern now accepts any whitespace and the binary-mode `*` marker, and is anchored so `yt-dlp.tar.gz.sig` cannot match. The same workflow's `pip` upgrade, missed by the 0.1.3 pinning pass, is now pinned to `pip==26.1.2`.
- **`Set up Python` failing across CI after the setup-python v6.3.0 bump.** GitHub now serves release assets from `release-assets.githubusercontent.com`, and setup-python v6.3.0 installs pip from PyPI during setup. harden-runner's block-mode allowlists rejected both, failing every job with `connect ECONNREFUSED`. `release-assets.githubusercontent.com` was added to the 12 allowlist blocks that lacked it (#29), and `pypi.org` / `files.pythonhosted.org` to `codeql.yml` (#30).

### Changed

- **Bundled yt-dlp engine bumped from `2026.06.09` to `2026.08.19`.** Tarball SHA-256 `072aad4f2a7604e92155f61a275a4752dc64046c8f6d90df3710525d94cd37c1`, matching the `SHA2-256SUMS` file signed by the yt-dlp release key (`AC0CBBE6848D6A873464AF4E57CF65933B5A7581`, GPG "Good signature"). Includes the `2026.07.04` and `2026.08.19` YouTube fixes (new `visionos` and `web_embedded` client fallbacks, `android_vr` removed from default clients, player client version updates, tab/playlist metadata and pagination fixes) plus TikTok, Instagram, Vimeo and Bandcamp fixes. New extractors: `omnyfm`, `zan`. Removed upstream: `gofile`, `trovo`, and the dead `ARDIE` extractor (other ARD extractors remain). Still requires `yt-dlp-ejs==0.8.0`, matching `requirements/lock.txt`.
- **Deno bumped from `2.6.10` to `2.9.6`** in `src/utils/deno_installer.py`, `build.yml` and `release.yml`. SHA-256 `15e5300b0ba3c3695a7621d90160a746ec9e710228cee639afa9d580f6e3cd11` agrees across the publisher's `.sha256sum` sidecar, the downloaded asset and the GitHub release digest. `2.9.7` was skipped because it was one day old, inside the 14-day cooldown.
- **FFmpeg bumped from `8.1.1` to `8.1.2`** in `build.yml` and `release.yml` (SHA-256 `cba748035c21ce1431d0823c7a3a711f38616f89f87a265dceddf9b7f6749d2d`). FFmpeg `9.0.1` was deliberately not taken: it moves every library soname (`avcodec-62` to `avcodec-63`, `swscale-9` to `swscale-10`, and so on), which would break the seven hardcoded DLL entries in `build.spec`. That bump belongs in a release that can absorb a spec change.
- **FFmpeg and Deno lookup is platform-aware.** `YtDlpWrapper` now looks for `ffmpeg` / `deno` without the `.exe` suffix on non-Windows platforms. No behaviour change on Windows; brought forward from the in-progress Linux work.
- **Renovate now tracks every copy of the Deno and FFmpeg pins.** The FFmpeg manager watched only `build.yml`, leaving `release.yml` (the published EXE) to drift, and the Deno manager watched only `deno_installer.py`, missing both workflows. Both managers now cover `build.yml` and `release.yml`. The workflows also pin a SHA-256 that Renovate cannot compute, so its PR fails the hash check until the verified digest is pasted in, which is the intended manual gate.
- **`test_engine_imports_at_pinned_version` compares against `YTDLP_VERSION`** instead of a string literal, so the vendored tree and the constant cannot drift and the bump workflow's pytest step no longer needs a test edit on every bump.

### Security

- **msgpack bumped to `1.2.1` in the CI tooling lock** (GHSA-6v7p-g79w-8964, High: out-of-bounds read when an `Unpacker` is reused after a caught error). Reachable only through `pip-audit -> cachecontrol -> msgpack` in `requirements/ci-tools.txt`; not bundled into the EXE. Done as a surgical pin-and-hash swap (#31), because a full re-lock on Linux drops Windows-only transitives such as `colorama`, which is what broke the Dependabot PR (#24).

### Dependencies

- Merged the pending Renovate queue: `actions/checkout` v6.0.3, `actions/setup-python` v6.3.0, `github/codeql-action` v4.36.3, `actions/attest-build-provenance` v4.1.1, `softprops/action-gh-release` v3.0.1 (#13); `packaging>=23.2` (#21); `black>=26.5.1` (#27); `pip-tools>=7.5.3` (#28); `mkdocs-material>=9.7.6` (#20); pre-commit hooks `psf/black` v26.5.1 (#17), `gitleaks` v8.30.1 (#16), `ruff-pre-commit` v0.15.20 (#15).

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
