# YT-DLP Studio

YT-DLP Studio is a desktop app for Windows and Linux that puts a graphical interface on top of [yt-dlp](https://github.com/yt-dlp/yt-dlp).

[![Latest release](https://img.shields.io/github/v/release/NX1X/yt-dlp-studio?label=release)](https://github.com/NX1X/yt-dlp-studio/releases/latest)
[![Build](https://github.com/NX1X/yt-dlp-studio/actions/workflows/build.yml/badge.svg)](https://github.com/NX1X/yt-dlp-studio/actions/workflows/build.yml)
[![License: Apache-2.0](https://img.shields.io/github/license/NX1X/yt-dlp-studio)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)

yt-dlp is a command-line tool. YT-DLP Studio lets you use it without the command line: paste a URL, pick a quality and download. It downloads video and audio from YouTube, Instagram, TikTok, Facebook, X and many more sites.

YT-DLP Studio is part of [NXTools](https://nx1xlab.dev/nxtools), a collection of tools by NX1X. Project website: [studio.nx1xlab.dev](https://studio.nx1xlab.dev).

## Contents

- [Project status](#project-status)
- [Supported sites](#supported-sites)
- [Features](#features)
- [Download and install](#download-and-install)
- [Quick start](#quick-start)
- [FAQ and troubleshooting](#faq-and-troubleshooting)
- [Documentation](#documentation)
- [Languages](#languages)
- [Contributing](#contributing)
- [Security](#security)
- [License](#license)
- [Credits](#credits)

## Project status

YT-DLP Studio is stable. The current release is
[1.0.0](https://github.com/NX1X/yt-dlp-studio/releases/tag/v1.0.0).

Five sites are tested. Every other site is experimental. See [Supported sites](#supported-sites).

## Supported sites

Sites are in two tiers. The Download tab shows the tier next to the URL field: "Tested site" or "Experimental site: may not work". Hover over the label for an explanation.

| Tier | Sites | How they are checked |
|------|-------|----------------------|
| **Tested** | YouTube, Instagram, TikTok, Facebook, X (Twitter) | Before every release |
| **Experimental** | Every other site that yt-dlp supports (more than 1000) | Not tested by YT-DLP Studio |

- **How the checks work:** YouTube and TikTok are covered by the automatic weekly check in CI (one video each, and one playlist for YouTube). Instagram, Facebook and X are checked by hand before each release. TikTok may block the CI runner, and then the check is inconclusive. A site can change at any time, so a tested site can still break between releases.
- **Photo posts:** photos of Instagram and X posts (one photo, a carousel, or a post that mixes photos and videos) download as image files. Facebook photo posts are not supported, and a TikTok photo slideshow gives only its audio.
- **Experimental sites:** the app does not block them. The download may work, partly work or fail.
- **How the app finds the tier:** it compares the host name of the URL with a fixed list. Only exact host names count, so a look-alike host such as `youtube.com.example.net` is experimental, not YouTube.
- **Tested host names:**
  - YouTube: `youtube.com`, `www.youtube.com`, `m.youtube.com`, `music.youtube.com`, `youtu.be`
  - Instagram: `instagram.com`, `www.instagram.com`
  - TikTok: `tiktok.com`, `www.tiktok.com`, `vm.tiktok.com`
  - Facebook: `facebook.com`, `www.facebook.com`, `m.facebook.com`, `fb.watch`
  - X: `x.com`, `www.x.com`, `twitter.com`, `www.twitter.com`, `mobile.twitter.com`

To ask for a site, [open a feature request](https://github.com/NX1X/yt-dlp-studio/issues/new/choose).

## Features

- **Downloads:** paste a URL and download one video, a playlist or a full channel.
- **Video quality:** Best Quality, 8K, 4K, 2K, 1080p, 720p, 480p or 360p.
- **Video containers:** MP4, MKV, WebM, or Auto (yt-dlp chooses).
- **Audio only:** MP3, M4A, OPUS, FLAC, WAV or Vorbis, at 320, 256, 192 or 128 kbps.
- **Queue:** add many URLs and run up to 3 downloads at the same time. The queue is kept when you restart the app.
- **Batch input:** paste a list of URLs or import them from a file.
- **Video info preview:** see the title, thumbnail, duration and other details before you download.
- **Photo posts:** Instagram and X photos (single, carousel or mixed with videos) download as image files.
- **Extras:** subtitles, thumbnails, comments and metadata (JSON).
- **Speed limit:** set a maximum download speed in KB/s.
- **Notifications:** a desktop notification when a download completes or fails, and a sound on success.
- **History:** search past downloads and export them to CSV.
- **Interface:** dark and light themes, English and Hebrew (right-to-left), drag and drop, keyboard shortcuts.
- **Updates:** check for a new release from inside the app. The app checks the SHA-256 of a downloaded update against the digest that GitHub publishes. It never starts an update that it could not verify.

The [Getting Started guide](docs/GETTING_STARTED.md) is a short quick start. The [User Guide](docs/USER_GUIDE.md) explains each feature.

## Download and install

Download every file from the [Releases page](https://github.com/NX1X/yt-dlp-studio/releases/latest). The examples below use version 1.0.0.

### System requirements

- **Windows:** 64-bit. Tested on Windows 11. Windows 10 should work but is not tested.
- **Linux:** 64-bit (x86_64) with glibc 2.35 or later. This includes Ubuntu 22.04+, Debian 12+, Fedora 36+, Linux Mint 21+, Arch and most distributions from 2022 and later.
- **Run from source:** Python 3.11 or later, on Windows or Linux.

The Linux builds need no Python. They also run on Ubuntu 22.04, whose system Python is 3.10.

### Windows

| File | Type | Notes |
|------|------|-------|
| `YT-DLP-Studio-Setup-1.0.0.exe` | Installer (recommended) | Installs per user. No admin rights. Updates itself in place. |
| `YT-DLP.Studio.exe` | Portable EXE | One file. No install. Run it from any folder. |
| `yt-dlp-studio-v1.0.0-Windows.zip` | Portable ZIP | The same portable EXE in a ZIP file. |

All three Windows downloads include FFmpeg and Deno. You do not need to install anything else.

**Installer (recommended):**

1. Download `YT-DLP-Studio-Setup-<version>.exe`.
2. Run it. If SmartScreen shows a warning, see [the FAQ](#windows-shows-a-smartscreen-warning).
3. Start YT-DLP Studio from the Start menu.

The installer puts the app in `%LOCALAPPDATA%\Programs\YT-DLP Studio`. It adds a Start menu shortcut and, if you select it, a desktop shortcut. When a new release is out, the app can download the new installer and update itself in place.

**Portable EXE or ZIP:**

1. Download `YT-DLP.Studio.exe`, or download the ZIP file and extract it.
2. Run the EXE.

A portable copy does not update itself in place. When you update, the app downloads the new portable EXE as a separate file. You can delete the old copy afterwards.

### Linux

Linux packages are available for 0.3.1 and later.

| Distribution | File | Install command |
|--------------|------|-----------------|
| Debian, Ubuntu, Mint | `yt-dlp-studio_1.0.0_amd64.deb` | `sudo apt install ./yt-dlp-studio_*_amd64.deb` |
| Fedora, openSUSE | `yt-dlp-studio-1.0.0-1.x86_64.rpm` | `sudo dnf install ./yt-dlp-studio-*.rpm` (openSUSE: `sudo zypper install ./yt-dlp-studio-*.rpm`) |
| Any distribution | `YT-DLP-Studio-1.0.0-x86_64.AppImage` | `chmod +x YT-DLP-Studio-*.AppImage`, then run the file |
| Any distribution | `yt-dlp-studio-v1.0.0-Linux.tar.gz` | See [Linux archive](#linux-archive-targz) below |

**.deb and .rpm packages:** the package manager installs FFmpeg as a dependency and adds YT-DLP Studio to your app menu. On Fedora, FFmpeg comes from `ffmpeg-free` or from RPM Fusion.

**AppImage:** no install is needed. Install FFmpeg yourself first (see the table below). Your desktop may offer to add the AppImage to the app menu.

**FFmpeg:** the AppImage and the Linux archive need FFmpeg from your distribution.

| Distribution | Command |
|--------------|---------|
| Debian, Ubuntu, Mint | `sudo apt install ffmpeg` |
| Fedora, RHEL | `sudo dnf install ffmpeg` (may need RPM Fusion) |
| Arch, Manjaro | `sudo pacman -S ffmpeg` |
| openSUSE | `sudo zypper install ffmpeg` |
| Alpine | `sudo apk add ffmpeg` |

**Deno:** the Linux builds do not include Deno. yt-dlp uses Deno to solve YouTube's JavaScript challenges. Without Deno, the app still works, but YouTube may offer fewer formats. To use Deno, install it from [deno.land](https://deno.land/) and make sure `deno` is on your `PATH`.

#### Linux archive (.tar.gz)

1. Install FFmpeg (see the table above).
2. Download `yt-dlp-studio-v<version>-Linux.tar.gz`.
3. Extract the archive:

   ```bash
   tar -xzf yt-dlp-studio-*-Linux.tar.gz
   ```

4. Add the app to your app menu (installs to `~/.local`, no root needed):

   ```bash
   ./install.sh
   ```

5. Start YT-DLP Studio from your app menu, or run `yt-dlp-studio`.

`install.sh` works on any desktop that follows the XDG specification (GNOME, KDE, XFCE, Cinnamon and others). To remove the app, run `./uninstall.sh`. To run the binary without installing it, run `chmod +x yt-dlp-studio && ./yt-dlp-studio`.

### Run from source

You need Python 3.11 or later and Git. On Linux, install FFmpeg first (see the table above).

```bash
git clone https://github.com/NX1X/yt-dlp-studio.git
cd yt-dlp-studio
pip install -e .
python launcher.py
```

When you run from source, the app downloads Deno 2.9.8 on the first start if it cannot find Deno. The download is about 30 MB.

The [Installation Guide](docs/INSTALLATION_GUIDE.md) has more detail, including a virtual environment setup and how to uninstall.

## Quick start

1. Copy a YouTube video, playlist or channel URL from your browser.
2. Paste it into the URL field (`Ctrl+V`).
3. Select a quality and a format.
4. Select the output folder, or keep the default (your `Downloads` folder).
5. Click **Download Now**, or click **Add to Queue** to download it later.

For a playlist or channel, the app shows a list of all videos. Select the videos you want, then add them to the queue. The About tab lists all keyboard shortcuts.

## FAQ and troubleshooting

### Windows shows a SmartScreen warning

The Windows EXE files are not code-signed (no Authenticode signature). For this reason, SmartScreen may show an "Unknown publisher" warning the first time you run them.

1. Optional: verify the file first (see [Verify a download](#verify-a-download)).
2. Click **More info**.
3. Click **Run anyway**.

[docs/CODE_SIGNING.md](docs/CODE_SIGNING.md) explains the plan to sign future releases.

### Verify a download

Each release publishes a signed build provenance attestation. It covers the portable EXE, the Linux binary, the AppImage, the .deb and the .rpm. It does not cover the Windows installer. To verify a file, install the [GitHub CLI](https://cli.github.com/) and run:

```bash
gh attestation verify "YT-DLP.Studio.exe" --repo NX1X/yt-dlp-studio
```

If the command fails, do not run the file. [SECURITY.md](SECURITY.md#verifying-a-downloaded-release) has the details.

### Where are my settings, history and logs?

They are in the app data folder:

| System | App data folder |
|--------|-----------------|
| Windows | `%APPDATA%\YT-DLP Studio` |
| Linux | `~/.config/YT-DLP Studio` |

The app data folder holds the settings (`yt-dlp-studio_config.json`), the language choice (`language.json`), the log (`yt-dlp-studio.log`), the download history, the saved queue and crash reports (`crashes`). The Settings tab shows the paths to the log, crash reports and settings file.

If one of these files is damaged, the app keeps a copy with `.bad` at the end of the name (for example `download_history.json.bad`) and starts with defaults. If a file was saved by a newer version of the app, the app keeps a copy with `.v<N>.bak` at the end (for example `yt-dlp-studio_config.json.v2.bak`) before it saves the file.

Versions up to 0.4.0 stored the language choice in `.yt-dlp-studio` in your home folder. The app moves that file into the app data folder on the next start, and deletes the old folder if it is empty.

### How do I uninstall? Do I lose my data?

Uninstalling never deletes your downloaded videos. It keeps the app data folder unless you ask to delete it.

- **Installer:** uninstall from Windows Settings, in the list of installed apps. The uninstaller asks if it should also delete your settings, history and logs. The default answer is No.
- **Portable EXE or ZIP:** delete the EXE file.
- **.deb or .rpm:** remove the package with `apt` or `dnf`. Removing or purging the package keeps the app data folder.
- **AppImage:** delete the AppImage file.
- **Linux archive:** run `./uninstall.sh`.

To delete your settings and history too, delete the app data folder by hand.

### A site fails

If the label next to the URL field says "Experimental site: may not work", the site is not tested by YT-DLP Studio, and a failure can be expected. If a tested site fails, [report a bug](https://github.com/NX1X/yt-dlp-studio/issues/new/choose). See [Supported sites](#supported-sites).

### "Invalid URL"

Make sure the URL starts with `http://` or `https://`. You can also try another video.

### "Directory not writable"

Select a different output folder, or fix the permissions of the folder.

### Extraction error

The video may be private, removed or geo-restricted. Check your internet connection and try another video.

### Does it work on macOS?

No. YT-DLP Studio supports Windows and Linux. Windows releases are tested on Windows 11. Windows 10 should work but is not tested. macOS support is possible later.

### Why are the Windows downloads so large?

The Windows downloads are about 200 MB (0.3.1). They include Python, PySide6, yt-dlp, FFmpeg and Deno, so you do not need to install anything else.

### Is it free? Can I use it commercially?

Yes. YT-DLP Studio is free and open source under the [Apache License 2.0](LICENSE). The license permits commercial use, modification and redistribution, if you keep the copyright and license notices.

### Report a bug

1. Open an [issue](https://github.com/NX1X/yt-dlp-studio/issues/new/choose) with the Bug Report template.
2. Describe what you tried, what happened and the steps to reproduce it.
3. Add your operating system, the app version and the relevant lines from the log file.

## Documentation

- [Getting Started](docs/GETTING_STARTED.md): a short quick start: install, first download, where files go.
- [User Guide](docs/USER_GUIDE.md): every tab and setting, and common tasks.
- [Troubleshooting](docs/TROUBLESHOOTING.md): fixes for common problems, and how to report an issue.
- [Installation Guide](docs/INSTALLATION_GUIDE.md): all install options, run from source, uninstall.
- [Translating](docs/TRANSLATING.md): add or improve a language, with or without code.
- [Development Guide](docs/DEVELOPMENT.md): set up a development environment, test and build.
- [Architecture](docs/ARCHITECTURE.md): code structure and design.
- [Roadmap](ROADMAP.md): planned features.
- [Changelog](CHANGELOG.md): changes in each release.

## Languages

The app speaks English and Hebrew today. Help is wanted for other languages. You do not need to write code: fill in a spreadsheet and send it. See [docs/TRANSLATING.md](docs/TRANSLATING.md).

## Contributing

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before you open a pull request. This project follows the [Code of Conduct](CODE_OF_CONDUCT.md).

## Security

Do not report security problems in public issues. [SECURITY.md](SECURITY.md) explains how to report them privately.

## License

Copyright 2024-present NX1X. Licensed under the [Apache License, Version 2.0](LICENSE).

Bundled third-party components keep their own licenses. Inclusion in this project does not relicense them under Apache-2.0. See [NOTICE](NOTICE).

| Component | License |
|-----------|---------|
| PySide6 | LGPL v3 |
| yt-dlp | The Unlicense (public domain) |
| FFmpeg | LGPL or GPL, depending on the build |
| Deno | MIT |

## Credits

YT-DLP Studio is built on these open-source projects:

- [yt-dlp](https://github.com/yt-dlp/yt-dlp): the download engine (The Unlicense).
- [FFmpeg](https://ffmpeg.org/): audio and video processing (LGPL/GPL).
- [Deno](https://deno.land/): JavaScript runtime for YouTube JavaScript challenges (MIT).
- [PySide6 / Qt 6](https://www.qt.io/qt-for-python): the GUI framework (LGPL).
- [Python](https://www.python.org/): the programming language (PSF License).
- [PyInstaller](https://pyinstaller.org/): builds the executables (GPL).
- [UPX](https://upx.github.io/): compresses the executables (GPL).

Thanks to all contributors and users.

## Contact and support

- Issues: [github.com/NX1X/yt-dlp-studio/issues](https://github.com/NX1X/yt-dlp-studio/issues)
- Maintainer: [nx1xlab.dev](https://nx1xlab.dev) ([contact](https://nx1xlab.dev/contact), [LinkedIn](https://linkedin.com/in/edenporat))

---

YT-DLP Studio is an independent project. It is not affiliated with, endorsed by or sponsored by YouTube, Google or the yt-dlp project.
