# YT-DLP Studio - Roadmap

**Part of NXTools by NX1X**
Website: https://nx1xlab.dev/nxtools

---

## Current Version: 0.1.3 released · 0.2.0 in progress (Public Beta)

> The project is in **public beta**. The core feature set is functional but UI bugs, polish items, and additional UI options remain. We will reach **v1.0.0** when the feature set is stable and beta exit criteria are met (see below).
>
> Latest released: **0.1.3** (supply-chain hardening). In progress: **0.2.0** (Linux/Ubuntu desktop support).
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
- ✅ Queue management system
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

### v0.2.0 - Linux (Ubuntu) Desktop Support  *(in progress)*
First officially built and published Linux desktop package, alongside the existing Windows EXE.
- ✅ Platform-aware FFmpeg / Deno resolution (no hardcoded `.exe`)
- ✅ Linux-aware in-app updater (selects the Linux archive; reveals in file manager)
- ✅ PNG application icon + `.desktop` launcher + hicolor icons
- ✅ `install.sh` / `uninstall.sh` (per-user `~/.local` install, no root; distro-agnostic FFmpeg guidance)
- ✅ Linux build in CI (build + release), with a runtime smoke-launch and Sigstore provenance
- ✅ Wide-distro support: built on glibc 2.35 (Ubuntu 22.04+, Debian 12+, Fedora 36+, Arch, ...)
- ✅ Restored Python 3.10 support (run-from-source on stock Ubuntu 22.04)
- ⬜ Community testing on multiple distributions before promoting to "stable Linux"

### v0.3.0 - Distribution: Installer, Portable & Package Managers
Ship the app the way users on each OS expect to get it, while keeping the no-install option.
- ⬜ **Windows: two artifacts** - the current **portable** EXE/ZIP *plus* a per-user **installer** (Inno Setup, no admin required: Start-menu shortcut, uninstaller, stable install path)
- ⬜ In-place updater enabled by the installer's stable path (retires the "two copies" limitation - see `docs/UPDATE_SERVICE_NOTES.md`)
- ⬜ Updater copy honesty fix in the meantime ("download the new version", not "run the installer")
- ⬜ **Windows package manager: winget** (submit manifest to `microsoft/winget-pkgs`)
- ⬜ **Linux package managers / native packages**: AppImage, plus `.deb` (Debian/Ubuntu) and `.rpm` (Fedora); explore Flatpak / AUR
- ⬜ Note: released binaries remain **unsigned for now** (no code-signing certificate - see the signing plan under v1.0.0); Sigstore provenance already covers cryptographic verification

### v0.4.0 - Enhanced Download Management
- ⬜ Resume interrupted downloads
- ⬜ Download scheduling (download at specific time)
- ⬜ Batch download from text file (multiple URLs)
- ⬜ Browser extension integration (download from browser)
- ⬜ Automatic retry on failure

### v0.5.0 - Advanced Format Options
- ⬜ Custom format string builder (advanced users)
- ⬜ Video codec selection (H.264, H.265, VP9, AV1)
- ⬜ Audio codec selection (AAC, Opus, Vorbis)
- ⬜ Bitrate control for video and audio
- ⬜ Frame rate control

### v0.6.0 - Post-Processing
- ⬜ Built-in video trimmer (cut segments)
- ⬜ Video merger (combine multiple videos)
- ⬜ Watermark addition
- ⬜ Custom FFmpeg post-processing commands
- ⬜ Automatic file organization (by channel, date, etc.)

### v0.7.0 - Social Features
- ⬜ Channel/Playlist monitoring (auto-download new videos)
- ⬜ Download notifications via email/Discord/Telegram
- ⬜ Share download configurations (export/import presets)
- ⬜ Cloud storage integration (Google Drive, Dropbox, OneDrive)

### v1.0.0 - Stable Release / Beta Exit
The first non-beta release. Reached when:
- ⬜ No known critical UI bugs
- ⬜ Feature set frozen (no breaking changes planned for short term)
- ⬜ Config and history file formats stable (backwards-compatibility commitment begins here)
- ⬜ Tested clean on Windows 10 and Windows 11
- ⬜ Documentation complete (user guide, troubleshooting, install guide)
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

### v1.1.0 - More Platforms (macOS / Android)

> **Linux desktop is done** - shipped in **v0.2.0** (platform-aware binary resolution, `.desktop` + PNG icons, `install.sh`, Linux CI build with smoke-launch). Native Linux packages (AppImage / `.deb` / `.rpm` / Flatpak) are tracked under **v0.3.0**.

- ⬜ macOS build (.app, .dmg) - PyInstaller is platform-native, so this needs a macOS CI runner
- ⬜ Android app (mobile version) - separate effort, likely a different UI toolkit

### v2.0.0 - Major Overhaul
- ⬜ Complete UI redesign (modern, sleek interface)
- ⬜ Plugin system (community extensions)
- ⬜ Web interface (browser-based control)
- ⬜ API server (remote control)
- ⬜ Multi-threaded downloads (concurrent downloads)
- ⬜ Download manager improvements
- ⬜ Built-in media player (preview before download)

---

## Potential Features (Under Consideration)

### Download Features
- Video preview before download (thumbnail gallery, duration, size estimate)
- Smart quality selection (based on internet speed)
- Age-restricted video support (authentication)
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

- ❌ Built-in video player (use VLC, MPC-HC, or other players)
- ❌ Video editing suite (use dedicated video editors)
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

Full per-release detail lives in [CHANGELOG.md](CHANGELOG.md) - that file is the source of truth for what shipped in each version. Current released version: **0.1.3** (2026-07-11). In progress: **0.2.0** (Linux desktop support). Earlier private development history (internal 0.1.0 to 0.9.2) is archived in [docs-internal/OLD_CHANGELOG.md](docs-internal/OLD_CHANGELOG.md).

---

**Last Updated:** 2026-07-12
**Current Version:** 0.1.3 released, 0.2.0 in progress (Public Beta)
**Status:** Active Development

For more information, visit: https://nx1xlab.dev/nxtools
