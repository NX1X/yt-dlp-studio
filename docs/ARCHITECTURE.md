# YT-DLP Studio Architecture

This document explains the architecture and structure of YT-DLP Studio to help you (or AI assistants like Claude) understand and modify the codebase.

## Table of Contents
- [Overview](#overview)
- [Project Structure](#project-structure)
- [Key Components](#key-components)
- [Data Flow](#data-flow)
- [How to Add Features](#how-to-add-features)
- [Debugging Guide](#debugging-guide)

---

## Overview

YT-DLP Studio is a GUI application that wraps yt-dlp to provide a user-friendly interface for downloading videos.

**Architecture Pattern:** Layered Architecture
- **UI Layer:** PySide6 widgets (in `src/ui/`)
- **Business Logic:** Backend operations (in `src/backend/`)
- **Data Models:** Data structures (in `src/models/`)
- **Utilities:** Helper functions (in `src/utils/`)

**Threading Model:**
- Main thread: GUI rendering and user interaction
- Worker threads: Download operations (using `QThread`)

---

## Project Structure

```
yt-dlp-for-users/
├── launcher.py                 # Entry point - START HERE
├── src/                        # Main application source
│   ├── app.py                  # Application initialization
│   ├── ui/                     # User interface components
│   │   ├── main_window.py      # Main window with tabs
│   │   ├── download_tab.py     # Download interface
│   │   ├── settings_tab.py     # Settings interface
│   │   ├── progress_bar.py     # Progress display widget
│   │   └── log_widget.py       # Log display widget
│   ├── backend/                # Business logic
│   │   ├── config_manager.py   # Settings persistence
│   │   ├── yt_dlp_wrapper.py   # yt-dlp API interface
│   │   ├── download_worker.py  # Threading for downloads
│   │   ├── progress_handler.py # Progress data processing
│   │   └── format_handler.py   # Quality/format selection
│   ├── models/                 # Data structures
│   │   ├── app_config.py       # Configuration model
│   │   ├── download_task.py    # Download task model
│   │   └── video_info.py       # Video metadata model
│   ├── utils/                  # Utilities
│   │   ├── constants.py        # App constants
│   │   ├── logger.py           # Logging setup
│   │   ├── validators.py       # Input validation
│   │   └── file_helper.py      # File operations
│   └── resources/              # Assets
│       ├── icons/              # Icons (placeholders for now)
│       ├── styles/             # Qt stylesheets
│       └── config/             # Default config
├── yt_dlp_engine/              # Bundled yt-dlp
│   └── yt_dlp/                 # Actual yt-dlp module
├── docs/                       # Documentation
├── tests/                      # Test files
└── build/                      # Build artifacts

```

---

## Key Components

### 1. Application Entry Point

**File:** `launcher.py` (30 lines)

This is where the application starts. It:
1. Adds `src/` to Python path
2. Creates `App` instance
3. Runs the app

**To debug startup issues:** Add print statements or check logs here.

---

### 2. Application Class

**File:** `src/app.py` (~70 lines)

Creates and configures the Qt application:
- Initializes `QApplication`
- Loads configuration
- Creates main window
- Starts event loop

**Key methods:**
- `__init__()`: Setup
- `run()`: Start the app

---

### 3. Main Window

**File:** `src/ui/main_window.py` (~150 lines)

The main application window with:
- Tab widget (Download, Settings)
- Menu bar (File, Help)
- Status bar
- Window state management

**To add a new tab:**
1. Create new tab class in `src/ui/`
2. Import it in `main_window.py`
3. Add with `self.tabs.addTab(NewTab(), "Tab Name")`

---

### 4. Download Tab

**File:** `src/ui/download_tab.py` (~250 lines)

Main download interface:
- URL input
- Quality selector
- Directory chooser
- Download button
- Progress display
- Log output

**Key methods:**
- `_on_download_clicked()`: Start download
- `_start_download(task)`: Create worker thread
- `_on_progress_updated(data)`: Update progress bar

**To modify UI:** Edit `_setup_ui()` method

---

### 5. Download Worker

**File:** `src/backend/download_worker.py` (~180 lines)

**CRITICAL COMPONENT** - Handles threaded downloads

Extends `QThread` to run downloads without blocking GUI.

**Signals (for GUI communication):**
- `progress_updated` → Update progress bar
- `download_started` → Show video title
- `download_completed` → Show success
- `download_failed` → Show error

**Key methods:**
- `run()`: Executes in background thread (AUTO-CALLED)
- `_on_progress()`: Receives yt-dlp progress

**Threading Safety:**
- All GUI updates MUST use signals
- Direct GUI manipulation will crash

---

### 6. yt-dlp Wrapper

**File:** `src/backend/yt_dlp_wrapper.py` (~160 lines)

**CRITICAL COMPONENT** - Interfaces with yt-dlp

Handles:
- Importing bundled yt-dlp
- Extracting video info
- Downloading videos
- Progress callbacks

**Key methods:**
- `get_video_info(url)`: Extract metadata
- `download(url, output_dir, format_string)`: Download video
- `_progress_hook(data)`: Receive yt-dlp progress

**Path handling:**
- Adds `yt_dlp_engine/` to `sys.path`
- Imports `yt_dlp` module
- See lines 14-30 for path setup

---

### 7. Configuration Manager

**File:** `src/backend/config_manager.py` (~150 lines)

Manages settings persistence:
- Load from JSON
- Save to JSON
- Validate settings
- Default values

**Config location:** `~/.config/YT-DLP Studio/yt-dlp-studio_config.json` (Linux) or `%APPDATA%/YT-DLP Studio/...` (Windows)

**To add new setting:**
1. Add field to `AppConfig` in `src/models/app_config.py`
2. Update default in `_create_default_config()`
3. Use in UI: `config.new_field`

---

## Data Flow

### Download Operation Flow

```
User clicks Download
    ↓
DownloadTab._on_download_clicked()
    ↓
Validate URL and directory
    ↓
Create DownloadTask model
    ↓
Create DownloadWorker thread
    ↓
Connect signals to UI callbacks
    ↓
Worker.start() → runs in background
    ↓
Worker.run() executes:
    ↓
    ├─→ YtDlpWrapper.get_video_info()
    ├─→ YtDlpWrapper.download()
    └─→ Progress updates via signals
        ↓
        UI receives signals and updates:
        ├─→ Progress bar
        ├─→ Speed/ETA labels
        └─→ Log messages
    ↓
Download completes/fails
    ↓
Worker emits final signal
    ↓
UI shows result dialog
```

---

## How to Add Features

### Adding a New Quality Option

1. **Edit:** `src/utils/constants.py`
   - Add to `QUALITY_OPTIONS` dict
   ```python
   "4K": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
   ```

2. **No other changes needed!**
   - FormatHandler automatically reads from QUALITY_OPTIONS

---

### Adding a New Setting

1. **Edit:** `src/models/app_config.py`
   ```python
   @dataclass
   class AppConfig:
       ...
       new_setting: str = "default_value"
   ```

2. **Edit:** `src/backend/config_manager.py`
   - Update `_create_default_config()`

3. **Edit:** `src/ui/settings_tab.py`
   - Add UI widget for new setting
   - Update `_load_settings()` and `_save_settings()`

---

### Adding Download Queue Support (Future)

1. **Create:** `src/backend/download_queue.py`
   - Manage list of DownloadTask objects
   - Handle concurrent downloads limit

2. **Modify:** `src/ui/download_tab.py`
   - Add queue table widget
   - Multiple tasks instead of single

3. **Modify:** `src/backend/download_worker.py`
   - Support cancellation better

---

## Debugging Guide

### Application Won't Start

**Check:**
1. Python version: Requires Python 3.10+
   ```bash
   python --version
   ```

2. Dependencies installed:
   ```bash
   pip install -r requirements.txt
   ```

3. Log file location:
   - Windows: `%APPDATA%/YT-DLP Studio/yt-dlp-studio.log`
   - Linux: `~/.config/YT-DLP Studio/yt-dlp-studio.log`

---

### Download Fails

**Check logs first!**

Common issues:
1. **yt-dlp import fails:**
   - Check `yt_dlp_engine/yt_dlp/` exists
   - See: `src/backend/yt_dlp_wrapper.py:14-30`

2. **URL not supported:**
   - Check yt-dlp version
   - Try URL in command line: `python -m yt_dlp URL`

3. **Permission denied:**
   - Check output directory is writable
   - See: `src/utils/validators.py:is_valid_directory()`

---

### GUI Freezes During Download

**This should NEVER happen!**

If it does:
- Downloads are NOT running in background thread
- Check: `src/backend/download_worker.py` is being used
- Check: Signals are connected properly

---

### Adding Debug Logging

```python
from src.utils.logger import get_logger

logger = get_logger()

logger.debug("Debug message")  # Only in log file
logger.info("Info message")    # Console + file
logger.error("Error message")  # Console + file
```

---

## For AI Assistants (Like Claude)

### When Helping with Bugs

1. **Ask for log file first:**
   - `%APPDATA%/YT-DLP Studio/yt-dlp-studio.log` (Windows)
   - `~/.config/YT-DLP Studio/yt-dlp-studio.log` (Linux)

2. **Read relevant files:**
   - Each file is ~50-250 lines (AI-friendly)
   - Files are single-purpose

3. **Check imports:**
   - Circular imports will cause issues
   - Check file header imports

### When Adding Features

1. **Follow existing patterns:**
   - Look at similar existing features
   - Use same naming conventions
   - Add logging

2. **Update documentation:**
   - Update this file
   - Update ROADMAP.md if future feature

3. **Test incrementally:**
   - Add small changes
   - Test each change
   - Don't modify 10 files at once

### File Size Reference

Each file is intentionally kept small:
- Utils: ~50-100 lines
- Models: ~50-100 lines
- Backend: ~100-200 lines
- UI: ~100-250 lines

**Why?** Easier for AI to read and understand entire files.

---

## Common Modification Points

| Task | Files to Edit |
|------|---------------|
| Add quality option | `src/utils/constants.py` |
| Add setting | `src/models/app_config.py`, `src/ui/settings_tab.py` |
| Change UI layout | `src/ui/download_tab.py` or `settings_tab.py` |
| Modify download logic | `src/backend/yt_dlp_wrapper.py` |
| Change progress display | `src/ui/progress_bar.py` |
| Add logging | Any file - import `get_logger()` |
| Change styling | `src/resources/styles/stylesheet.qss` |

---

## Questions?

- Check other docs in `docs/`
- Read code comments
- Check log files
- Each file has docstrings explaining purpose

---

**Last Updated:** 2024-10-26
**For:** YT-DLP Studio v1.0.0
