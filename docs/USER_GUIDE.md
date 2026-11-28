# User Guide

This guide explains every tab and setting of YT-DLP Studio, and how to do common tasks. For install steps, see the [Installation Guide](INSTALLATION_GUIDE.md). If something goes wrong, see [Troubleshooting](TROUBLESHOOTING.md).

This guide names tabs, buttons and settings by their label in the English interface. It does not describe where they are on the screen, because the layout can change.

## Contents

- [Before you start](#before-you-start)
- [Download tab](#download-tab)
- [Queue tab](#queue-tab)
- [History tab](#history-tab)
- [Settings tab](#settings-tab)
- [About tab](#about-tab)
- [Common tasks](#common-tasks)
- [Where your files go](#where-your-files-go)

## Before you start

- **Platforms:** Tested on Windows 11. Windows 10 should work but is not tested. Linux builds are also available.
- **Supported sites:** the app is in public beta. Next to the URL field, the app shows "Tested site" or "Experimental site: may not work".
  - Tested sites: YouTube, Instagram, TikTok, Facebook and X.
  - Experimental sites: every other site that yt-dlp supports. A download can work, partly work or fail. The app does not block it.
- **FFmpeg:** the Windows builds include FFmpeg. On Linux, the .deb and .rpm packages install it. For the AppImage and the .tar.gz archive, install FFmpeg yourself.

## Download tab

Use the Download tab to start a download now, or to add it to the queue.

### Fields and buttons

| Control | What it does |
|---------|--------------|
| URL | The video, playlist or channel address. You can type it, paste it or drag it into the field. |
| Paste | Pastes the URL from the clipboard. Shortcut: `Ctrl+V`. |
| Show Info | Shows the title, thumbnail, duration and other details before you download. Shortcut: `Ctrl+Shift+I`. |
| Download Type | **Video** or **Audio Only**. |
| Quality | The maximum quality (video) or the bit rate (audio). |
| Video Format | The video container: MP4, MKV, WebM or Auto. |
| Audio Format | The audio format for **Audio Only**: MP3, M4A/AAC, OPUS, FLAC, WAV or Vorbis/OGG. |
| Save to | The output folder. Click **Browse** to change it. Click **Open** to open the folder. |
| Speed Limit | A maximum speed in KB/s. Zero means no limit. |
| Download Now | Starts the download at once. Shortcut: `Ctrl+D`. |
| Add to Queue | Adds the download to the queue. Shortcut: `Ctrl+Shift+Q`. |
| Batch Input | Adds many URLs at once (see [Batch input](#batch-input)). |
| Show Advanced Log | Shows the log of the current download in the window. |

Quality choices for video: Best Quality, 8K (4320p), 4K (2160p), 2K (1440p), 1080p (Full HD), 720p (HD), 480p (SD) and 360p. Each choice is a maximum. yt-dlp downloads the best quality up to that height.

Quality choices for audio: Audio 320kbps, Audio 256kbps, Audio 192kbps and Audio 128kbps.

### Extra files

These check boxes are off by default.

| Check box | What it does |
|-----------|--------------|
| Download Thumbnail | Saves the thumbnail as a JPG file. |
| Download Subtitles | Downloads subtitles and embeds them. Enter language codes in **Languages**, for example `en,es,he`. Click **Select Subs...** to choose from the languages that the video has. |
| Download Metadata | Saves the video metadata, including an `.info.json` file and readable text files. |
| Download Comments | Saves the comments to a separate text file. This can be slow for popular videos. |

### Batch input

1. Click **Batch Input**.
2. Paste one URL per line, or click **Import from File**.
3. Click **Validate URLs** to check the list.
4. Click **Add URLs**.

The app adds every valid URL to the queue.

### Playlists and channels

When you enter a playlist or channel URL, the app asks if you want to view and select videos. If you answer Yes, the Playlist Viewer opens.

1. Clear the videos you do not want. All videos are selected by default.
2. Select one quality for all selected videos.
3. Optional: turn on subtitles for every selected video, and select the languages. These settings override the subtitle settings of the Download tab.
4. Add the videos to the queue.

## Queue tab

The Queue tab shows every download that waits, runs or has ended. The queue runs up to 3 downloads at the same time. The app saves the queue and restores it when you start the app again.

| Control | What it does |
|---------|--------------|
| Start Queue / Pause Queue | Starts the queue, or pauses it. Shortcut: `Space`. |
| Stop All | Stops every running download. |
| Move Up / Move Down | Changes the order of the selected task. Shortcuts: `Ctrl+Up`, `Ctrl+Down`. |
| Remove | Removes the selected task. Shortcut: `Delete`. |
| Open File | Opens the file of a completed download. |
| Retry | Tries a failed task again. |
| Retry All Failed | Tries every failed task again. |
| Clear Completed | Removes completed tasks from the list. |
| Clear Failed | Removes failed tasks from the list. |

The table shows the video name, URL, quality, status, progress, speed and output file of each task. A statistics area shows the counts of total, pending, active, completed and failed tasks.

The app tries a download again one time on its own after a network error. Downloads that you start with **Download Now** also appear in the Queue tab.

## History tab

The History tab lists past downloads. The app keeps up to 1000 entries.

| Control | What it does |
|---------|--------------|
| Search | Filters the list by title or URL. |
| Refresh | Reloads the list. |
| Export CSV | Saves the history as a CSV file. |
| Open Directory | Opens the download folder. |
| Clear All | Deletes the whole history after you confirm. You cannot undo this. |

The Statistics area shows total downloads, completed, failed and cancelled downloads, success rate, total downloaded and average speed. Clearing the history never deletes the downloaded files.

## Settings tab

Change settings, then click **Save Settings**. Click **Reset to Defaults** to restore the default values after you confirm.

### General Settings

- **Default Download Folder:** the folder for new downloads. The first default is your `Downloads` folder.
- **Default Quality:** the quality that is selected when the app starts.

### Appearance

- **Language:** English or Hebrew. Restart the app after you change the language.
- **Theme:** Dark or Light. Use **Toggle Theme (Dark/Light)** to switch.

### Features

- **Enable Desktop Notifications:** shows a notification when a download completes or fails. It is on by default.
- **Notify me about new versions on startup:** checks GitHub when the app starts. It is off by default. It does not install anything.
- **Keep running in the tray when I close the window:** closing the window hides it, and downloads keep running. Use **Quit** in the tray menu to exit. It is off by default. It is not available on a desktop without a system tray.
- **Check for Updates Now:** checks for a new release at once.

### Storage

This section shows the path of the **Log file**, the **Crash reports** folder and the **Config file**. Click **Copy** next to a path to copy it.

### Advanced Download Options

This section is closed by default. Click **Show Advanced Download Options** to open it. The settings apply to downloads that start after you save.

| Setting | What it does |
|---------|--------------|
| Use cookies from | Reads the cookies of a browser, so that private and age-restricted videos can be downloaded. Choices: None, Firefox. On Windows, also Chrome, Microsoft Edge and Brave. |
| Browser profile | Optional. A profile name or folder. Leave it empty for the default profile. |
| Proxy | A proxy for downloads and for video, subtitle and playlist info. Types: http, https, socks5 and socks5h. Form: `socks5://host:1080`. Leave it empty for no proxy. |
| File name | How the app names files: **Title_Quality (default)**, **Uploader - Title**, **Date - Title** or **Custom template**. |
| Custom template | A yt-dlp output template. It must end with `.%(ext)s`. It must be a file name only, without folders. |
| Video codec | Prefer H.264, H.265/HEVC, VP9 or AV1. The default is **Any**. |
| Audio codec | Prefer AAC, Opus or Vorbis for video downloads. The default is **Any**. |
| Custom format | A yt-dlp format string for advanced users. When it is set, it replaces the quality and codec choices. |

Notes:

- **Cookies and privacy:** cookies stay on this computer. The app does not save them and does not write them to the log. The app removes them from a saved `.info.json` file.
- **Cookies and Linux:** only Firefox is offered on Linux.
- **Cookies and Chrome:** Chrome 127 and later encrypt cookies in a way that yt-dlp cannot read. The app shows a message. Use Firefox instead. See [Troubleshooting](TROUBLESHOOTING.md#chrome-cookies-do-not-work-on-windows).
- **Proxy password:** if the proxy address has a user name and password, the app saves them in plain text in the settings file (`yt-dlp-studio_config.json`). The app masks them in the log. Do not share your settings file.
- **File names:** if a file with the same name exists, the app adds a number, for example `(1)`. This works with every template.
- **Codec preference:** to get the codec, a download can use a lower resolution, within the quality you chose.
- **Invalid values:** if a value is not valid, the app shows a message when you click **Save Settings**.

## About tab

The About tab shows:

- **Details:** the application version, and the versions of the yt-dlp engine, FFmpeg, Python and PySide6 (Qt).
- **About the Developer:** information about NX1X and NXTools, and a link to the project on GitHub.
- **Credits:** the open-source projects that the app uses.
- **Keyboard Shortcuts:** the list of all shortcuts.

If FFmpeg is missing, the FFmpeg line shows "Not found in PATH".

## Common tasks

### Download a single video

1. Open the **Download** tab.
2. Paste the video URL into the URL field.
3. Set **Download Type** to **Video**.
4. Select a **Quality** and a **Video Format**.
5. Check the **Save to** folder.
6. Click **Download Now**.

### Download a playlist

1. Open the **Download** tab.
2. Paste the playlist URL.
3. Click **Add to Queue**, and answer Yes when the app asks to view the playlist.
4. Select the videos and the quality in the Playlist Viewer.
5. Click **Add to Queue**.
6. Open the **Queue** tab and click **Start Queue**.

### Download audio only

1. Open the **Download** tab.
2. Paste the video URL.
3. Set **Download Type** to **Audio Only**.
4. Select an audio **Quality**, for example Audio 192kbps.
5. Select an **Audio Format**, for example MP3.
6. Click **Download Now**.

FFmpeg converts the audio, so FFmpeg must be present.

### Download subtitles

1. Open the **Download** tab.
2. Paste the video URL.
3. Turn on **Download Subtitles**.
4. Enter language codes in **Languages**, or click **Select Subs...** to choose.
5. Click **Download Now**.

If the video has no subtitles, the app tells you. If YouTube blocks the subtitle request, the video still downloads without subtitles. See [Troubleshooting](TROUBLESHOOTING.md#subtitles-are-missing-or-http-429-appears).

### Download a private or age-restricted video

1. Sign in to the site in Firefox. On Windows, you can use Edge or Brave. Chrome 127 and later does not work.
2. Close the browser completely.
3. Open the **Settings** tab, then click **Show Advanced Download Options**.
4. Set **Use cookies from** to the browser.
5. Click **Save Settings**.
6. Start the download from the **Download** tab.

You must have the right to see the video with your account.

## Where your files go

### Downloaded files

The app saves downloads in the **Save to** folder. The default is your `Downloads` folder. The default file name is `Title_Quality`. Change it in **File name** (see [Advanced Download Options](#advanced-download-options)).

If you turn on extra files, the app writes them next to the video:

- Thumbnail: a JPG file.
- Subtitles: SRT files.
- Metadata: an `.info.json` file, and text files named `<name>_metadata.txt` and `<name>_description.txt`.
- Comments: `<name> Comments.txt`.

### App data folder

The app keeps its own files in the app data folder.

| System | Folder |
|--------|--------|
| Windows | `%APPDATA%\YT-DLP Studio` |
| Linux | `~/.config/YT-DLP Studio` |

| File or folder | Content |
|----------------|---------|
| `yt-dlp-studio_config.json` | Your settings |
| `download_history.json` | The download history |
| `download_queue.json` | The saved queue |
| `language.json` | The language choice |
| `yt-dlp-studio.log` | The log file |
| `crashes/` | Crash reports (`crash-<time>.json`) |
| `deno/` | Linux only: the Deno copy that the app downloads |

Each settings, history, queue and language file has a version number. If a file is damaged, the app keeps a copy as `<name>.bad` and starts with defaults. If a file comes from a newer app version, the app keeps a copy as `<name>.v<N>.bak` before it saves. See [Troubleshooting](TROUBLESHOOTING.md#the-app-reset-my-settings-or-history).
