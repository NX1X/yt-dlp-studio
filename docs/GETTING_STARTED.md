# Getting Started with YT-DLP Studio

A practical guide to using YT-DLP Studio. For installation details see the
[Installation Guide](INSTALLATION_GUIDE.md); for contributing see the
[Development Guide](DEVELOPMENT.md).

---

## ⚠️ Supported Sites (Beta)

YT-DLP Studio is in **public beta**. Right now **only YouTube is officially
supported and tested** (videos, playlists, and channels).

The underlying engine (yt-dlp) can handle many other sites, and broader support
is planned during the beta and ongoing development. Until a site is officially
listed as supported, treat it as untested - it may work, partially work, or
fail. If a site matters to you,
[open a feature request](https://github.com/NX1X/yt-dlp-studio/issues/new/choose).

---

## Install & Launch

**Standalone (no Python):** download the latest `YT-DLP-Studio-Windows.zip` from
[Releases](https://github.com/NX1X/yt-dlp-studio/releases), extract it, and run
`yt-dlp-studio.exe`.

**From source:**

```bash
git clone https://github.com/NX1X/yt-dlp-studio.git
cd yt-dlp-studio
pip install -e .
python launcher.py
```

Requires Python 3.10 or newer. See the
[Installation Guide](INSTALLATION_GUIDE.md) for venv and platform notes.

---

## Basic Download

1. **Paste URL** - copy a YouTube video URL from your browser
2. **Select quality** - choose from the dropdown (Best, 1080p, 720p, 480p, Audio Only)
3. **Choose folder** - pick where to save, or use the default
4. **Click Download** - watch progress (size, speed, ETA)

---

## Video Info Preview

1. Paste a video URL
2. Click "Show Info" (or press Ctrl+Shift+I)
3. See details before downloading: thumbnail, title, duration,
   uploader/channel, view count, upload date, and a description preview

---

## Keyboard Shortcuts

Press **F1** in the app for the full list. Common ones:

**Download tab**
- `Ctrl+V` - paste URL from clipboard
- `Enter` - start download
- `Ctrl+D` - Download Now
- `Ctrl+Shift+Q` - Add to Queue
- `Ctrl+Shift+I` - show video info

**Queue tab**
- `Delete` - remove selected task
- `Ctrl+Up` / `Ctrl+Down` - reorder tasks
- `Space` - start/pause queue

**General**
- `Ctrl+Q` - quit
- `F1` - show shortcuts help

---

## Playlists & Channels

1. Paste a YouTube playlist or channel URL
2. Click "Show Info" or "Add to Queue"
3. The app detects it and shows a dialog listing every video
   (title, duration, uploader; all selected by default)
4. Select or deselect videos as needed
5. Choose a quality for all selected videos
6. Click "Add to Queue" - every selected video is queued

Supported URL forms: playlists (`/playlist?list=...`) and channels
(`/@channel/videos`).

---

## Audio Extraction

1. Select an audio option from the quality dropdown (e.g. "Audio Only")
2. Pick an audio format (MP3, M4A, OPUS, FLAC, WAV)
3. Download as normal

---

## Settings

- **Default Folder** - your preferred download directory
- **Default Quality** - the quality selected by default
- Settings are saved automatically and remembered between sessions

---

## Troubleshooting

**"Invalid URL"** - make sure the URL starts with `https://`, or try another video.

**Non-YouTube site fails** - expected during beta; only YouTube is officially
supported right now.

**"Directory not writable"** - choose a different output folder or fix folder
permissions.

**Extraction error** - the video may be private, removed, or geo-restricted;
check your connection and try another video.

**Log file location**
- Windows: `%APPDATA%\YT-DLP Studio\yt-dlp-studio.log`
- Linux: `~/.config/YT-DLP Studio/yt-dlp-studio.log`

Still stuck? [Open an issue](https://github.com/NX1X/yt-dlp-studio/issues/new/choose)
and include what you did, what happened, and the relevant log lines.
