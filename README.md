# YT-DLP Studio

<div align="center">

[![Version](https://img.shields.io/github/v/release/NX1X/yt-dlp-studio?label=version&color=blue)](https://github.com/NX1X/yt-dlp-studio/releases)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-blue)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue.svg)](https://www.python.org/)
[![Build YT-DLP Studio](https://github.com/NX1X/yt-dlp-studio/actions/workflows/build.yml/badge.svg)](https://github.com/NX1X/yt-dlp-studio/actions/workflows/build.yml)
[![Release](https://github.com/NX1X/yt-dlp-studio/actions/workflows/release.yml/badge.svg)](https://github.com/NX1X/yt-dlp-studio/actions/workflows/release.yml)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Support-yellow?logo=buy-me-a-coffee&logoColor=white)](https://buymeacoffee.com/nx1x)
![Views](https://visitor-badge.laobi.icu/badge?page_id=NX1X.yt-dlp-studio)

**A user-friendly GUI for yt-dlp**

Download videos from YouTube with a simple, intuitive interface - more sites coming during the beta.

</div>

---

### Part of NXTools 🔧

This tool is part of **[NXTools](https://nx1xlab.dev/nxtools)** by **NX1X** - a collection of productivity and development tools.

- **Website:** https://nx1xlab.dev/nxtools
- **Main Site:** https://nx1xlab.dev
- **Support Development:** https://buymeacoffee.com/nx1x

---

## 💡 Why I Built This

I was looking for a feature-rich, modern tool to download videos from YouTube
and other sites. yt-dlp is an awesome tool, but it's command-line only, so a lot
of people never get the most out of it. I built YT-DLP Studio to put a clean,
intuitive UI on top of it so anyone can use its full power without touching the
CLI.

Have a feature request or feedback? I'd love to hear it:

- Open a [feature request](https://github.com/NX1X/yt-dlp-studio/issues/new/choose) in the Issues tab
- Connect on [LinkedIn](https://linkedin.com/in/edenporat)
- Reach out via my [website](https://nx1xlab.dev/contact)

---

## ✨ Features

- 🎥 **Easy downloads** - paste a URL and click; works with playlists and full channels
- ⚡ **Quality options** - Best, 8K, 4K, 2K, 1080p, 720p, 480p, 360p
- 🎵 **Audio extraction** - MP3, M4A, OPUS, FLAC, WAV, Vorbis at multiple bitrates
- 📦 **Format selection** - MP4, MKV, WebM containers
- 🎬 **YouTube** - videos, playlists, and full channels (more sites planned)
- 📋 **Download queue** - queue many videos, up to 3 concurrent downloads
- 🔍 **Info preview** - title, thumbnail, duration before downloading
- 💬 **Extras** - comments, subtitles, thumbnails, and metadata (JSON)
- ⚡ **Speed limiting** - cap download bandwidth
- 🔔 **Alerts** - audio/visual notification when downloads finish or fail
- ⌨️ **Keyboard shortcuts** - paste, download, and queue without the mouse
- 🎨 **Dark/Light theme** and 🌍 **multi-language** (English, Hebrew RTL)
- 🖱️ **Drag & drop**, custom output folder, persistent settings, download history

See the [Getting Started guide](docs/GETTING_STARTED.md) for how to use each feature.

---

## 🚀 Quick Start

**Requirements:** Windows 10/11 (Linux support in progress). Python 3.10+ only if
running from source.

### Option 1: Standalone executable (no Python)

1. Download the latest `YT-DLP-Studio-Windows.zip` from [Releases](https://github.com/NX1X/yt-dlp-studio/releases)
2. Extract and run `yt-dlp-studio.exe`

### Option 2: Run from source

```bash
git clone https://github.com/NX1X/yt-dlp-studio.git
cd yt-dlp-studio
pip install -e .
python launcher.py
```

Full details: [Installation Guide](docs/INSTALLATION_GUIDE.md) ·
[Getting Started](docs/GETTING_STARTED.md)

---

## 🎯 Supported Sites

YT-DLP Studio is in **public beta**. Right now **YouTube is the only officially
supported and tested site** (videos, playlists, and channels).

It's built on [yt-dlp](https://github.com/yt-dlp/yt-dlp), which supports 1000+
sites under the hood, so broader support is planned during the beta and ongoing
development. Until a site is officially listed here, treat it as untested. Want a
specific site? [Open a feature request](https://github.com/NX1X/yt-dlp-studio/issues/new/choose).

---

## 📚 Documentation

- [Getting Started](docs/GETTING_STARTED.md) - using the app, shortcuts, playlists
- [Installation Guide](docs/INSTALLATION_GUIDE.md) - setup and build
- [Architecture](docs/ARCHITECTURE.md) - code structure and design
- [Development](docs/DEVELOPMENT.md) - how to contribute and build from source
- [Roadmap](ROADMAP.md) - planned features · [Changelog](CHANGELOG.md) - what shipped

---

## 🤝 Contributing

Contributions are welcome. Please read [ARCHITECTURE.md](docs/ARCHITECTURE.md)
and [DEVELOPMENT.md](docs/DEVELOPMENT.md), keep files small and focused, add
tests and documentation, and open a pull request.

---

## 🐛 Bug Reports

[Open an issue](https://github.com/NX1X/yt-dlp-studio/issues/new/choose) using the
Bug Report template. Include what you tried, what happened, steps to reproduce,
your OS/Python version, and relevant log lines.

**Log file location**
- Windows: `%APPDATA%\YT-DLP Studio\yt-dlp-studio.log`
- Linux: `~/.config/YT-DLP Studio/yt-dlp-studio.log`

---

## 📄 License

**License:** [Apache License 2.0](LICENSE)

Copyright © 2024–2026 NX1X. Licensed under the Apache License, Version 2.0.
You may obtain a copy at https://www.apache.org/licenses/LICENSE-2.0.

### Bundled / Third-Party Components

- **PySide6** - LGPL v3
- **yt-dlp** - The Unlicense (Public Domain)
- **FFmpeg** - LGPL/GPL depending on build
- **Deno** - MIT License

These components retain their original licenses and are not relicensed under
Apache-2.0 by inclusion in this project. See [LICENSE](LICENSE) for the full
notice.

---

## 💝 Acknowledgments

Built with and thanks to these open source projects:

- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** - the video downloader engine (Unlicense)
- **[FFmpeg](https://ffmpeg.org/)** - multimedia processing (LGPL/GPL)
- **[Deno](https://deno.land/)** - JavaScript runtime for YouTube JS challenges (MIT)
- **[Python](https://www.python.org/)** - programming language (PSF License)
- **[PySide6/Qt6](https://www.qt.io/qt-for-python)** - GUI framework (LGPL)
- **[PyInstaller](https://pyinstaller.org/)** - executable bundler (GPL)
- **[UPX](https://upx.github.io/)** - executable compressor (GPL)

Special thanks to all contributors, users, and everyone who supports
development ☕.

---

## ❓ FAQ

**Is this free?** Yes - free and open source under the [Apache 2.0 license](LICENSE).

**Can I use it commercially?** Yes - Apache 2.0 permits commercial use,
modification, and redistribution, provided you preserve copyright and license
notices.

**Is it safe?** All downloads go through yt-dlp, which is trusted by millions.

**Does it work on macOS?** Not currently. Windows 10/11 now, Linux in progress,
macOS possibly later.

**Why is the exe so large (~100MB)?** It bundles Python, PySide6, and yt-dlp so
it runs with no installation.

---

## 📞 Contact & Links

- **Issues:** [github.com/NX1X/yt-dlp-studio/issues](https://github.com/NX1X/yt-dlp-studio/issues)
- **Discussions:** [github.com/NX1X/yt-dlp-studio/discussions](https://github.com/NX1X/yt-dlp-studio/discussions)
- **Security:** see [SECURITY.md](SECURITY.md)
- **Maintainer:** [nx1xlab.dev](https://nx1xlab.dev) · [LinkedIn](https://linkedin.com/in/edenporat)
- **Support:** [Buy Me a Coffee](https://buymeacoffee.com/nx1x)

If you find this useful, please star the repository! ⭐

---

**Made with ❤️ for the community**

*YT-DLP Studio is not affiliated with yt-dlp or YouTube.*
