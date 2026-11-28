# Getting Started

This page gets you from install to your first download. For details, see the [Installation Guide](INSTALLATION_GUIDE.md), the [User Guide](USER_GUIDE.md) and [Troubleshooting](TROUBLESHOOTING.md).

## Install

Tested on Windows 11. Windows 10 should work but is not tested. Linux builds are also available.

**Windows:**

1. Download `YT-DLP-Studio-Setup-<version>.exe` from the [Releases page](https://github.com/NX1X/yt-dlp-studio/releases/latest).
2. Run it. If SmartScreen shows a warning, click **More info**, then **Run anyway**.
3. Start YT-DLP Studio from the Start menu.

The installer needs no admin rights. FFmpeg and Deno are included. For a portable copy, use `YT-DLP.Studio.exe`.

**Linux:**

1. Download the package for your system from the [Releases page](https://github.com/NX1X/yt-dlp-studio/releases/latest).
2. For Debian, Ubuntu or Mint, run `sudo apt install ./yt-dlp-studio_*_amd64.deb`.
3. For Fedora, run `sudo dnf install ./yt-dlp-studio-*.rpm`.
4. For other systems, use the AppImage or the .tar.gz archive. Install FFmpeg yourself first.

The [Installation Guide](INSTALLATION_GUIDE.md) has all options, including running from source and uninstalling.

## Your first download

1. Open the **Download** tab.
2. Paste a video link into the **Link** field.
3. Set **Get** to **Video**, and select a **Quality** and a **Format**.
4. Check the **Save to** folder. Click **Browse** to change it.
5. Click **Download**.

The **Now downloading** panel shows the progress. When the download ends, click **Open folder** to see the file.

To get only the sound, set **Get** to **Audio Only**.

## Sites

- **Tested:** YouTube, Instagram, TikTok, Facebook and X.
- **Experimental:** every other site that yt-dlp supports. A download can work, partly work or fail.

The app shows "Tested site" or "Experimental site: may not work" next to the Link field.

## Where files go

- **Downloads:** the **Save to** folder. The default is your `Downloads` folder.
- **Settings, history, queue and log:** the app data folder. On Windows it is `%APPDATA%\YT-DLP Studio`. On Linux it is `~/.config/YT-DLP Studio`.

See [Where your files go](USER_GUIDE.md#where-your-files-go) for the file names.

## Next steps

- Download many videos: use **Add to queue** or **Batch links...**, then open the **Queue** tab. See the [User Guide](USER_GUIDE.md#queue-tab).
- Download a playlist, subtitles or a private video: see [Common tasks](USER_GUIDE.md#common-tasks).
- Change the default folder, theme or language: open the **Settings** tab. See [Settings tab](USER_GUIDE.md#settings-tab).
- Learn the keyboard shortcuts: see [Keyboard shortcuts](USER_GUIDE.md#keyboard-shortcuts).
- Something went wrong: see [Troubleshooting](TROUBLESHOOTING.md).
