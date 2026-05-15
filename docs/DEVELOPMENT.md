# Development Guide for YT-DLP Studio

Guide for developers working on YT-DLP Studio.

---

## Getting Started

### Prerequisites

- **Python 3.10 or higher**
  ```bash
  python --version
  ```

- **pip (Python package manager)**
  ```bash
  pip --version
  ```

- **Git** (for version control)
  ```bash
  git --version
  ```

---

### Initial Setup

1. **Clone the repository**
   ```bash
   cd "path/to/yt-dlp-for-users"
   ```

2. **Create virtual environment** (recommended)
   ```bash
   python -m venv .venv
   ```

3. **Activate virtual environment**
   - Windows:
     ```bash
     .venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source .venv/bin/activate
     ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Verify yt-dlp engine is present**
   ```bash
   dir yt_dlp_engine\yt_dlp  # Windows
   ls yt_dlp_engine/yt_dlp    # Linux
   ```

---

### Running the Application

**From command line:**
```bash
python launcher.py
```

**From IDE (VS Code, PyCharm, etc.):**
- Set `launcher.py` as the main entry point
- Run/Debug as normal

---

## Project Structure

```
yt-dlp-for-users/
├── launcher.py              # Entry point
├── src/                     # Application source
│   ├── app.py              # App initialization
│   ├── ui/                 # UI components
│   ├── backend/            # Business logic
│   ├── models/             # Data models
│   ├── utils/              # Utilities
│   └── resources/          # Assets
├── yt_dlp_engine/          # Bundled yt-dlp
├── docs/                   # Documentation
├── tests/                  # Test files
├── requirements.txt        # Dependencies
└── build.spec             # PyInstaller config
```

See `docs/ARCHITECTURE.md` for detailed structure explanation.

---

## Development Workflow

### 1. Before Making Changes

- Read `docs/ARCHITECTURE.md`
- Understand the component you're modifying
- Check existing issues/features

### 2. Making Changes

- Create a new branch (if using git)
- Make small, focused changes
- Add logging for debugging
- Update docstrings and comments

### 3. Testing Changes

- Test manually in the GUI
- Check log file for errors
- Test edge cases
- Verify on Windows 10 and 11 (if possible)

### 4. Before Committing

- Remove debug print statements
- Check code formatting
- Update documentation if needed
- Test one more time

---

## Coding Guidelines

### Python Style

- Follow PEP 8 (mostly)
- Use type hints
- Write docstrings for functions/classes
- Keep functions small and focused

**Example:**
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

### File Organization

- One class per file (usually)
- Group related functions together
- Keep files under 250 lines
- Use `__init__.py` for imports

### Import Style

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

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `DownloadTask`)
- **Functions:** `snake_case` (e.g., `download_video`)
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `APP_VERSION`)
- **Private:** Prefix with `_` (e.g., `_internal_method`)

---

## Logging

### Using the Logger

```python
from src.utils.logger import get_logger

logger = get_logger()

logger.debug("Detailed debug info")      # Only in log file
logger.info("General information")       # Console + file
logger.warning("Warning message")        # Console + file
logger.error("Error occurred")           # Console + file
logger.critical("Critical error")        # Console + file
```

### Log Levels

- `DEBUG`: Detailed diagnostic info
- `INFO`: General information
- `WARNING`: Warning messages
- `ERROR`: Errors that don't crash app
- `CRITICAL`: Critical errors

### Log File Location

- Windows: `%APPDATA%\YT-DLP Studio\yt-dlp-studio.log`
- Linux: `~/.config/YT-DLP Studio/yt-dlp-studio.log`

---

## Common Development Tasks

### Adding a New Setting

1. **Edit:** `src/models/app_config.py`
   ```python
   @dataclass
   class AppConfig:
       ...
       new_setting: str = "default"
   ```

2. **Edit:** `src/backend/config_manager.py`
   - Update `_create_default_config()`

3. **Edit:** `src/ui/settings_tab.py`
   - Add UI widget
   - Update `_load_settings()` and `_save_settings()`

4. **Test:**
   - Run app, change setting, restart
   - Verify setting persists

---

### Adding a New Quality Option

1. **Edit:** `src/utils/constants.py`
   ```python
   QUALITY_OPTIONS = {
       ...
       "4K": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
   }
   ```

2. **Test:**
   - Run app
   - Check dropdown has new option
   - Download with new quality

---

### Modifying the UI

1. **Find the relevant file:**
   - Main window: `src/ui/main_window.py`
   - Download tab: `src/ui/download_tab.py`
   - Settings tab: `src/ui/settings_tab.py`

2. **Edit `_setup_ui()` method**

3. **Test immediately:**
   - Run app
   - Check visual changes
   - Test functionality

---

### Adding Logging to Existing Code

```python
# At top of file
from ..utils.logger import get_logger

logger = get_logger()

# In functions
def some_function():
    logger.debug("Function started")
    try:
        # ... code ...
        logger.info("Operation successful")
    except Exception as e:
        logger.error(f"Error occurred: {e}")
```

---

## Testing

### Manual Testing Checklist

- [ ] Application starts without errors
- [ ] URL validation works
- [ ] Directory selection works
- [ ] Download completes successfully
- [ ] Progress bar updates correctly
- [ ] Log messages appear
- [ ] Settings save and load
- [ ] Error handling works
- [ ] Window size persists

### Test with Different URLs

- YouTube video
- YouTube playlist
- Vimeo video
- Twitter video
- Invalid URL
- Non-existent video

---

## Debugging

### Common Issues

**App won't start:**
1. Check log file
2. Verify Python version
3. Check dependencies installed
4. Verify yt_dlp_engine exists

**Import errors:**
1. Check virtual environment activated
2. Verify file paths are correct
3. Check for circular imports

**Download fails:**
1. Check log file for yt-dlp errors
2. Test URL with command line yt-dlp
3. Check network connection
4. Verify output directory writable

### Debug Mode

**Add to launcher.py temporarily:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Or set in constants.py:**
```python
LOG_LEVEL = "DEBUG"
```

---

## Building Executable

### Using PyInstaller

1. **Install PyInstaller:**
   ```bash
   pip install pyinstaller
   ```

2. **Build:**
   ```bash
   pyinstaller build.spec
   ```

3. **Find executable:**
   - Location: `dist/yt-dlp-studio.exe`
   - Size: ~100-120MB

4. **Test executable:**
   - Run on clean system if possible
   - Test all features
   - Check for missing dependencies

---

## Updating yt-dlp

When a new yt-dlp version is released:

1. **Download latest yt-dlp:**
   ```bash
   pip download yt-dlp
   tar -xzf yt-dlp-YYYY.MM.DD.tar.gz
   ```

2. **Replace yt_dlp_engine:**
   ```bash
   # Backup old version
   mv yt_dlp_engine yt_dlp_engine_backup

   # Copy new version
   cp -r yt-dlp-YYYY.MM.DD/yt_dlp yt_dlp_engine/
   ```

3. **Update version in constants.py:**
   ```python
   YTDLP_VERSION = "YYYY.MM.DD"
   ```

4. **Test thoroughly:**
   - Download from various sites
   - Check all quality options
   - Verify progress tracking works

---

## Git Workflow (When Using Git)

### Branching Strategy

- `main`: Stable releases
- `develop`: Development branch
- `feature/feature-name`: New features
- `fix/bug-name`: Bug fixes

### Commit Messages

**Format:**
```
type: Brief description

Longer description if needed.
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Adding tests

**Examples:**
```
feat: Add download queue support

Implements basic download queue with add/remove functionality.
```

```
fix: Correct progress percentage calculation

Progress was showing >100% due to integer division.
```

---

## Dependencies Management

### Adding a New Dependency

1. **Install:**
   ```bash
   pip install package-name
   ```

2. **Update requirements.txt:**
   ```bash
   pip freeze > requirements.txt
   ```

3. **Document why needed** in commit message

4. **Check license compatibility**

### Updating Dependencies

```bash
pip install --upgrade PySide6
pip freeze > requirements.txt
```

**Test thoroughly after updates!**

---

## Performance Optimization

### Profiling

**Find slow code:**
```python
import time

start = time.time()
# ... code to profile ...
elapsed = time.time() - start
logger.debug(f"Operation took {elapsed:.2f}s")
```

### Memory Usage

**Check memory:**
```python
import psutil
import os

process = psutil.Process(os.getpid())
memory_mb = process.memory_info().rss / 1024 / 1024
logger.info(f"Memory usage: {memory_mb:.1f} MB")
```

---

## Documentation

### When to Update Docs

- New feature added → Update ROADMAP.md
- Feature completed → Update ROADMAP.md
- Code structure changed → Update ARCHITECTURE.md
- Feature idea → Add to FUTURE_FEATURES.md
- Bug fix or change → Update relevant docs

### Doc Files

- `README.md`: User-facing overview
- `ARCHITECTURE.md`: Code structure (for devs/AI)
- `DEVELOPMENT.md`: This file (dev guide)
- `ROADMAP.md`: Feature planning
- `FUTURE_FEATURES.md`: Feature ideas
- `LICENSE_DECISION.md`: Licensing info

---

## Getting Help

### Resources

- Check `docs/` folder
- Read code comments and docstrings
- Check log files
- Read Qt/PySide6 documentation
- Read yt-dlp documentation

### Asking for Help

When asking for help, include:
1. What you're trying to do
2. What's happening instead
3. Error messages (from log file)
4. Steps to reproduce
5. Python/OS version

---

## Best Practices

### Before Coding

- ✅ Understand the problem
- ✅ Read existing code
- ✅ Plan the solution
- ✅ Keep it simple

### While Coding

- ✅ Write clean code
- ✅ Add comments for complex logic
- ✅ Use logging liberally
- ✅ Test as you go

### After Coding

- ✅ Test thoroughly
- ✅ Update documentation
- ✅ Clean up debug code
- ✅ Review changes

---

## Release Checklist

When preparing a release:

- [ ] All features working
- [ ] No critical bugs
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Version number bumped
- [ ] Build executable
- [ ] Test executable on clean system
- [ ] Create release notes
- [ ] Tag release in git
- [ ] Create installer (optional)

---

**Last Updated:** 2024-10-26
**For Version:** 1.0.0
