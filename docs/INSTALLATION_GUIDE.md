# Installation Guide

This guide covers every way to install YT-DLP Studio: the Windows installer, the portable EXE, the Linux packages and a source install. It also explains how to uninstall.

Download all release files from the [Releases page](https://github.com/NX1X/yt-dlp-studio/releases/latest). The file names below use `<version>` for the version number, for example `0.3.1`.

## System requirements

| Item | Requirement |
|------|-------------|
| Windows | Windows 10 or 11, 64-bit |
| Linux | 64-bit (x86_64), glibc 2.35 or later (Ubuntu 22.04+, Debian 12+, Fedora 36+, Linux Mint 21+, Arch and most distributions from 2022 and later) |
| macOS | Not supported |
| Python | Only for a source install: Python 3.11 or later. CI builds and tests on Python 3.14. |
| Internet | Needed to download videos |

The Windows downloads are about 200 MB and the Linux downloads are about 75 MB (0.3.1).

## Windows

There are three Windows downloads. All three include FFmpeg and Deno.

| File | Type |
|------|------|
| `YT-DLP-Studio-Setup-<version>.exe` | Installer (recommended) |
| `YT-DLP.Studio.exe` | Portable EXE |
| `yt-dlp-studio-v<version>-Windows.zip` | Portable ZIP (the portable EXE in a ZIP file) |

The installer and the portable EXE contain the same program.

### Installer

1. Download `YT-DLP-Studio-Setup-<version>.exe`.
2. Run it. If SmartScreen shows a warning, see [SmartScreen warning](#smartscreen-warning).
3. Select if you want a desktop shortcut. It is off by default.
4. Finish the setup. You can start the app from the last page.

The installer:

- installs for the current user only, with no admin rights and no UAC prompt;
- installs to `%LOCALAPPDATA%\Programs\YT-DLP Studio`;
- adds a Start menu shortcut;
- shows its pages in English or Hebrew.

**Updates:** when a new release is out, the app can download the new installer. It checks the SHA-256 of the file, runs the installer silently, and starts again when the update is done.

### Portable EXE or ZIP

1. Download `YT-DLP.Studio.exe`, or download the ZIP file and extract it to any folder.
2. Run the EXE.

**Updates:** a portable copy does not update itself in place. The app downloads the new portable EXE as a separate file. The new file does not replace the copy you use now. You can delete the old copy afterwards.

### SmartScreen warning

The Windows EXE files are not code-signed. For this reason, SmartScreen may show an "Unknown publisher" warning the first time you run them.

1. Optional: verify the portable EXE first (see [Verify a download](#verify-a-download)).
2. Click **More info**.
3. Click **Run anyway**.

[CODE_SIGNING.md](CODE_SIGNING.md) explains the plan to sign future releases.

## Linux

The Linux packages are available for 0.3.1 and later. All Linux downloads contain the same program.

| Distribution | File | Install command |
|--------------|------|-----------------|
| Debian, Ubuntu, Mint | `yt-dlp-studio_<version>_amd64.deb` | `sudo apt install ./yt-dlp-studio_*_amd64.deb` |
| Fedora, openSUSE | `yt-dlp-studio-<version>-1.x86_64.rpm` | `sudo dnf install ./yt-dlp-studio-*.rpm` (openSUSE: `sudo zypper install ./yt-dlp-studio-*.rpm`) |
| Any distribution | `YT-DLP-Studio-<version>-x86_64.AppImage` | `chmod +x YT-DLP-Studio-*.AppImage`, then run the file |
| Any distribution | `yt-dlp-studio-v<version>-Linux.tar.gz` | See [Linux archive](#linux-archive-targz) |

### .deb and .rpm packages

The packages install the app to `/opt/yt-dlp-studio` and add the `yt-dlp-studio` command and an app menu entry. The package manager installs FFmpeg as a dependency. On Fedora, FFmpeg comes from `ffmpeg-free` or from RPM Fusion.

**Updates:** the app can download the new .deb or .rpm file. Open it with your software installer to update. Your settings and history are kept.

### AppImage

The AppImage needs no install.

1. Install FFmpeg (see [FFmpeg](#ffmpeg)).
2. Make the AppImage executable: `chmod +x YT-DLP-Studio-*.AppImage`.
3. Run the AppImage.

Your desktop may offer to add the AppImage to the app menu.

**Updates:** the app can download the new AppImage. Make the new file executable and start it. You can delete the old AppImage afterwards.

### Linux archive (.tar.gz)

1. Install FFmpeg (see [FFmpeg](#ffmpeg)).
2. Download `yt-dlp-studio-v<version>-Linux.tar.gz`.
3. Extract the archive:

   ```bash
   tar -xzf yt-dlp-studio-*-Linux.tar.gz
   ```

4. Add the app to your app menu. The script installs to `~/.local` and needs no root:

   ```bash
   ./install.sh
   ```

5. Start YT-DLP Studio from your app menu, or run `yt-dlp-studio`.

`install.sh` works on any desktop that follows the XDG specification (GNOME, KDE, XFCE, Cinnamon and others). If FFmpeg is missing, it prints the install command for your package manager. To run the binary without installing it, run `chmod +x yt-dlp-studio && ./yt-dlp-studio`.

### FFmpeg

The AppImage and the Linux archive need FFmpeg from your distribution. The .deb and .rpm packages install it for you.

| Distribution | Command |
|--------------|---------|
| Debian, Ubuntu, Mint | `sudo apt install ffmpeg` |
| Fedora, RHEL | `sudo dnf install ffmpeg` (may need RPM Fusion) |
| Arch, Manjaro | `sudo pacman -S ffmpeg` |
| openSUSE | `sudo zypper install ffmpeg` |
| Alpine | `sudo apk add ffmpeg` |

### Deno

yt-dlp uses Deno to solve YouTube's JavaScript challenges. The Linux builds do not include Deno. Without Deno, the app still works, but YouTube may offer fewer formats. To use Deno, install it from [deno.land](https://deno.land/) and make sure `deno` is on your `PATH`.

### Desktop libraries

The Linux builds include Qt. They also need some system libraries, for example libGL, libEGL, libxkbcommon, libdbus, libxcb-cursor, fontconfig and GLib. A desktop environment usually has them. On a minimal or server install, you may need to install them with your package manager. The .deb package lists them as dependencies.

## Run from source

Use a source install if you want to change the code, or if no build fits your system.

### 1. Install the prerequisites

1. Install Python 3.11 or later from [python.org](https://www.python.org/downloads/).
2. On Windows, select **Add python.exe to PATH** in the Python installer.
3. Install Git.
4. On Linux, install FFmpeg (see [FFmpeg](#ffmpeg)).

### 2. Get the code

```bash
git clone https://github.com/NX1X/yt-dlp-studio.git
cd yt-dlp-studio
```

### 3. Create and activate a virtual environment

A virtual environment is optional, but recommended. It keeps the app's dependencies apart from other Python projects.

```bash
python -m venv .venv
```

Activate it:

| Shell | Command |
|-------|---------|
| Windows Command Prompt | `.venv\Scripts\activate.bat` |
| Windows PowerShell | `.venv\Scripts\Activate.ps1` |
| Git Bash on Windows | `source .venv/Scripts/activate` |
| Linux | `source .venv/bin/activate` |

When the environment is active, your prompt shows `(.venv)`. To leave it, run `deactivate`.

### 4. Install the dependencies

```bash
pip install -e .
```

This installs the runtime dependencies from `pyproject.toml`:

- PySide6 (the Qt 6 GUI framework). It is the largest dependency, about 650 MB on disk (measured on Linux with Python 3.13).
- requests (used by the update checker).
- packaging (used to compare version numbers).
- yt-dlp-ejs (the JavaScript challenge solver scripts for the bundled yt-dlp).

To install the exact, hash-pinned versions that CI uses, run this instead:

```bash
pip install --require-hashes -r requirements/lock.txt
```

### 5. Start the app

```bash
python launcher.py
```

If the app cannot find Deno on the first start, it downloads Deno 2.9.8 into the `deno` folder of the project. The download is about 30 MB and happens once. If the download fails, the app still works, with fewer YouTube formats.

### Alternative: Conda

```bash
conda create -n ytdlp python=3.11
conda activate ytdlp
cd yt-dlp-studio
pip install -e .
python launcher.py
```

## Change the language

1. Open the **Settings** tab.
2. Select a language in **Language** (English or עברית, Hebrew).
3. Click **Save Settings**.
4. Restart the app.

## Uninstall

Uninstalling never deletes your downloaded videos. It keeps the app data folder unless you ask to delete it.

| Install type | How to uninstall |
|--------------|------------------|
| Installer | Uninstall from Windows Settings, in the list of installed apps. |
| Portable EXE or ZIP | Delete the EXE file. |
| .deb package | `sudo apt remove yt-dlp-studio` |
| .rpm package | `sudo dnf remove yt-dlp-studio` |
| AppImage | Delete the AppImage file. |
| Linux archive | Run `./uninstall.sh` from the extracted archive. |
| Source install | Delete the project folder. |

The Windows uninstaller asks if it should also delete your settings, history and logs. The default answer is No. For an unattended uninstall, the data is kept unless you pass `/PURGEDATA=yes`. Removing or purging the .deb or .rpm package keeps the app data folder.

### App data folder

The app data folder holds your settings, log file, download history, saved queue and crash reports.

| System | App data folder |
|--------|-----------------|
| Windows | `%APPDATA%\YT-DLP Studio` |
| Linux | `~/.config/YT-DLP Studio` |

The language choice is stored in a different folder: `.yt-dlp-studio` in your home folder. No uninstaller removes it.

To remove all your data, delete both folders by hand.

## Verify a download

Each release publishes a signed build provenance attestation. It covers the portable EXE, the Linux binary, the AppImage, the .deb and the .rpm. It does not cover the Windows installer.

1. Install the [GitHub CLI](https://cli.github.com/).
2. Run `gh attestation verify <file> --repo NX1X/yt-dlp-studio`.

If the command fails, do not run the file. [SECURITY.md](../SECURITY.md#verifying-a-downloaded-release) has the details.

## Troubleshooting a source install

### "py: command not found"

Use `python` instead of `py`, for example `python -m venv .venv`.

### "cannot be loaded because running scripts is disabled"

PowerShell blocks the activation script. Allow local scripts for your user, then activate the environment again:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### "No module named 'PySide6'"

The virtual environment is not active. Activate it again (see step 3). Your prompt must show `(.venv)`.

### PySide6 does not install

Possible causes:

1. Your Python version is older than 3.11. Run `python --version` to check.
2. There is a problem with your internet connection.
3. There is not enough disk space.

### Other checks

1. Run `pip list` to see the installed packages.
2. Reinstall the dependencies with `pip install --force-reinstall -e .`.

If you still have a problem, [open an issue](https://github.com/NX1X/yt-dlp-studio/issues/new/choose).
