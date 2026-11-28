# Troubleshooting

This guide lists common problems and their fixes. For how to use the app, see the [User Guide](USER_GUIDE.md). For install steps, see the [Installation Guide](INSTALLATION_GUIDE.md).

## Contents

- [A video needs you to sign in](#a-video-needs-you-to-sign-in)
- [Cookies work only with Firefox](#cookies-work-only-with-firefox)
- [Subtitles are missing or HTTP 429 appears](#subtitles-are-missing-or-http-429-appears)
- [YouTube downloads fail or offer few formats on Linux](#youtube-downloads-fail-or-offer-few-formats-on-linux)
- [FFmpeg is missing](#ffmpeg-is-missing)
- [Windows SmartScreen blocks the EXE](#windows-smartscreen-blocks-the-exe)
- [The app does not start on Linux](#the-app-does-not-start-on-linux)
- [The app reset my settings or history](#the-app-reset-my-settings-or-history)
- [A proxy does not work](#a-proxy-does-not-work)
- [A photo post does not download](#a-photo-post-does-not-download)
- [A site does not work](#a-site-does-not-work)
- [Where the log and crash reports are](#where-the-log-and-crash-reports-are)
- [How to report an issue](#how-to-report-an-issue)

## A video needs you to sign in

**Symptom:** the app says that the video needs a signed-in account. This happens with private and age-restricted videos.

**Fix:**

1. Sign in to the site in Firefox.
2. Close the browser completely.
3. Open the **Settings** tab, then click **Show Advanced Download Options**.
4. Set **Use cookies from** to that browser. If you use more than one profile, enter it in **Browser profile**.
5. Click **Save Settings**.
6. Start the download again.

If the message still appears, the site does not see a signed-in session in that browser or profile. Sign in again, and check the profile.

Cookies stay on your computer. The app does not save them and does not write them to the log.

## Cookies work only with Firefox

**Symptom:** **Use cookies from** offers only Firefox. Or the app says it could not read the cookies, and mentions app-bound encryption.

**Cause:** Chrome 127 and later protect their cookies with app-bound encryption. yt-dlp cannot read them. Microsoft Edge does the same on Windows 11. On Linux, reading Chromium cookies needs a package that the project does not use. So the app offers only Firefox.

**Fix:** sign in to the site in Firefox and set **Use cookies from** to **Firefox**. A setting from an older test build that named Chrome, Edge or Brave becomes **None**.

Other cookie messages:

- **"keeps its cookie database locked":** close the browser completely, then try again.
- **"No cookies from ... were found":** check that the browser is installed. Check the **Browser profile** setting.


## Subtitles are missing or HTTP 429 appears

**Symptom:** the log shows "Subtitle download failed" and "continuing without subtitles". The log may also show HTTP 429.

**Cause:** HTTP 429 means "too many requests". YouTube limits how fast one IP address can send requests. This happens most often when you turn on **Subtitles** together with **Comments** or **Metadata (description, info.json)** in **More options**.

**What the app does:** a failed subtitle request never stops the video download. The video downloads without subtitles. When subtitles are on together with comments or metadata, the app adds a pause of 1 second between requests. This makes the download slower.

**Fix:**

1. Wait some minutes.
2. Download the video again with only **Subtitles** turned on in **More options**.

Other causes of missing subtitles:

- The video has no subtitles in the languages you entered. Open **More options** in the Download tab and click **Choose...** to see the available languages.
- Language codes must be separated by commas, for example `en,es,he`.

## YouTube downloads fail or offer few formats on Linux

**Cause:** yt-dlp uses Deno to solve YouTube's JavaScript challenges. The Linux builds do not include Deno. The app uses a `deno` on your `PATH`. If there is none, the app downloads Deno 2.9.8 once, at startup, to `~/.config/YT-DLP Studio/deno/2.9.8/`.

**Symptom in the log:** "Deno auto-install failed" or "Deno was not installed", with a note that some YouTube formats may be unavailable.

**Fix:**

1. Check your internet connection and any firewall that blocks `github.com`.
2. Restart the app. The app tries the download again at startup.
3. If that fails, install Deno from [deno.land](https://deno.land/) and put `deno` on your `PATH`. Restart the app.

Windows builds include Deno.

## FFmpeg is missing

**Symptom:** audio extraction, merging of video and audio, and subtitle embedding fail. The **About** tab shows "Not found in PATH" next to FFmpeg.

**Fix on Windows:** the Windows builds include FFmpeg. Install the app again from the [Releases page](https://github.com/NX1X/yt-dlp-studio/releases/latest). If you run from source, put FFmpeg on your `PATH`.

**Fix on Linux:** install FFmpeg with your package manager (see [FFmpeg in the Installation Guide](INSTALLATION_GUIDE.md#ffmpeg)). Restart the app. The app looks for FFmpeg once, so it does not see a new install until you restart. The .deb and .rpm packages install FFmpeg as a dependency.

## Windows SmartScreen blocks the EXE

**Symptom:** Windows shows "Windows protected your PC" or "Unknown publisher".

**Cause:** the EXE files and the installer are not code-signed yet. Windows shows this warning for files without a known publisher.

**Fix:**

1. Download the file only from the [Releases page](https://github.com/NX1X/yt-dlp-studio/releases/latest).
2. Optional: verify the file (see [Verify a download](INSTALLATION_GUIDE.md#verify-a-download)).
3. Click **More info**.
4. Click **Run anyway**.

[CODE_SIGNING.md](CODE_SIGNING.md) explains the plan to sign future releases.

## The app does not start on Linux

**Symptom:** the app does not open, and a terminal shows an error such as `libEGL.so.1: cannot open shared object file`.

**Cause:** the Linux builds need some system libraries: libEGL, libGL, libxkbcommon, libdbus, libxcb-cursor, GLib and fontconfig. A minimal or server install may not have them.

**Fix:** install the libraries with your package manager. The .deb and .rpm packages install them for you. The AppImage and the .tar.gz archive do not.

## The app reset my settings or history

**Cause:** the app could not read a file in the app data folder. It keeps the damaged file as a copy and starts with defaults.

**Where to look:** the app data folder is `%APPDATA%\YT-DLP Studio` on Windows and `~/.config/YT-DLP Studio` on Linux.

| File you find | Meaning |
|---------------|---------|
| `<name>.bad` | The file was damaged. For example, `download_history.json.bad` is a copy of a damaged history file. |
| `<name>.v<N>.bak` | The file came from a newer app version (format version N). The app kept a copy before it saved. |

The files are `yt-dlp-studio_config.json` (settings), `download_history.json`, `download_queue.json` and `language.json`.

**Fix:**

1. Close the app.
2. Open the `.bad` file in a text editor. Look for the damage. A common cause is a half-written or hand-edited file.
3. Repair the file, and save it under the original name.
4. Start the app.

If you cannot repair the file, attach it to an [issue](https://github.com/NX1X/yt-dlp-studio/issues/new/choose) after you remove private data from it.

If you moved back to an older app version, the `.v<N>.bak` file has your newer data. Update the app to the newer version to use it again.

## A proxy does not work

**Symptom:** the app says it could not connect through the proxy, or it says the proxy address is not valid.

**Fix:**

1. Open **Settings**, then **Show Advanced Download Options**.
2. Use the form `type://host:port`, for example `socks5://127.0.0.1:1080`.
3. Use one of these types: http, https, socks5 or socks5h.
4. Click **Save Settings**.

Empty means no proxy. Do not share your settings file when the proxy address has a password. The app saves the password in plain text in `yt-dlp-studio_config.json`. The app masks it in the log.

## A photo post does not download

Photo posts from Instagram and X download as image files. Other sites are different:

- **Facebook:** photo posts are not supported. The app says "This post has no video. Photo posts from Facebook are not supported." Videos from Facebook still download.
- **TikTok:** a photo slideshow gives only its audio. The app has no photo download for TikTok.
- **"This post has no photo or video that can be downloaded":** the Instagram or X post holds no media that the site shows to a visitor who is not signed in (for example a text-only post). If the post is private, or it asks for a login, see [A video needs you to sign in](#a-video-needs-you-to-sign-in).

If an Instagram or X photo post that you can see in a private window fails with another message, [report an issue](#how-to-report-an-issue).

## A site does not work

If the label next to the Link field says "Experimental site: may not work", the site is not tested. A failure is possible. The tested sites are YouTube, Instagram, TikTok, Facebook and X.

If a tested site fails, [report an issue](#how-to-report-an-issue). Site changes often break downloads. A newer app version includes a newer yt-dlp engine, so update the app first.

## Where the log and crash reports are

The app data folder holds both. Open the **Settings** tab to see the exact paths under **Files for bug reports**. Click **Copy** to copy a path, or **Open folder** to open the folder.

| What | Windows | Linux |
|------|---------|-------|
| Log file | `%APPDATA%\YT-DLP Studio\yt-dlp-studio.log` | `~/.config/YT-DLP Studio/yt-dlp-studio.log` |
| Crash reports | `%APPDATA%\YT-DLP Studio\crashes\` | `~/.config/YT-DLP Studio/crashes/` |

- The log file is at most 5 MB. The app keeps 3 older log files next to it.
- Each crash is a file named `crash-<time>.json`. The app keeps the 20 newest.
- A crash inside Qt or another native library does not make a `.json` report. It writes the stack of every thread to `native-crash.log` in the same folder. Each app start adds one "session" line there, so the file also shows which run crashed.
- A crash report has the app and engine versions, the Python and system versions, the error, and the last 200 log lines.
- The app removes passwords, tokens and similar secrets from the log and from crash reports. Read a file before you share it.
- Each start writes an "Environment" line to the log, with the app, engine, FFmpeg and Deno versions. Include it in a bug report.

## How to report an issue

1. Update to the latest release, and try again.
2. Search the [existing issues](https://github.com/NX1X/yt-dlp-studio/issues).
3. Open a new issue with the Bug Report template: [new issue](https://github.com/NX1X/yt-dlp-studio/issues/new/choose).
4. Describe what you did, what you expected and what happened.
5. Open the **About** tab and click **Copy for bug report**. Paste the result into the issue. It has the app, engine, FFmpeg, Python and Qt versions and your system details.
6. Paste the relevant log lines. Find the log file in **Settings**, under **Files for bug reports**. Attach the crash report if the app crashed.
7. If a download failed, click **Copy details** in the error dialog. Paste the text into the issue.
8. Remove private data, such as links to private videos, before you post.

Do not report security problems in a public issue. [SECURITY.md](../SECURITY.md) explains how to report them privately.
