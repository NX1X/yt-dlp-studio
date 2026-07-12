# YT-DLP Studio v0.2.0 - Release Notes

**Release Date:** 2026-07-11
**Status:** Public Beta

> This file describes the **current release**. For full per-version history, see [CHANGELOG.md](CHANGELOG.md). For planned future work, see [ROADMAP.md](ROADMAP.md).
>
> The project was developed privately prior to the public beta - that archived history lives in [docs-internal/OLD_CHANGELOG.md](docs-internal/OLD_CHANGELOG.md).

---

## What is YT-DLP Studio?

A user-friendly desktop GUI for [yt-dlp](https://github.com/yt-dlp/yt-dlp) - download videos and audio from YouTube without touching the command line.

This is a **public beta**. The core feature set is functional and the app is usable for daily downloads, but expect rough edges and bug fixes in subsequent 0.x releases. We will tag **v1.0.0** when the feature set is stable and the beta exit criteria (in [ROADMAP.md](ROADMAP.md)) are met.

---

## What's new in v0.2.0

**Linux (Ubuntu) desktop support.** This release adds an officially built and published Linux package alongside the Windows EXE.

- New `yt-dlp-studio-<version>-Linux.tar.gz` release artifact: a self-contained PyInstaller binary plus a desktop-integration bundle.
- `install.sh` adds YT-DLP Studio to the Ubuntu application menu / dock (icon + `.desktop` launcher) with no root required; `uninstall.sh` removes it.
- The in-app updater is now Linux-aware: it downloads the Linux archive and reveals it in the file manager instead of trying to run a Windows installer.
- Platform-aware FFmpeg/Deno resolution, a signed build-provenance attestation for the Linux binary, and a Linux build leg in CI so Linux regressions are caught before merge.

See [CHANGELOG.md](CHANGELOG.md) for the full list, including the frozen-build `NameError` fix.

---

## Installation

### Windows
Download `yt-dlp-studio-<version>-Windows.zip` from the [Releases page](https://github.com/NX1X/yt-dlp-studio/releases), extract, and run `yt-dlp-studio.exe`. FFmpeg and Deno are bundled - no dependencies.

### Linux (Ubuntu)
```bash
sudo apt install ffmpeg                      # required
tar -xzf yt-dlp-studio-*-Linux.tar.gz
./install.sh                                 # installs to ~/.local, no root
```
Then launch from your app menu or run `yt-dlp-studio`. Deno is downloaded automatically on first run. Run `./uninstall.sh` to remove it.

### From source (developers)
```bash
git clone https://github.com/NX1X/yt-dlp-studio.git
cd yt-dlp-studio
pip install -e .
python launcher.py
```
Requires Python 3.10+. On Linux, install FFmpeg first (`sudo apt install ffmpeg`).

---

## System Requirements

- **OS:** Windows 10/11 (64-bit), or Linux 64-bit with glibc 2.31+ (tested on Ubuntu 22.04+)
- **RAM:** 512 MB minimum, 2 GB recommended
- **Disk:** 200 MB for the app + space for downloads
- **Internet:** Required for downloads
- **Linux only:** system FFmpeg (`sudo apt install ffmpeg`)

macOS support is on the roadmap (see [ROADMAP.md](ROADMAP.md)).

---

## Known Beta Limitations

- Some UI options could be more discoverable
- Resume of interrupted downloads is not yet supported
- macOS build not yet available

If you hit something unexpected, please open an [issue](https://github.com/NX1X/yt-dlp-studio/issues) - beta feedback shapes the path to v1.0.0.

---

## Support

- **Bug reports & feature requests:** [GitHub Issues](https://github.com/NX1X/yt-dlp-studio/issues)
- **Discussion:** [GitHub Discussions](https://github.com/NX1X/yt-dlp-studio/discussions)
- **Log file location:** Windows `%APPDATA%\YT-DLP Studio\yt-dlp-studio.log`, Linux `~/.config/YT-DLP Studio/yt-dlp-studio.log`

---

## License

Apache License 2.0 - see [LICENSE](LICENSE).

---

**YT-DLP Studio** is part of the [NXTools](https://nx1xlab.dev/nxtools) collection by NX1X.
