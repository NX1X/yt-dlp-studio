# YT-DLP Studio v0.1.0 - Release Notes

**Release Date:** 2026-05-10
**Status:** Public Beta - first public release

> This file describes the **current release**. For full per-version history, see [CHANGELOG.md](CHANGELOG.md). For planned future work, see [ROADMAP.md](ROADMAP.md).
>
> The project was developed privately prior to this point - that archived history lives in [docs-internal/OLD_CHANGELOG.md](docs-internal/OLD_CHANGELOG.md).

---

## What is YT-DLP Studio?

A user-friendly Windows desktop GUI for [yt-dlp](https://github.com/yt-dlp/yt-dlp) - download videos and audio from YouTube without touching the command line. Bundles FFmpeg and the Deno JS runtime, so there are no external dependencies to install.

This is the **first public beta**. The core feature set is functional and the app is usable for daily downloads, but expect rough edges in the UI, missing options, and bug fixes coming in subsequent 0.x releases. We will tag **v1.0.0** when the feature set is stable and beta exit criteria (in [ROADMAP.md](ROADMAP.md)) are met.

---

## What's in v0.1.0

This is the initial public release, so "what's new" is essentially the whole feature set. Highlights:

### Downloads
- Quality selection: Best Quality, 8K, 4K, 2K, 1080p, 720p, 480p, 360p
- Audio-only downloads with bitrate selection (Best/VBR, 320/256/192/128 kbps)
- Audio formats: MP3, M4A/AAC, OPUS, FLAC, WAV, Vorbis/OGG
- Video containers: MP4, MKV, WebM, Auto
- Subtitle, comment, thumbnail, and metadata downloads
- Playlist and channel support with per-video selection
- Download queue with up to 3 concurrent downloads
- Speed limiting, auto-numbering for duplicates

### User experience
- English and Hebrew UI with full RTL layout
- Dark / Light theme toggle, persisted across sessions
- Comprehensive keyboard shortcuts
- System tray notifications and audio alerts
- In-app update checker

### Build
- Single-file Windows EXE (Windows 10/11, 64-bit)
- Bundled FFmpeg, bundled Deno v2.6.10 JS runtime
- No external dependencies for end users

See [CHANGELOG.md](CHANGELOG.md) for the full list.

---

## Installation

### Windows (Recommended)
Download `YT-DLP Studio.exe` from the [Releases page](https://github.com/NX1X/yt-dlp-studio/releases) and run it. No installer, no dependencies.

### From Source (Developers)
```powershell
git clone https://github.com/NX1X/yt-dlp-studio.git
cd yt-dlp-studio
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python launcher.py
```

Requires Python 3.10+ on Windows 10/11.

---

## System Requirements

- **OS:** Windows 10 or Windows 11 (64-bit)
- **RAM:** 512 MB minimum, 2 GB recommended
- **Disk:** 200 MB for the app + space for downloads
- **Internet:** Required for downloads

Linux and macOS support is on the roadmap (see [ROADMAP.md](ROADMAP.md) - `v1.1.0`).

---

## Known Beta Limitations

This is a beta release. Known areas needing improvement:
- Some UI options are still missing or could be more discoverable
- A handful of UI bugs are tracked for the next release (`v0.2.0` stabilization)
- Resume of interrupted downloads is not yet supported
- Linux build not yet available (planned post-`v1.0.0`)

If you hit something unexpected, please open an [issue](https://github.com/NX1X/yt-dlp-studio/issues) - beta feedback shapes the path to v1.0.0.

---

## Support

- **Bug reports & feature requests:** [GitHub Issues](https://github.com/NX1X/yt-dlp-studio/issues)
- **Discussion:** [GitHub Discussions](https://github.com/NX1X/yt-dlp-studio/discussions)
- **Log file location:** `%APPDATA%\yt-dlp-studio\yt-dlp-studio.log`

---

## License

Apache License 2.0 - see [LICENSE](LICENSE).

---

**YT-DLP Studio** is part of the [NXTools](https://nx1xlab.dev/nxtools) collection by NX1X.
