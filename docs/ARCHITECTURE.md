# Architecture

This document explains the structure of the YT-DLP Studio code. It helps contributors find the right place for a change.

## Contents

- [Overview](#overview)
- [Project structure](#project-structure)
- [Key components](#key-components)
- [Download flow](#download-flow)
- [Runtime files](#runtime-files)
- [Packaging](#packaging)
- [How to add features](#how-to-add-features)
- [Debugging guide](#debugging-guide)
- [Common change points](#common-change-points)

## Overview

YT-DLP Studio is a PySide6 GUI application. It wraps a vendored copy of yt-dlp.

**Layers:**

| Layer | Folder | Contents |
|-------|--------|----------|
| UI | `src/ui/` | PySide6 tabs, dialogs, widgets and the theme |
| Backend | `src/backend/` | Downloads, queue, history, config, update checks |
| Data models | `src/models/` | Data classes for config, tasks, queue, history, video info |
| Utilities | `src/utils/` | Constants, logging, translations, validation, helpers |

**Threading model:**

- The main thread renders the GUI and handles user input.
- Worker threads (`QThread`) run downloads and other network work: video info, playlist info, subtitle lists and update checks.
- Workers talk to the GUI only through Qt signals.

## Project structure

```
yt-dlp-studio/
├── launcher.py                  # Entry point - start here
├── src/
│   ├── app.py                   # Application setup
│   ├── ui/
│   │   ├── main_window.py       # Main window with five tabs
│   │   ├── download_tab.py      # Download tab
│   │   ├── queue_tab.py         # Queue tab
│   │   ├── history_tab.py       # History tab
│   │   ├── settings_tab.py      # Settings tab
│   │   ├── about_tab.py         # About tab (versions, credits, shortcuts)
│   │   ├── playlist_dialog.py   # Select videos from a playlist or channel
│   │   ├── batch_input_dialog.py         # Add many URLs at once
│   │   ├── subtitle_selection_dialog.py  # Select subtitle languages
│   │   ├── video_info_dialog.py # Video info preview
│   │   ├── update_dialog.py     # Update download and install
│   │   ├── progress_bar.py      # Progress widget
│   │   ├── log_widget.py        # Log widget
│   │   └── theme.py             # Dark and light themes
│   ├── backend/
│   │   ├── yt_dlp_wrapper.py    # Interface to yt-dlp
│   │   ├── download_worker.py   # QThread for one download
│   │   ├── queue_manager.py     # Queue, concurrency, retries, queue file
│   │   ├── history_manager.py   # Download history file
│   │   ├── config_manager.py    # Settings file
│   │   ├── format_handler.py    # Quality names to yt-dlp format strings
│   │   ├── progress_handler.py  # Raw yt-dlp progress to UI data
│   │   ├── playlist_fetcher.py  # Playlist information
│   │   ├── playlist_worker.py, video_info_worker.py, subtitle_list_worker.py
│   │   ├── update_checker.py    # GitHub release checks and verified downloads
│   │   └── environment.py       # Runtime details (FFmpeg version, startup log line)
│   ├── models/
│   │   ├── app_config.py        # Settings model
│   │   ├── download_task.py     # One download task
│   │   ├── download_queue.py    # Queue model
│   │   ├── download_history.py  # History model
│   │   └── video_info.py        # Video metadata
│   ├── utils/
│   │   ├── constants.py         # App constants, quality options, paths
│   │   ├── logger.py            # Logging setup
│   │   ├── translations.py      # English and Hebrew strings, RTL
│   │   ├── validators.py        # URL and folder validation
│   │   ├── notification_manager.py  # Desktop notifications, tray icon
│   │   ├── crash_handler.py     # Crash reports
│   │   ├── deno_installer.py    # Downloads Deno when running from source
│   │   └── ...                  # Other helpers
│   └── resources/               # Icons, stylesheet, default config
├── vendor/yt_dlp_engine/yt_dlp/ # Vendored yt-dlp
├── packaging/                   # PyInstaller specs, Inno Setup, Linux packaging
├── requirements/                # Hash-pinned lock files
├── scripts/                     # Build checks, version sync, relock
├── tests/                       # pytest suite
└── docs/                        # Documentation
```

## Key components

### Entry point: `launcher.py`

The app starts here. `launcher.py`:

1. adds `src/` to the Python path;
2. installs the global crash handler;
3. creates the `App` instance;
4. runs the app and exits with its exit code.

To debug startup problems, check the log file first.

### Application: `src/app.py`

The `App` class:

- calls `ensure_deno_installed()` (this downloads Deno only when the app runs from source and cannot find it);
- on Windows, sets the AppUserModelID for the taskbar;
- creates the `QApplication`;
- loads the configuration through `ConfigManager`;
- creates the main window.

`App.run()` starts the Qt event loop.

### Main window: `src/ui/main_window.py`

The main window holds five tabs: Download, Queue, History, Settings and About. It creates the shared `QueueManager` (up to 3 concurrent downloads), `HistoryManager` and `NotificationManager`. It also restores the saved queue and the window state.

To add a tab:

1. Create a tab class in `src/ui/`.
2. Import it in `main_window.py`.
3. Add it with `self.tabs.addTab(NewTab(), tr("tab_new"))`, and add the translation key.

### Download tab: `src/ui/download_tab.py`

The main download interface: URL input, quality, format, options, output folder, the download buttons, progress and the log.

Key methods:

- `_setup_ui()`: builds the layout. Edit it to change the UI.
- `_on_download_clicked()`: validates the input, adds the task to the queue, and the queue starts it at once.
- `_on_progress_updated(data)`: updates the progress display.

### Queue manager: `src/backend/queue_manager.py`

Coordinates all downloads, including **Download Now**. It:

- starts a `DownloadWorker` for each task, with at most `max_concurrent` running at the same time;
- handles pause, resume, cancel, reorder and retry, including automatic retries for some errors;
- records finished downloads in the history;
- saves the queue to a file and restores it on the next start.

Signals: `queue_updated`, `task_started`, `task_completed`, `task_failed`, `task_progress`, `all_completed`, `history_recorded`.

### Download worker: `src/backend/download_worker.py`

**Critical component.** A `QThread` subclass that runs one download without blocking the GUI.

Signals:

- `progress_updated`: progress data
- `download_started`: video title
- `download_completed`: file name
- `download_failed`: error message
- `log_message`: log messages

Key methods:

- `run()`: runs in the background thread (Qt calls it).
- `_on_progress()`: receives the yt-dlp progress.

**Thread safety:** all GUI updates must go through signals. Direct GUI changes from a worker thread can crash the app.

### yt-dlp wrapper: `src/backend/yt_dlp_wrapper.py`

**Critical component.** The interface to yt-dlp. It:

- imports the vendored yt-dlp;
- extracts video information;
- downloads videos;
- passes progress through callbacks;
- finds FFmpeg and Deno.

Key methods:

- `get_video_info(url)`: extracts metadata.
- `download(...)`: downloads a video.
- `get_available_subtitles(url)`: lists subtitle languages.
- `_progress_hook(data)`: receives the yt-dlp progress.

**Path setup:** the top of the file adds `vendor/yt_dlp_engine/` to `sys.path` (in a frozen build, the bundled `yt_dlp_engine` folder), then imports `yt_dlp`.

### Configuration manager: `src/backend/config_manager.py`

Loads and saves the settings as JSON, validates them and supplies default values. The file is `yt-dlp-studio_config.json` in the app data folder (see [Runtime files](#runtime-files)).

## Download flow

```
User clicks Download Now (or Add to Queue, then Start Queue)
    ↓
DownloadTab validates the URL and the folder
    ↓
DownloadTab creates a DownloadTask and calls QueueManager.add_task()
    ↓
QueueManager starts a DownloadWorker when a slot is free (max 3)
    ↓
DownloadWorker.run() in the background thread:
    ├─→ YtDlpWrapper.get_video_info()
    ├─→ YtDlpWrapper.download()
    └─→ progress updates through signals
        ↓
        QueueManager forwards them; the UI updates:
        ├─→ progress bar
        ├─→ speed and ETA
        └─→ log messages
    ↓
The download completes or fails
    ↓
QueueManager records the result in the history,
sends a notification and starts the next task
```

## Runtime files

All files below are in the app data folder: `%APPDATA%\YT-DLP Studio` on Windows, `~/.config/YT-DLP Studio` on Linux (`get_app_data_dir()` in `src/utils/constants.py`).

| File | Contents |
|------|----------|
| `yt-dlp-studio_config.json` | Settings |
| `yt-dlp-studio.log` | Log file (rotates at 5 MB, 3 backups) |
| `download_history.json` | Download history |
| `download_queue.json` | Saved queue |
| `crashes/crash-*.json` | Crash reports |

The language choice is an exception. `src/ui/settings_tab.py` saves it to `~/.yt-dlp-studio/language.json`.

## Packaging

- `packaging/build.spec`: the Windows one-file EXE. It bundles FFmpeg, Deno, the vendored yt-dlp and `src/resources`.
- `packaging/build_linux.spec`: the Linux binary. It does not bundle FFmpeg or Deno.
- `packaging/installer.iss`: the Inno Setup installer around the Windows EXE.
- `packaging/linux/build_packages.sh`: builds the AppImage, .deb and .rpm from the Linux binary.
- `scripts/check_bundle.py`: checks the contents of a built executable.

## How to add features

### Add a quality option

1. Add it to `QUALITY_OPTIONS` in `src/utils/constants.py`:

   ```python
   "4K (2160p)": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
   ```

2. `FormatHandler` reads `QUALITY_OPTIONS` automatically. For an audio option, also add the bitrate to `AUDIO_QUALITY_MAP`. To translate the name, add it to `quality_map` in `FormatHandler.get_available_qualities()`.

### Add a setting

1. Add the field to `AppConfig` in `src/models/app_config.py`:

   ```python
   @dataclass
   class AppConfig:
       ...
       new_setting: str = "default_value"
   ```

2. Update `_create_default_config()` in `src/backend/config_manager.py`.
3. In `src/ui/settings_tab.py`, add a widget and update `_load_settings()` and `_save_settings()`.

## Debugging guide

### The app does not start

1. Check the Python version. The app needs Python 3.11 or later:

   ```bash
   python --version
   ```

2. Check that the dependencies are installed:

   ```bash
   pip install --require-hashes -r requirements/lock.txt
   ```

3. Read the log file:
   - Windows: `%APPDATA%\YT-DLP Studio\yt-dlp-studio.log`
   - Linux: `~/.config/YT-DLP Studio/yt-dlp-studio.log`

### A download fails

Check the log first. Common causes:

1. **The yt-dlp import fails:** check that `vendor/yt_dlp_engine/yt_dlp/` exists. See the path setup at the top of `src/backend/yt_dlp_wrapper.py`.
2. **The URL is not supported:** check the yt-dlp version (`YTDLP_VERSION` in `src/utils/constants.py`). Try the URL with yt-dlp on the command line.
3. **Permission denied:** check that the output folder is writable. See `Validators.is_valid_directory()` in `src/utils/validators.py`.

### The GUI freezes during a download

This must never happen. If it does:

- a download or network call runs on the main thread instead of a worker;
- check that the code uses `DownloadWorker` (or another worker);
- check that the signals are connected.

### Add debug logging

```python
from src.utils.logger import get_logger

logger = get_logger()

logger.debug("Debug message")
logger.info("Info message")
logger.error("Error message")
```

`DEBUG` messages appear only if `LOG_LEVEL` in `src/utils/constants.py` is `"DEBUG"`. The default is `"INFO"`.

## Working on the code

### Fixing bugs

1. Ask for the log file first.
2. Read the relevant files. Most files have one purpose.
3. Check the imports. Circular imports cause problems.

### Adding features

1. Follow the existing patterns: look at similar features, use the same naming, add logging.
2. Update this document and, for planned features, `ROADMAP.md`.
3. Change a little at a time and test each change. Do not change many files at once.

Keep new files small and focused. Some existing files are large (for example `download_tab.py`, `queue_manager.py` and `yt_dlp_wrapper.py` have more than 1000 lines each).

## Common change points

| Task | Files |
|------|-------|
| Add a quality option | `src/utils/constants.py` |
| Add a setting | `src/models/app_config.py`, `src/backend/config_manager.py`, `src/ui/settings_tab.py` |
| Change a tab layout | `src/ui/<name>_tab.py` |
| Change download logic | `src/backend/yt_dlp_wrapper.py` |
| Change queue behavior | `src/backend/queue_manager.py` |
| Change the progress display | `src/ui/progress_bar.py` |
| Add or change a UI string | `src/utils/translations.py` (`en` and `he`) |
| Add logging | Any file: import `get_logger()` |
| Change the styling | `src/ui/theme.py` |

## Questions

- Read the other docs in `docs/`.
- Read the code comments. Each file has a docstring that explains its purpose.
- Check the log files.
