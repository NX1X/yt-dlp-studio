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
- [Keyboard shortcuts](#keyboard-shortcuts)
- [Common tasks](#common-tasks)
- [Where your files go](#where-your-files-go)

## Before you start

- **Platforms:** Tested on Windows 11. Windows 10 should work but is not tested. Linux builds are also available.
- **Supported sites:** next to the Link field, the app shows "Tested site" or "Experimental site: may not work".
  - Tested sites: YouTube, Instagram, TikTok, Facebook and X.
  - Experimental sites: every other site that yt-dlp supports. A download can work, partly work or fail. The app does not block it.
- **FFmpeg:** the Windows builds include FFmpeg. On Linux, the .deb and .rpm packages install it. For the AppImage and the .tar.gz archive, install FFmpeg yourself.

## Download tab

Use the Download tab to start a download at once, or to add it to the queue.

### The form

| Control | What it does |
|---------|--------------|
| Link | The video, playlist or channel address. You can type it, paste it or drag it into the field. The app shows "Tested site" or "Experimental site: may not work" next to it. |
| Paste | Pastes the link from the clipboard. Shortcut: `Ctrl+V`. |
| Info | Shows the title, thumbnail, length and other details of the link before you download. Shortcut: `Ctrl+Shift+I`. |
| Get | **Video** or **Audio Only**. |
| Quality | For video, the maximum quality. For audio, **Best Quality** or a bit rate. |
| Format | For video, the container: MP4, MKV, WebM or Auto. For audio, the format: MP3, M4A/AAC, OPUS, FLAC, WAV or Vorbis/OGG. |
| Save to | The output folder. Click **Browse** to change it. Click **Open folder** to open it. The field is read-only. |
| Batch links... | Adds many links at once (see [Batch links](#batch-links)). |
| Add to queue | Puts the download at the end of the queue (see [Download and Add to queue](#download-and-add-to-queue)). Shortcut: `Ctrl+Shift+Q`. |
| Download | Starts the download at once (see [Download and Add to queue](#download-and-add-to-queue)). Shortcuts: `Enter` in the Link field, or `Ctrl+D`. |

Quality choices for video: Best Quality, 8K (4320p), 4K (2160p), 2K (1440p), 1080p (Full HD), 720p (HD), 480p (SD) and 360p. Each choice is a maximum. yt-dlp downloads the best quality up to that height.

Quality choices for audio: Best Quality, Audio 320kbps, Audio 256kbps, Audio 192kbps and Audio 128kbps.

If the link is empty or not valid, or the folder is missing or not writable, a message appears under the field. Nothing is added until you fix it.

### Download and Add to queue

Both buttons run the same checks. They ask the same playlist question and the same duplicate question. They differ in when the download starts.

- **Download** starts the download at once, also when the queue is paused. If the maximum number of downloads (3) already runs, it starts next.
- **Add to queue** puts the download at the end of the queue. It waits its turn. It does not start while the queue is paused.

A message in the status bar tells you what happened, for example "Added to the queue at position 2." If the queue is paused, the message tells you to press **Start** in the Queue tab.

If the same download (same link, quality and type) is already in the queue, the app asks if you want to add it again.

### More options

This section is closed by default. A summary line next to its title shows what is on, for example "Subtitles (en), Thumbnail". With nothing on, it shows "All off, no speed limit".

| Setting | What it does |
|---------|--------------|
| Subtitles | Downloads subtitles and embeds them. Enter language codes in **Languages**, for example `en,es,he`. Click **Choose...** to pick from the languages that the video has. |
| Thumbnail | Saves the thumbnail as a JPG file. |
| Metadata (description, info.json) | Saves the video metadata, including an `.info.json` file and readable text files. |
| Comments | Saves the comments to a separate text file. This can be slow for popular videos. |
| Speed limit | A maximum speed in KB/s. Zero shows as "Unlimited". |

The section also has a link, **Open Settings**. Cookies, proxy, file names and format options are in the Settings tab, under Advanced Download Options.

**Choose...** needs a valid link in the Link field. It opens "Choose subtitle languages". Type to filter the list, check the languages, then click **Use selected languages**. If you check none, the app asks if you want to continue without subtitles.

### Batch links

1. Click **Batch links...**.
2. Paste one link per line, or click **Import from File**.
3. Optional: click **Validate URLs**. The dialog shows the count of valid links and invalid lines.
4. Click **Add to queue**.

The app adds every valid link to the queue. If some lines are not valid, the app asks if it should add only the valid links.

### Playlists and channels

When you click **Download** or **Add to queue** with a playlist or channel link, the app asks what to do:

- **Choose videos...** opens the Playlist Viewer.
- **Whole playlist** adds the playlist link as one download.
- **Cancel** adds nothing.

In the Playlist Viewer:

1. Clear the videos you do not want. All videos are selected by default. Use **Select All** and **Select None** to change many at once.
2. Select one quality for all selected videos.
3. Optional: turn on subtitles for every selected video, and select the languages. These settings override the subtitle settings of the Download tab.
4. Click **Add to queue**. The button shows the number of selected videos.

If you started with **Download**, the chosen videos start at once. If you started with **Add to queue**, they wait their turn. **Info** on a playlist link opens the same viewer, and the videos go to the queue like **Add to queue**.

### Photo posts

An Instagram or X post can hold photos instead of a video, or next to one. The app downloads them without a setting:

- A post with one photo gives one image file.
- A carousel or a post with several photos gives one file per photo. Videos in the same post download as videos.
- Each image file is named `Title [id].jpg`, with the largest size that the site offers (Instagram: up to 1080 pixels wide). A file name template that you chose in Advanced Download Options is kept.
- **Open file** in the Queue and History tabs opens the image. If a post gave several files, it opens the first one.
- Metadata and comments files are written for each photo. Audio extraction, tag embedding and subtitles do not apply to photos, also when **Audio Only** is on.
- Facebook photo posts are not supported. A TikTok photo slideshow gives only its audio.

### Info dialog

**Info** on a single video opens the Video Information dialog. It has a **Download** button. Click it to close the dialog and start the download as if you had clicked **Download** on the form. **Close** only closes the dialog.

### Now downloading

This panel shows each running download with its title, a progress bar, the percent, the speed and the time left. A line below it shows how many downloads wait and how many failed. Click **Open queue** to go to the Queue tab. With nothing running, the panel says "Nothing is downloading. Paste a link above to start." If the queue is paused, it also shows how many downloads wait.

### Activity log

This section is closed by default. It shows the log of the app while it works. Click **Clear Log** to empty it.

### If a download fails

A dialog shows a friendly explanation and suggestions. It also shows the technical details. Click **Copy details** to copy the technical text, to paste into a bug report.

## Queue tab

The Queue tab shows every download that waits, runs or has ended. The queue runs up to 3 downloads at the same time. The app saves the queue and restores it when you start the app again.

### Top bar

| Control | What it does |
|---------|--------------|
| Start | Starts the waiting downloads. New links then start on their own. |
| Pause | Lets the running downloads finish, but starts no new ones. Click **Start** to continue. |
| Stop all | Asks first. If you agree, it cancels the running downloads and pauses the queue. Waiting downloads stay in the queue. |
| Retry failed | Tries every failed download again. It is on only while a failed download exists. |
| Clear finished | A menu. Choose **Completed downloads**, **Failed downloads** or **Cancelled downloads** to remove them from the list. The files stay on disk. |

A counters line in the top bar shows the number of downloading, waiting, failed and done downloads, and "queue paused".

### Table and selected download

The table shows the title, status, size, speed and time left of each download. A running download shows a progress bar in the Status column. Point at a title to see the link, folder and quality.

Select a row to use these buttons under the table:

| Button | What it does |
|--------|--------------|
| Open file | Opens the file of a completed download. |
| Open folder | Opens the folder of the selected download. |
| Retry | Tries the selected failed download again. |
| Cancel | Cancels the selected download. A waiting download is removed. |
| Up, Down | Moves the selected download in the queue. |
| Remove | Removes the selected download from the queue. If it runs or waits, the app asks first. |

Right-click a row for a menu with the same actions, plus **Copy link** and **Show error details**. Double-click a completed row to open the file. Double-click a failed row to see the error.

The app tries a download again one time on its own after a network error.

### Closing the app

If downloads run when you close the app, it asks if you want to exit. If you exit, the app saves the running downloads and continues them at the next start. If **Keep running in the tray when I close the window** is on, closing the window only hides it. Use **Quit** in the tray menu to exit.

## History tab

The History tab lists past downloads. The app keeps up to 1000 entries. The tab updates on its own when a download ends.

| Control | What it does |
|---------|--------------|
| Search | Filters the list by title or link. |
| Status filter | Shows all statuses, or only completed, failed or cancelled downloads. |
| Export CSV | Saves the history as a CSV file. |
| Open downloads folder | Opens the download folder. |
| Clear | A menu: **Clear completed**, **Clear failed** or **Clear all history**. The app asks first. Downloaded files stay on disk. |

A summary line shows the number of downloads and how many are done, failed and cancelled, and the total size. Point at it to see the success rate and the average speed.

Right-click a row for the actions: **Open file** (completed downloads only), **Open folder**, **Copy link** and **Download again**. **Download again** puts the link into the Download tab. Check the options, then click **Download**. Double-click a completed row to open the file. Double-click any other row to use **Download again**.

With no history, the tab says "No download history". If a search finds nothing, it says "No matches".

## Settings tab

Change settings, then click **Save Settings**. Click **Reset to Defaults** to restore the default values after you confirm. Both buttons are always visible at the bottom of the tab. The theme is the exception: it applies and saves at once.

### Downloads

- **Default Download Folder:** the folder for new downloads. The first default is your `Downloads` folder. Click **Browse** to change it.
- **Default Quality:** the quality that is selected when the app starts.

### Appearance

- **Theme:** **Dark** or **Light**. The change applies at once and is saved. You do not need to click **Save Settings**.
- **Language:** English or Hebrew. Restart the app to apply a change.

### Behavior

- **Enable Desktop Notifications:** shows a notification when a download completes or fails. It is on by default.
- **Keep running in the tray when I close the window:** closing the window hides it, and downloads keep running. Use **Quit** in the tray menu to exit. It is off by default. It is not available on a desktop without a system tray.
- **Notify me about new versions on startup:** checks GitHub when the app starts. It is off by default. It does not install anything.
- **Check for Updates Now:** checks for a new release at once.

### Advanced Download Options

This section is closed by default. Click **Show Advanced Download Options** to open it. The settings apply to downloads that start after you save.

| Setting | What it does |
|---------|--------------|
| Use cookies from | Reads the cookies of a browser, so that private and age-restricted videos can be downloaded. Choices: None, Firefox. |
| Browser profile | Optional. A profile name or folder. Leave it empty for the default profile. |
| Proxy | A proxy for downloads and for video, subtitle and playlist info. Types: http, https, socks5 and socks5h. Form: `socks5://host:1080`. Leave it empty for no proxy. |
| File name | How the app names files: **Title_Quality (default)**, **Uploader - Title**, **Date - Title** or **Custom template**. |
| Custom template | A yt-dlp output template. It must end with `.%(ext)s`. It must be a file name only, without folders. |
| Video codec | Prefer H.264, H.265/HEVC, VP9 or AV1. The default is **Any**. |
| Audio codec | Prefer AAC, Opus or Vorbis for video downloads. The default is **Any**. |
| Custom format | A yt-dlp format string for advanced users. When it is set, it replaces the quality and codec choices. |

Notes:

- **Cookies and privacy:** cookies stay on this computer. The app does not save them and does not write them to the log. The app removes them from a saved `.info.json` file.
- **Why only Firefox:** Chrome, Edge and Brave encrypt their cookies in a way that yt-dlp cannot read on Windows. See [Troubleshooting](TROUBLESHOOTING.md#cookies-work-only-with-firefox).
- **Proxy password:** if the proxy address has a user name and password, the app saves them in plain text in the settings file (`yt-dlp-studio_config.json`). The app masks them in the log. Do not share your settings file.
- **File names:** if a file with the same name exists, the app adds a number, for example `(1)`. This works with every template.
- **Codec preference:** to get the codec, a download can use a lower resolution, within the quality you chose.
- **Invalid values:** if a value is not valid, the app shows a message when you click **Save Settings**.

### Files for bug reports

This group shows the paths of the **Log file**, the **Crash reports** folder and the **Config file**. Click **Copy** next to a path to copy it. Click **Open folder** to open the folder in your file manager.

## About tab

The About tab shows:

- **A header:** the app name, the current version, one sentence about the app, and the links **View on GitHub** and **Visit Website**.
- **System Information:** the versions of the app, the yt-dlp engine, FFmpeg, Python and PySide6 (Qt). Click **Copy for bug report** to copy these versions and your system details. Paste them into a bug report.
- **Credits:** the open-source projects that the app uses, and the license.
- **Keyboard Shortcuts:** the list of all shortcuts (see [Keyboard shortcuts](#keyboard-shortcuts)).

If FFmpeg is missing, the FFmpeg line shows "Not found in PATH".

## Keyboard shortcuts

| Where | Shortcut | Action |
|-------|----------|--------|
| Anywhere | `Ctrl+Q` | Quit |
| Anywhere | `F1` | Open the guide on the website, at the section of the open tab |
| Dialogs | `Esc` | Close the dialog |
| Download tab | `Ctrl+V` | Paste the link from the clipboard |
| Download tab | `Enter` | Start the download (when the Link field has the focus) |
| Download tab | `Ctrl+D` | Download |
| Download tab | `Ctrl+Shift+Q` | Add to queue |
| Download tab | `Ctrl+Shift+I` | Show info |
| Queue tab | `Delete` | Remove the selected download |
| Queue tab | `Ctrl+Up`, `Ctrl+Down` | Move the selected download up or down |

The queue shortcuts work while the table has the focus. There is no `Space` shortcut for the queue.

## Common tasks

### Download a single video

1. Open the **Download** tab.
2. Paste the video link into the **Link** field.
3. Set **Get** to **Video**.
4. Select a **Quality** and a **Format**.
5. Check the **Save to** folder.
6. Click **Download**.

### Download a playlist

1. Open the **Download** tab.
2. Paste the playlist link.
3. Click **Add to queue**.
4. Click **Choose videos...** when the app asks.
5. Select the videos and the quality in the Playlist Viewer.
6. Click **Add to queue**.
7. Open the **Queue** tab. If the queue is paused, click **Start**.

To download the whole playlist as one download, click **Whole playlist** instead of **Choose videos...**.

### Download audio only

1. Open the **Download** tab.
2. Paste the video link.
3. Set **Get** to **Audio Only**.
4. Select an audio **Quality**, for example Audio 192kbps.
5. Select a **Format**, for example MP3.
6. Click **Download**.

FFmpeg converts the audio, so FFmpeg must be present.

### Download subtitles

1. Open the **Download** tab.
2. Paste the video link.
3. Open **More options**.
4. Turn on **Subtitles**.
5. Enter language codes in **Languages**, or click **Choose...** to pick from the list.
6. Click **Download**.

If the video has no subtitles, the app tells you. If YouTube blocks the subtitle request, the video still downloads without subtitles. See [Troubleshooting](TROUBLESHOOTING.md#subtitles-are-missing-or-http-429-appears).

### Download a private or age-restricted video

1. Sign in to the site in Firefox.
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
