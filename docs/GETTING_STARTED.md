# Getting Started

This guide explains how to use YT-DLP Studio. For install options, see the [Installation Guide](INSTALLATION_GUIDE.md). To contribute, see the [Development Guide](DEVELOPMENT.md).

## Supported sites

YT-DLP Studio is in public beta. Only YouTube is officially supported and tested (videos, playlists and channels).

The download engine (yt-dlp) can handle many other sites, and support for more sites is planned. Until a site is officially listed as supported, treat it as untested: it may work, partly work or fail. If a site is important to you, [open a feature request](https://github.com/NX1X/yt-dlp-studio/issues/new/choose).

## Install and start

- **Windows:** download `YT-DLP-Studio-Setup-<version>.exe` (the installer) from [Releases](https://github.com/NX1X/yt-dlp-studio/releases) and run it. It needs no admin rights and no Python. For a portable copy, download the portable EXE (`YT-DLP.Studio.exe`) or the portable ZIP (`yt-dlp-studio-v<version>-Windows.zip`).
- **Linux:** use the .deb package, the .rpm package, the AppImage or the Linux archive (.tar.gz). The [Installation Guide](INSTALLATION_GUIDE.md#linux) has the commands.
- **From source:** you need Python 3.11 or later.

  ```bash
  git clone https://github.com/NX1X/yt-dlp-studio.git
  cd yt-dlp-studio
  pip install -e .
  python launcher.py
  ```

## The tabs

The main window has five tabs:

| Tab | What it does |
|-----|--------------|
| Download | Enter URLs, select quality and options, start downloads. |
| Queue | See and control all downloads, including downloads started with **Download Now**. |
| History | Search past downloads, export them to CSV, open the download folder. |
| Settings | Default folder, default quality, language, theme, notifications, update checks. |
| About | Version information, credits and the list of keyboard shortcuts. |

## Download a video

1. Copy a YouTube video URL from your browser.
2. Paste the URL into the URL field. You can also drag the URL from the browser into the field.
3. Select a quality.
4. Select a format.
5. Select the output folder, or keep the default.
6. Click **Download Now**.

The progress bar shows the size, speed and time left (ETA).

### Quality options

- **Video:** Best Quality, 8K (4320p), 4K (2160p), 2K (1440p), 1080p (Full HD), 720p (HD), 480p (SD), 360p.
- **Audio only:** Audio 320kbps, Audio 256kbps, Audio 192kbps, Audio 128kbps.

Each video quality is a maximum. yt-dlp downloads the best quality up to that height.

### Format options

- **Video containers:** MP4 (the default, best compatibility), MKV, WebM, or Auto (yt-dlp chooses).
- **Audio formats** (for audio-only qualities): MP3 (the default), M4A/AAC, OPUS, FLAC (lossless), WAV (uncompressed), Vorbis/OGG.

### Download options

These check boxes are off by default:

- **Thumbnail:** save the video thumbnail as a JPG file.
- **Subtitles:** download subtitles and embed them in the video. You can select the subtitle languages.
- **Metadata:** save the video metadata (description, `info.json`, annotations).
- **Comments:** save the video comments to a separate .txt file. This may be slow for popular videos.

**Speed limit:** set a maximum download speed in KB/s. The value 0 means no limit.

## Extract audio

1. Paste a video URL.
2. Select an audio quality (for example, **Audio 192kbps**).
3. Select an audio format (MP3, M4A, OPUS, FLAC, WAV or Vorbis).
4. Click **Download Now**.

## Preview video info

1. Paste a video URL.
2. Click **Show Info**, or press `Ctrl+Shift+I`.

The preview shows the thumbnail, title, duration, uploader or channel, view count, upload date and the start of the description.

## Use the queue

1. Paste a URL.
2. Click **Add to Queue**, or press `Ctrl+Shift+Q`.
3. Repeat for each video.
4. Open the Queue tab.
5. Click **Start Queue**.

The queue runs up to 3 downloads at the same time. You can pause the queue, reorder tasks, cancel or retry a task, and clear completed or failed tasks. The app saves the queue and restores it when you start the app again.

To add many URLs at once, click **Batch Input**. Paste one URL per line, or import the URLs from a file.

## Download playlists and channels

1. Paste a YouTube playlist or channel URL.
2. Click **Show Info** or **Add to Queue**.
3. The app shows a list of all videos with title, duration and uploader. All videos are selected by default.
4. Clear the videos you do not want.
5. Select one quality for all selected videos.
6. Click **Add to Queue**.

The app adds each selected video to the queue. These URL forms are supported:

- Playlists: `/playlist?list=...`
- Channels: `/@channel/videos`

## Keyboard shortcuts

The About tab lists all shortcuts.

| Where | Shortcut | Action |
|-------|----------|--------|
| Download tab | `Ctrl+V` | Paste the URL from the clipboard |
| Download tab | `Enter` | Start the download |
| Download tab | `Ctrl+D` | Download Now |
| Download tab | `Ctrl+Shift+Q` | Add to Queue |
| Download tab | `Ctrl+Shift+I` | Show video info |
| Queue tab | `Delete` | Remove the selected task |
| Queue tab | `Ctrl+Up` / `Ctrl+Down` | Move the selected task up or down |
| Queue tab | `Space` | Start or pause the queue |
| Anywhere | `Ctrl+Q` | Quit |

## Settings

- **Default folder:** the folder for new downloads. The first default is your `Downloads` folder.
- **Default quality:** the quality that is selected when the app starts.
- **Language:** English or Hebrew. Restart the app after you change the language.
- **Theme:** switch between the dark and light theme.
- **Notifications:** show a desktop notification when a download completes or fails.
- **Update checks:** check for a new release when the app starts (off by default), or check now.

Click **Save Settings** to save your changes. The app keeps them between sessions. The Settings tab also shows the paths to the log file, the crash reports and the settings file.

## Troubleshooting

**"Invalid URL":** make sure the URL starts with `http://` or `https://`, or try another video.

**A site other than YouTube fails:** this is expected during the beta. Only YouTube is officially supported now.

**"Directory not writable":** select a different output folder, or fix the permissions of the folder.

**Extraction error:** the video may be private, removed or geo-restricted. Check your internet connection and try another video.

**Log file location:**

- Windows: `%APPDATA%\YT-DLP Studio\yt-dlp-studio.log`
- Linux: `~/.config/YT-DLP Studio/yt-dlp-studio.log`

If you still have a problem, [open an issue](https://github.com/NX1X/yt-dlp-studio/issues/new/choose). Describe what you did and what happened, and add the relevant log lines.
