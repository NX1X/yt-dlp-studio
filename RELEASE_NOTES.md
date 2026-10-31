# YT-DLP Studio v0.3.0 - Release Notes

**Release Date:** 2026-10-31
**Status:** Public Beta

> This file describes the **current release**. For full per-version history, see [CHANGELOG.md](CHANGELOG.md). For planned future work, see [ROADMAP.md](ROADMAP.md).
>
> The project was developed privately prior to the public beta - that archived history lives in [docs-internal/OLD_CHANGELOG.md](docs-internal/OLD_CHANGELOG.md).

---

## What is YT-DLP Studio?

A user-friendly desktop GUI for [yt-dlp](https://github.com/yt-dlp/yt-dlp) - download videos and audio from YouTube without touching the command line.

This is a **public beta**. The core feature set is functional and the app is usable for daily downloads, but expect rough edges and bug fixes in subsequent 0.x releases. We will tag **v1.0.0** when the feature set is stable and the beta exit criteria (in [ROADMAP.md](ROADMAP.md)) are met.

---

## What's new in v0.3.0

**An installer, and updates that replace the app.**

- **Install it like a normal Windows app.** Download `YT-DLP-Studio-Setup-0.3.0.exe` and run it. It needs no admin rights and adds a Start-menu shortcut. The portable EXE and ZIP are still available.
- **Updates install themselves.** If you used the installer, accepting an update now installs it and restarts the app. No second copy in your Downloads folder.
- **Uninstalling keeps your data.** Your settings and download history stay, unless you choose to delete them.
- **Your queue survives a restart.** Close the app with downloads waiting, and they are still there next time.
- **Retry failed downloads** with one click, or let the app retry a dropped connection once on its own.
- **Notifications work.** You now get a notice when a download finishes.
- **Newer download engine and tools:** yt-dlp 2026.10.26 (with the latest YouTube fixes), Deno 2.9.8 and FFmpeg 9.0.2.
- **The real file name everywhere.** The Queue tab, notifications and "Open file" now use the actual file, and the History tab finally records your downloads.

Coming from v0.2.x? Install v0.3.0 with the new installer once; after that, updates install themselves. Your settings and history carry over. Running from source now needs Python 3.11 or newer. Full detail is in [CHANGELOG.md](CHANGELOG.md).

---

## What was new in v0.2.0

**Linux (Ubuntu) desktop support.** This release adds an officially built and published Linux package alongside the Windows EXE.

- New `yt-dlp-studio-<version>-Linux.tar.gz` release artifact: a self-contained PyInstaller binary plus a desktop-integration bundle.
- `install.sh` adds YT-DLP Studio to the Ubuntu application menu / dock (icon + `.desktop` launcher) with no root required; `uninstall.sh` removes it.
- The in-app updater is now Linux-aware: it downloads the Linux archive and reveals it in the file manager instead of trying to run a Windows installer.
- Platform-aware FFmpeg/Deno resolution, a signed build-provenance attestation for the Linux binary, and a Linux build leg in CI so Linux regressions are caught before merge.

See [CHANGELOG.md](CHANGELOG.md) for the full list, including the frozen-build `NameError` fix.

---

## Installation

### Windows
Download `YT-DLP-Studio-Setup-<version>.exe` from the [Releases page](https://github.com/NX1X/yt-dlp-studio/releases) and run it. It needs no admin rights. FFmpeg and Deno are bundled, so there are no dependencies.

For a portable copy, download `yt-dlp-studio-<version>-Windows.zip`, extract it and run `yt-dlp-studio.exe`.

### Linux (any glibc 2.35+ distro, not just Ubuntu)
```bash
# Install FFmpeg with your package manager (required):
#   Debian/Ubuntu: sudo apt install ffmpeg
#   Fedora/RHEL:   sudo dnf install ffmpeg
#   Arch:          sudo pacman -S ffmpeg
#   openSUSE:      sudo zypper install ffmpeg
tar -xzf yt-dlp-studio-*-Linux.tar.gz
./install.sh                                 # installs to ~/.local, no root
```
Then launch from your app menu or run `yt-dlp-studio`. `install.sh` prints the right FFmpeg command for your package manager if it's missing. Deno is downloaded automatically on first run. Run `./uninstall.sh` to remove it.

### From source (developers)
```bash
git clone https://github.com/NX1X/yt-dlp-studio.git
cd yt-dlp-studio
pip install -e .
python launcher.py
```
Requires Python 3.11+. On Linux, install FFmpeg first (`sudo apt install ffmpeg`).

---

## System Requirements

- **OS:** Windows 10/11 (64-bit), or 64-bit Linux with glibc 2.35+ (Ubuntu 22.04+, Debian 12+, Fedora 36+, Mint 21+, Arch, and most 2022-and-later distributions)
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
