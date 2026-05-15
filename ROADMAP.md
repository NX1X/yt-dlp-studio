# YT-DLP Studio - Roadmap

**Part of NXTools by NX1X**
Website: https://nx1xlab.dev/nxtools

---

## Current Version: 0.1.0 (Public Beta)

> The project is in its **first public beta**. The core feature set is functional but UI bugs, polish items, and additional UI options remain. We will reach **v1.0.0** when the feature set is stable and beta exit criteria are met (see below).
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

### v0.2.0 - Stabilization & UI Polish
Focused on the public beta feedback: bug fixes, UI option improvements, and overall polish.
- ⬜ Fix outstanding UI bugs reported during beta
- ⬜ Add missing UI options (TBD based on user feedback)
- ⬜ Improved error messages and user feedback
- ⬜ Performance/responsiveness pass

### v0.3.0 - Enhanced Download Management
- ⬜ Resume interrupted downloads
- ⬜ Download scheduling (download at specific time)
- ⬜ Batch download from text file (multiple URLs)
- ⬜ Browser extension integration (download from browser)
- ⬜ Automatic retry on failure

### v0.4.0 - Advanced Format Options
- ⬜ Custom format string builder (advanced users)
- ⬜ Video codec selection (H.264, H.265, VP9, AV1)
- ⬜ Audio codec selection (AAC, Opus, Vorbis)
- ⬜ Bitrate control for video and audio
- ⬜ Frame rate control

### v0.5.0 - Post-Processing
- ⬜ Built-in video trimmer (cut segments)
- ⬜ Video merger (combine multiple videos)
- ⬜ Watermark addition
- ⬜ Custom FFmpeg post-processing commands
- ⬜ Automatic file organization (by channel, date, etc.)

### v0.6.0 - Social Features
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

### v1.1.0 - Cross-Platform Support

#### Linux Desktop Build
Foundation already in place: `build_linux.spec` exists, and `src/utils/deno_installer.py` already handles the Linux Deno binary. Remaining work:

**Code changes**
- ⬜ `src/backend/yt_dlp_wrapper.py` - replace hardcoded `ffmpeg.exe` / `deno.exe` lookups with platform-aware binary names
- ⬜ `src/backend/update_checker.py` - detect Linux release assets (`.AppImage`, `.tar.gz`, `.deb`) instead of only `.exe`
- ⬜ `src/ui/update_dialog.py` - use platform-appropriate download filename
- ⬜ Provide a PNG icon alongside the existing `.ico` (Linux menus don't read `.ico`)
- ⬜ Add a `.desktop` file for application menu integration

**Build & distribution**
- ⬜ GitHub Actions `ubuntu-latest` job to run PyInstaller (PyInstaller is platform-native - must build on Linux, no cross-compile)
- ⬜ Primary artifact: **AppImage** (single portable file, bundles FFmpeg, no install required)
- ⬜ Secondary artifacts (optional): `.deb` for Debian/Ubuntu, `.rpm` for Fedora - these can declare `ffmpeg` as a system dependency instead of bundling it
- ⬜ Smoke-test on at least Ubuntu LTS and Fedora before release

#### Other platforms
- ⬜ macOS build (.app, .dmg)
- ⬜ Portable version (no installation required)
- ⬜ Android app (mobile version)

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

Full per-release detail lives in [CHANGELOG.md](CHANGELOG.md) - that file is the source of truth for what shipped in each version. Current released version: **0.1.0** (2026-05-10) - first public beta. Earlier private development history (internal 0.1.0–0.9.2) is archived in [docs-internal/OLD_CHANGELOG.md](docs-internal/OLD_CHANGELOG.md).

---

**Last Updated:** 2026-05-10
**Current Version:** 0.1.0 (Public Beta)
**Status:** Active Development

For more information, visit: https://nx1xlab.dev/nxtools
