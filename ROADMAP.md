# YT-DLP Studio - Roadmap

**Part of NXTools by NX1X**
Website: https://nx1xlab.dev/nxtools

---

## Current Version: 0.3.0 released · 0.3.1 next (Public Beta)

> The project is in **public beta**. The core feature set is functional but UI bugs, polish items, and additional UI options remain. We will reach **v1.0.0** when the feature set is stable and beta exit criteria are met (see below).
>
> Latest released: **0.3.0** (Windows installer, in-place updates, queue that survives a restart, 2026-10-31). Next: **0.3.1** (Linux packages and winget).
>
> Earlier private development history (up through internal version 0.9.2) is archived in [docs-internal/OLD_CHANGELOG.md](docs-internal/OLD_CHANGELOG.md). The reasoning behind the version reset to 0.1.0 lives in [docs-internal/VERSIONING.md](docs-internal/VERSIONING.md).

### Completed Features

#### Core Download Features
- ✅ User-friendly GUI for yt-dlp video downloader
- ✅ Support for YouTube and 1000+ websites
- ✅ Multiple quality options:
  - Best Quality (automatic)
  - 8K (4320p)
  - 4K (2160p)
  - 2K (1440p)
  - 1080p (Full HD)
  - 720p (HD)
  - 480p (SD)
  - 360p
- ✅ Audio-only download with quality options:
  - 320kbps
  - 256kbps
  - 192kbps
  - 128kbps

#### Format Support
- ✅ Video container formats:
  - MP4 (best compatibility)
  - MKV (Matroska)
  - WebM
  - Auto (best quality)
- ✅ Audio formats:
  - MP3 (most compatible)
  - M4A/AAC (high quality)
  - OPUS (best quality/size ratio)
  - FLAC (lossless)
  - WAV (uncompressed)
  - Vorbis/OGG

#### Advanced Features
- ✅ **Comment download** (v3.0.0)
  - Downloads video comments to separate .txt file
  - Includes comment metadata (author, likes, timestamp)
  - Formatted output with comment count
  - "Comments" appended to filename
- ✅ Subtitle download and selection
  - Auto-download subtitles in multiple languages
  - Manual subtitle selection dialog
  - Support for auto-generated and manual subtitles
- ✅ Thumbnail download
- ✅ Metadata download (.info.json)
- ✅ Download speed limiting
- ✅ Playlist support
- ✅ Queue management system (up to 3 concurrent downloads, pause and resume the queue)
- ✅ Batch download: paste many URLs, or import them from a text file
- ✅ Download history tracking
- ✅ Auto-numbering for duplicate downloads

#### User Experience
- ✅ **Audio/visual alerts** (v3.0.0)
  - Success sound on download completion
  - Error sound on download failure
- ✅ Dark/Light theme toggle
- ✅ Multi-language support (English/Hebrew with RTL layout)
- ✅ Comprehensive keyboard shortcuts
- ✅ Progress tracking with speed and ETA
- ✅ Detailed logging
- ✅ FFmpeg bundled (no external dependencies)

#### User Interface
- ✅ Download Tab (main interface)
- ✅ Queue Tab (manage download queue)
- ✅ History Tab (view past downloads)
- ✅ Settings Tab (configuration and preferences)
- ✅ **About Tab** (v3.0.0 - reorganized)
  - Details section
  - About the Developer (NX1X/NXTools)
  - Credits (opensource projects)
  - Keyboard Shortcuts

---

## Future Roadmap

### v0.2.0 - Linux (Ubuntu) Desktop Support  *(released 2026-09-20)*
First officially built and published Linux desktop package, alongside the existing Windows EXE.
- ✅ Platform-aware FFmpeg / Deno resolution (no hardcoded `.exe`)
- ✅ Linux-aware in-app updater (selects the Linux archive; reveals in file manager)
- ✅ PNG application icon + `.desktop` launcher + hicolor icons
- ✅ `install.sh` / `uninstall.sh` (per-user `~/.local` install, no root; distro-agnostic FFmpeg guidance)
- ✅ Linux build in CI (build + release), with a runtime smoke-launch and Sigstore provenance
- ✅ Wide-distro support: built on glibc 2.35 (Ubuntu 22.04+, Debian 12+, Fedora 36+, Arch, ...)
- ✅ Restored Python 3.10 support (run-from-source on stock Ubuntu 22.04)

#### Open follow-ups (carried past the release)
- ⬜ Community testing on multiple distributions before promoting to "stable Linux"
- ⬜ **Website:** add the Linux download to the website, and update docs + marketing to say the app is available for **Windows and Linux** (was Windows-only). Lives in the separate `yt-dlp-studio-website` repo.
- ⬜ **Website SEO / GEO pass:** update on-page keywords for cross-platform reach (e.g. "yt-dlp GUI for Windows and Linux", "Linux video downloader", "Ubuntu / Debian / Fedora yt-dlp desktop app", "open-source YouTube downloader"), refresh page titles + meta descriptions + OpenGraph/Twitter cards, add/verify JSON-LD `SoftwareApplication` structured data listing both `operatingSystem` values, keep `sitemap.xml` / `robots.txt` / `llms.txt` current so AI answer engines surface the Linux support too.

### Path to 1.0

Planned on 2026-10-30. Each release ships only when CI is green (including the
bundle check), a real download test passes, and the Windows build is smoke-tested
by hand.

| Release | Theme | Goal |
|---|---|---|
| 0.3.0 | Installable | Real installers on Windows and Linux, and updates that replace the app |
| 0.4.0 | Reliable | Fix known bugs, simplify the download path, test the UI |
| 0.5.0 | Complete | Add the missing basics: cookies, filename templates, format options |
| 1.0.0 | Stable | Feature freeze and beta exit |

### v0.3.0 - Installable  *(released 2026-10-31)*
Ship the app the way users on each OS expect, and keep the no-install option.
- ✅ **Windows installer** (#61): a per-user Inno Setup installer that needs no admin rights. It adds a Start-menu shortcut, an uninstaller and a stable install path. The portable EXE and ZIP stay.
- ✅ **In-place updates** (#64): the updater downloads the new installer, runs it silently and restarts the app. This removes the "two copies" limitation (see `docs/UPDATE_SERVICE_NOTES.md`).
- ✅ **Portable copy** (#64): honest updater text ("download the new version", not "run the installer").
- ✅ **Uninstall keeps user data** (#61): settings and download history stay unless the user chooses to delete them.
- ✅ **CI installer test** (#61) on a Windows runner: silent install, launch, silent uninstall, then check that user data survives.
- ✅ **Hash-pin every CI install** *(done in 0.2.1)*: the `pip install -e .[dev]` steps became `--require-hashes -r requirements/dev.txt`, clearing the 6 Scorecard `PinnedDependenciesID` alerts and Sonar S8541/S8544. Whether the SonarCloud gate itself turns green is tracked in [#33](https://github.com/NX1X/yt-dlp-studio/issues/33).
- ✅ Removed the `http://` retry adapter mount in `update_checker.py` (Sonar hotspot S5332) *(done in 0.2.1)*.
- ✅ Also in 0.3.0, from the 0.4.0 list: the queue survives a restart and failed tasks can be retried (#63), desktop notifications work (#62), the real file name is shown and opened (#65), and the History tab records downloads (#66).
- Note: release binaries stay **unsigned** until the signing work under v1.0.0. Sigstore provenance already lets users verify downloads.

### v0.3.1 - Linux packages and winget
Moved from 0.3.0 so the Windows installer could ship first.
- ⬜ **Linux packages:** AppImage, `.deb` (Debian, Ubuntu) and `.rpm` (Fedora). CI builds and smoke-launches each one. The `.tar.gz` with `install.sh` stays. Packaging tools are checked against the project's software-origin policy before use.
- ⬜ **winget:** submit a manifest to `microsoft/winget-pkgs` after the installer ships.

### v0.4.0 - Reliable
Fix what is known to be broken, and make the download path safe to change.
- ✅ **Delete dead code:** `src/ui/video_player_widget.py`, `src/ui/filter_dialog.py` and `src/ui/bandwidth_widget.py` (431 statements). Nothing imports them.
- ⬜ **Refactor `YtDlpWrapper.download()`:** split the ~500-line method (SonarCloud S3776 cognitive complexity 136, S107 with 15 parameters) into helpers plus a `DownloadOptions` object. Pin the current behaviour with tests first, and run a live download test before merging.
- ✅ **Desktop notifications that work** on Windows and Linux. Today every download logs `Could not send notification: No usable implementation found!` on Windows, and toasts fail on desktops without a tray (for example stock GNOME). Use Qt-native notifications, with `notify-send` as the Linux fallback, and a tray icon that is always available.
- ✅ **Fix the false log line:** the code logs `Notification sent` even after a failed notification. Log success only when a notification was sent.
- ✅ **Fix the audio-only label:** an audio-only download logs `Task N completed: video file`. Report the real output type.
- ✅ **Keep the queue across restarts:** save pending and unfinished tasks, and resume them on the next start. yt-dlp already continues `.part` files; the app does not yet save its queue.
- ✅ **Retry failed tasks:** a Retry button, plus one automatic retry for network errors. (yt-dlp already retries up to 10 times inside one download.)
- ⬜ **UI tests** for the Download tab (9% covered today), Settings (9%), History (8%) and the update dialog (0%). Target: about 70% overall coverage (41% today).
- ⬜ **Weekly extractor check in CI:** info extraction only (no download), against one public URL per tested site, so upstream breakage shows up early.

### v0.5.0 - Complete
Add the basics users expect before 1.0.
- ⬜ **Cookies from the browser** for private and age-restricted videos. Without them these downloads fail today ("Sign in ... Use --cookies-from-browser"). Firefox first. Unverified: Chrome on Windows may not work, because of Chrome's app-bound cookie encryption; check this during implementation.
- ⬜ **Filename templates** (for example `%(uploader)s - %(title)s`).
- ⬜ **Format options:** video codec (H.264, H.265, VP9, AV1), audio codec (AAC, Opus, Vorbis), and a custom format string for advanced users.
- ⬜ **Proxy setting.**
- ⬜ **Site tiers:** "Tested" for the sites checked every release (YouTube, Instagram, TikTok, Facebook, X), and "Experimental" for the other 1000+ yt-dlp sites, clearly labelled as untested.
- ⬜ **Versioned config and history files,** with migration of older files. v1.0 promises these formats stay compatible, so they need a version field first.

### v1.0.0 - Stable Release / Beta Exit
The first non-beta release. Reached when:
- ⬜ Every 0.3.0 to 0.5.0 item has shipped, or was moved to "After 1.0" by decision
- ⬜ No known critical UI bugs
- ⬜ Feature set frozen (no breaking changes planned for short term)
- ⬜ Config and history file formats stable (backwards-compatibility commitment begins here)
- ⬜ Tested clean on Windows 10 and Windows 11: CI on two Windows runner versions, plus a manual checklist
- ⬜ Documentation complete (user guide, troubleshooting, install guide)
- ⬜ The repository is public, so users can download releases and the in-app updater can find them
- ⬜ Windows release executable is Authenticode code-signed via the
  [SignPath Foundation](https://signpath.org/) free OSS program (kills the
  SmartScreen "Unknown publisher" warning). Application pending - process,
  alternatives, and CI wiring documented in [docs-internal/CODE_SIGNING.md](docs-internal/CODE_SIGNING.md).
  Non-blocking if approval is delayed: ship v1.0.0 unsigned and roll signing
  into the next patch release.
- ⬜ Release artifacts are Sigstore-signed (cosign + keyless OIDC) so any
  user - Linux, macOS, or Windows - can cryptographically verify the
  download independent of Authenticode/SmartScreen. SLSA build provenance
  attestations are already published on every release (see
  `actions/attest-build-provenance` in
  [`.github/workflows/release.yml`](.github/workflows/release.yml));
  remaining work is a `cosign sign-blob` step that publishes the detached
  `.sig` + `.crt` next to each release asset. Implementation notes,
  key-management decisions (keyless vs. managed), and end-user verification
  instructions live in [docs-internal/SIGSTORE_SIGNING.md](docs-internal/SIGSTORE_SIGNING.md).

### After 1.0 (not scheduled)
Kept as ideas. None of these block 1.0.
- Download scheduling (download at a set time)
- Browser extension (send a link from the browser)
- Bitrate and frame-rate control
- Custom FFmpeg post-processing commands
- Automatic file organization (by channel, date, and so on)
- Channel and playlist monitoring (download new videos automatically)
- Download notifications by email or Discord
- Export and import download presets
- Cloud storage (Google Drive, Dropbox, OneDrive)
- More Linux formats: Flatpak and AUR
- macOS build (`.app`, `.dmg`); PyInstaller is platform-native, so this needs a macOS CI runner
- Android app; a separate effort, likely with a different UI toolkit
- Plugin system, web interface, API server, full UI redesign
- **Containerized reproducible builds with [Dagger](https://dagger.io)**: move lint, tests, and the **Linux** PyInstaller build into a Dagger module (`dagger call ...`) that runs the same containerized pipeline locally and in CI. Real win: the Linux glibc floor is pinned by the container base image instead of the GitHub runner image. The Windows EXE build stays on a native `windows-latest` runner (Dagger runs Linux containers only). Blocked for now: pin to a stable Dagger release (0.21.x); the 1.0 beta line cannot yet install its Python SDK (`v1@v1` ref bug).

---

## Potential Features (Under Consideration)

### Download Features
- Video preview before download (thumbnail gallery, duration, size estimate)
- Smart quality selection (based on internet speed)
- Live stream recording (save ongoing streams)
- 360° video download support

### Organization
- Custom tags and categories
- Search within download history
- Duplicate detection and management
- Automatic file renaming templates

### Performance
- Multi-connection downloads (faster speeds)
- Download acceleration
- Bandwidth management (limit by time of day)
- Smart caching (avoid re-downloading)

### Integration
- Command-line interface (CLI mode)
- REST API for automation
- Integration with media servers (Plex, Jellyfin, Emby)
- Integration with cloud services

### Accessibility
- High contrast mode
- Screen reader support
- Font size adjustment
- Custom UI scaling

---

## Not Planned / Out of Scope

The following features are **NOT** planned for YT-DLP Studio:

- ❌ Built-in video or media player (use VLC, MPC-HC, or other players)
- ❌ Video editing, including trimming, merging and watermarks (use dedicated video editors)
- ❌ Telegram integration (excluded by the project's software-origin policy)
- ❌ Torrent/P2P downloads (out of scope)
- ❌ DRM-protected content download (illegal)
- ❌ Screen recording (different use case)
- ❌ Browser automation (not needed)

---

## Contributing

We welcome contributions to YT-DLP Studio! If you have ideas for new features or improvements:

1. Check if the feature is already in this roadmap
2. Open a GitHub issue to discuss the feature
3. Submit a pull request with your changes

---

## Version History

Full per-release detail lives in [CHANGELOG.md](CHANGELOG.md) - that file is the source of truth for what shipped in each version. Current released version: **0.3.0** (2026-10-31). Next: **0.3.1** (Linux packages and winget). Earlier private development history (internal 0.1.0 to 0.9.2) is archived in [docs-internal/OLD_CHANGELOG.md](docs-internal/OLD_CHANGELOG.md).

---

**Last Updated:** 2026-10-31
**Current Version:** 0.3.0 released, 0.3.1 next (Public Beta)
**Status:** Active Development

For more information, visit: https://nx1xlab.dev/nxtools
