# Installation Guide for YT-DLP Studio

## Issue: Python 3.14 Compatibility

Your system has **Python 3.14.0**, but PySide6 (the GUI framework) currently only supports **Python 3.9 to 3.13**.

---

## Solution Options

### Option 1: Install Python 3.13 (Recommended)

1. **Download Python 3.13:**
   - Visit: https://www.python.org/downloads/
   - Download Python 3.13.x (latest 3.13 version)

2. **Install Python 3.13:**
   - Run the installer
   - ✅ **IMPORTANT:** Check "Add Python to PATH"
   - Choose "Install Now"

3. **Create Virtual Environment (Optional but Recommended):**
   ```bash
   # Navigate to project directory
   cd yt-dlp-studio

   # Create virtual environment with Python 3.13
   py -3.13 -m venv venv

   # Activate virtual environment
   venv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt

   # Run the app
   python launcher.py
   ```

---

### Option 2: Use Python 3.12 or 3.11 (Also Compatible)

If you have Python 3.12 or 3.11 installed:

```bash
# Check available Python versions
py --list

# Use specific version to create venv
py -3.12 -m venv venv

# OR
py -3.11 -m venv venv

# Activate and install
venv\Scripts\activate
pip install -r requirements.txt
python launcher.py
```

---

### Option 3: Wait for PySide6 Update

PySide6 will eventually support Python 3.14, but this could take weeks or months.

**Not recommended** - better to use Python 3.13 now.

---

## Step-by-Step Installation (Recommended Path)

### 1. Install Python 3.13

Download from: https://www.python.org/downloads/release/python-3130/

**Windows Installer:**
- Select "Windows installer (64-bit)"
- Run the `.exe` file
- ✅ Check "Add python.exe to PATH"
- Click "Install Now"

### 2. Verify Installation

```bash
# Check Python 3.13 is installed
py -3.13 --version

# Should output: Python 3.13.x
```

### 3. Create Virtual Environment

```bash
# Navigate to project
cd yt-dlp-studio

# Create venv with Python 3.13
py -3.13 -m venv venv

# You should see a new "venv" folder created
```

### 4. Activate Virtual Environment

**Windows Command Prompt:**
```bash
venv\Scripts\activate.bat
```

**Windows PowerShell:**
```bash
venv\Scripts\Activate.ps1
```

**Git Bash:**
```bash
source venv/Scripts/activate
```

**After activation, your prompt should show:** `(venv)`

### 5. Install Dependencies

```bash
# With venv activated
pip install -r requirements.txt
```

This will install:
- PySide6 (Qt6 GUI framework)
- requests (for update checker)
- packaging (for version comparison)

### 6. Run the Application

```bash
python launcher.py
```

**The app should now start!**

### 7. Switch to Hebrew

1. Click **"Settings"** tab
2. Find **"Language"** dropdown
3. Select **"עברית (Hebrew)"**
4. Click **"Save Settings"**
5. **Restart the app**

---

## Troubleshooting

### Error: "py: command not found"

**Solution:** Use `python` instead of `py`:

```bash
python -m venv venv
```

### Error: "cannot be loaded because running scripts is disabled"

**Solution (PowerShell):** Allow script execution:

```bash
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then retry activating the venv.

### Error: "No module named 'PySide6'" after installation

**Solution:** Make sure venv is activated:

```bash
# You should see (venv) in your prompt
# If not, activate it again:
venv\Scripts\activate
```

### Error: PySide6 installation fails

**Possible issues:**
1. Python version incompatible (need 3.9-3.13)
2. Internet connection issue
3. Insufficient disk space

**Solution:** Check Python version:
```bash
python --version
```

Should be 3.9.x through 3.13.x (NOT 3.14)

---

## Alternative: Use Conda/Miniconda

If you use Conda:

```bash
# Create conda environment with Python 3.13
conda create -n ytdlp python=3.13

# Activate environment
conda activate ytdlp

# Navigate to project
cd yt-dlp-studio

# Install dependencies
pip install -r requirements.txt

# Run app
python launcher.py
```

---

## Quick Reference Commands

### Create & Activate Virtual Environment
```bash
# Create
py -3.13 -m venv venv

# Activate (Windows CMD)
venv\Scripts\activate.bat

# Activate (PowerShell)
venv\Scripts\Activate.ps1

# Activate (Git Bash)
source venv/Scripts/activate
```

### Install & Run
```bash
# Install dependencies
pip install -r requirements.txt

# Run application
python launcher.py
```

### Deactivate Virtual Environment
```bash
deactivate
```

---

## What Gets Installed

### PySide6 (GUI Framework)
- Qt6 bindings for Python
- Size: ~200MB
- Provides: Windows, buttons, layouts, etc.

### requests (HTTP Library)
- Used for checking app updates
- Size: ~100KB
- Provides: HTTP requests functionality

### packaging (Version Comparison)
- Used for comparing version numbers
- Size: ~50KB
- Provides: Version parsing utilities

**Total Size:** ~200MB

---

## After Installation

Once installed, you can:

1. **Run the app in English:**
   ```bash
   python launcher.py
   ```

2. **Test Hebrew translation:**
   - Open Settings tab
   - Select Hebrew (עברית)
   - Save and restart

3. **Test all features:**
   - Download a video
   - Use the queue system
   - Check history
   - View video info
   - Try playlists

---

## System Requirements

- **OS:** Windows 10/11, Linux, or macOS
- **Python:** 3.9, 3.10, 3.11, 3.12, or 3.13 (NOT 3.14 yet)
- **RAM:** 512MB minimum (2GB recommended)
- **Disk Space:** 500MB (for dependencies + videos)
- **Internet:** Required for downloading videos

---

## Next Steps

After installation:

1. ✅ **Install Python 3.13**
2. ✅ **Create virtual environment**
3. ✅ **Install dependencies**
4. ✅ **Run the app**
5. ✅ **Test Hebrew translation**

Then review:
- `QUICK_START_HEBREW.md` - Quick start guide
- `docs/HEBREW_TRANSLATION.md` - Full translation documentation
- `docs/HEBREW_TESTING_GUIDE.md` - Testing procedures

---

## Support

If you encounter issues:

1. Check Python version: `python --version` (should be 3.9-3.13)
2. Verify venv is activated: you should see `(venv)` in prompt
3. Check dependencies installed: `pip list`
4. Try reinstalling: `pip install -r requirements.txt --force-reinstall`

---

## Summary

**Current Issue:** Python 3.14 is too new for PySide6

**Solution:** Install Python 3.13 and create virtual environment

**Time to Setup:** 5-10 minutes

**Result:** Fully functional YT-DLP Studio with Hebrew support! 🇮🇱
