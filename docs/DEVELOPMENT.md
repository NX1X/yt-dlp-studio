# Development Guide

This guide is for developers who work on YT-DLP Studio. For the contribution rules (branches, commits, pull requests, changelog), see [CONTRIBUTING.md](../CONTRIBUTING.md). For the code structure, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Prerequisites

| Tool | Check |
|------|-------|
| Python 3.11 or later | `python --version` |
| pip | `pip --version` |
| Git | `git --version` |
| FFmpeg (Linux only; the Windows build bundles it) | `ffmpeg -version` |

## Set up the environment

1. Clone the repository:

   ```bash
   git clone https://github.com/NX1X/yt-dlp-studio.git
   cd yt-dlp-studio
   ```

2. Create a virtual environment (recommended):

   ```bash
   python -m venv .venv
   ```

3. Activate it:
   - Windows: `.venv\Scripts\activate`
   - Linux: `source .venv/bin/activate`

4. Install the hash-pinned runtime and development dependencies:

   ```bash
   pip install --require-hashes -r requirements/dev.txt
   ```

5. Make sure the vendored yt-dlp engine is present:

   ```bash
   ls vendor/yt_dlp_engine/yt_dlp
   ```

## Run the app

From the command line:

```bash
python launcher.py
```

From an IDE (VS Code, PyCharm and others), set `launcher.py` as the entry point, then run or debug as usual.

On the first start from source, the app downloads Deno 2.9.8 into `deno/` if it cannot find Deno (see `src/utils/deno_installer.py`).

## Project structure

```
yt-dlp-studio/
├── launcher.py            # Entry point
├── src/
│   ├── app.py             # Application setup
│   ├── ui/                # PySide6 tabs, dialogs, widgets, theme
│   ├── backend/           # Downloads, queue, history, config, updates
│   ├── models/            # Data models
│   ├── utils/             # Constants, logging, translations, helpers
│   └── resources/         # Icons, stylesheet, default config
├── vendor/yt_dlp_engine/  # Vendored yt-dlp
├── packaging/             # PyInstaller specs, Inno Setup script, Linux packaging
├── requirements/          # Hash-pinned lock files
├── scripts/               # Version sync, bundle checks, relock, test helpers
├── tests/                 # pytest suite
└── docs/                  # Documentation
```

[ARCHITECTURE.md](ARCHITECTURE.md) explains each part.

## Workflow

### Before you change code

- Read [ARCHITECTURE.md](ARCHITECTURE.md).
- Understand the component you change.
- Check the existing issues and feature requests.

### While you change code

- Create a new branch.
- Make small, focused changes.
- Add logging where it helps debugging.
- Update docstrings and comments.

### Test the change

- Run the test suite (see [Tests](#tests)).
- Test the change by hand in the GUI.
- Check the log file for errors.
- Test edge cases.
- If possible, test on Windows 10 and 11.

### Before you commit

- Remove debug print statements.
- Run the formatters and linters (`ruff`, `black`). The pre-commit hooks do this for you.
- Update the documentation if needed.
- Test one more time.

## Coding guidelines

### Python style

- Follow PEP 8, with a line length of 120 characters.
- Use type hints.
- Write docstrings for functions and classes.
- Keep functions small and focused.

Example:

```python
def download_video(url: str, output_dir: str) -> bool:
    """
    Download video from URL.

    Args:
        url: Video URL
        output_dir: Output directory

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Downloading: {url}")
    # ... implementation
```

### File organization

- Put one class in each file (usually).
- Group related functions together.
- Aim for files under 250 lines. Some existing files are much larger, for example `src/ui/download_tab.py` and `src/backend/yt_dlp_wrapper.py` (about 1300 lines each).
- Use `__init__.py` for imports.

### Import order

```python
# Standard library first
import os
import sys
from pathlib import Path

# Third-party packages
from PySide6.QtWidgets import QWidget

# Local imports
from ..models import DownloadTask
from ..utils.logger import get_logger
```

### Naming

| Kind | Style | Example |
|------|-------|---------|
| Classes | `PascalCase` | `DownloadTask` |
| Functions | `snake_case` | `download_video` |
| Constants | `UPPER_SNAKE_CASE` | `APP_VERSION` |
| Private members | `_` prefix | `_internal_method` |

### Threads

Downloads and other network work run in `QThread` workers. Update the GUI only through signals. Do not touch widgets from a worker thread.

### Translations

Every user-facing string goes through `tr()` and needs a key in both the `en` and `he` dictionaries in `src/utils/translations.py`.

## Logging

```python
from src.utils.logger import get_logger

logger = get_logger()

logger.debug("Detailed debug info")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical error")
```

| Level | Use for |
|-------|---------|
| `DEBUG` | Detailed diagnostic information |
| `INFO` | General information |
| `WARNING` | Warnings |
| `ERROR` | Errors that do not crash the app |
| `CRITICAL` | Critical errors |

The logger writes to the console (`INFO` and above) and to a rotating log file (5 MB, 3 backups). The logger level comes from `LOG_LEVEL` in `src/utils/constants.py`, which is `INFO` by default. To see `DEBUG` messages in the log file, set `LOG_LEVEL = "DEBUG"` temporarily. The logger removes secrets from messages before it writes them.

Log file location:

- Windows: `%APPDATA%\YT-DLP Studio\yt-dlp-studio.log`
- Linux: `~/.config/YT-DLP Studio/yt-dlp-studio.log`

## Common tasks

### Add a setting

1. Add the field to `AppConfig` in `src/models/app_config.py`:

   ```python
   @dataclass
   class AppConfig:
       ...
       new_setting: str = "default"
   ```

2. Update `_create_default_config()` in `src/backend/config_manager.py`.
3. Add a widget in `src/ui/settings_tab.py`.
4. Update `_load_settings()` and `_save_settings()` in the same file.
5. Add the translation keys for the label (`en` and `he`).
6. Start the app, change the setting, and restart. Check that the setting is kept.

### Add a quality option

1. Add the option to `QUALITY_OPTIONS` in `src/utils/constants.py`:

   ```python
   QUALITY_OPTIONS = {
       ...
       "4K (2160p)": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
   }
   ```

2. For an audio option, also add the bitrate to `AUDIO_QUALITY_MAP`.
3. If the name needs a translation, add it to `quality_map` in `FormatHandler.get_available_qualities()` (`src/backend/format_handler.py`). Names without an entry are shown as they are.
4. Start the app, check the dropdown, and download with the new option.

### Change the UI

1. Find the file:
   - Main window: `src/ui/main_window.py`
   - Download tab: `src/ui/download_tab.py`
   - Queue tab: `src/ui/queue_tab.py`
   - History tab: `src/ui/history_tab.py`
   - Settings tab: `src/ui/settings_tab.py`
   - About tab: `src/ui/about_tab.py`
2. Edit its `_setup_ui()` method.
3. Start the app and check the change.

## Tests

Run the full suite:

```bash
QT_QPA_PLATFORM=offscreen pytest -q
```

On a Linux machine without a display, use `xvfb-run --auto-servernum pytest tests/ -v`. [tests/README.md](../tests/README.md) has more examples.

### Manual test checklist

- [ ] The app starts without errors.
- [ ] URL validation works.
- [ ] Folder selection works.
- [ ] A download completes.
- [ ] The progress bar updates.
- [ ] Log messages appear.
- [ ] Settings are saved and loaded.
- [ ] Errors are handled.
- [ ] The window size is kept.

### Test URLs

- A YouTube video
- A YouTube playlist
- An invalid URL
- A video that does not exist
- Optional: a Vimeo or Twitter video. Only YouTube is officially supported, so a failure here is not a release blocker.

## Debugging

**The app does not start:**

1. Check the log file.
2. Check your Python version.
3. Check that the dependencies are installed.
4. Check that `vendor/yt_dlp_engine/yt_dlp` exists.

**Import errors:**

1. Check that the virtual environment is active.
2. Check the file paths.
3. Check for circular imports.

**A download fails:**

1. Check the log file for yt-dlp errors.
2. Test the URL with yt-dlp on the command line.
3. Check your network connection.
4. Check that the output folder is writable.

**Debug output:** set `LOG_LEVEL = "DEBUG"` in `src/utils/constants.py`. You can also add this to `launcher.py` temporarily:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Build the executables

The specs are in `packaging/`. CI builds the release files. To build locally:

1. Install PyInstaller with the hash-pinned build tools (`requirements/build-tools.txt`).
2. Check the imports before the build:

   ```bash
   python scripts/check_imports.py
   ```

3. Sync the version files:

   ```bash
   python scripts/sync_version.py
   ```

4. Build:
   - Windows: `pyinstaller packaging/build.spec`. Put Deno in `deno/deno.exe` and FFmpeg in `ffmpeg/bin/` first; the spec bundles them.
   - Linux: `pyinstaller packaging/build_linux.spec`. The Linux build does not bundle FFmpeg or Deno.
5. Check the bundle:

   ```bash
   python scripts/check_bundle.py dist/yt-dlp-studio.exe   # Windows
   python scripts/check_bundle.py dist/yt-dlp-studio       # Linux
   ```

6. Test the executable, on a clean system if possible.

The Windows EXE is about 200 MB (0.3.1). CI wraps it in the Inno Setup installer (`packaging/installer.iss`). It builds the Linux packages with `packaging/linux/build_packages.sh`.

## Update the vendored yt-dlp

Use the **Bump yt-dlp engine** workflow (`.github/workflows/bump-yt-dlp-engine.yml`). Start it by hand from the Actions tab. It:

1. downloads the official yt-dlp tarball for the version;
2. checks the published SHA-256 from `SHA2-256SUMS`;
3. replaces `vendor/yt_dlp_engine/yt_dlp/`;
4. updates `YTDLP_VERSION` in `src/utils/constants.py` and the note in `packaging/build.spec`;
5. runs `scripts/check_imports.py` and the test suite;
6. opens a pull request for review.

Renovate waits 7 days after a yt-dlp release before it proposes the update. The workflow saves the manual work after that cooldown; it is not a way around it.

## Dependencies

Runtime and optional dependencies are declared in `pyproject.toml`. The hash-pinned lock files are in `requirements/`.

To add or update a dependency:

1. Edit `pyproject.toml`.
2. Run `scripts/relock.sh` to regenerate the lock files. It needs uv, and applies the 14-day cooldown.
3. Explain in the commit message why the dependency is needed.
4. Check that its license is compatible.
5. Test well after the update.

## Performance checks

To time a block of code:

```python
import time

start = time.time()
# ... code to profile ...
elapsed = time.time() - start
logger.debug(f"Operation took {elapsed:.2f}s")
```

To check memory use, you can use `psutil`. It is not a project dependency, so install it only in your local environment:

```python
import os
import psutil

process = psutil.Process(os.getpid())
memory_mb = process.memory_info().rss / 1024 / 1024
logger.info(f"Memory usage: {memory_mb:.1f} MB")
```

## Documentation

### When to update docs

| Change | Update |
|--------|--------|
| User-visible change | `CHANGELOG.md` (under `## [Unreleased]`) and the user docs |
| Planned or completed feature | `ROADMAP.md` |
| Code structure change | `docs/ARCHITECTURE.md` |
| Feature idea | `docs/FUTURE_FEATURES.md` |
| Install or packaging change | `README.md` and `docs/INSTALLATION_GUIDE.md` |

### Doc files

- `README.md`: overview for users.
- `CONTRIBUTING.md`: contribution rules.
- `SECURITY.md`: security policy and release verification.
- `docs/GETTING_STARTED.md`: how to use the app.
- `docs/INSTALLATION_GUIDE.md`: install, run from source, uninstall.
- `docs/ARCHITECTURE.md`: code structure.
- `docs/DEVELOPMENT.md`: this guide.
- `docs/CODE_SIGNING.md` and `docs/UPDATE_SERVICE_NOTES.md`: maintainer notes.
- `ROADMAP.md`: feature planning.
- `docs/FUTURE_FEATURES.md`: feature ideas.

## Get help

Resources:

- The `docs/` folder.
- Code comments and docstrings.
- The log files.
- The Qt / PySide6 documentation.
- The yt-dlp documentation.

When you ask for help, include:

1. What you are trying to do.
2. What happens instead.
3. The error messages (from the log file).
4. The steps to reproduce.
5. Your Python version and operating system.

## Best practices

- **Before coding:** understand the problem, read the existing code, plan the solution, keep it simple.
- **While coding:** write clean code, comment complex logic, use logging, test as you go.
- **After coding:** test well, update the documentation, remove debug code, review your changes.

## Releases

The release workflow (`.github/workflows/release.yml`) runs on every push to `main`, and you can also start it by hand. It publishes a release only when `__version__` in `src/__init__.py` has no tag yet, and `CHANGELOG.md` must have a matching `## [<version>]` entry. Do not push version tags by hand. See [CONTRIBUTING.md](../CONTRIBUTING.md#versioning).

Before a release:

- [ ] All features work.
- [ ] There are no critical bugs.
- [ ] The tests pass.
- [ ] The documentation is updated.
- [ ] `__version__` is bumped and `python scripts/sync_version.py` has run.
- [ ] The CI build artifacts are tested, on a clean system if possible.
