# Release Notes

Release notes and changelog for YT-DLP Studio.

---

## Version 1.4.0 (Released)

**Release Date:** 2025-10-28

### New Features

#### Unified Download Tracking
- **All downloads tracked in Queue tab**
  - "Download Now" button now adds tasks to queue automatically
  - Queue tab shows ALL downloads (instant and queued)
  - Complete download history in one place
  - Consistent tracking across all download methods

#### Button Icons
- Added visual icons to all buttons using emojis
  - 📋 Paste, ℹ️ Show Info, 📁 Browse
  - ⬇️ Download Now, ➕ Add to Queue
  - ▶️ Start, ⏸️ Pause, ⏹️ Stop
  - ⬆️ Move Up, ⬇️ Move Down, ❌ Remove
  - ✓ Clear Completed, ✗ Clear Failed, 🗑️ Clear Log

#### Drag & Drop Support
- **Drag URLs directly into URL field**
  - Drag video URL from browser
  - Drop into URL input field
  - Auto-fills and validates
  - Updated placeholder text

#### NXtools Branding
- **Part of NXtools collection**
  - Added NXtools branding in About dialog
  - Links to https://nx1xlab.dev/nxtools
  - Buy Me a Coffee support link
  - Added to README with badge

### UI Improvements
- **Visual Polish**
  - Better spacing between sections (12px)
  - Added margins to layouts (8px)
  - Enhanced button padding and styling
  - Improved hover effects with borders
  - Pressed button animations
  - Larger font for Download Now button

### Technical Changes
- Updated About dialog with rich text and clickable links
- Prepared placeholder for custom app icon (future)
- Enhanced QLineEdit with drag-and-drop events
- Improved layout spacing and margins throughout

### Upgrade Notes
- No breaking changes from v1.3.0
- All "Download Now" tasks now appear in Queue tab
- Config file format unchanged

---

## Version 1.3.0 (Released)

**Release Date:** 2025-10-27

### New Features

#### Playlist Support
- **Automatic playlist detection**
  - Detects YouTube playlists (`/playlist?list=`)
  - Detects YouTube channels (`/@channel/videos`)
  - Detects Vimeo playlists and showcases
  - Detects Dailymotion playlists
  - Pattern-based detection for multiple platforms

- **Playlist viewer dialog**
  - Beautiful table showing all playlist videos
  - Video information: #, Title, Duration, Uploader
  - Checkboxes for selective downloading (all selected by default)
  - "Select All" / "Select None" buttons
  - Quality selection dropdown
  - Shows total selected videos count

- **Smart playlist handling**
  - "Show Info" button detects and displays playlists
  - "Add to Queue" button offers playlist viewing
  - Option to add entire playlist URL or select specific videos
  - Batch-add selected videos to download queue
  - All videos use the same quality setting

- **Background playlist fetching**
  - Non-blocking UI during playlist extraction
  - Progress feedback ("Fetching Playlist...")
  - Comprehensive error handling
  - Platform-specific detection messages

### Technical Changes
- New `PlaylistDetector` utility for URL pattern matching
- New `PlaylistInfo` and `PlaylistVideoInfo` data models
- New `PlaylistFetcher` backend for yt-dlp integration
- New `PlaylistWorker` QThread for async operations
- New `PlaylistDialog` UI widget with dark theme
- Enhanced `DownloadTab` with playlist support
- Integrated playlist/video routing logic

### Improvements
- Better URL handling for playlists vs single videos
- User can preview all playlist contents before downloading
- Selective video downloading from playlists
- Consistent error handling across playlist operations
- Clear user feedback for playlist detection

### Known Issues
- Channel playlists may take longer to fetch (many videos)
- Some platforms may have limited playlist support

### Upgrade Notes
- No breaking changes from v1.2.0
- Playlist features work automatically when detected
- Config file format unchanged
- All existing features remain functional

---

## Version 1.2.0 (Released)

**Release Date:** 2025-10-27

### New Features

#### Keyboard Shortcuts
- **Complete shortcut system** for faster workflow
  - `Ctrl+V` - Paste URL from clipboard
  - `Enter` - Start download (when URL field focused)
  - `Ctrl+D` - Download Now
  - `Ctrl+Shift+Q` - Add to Queue
  - `Ctrl+Shift+I` - Show Video Info
  - `Ctrl+Q` - Quit application
  - `F1` - Show keyboard shortcuts help
  - `Delete` - Remove selected queue task
  - `Ctrl+Up/Down` - Move tasks in queue
  - `Space` - Toggle queue start/pause

- **Keyboard Shortcuts Help Dialog** (F1)
  - Lists all available shortcuts
  - Organized by tab/context
  - Beautiful HTML-formatted display

#### Smart Clipboard Detection
- **Auto-detect URLs on startup**
  - Checks clipboard when app launches
  - Auto-fills URL field if valid video URL found
  - Smart logic: only fills if field is empty

- **"Paste" button**
  - Quick clipboard paste next to URL input
  - Provides visual feedback
  - Works alongside Ctrl+V shortcut

#### Enhanced Progress Display
- **File size display**
  - Shows total file size (MB/GB)
  - Real-time downloaded amount tracking

- **Better layout**
  - Row 1: File size + Downloaded amount
  - Row 2: Speed + ETA
  - All values formatted with proper units

- **Improved user feedback**
  - See exactly how much has downloaded
  - Better sense of progress

#### Better Error Messages
- **Error categorization system**
  - 9 distinct error categories
  - Network errors (connection, timeout, DNS)
  - Invalid URLs (unsupported, malformed)
  - Video unavailable (deleted, 404)
  - Geo-blocked content
  - Copyright/DMCA issues
  - Private videos (login required)
  - Format errors (codec issues)
  - Disk space problems
  - Permission errors

- **Helpful suggestions**
  - Context-specific advice for each error type
  - Step-by-step troubleshooting tips
  - Links to common solutions

- **Beautiful error dialogs**
  - HTML-formatted with colors
  - Clear category titles
  - Expandable technical details
  - User-friendly language

### Improvements
- Better user experience with keyboard navigation
- Faster workflow with shortcuts
- More informative progress tracking
- Clearer error communication
- Non-blocking clipboard operations

### Technical Changes
- New `ErrorHandler` utility for error categorization
- Enhanced `ProgressBar` widget with file size tracking
- Updated `DownloadTab` with keyboard shortcuts
- Updated `QueueTab` with keyboard shortcuts
- Updated `MainWindow` with F1 help dialog
- Auto-clipboard detection in `_load_config()`
- Progress data now includes total_bytes and downloaded_bytes

### Known Issues
- None reported

### Upgrade Notes
- No breaking changes from v1.1.5
- All new features work automatically
- Config file format unchanged
- Keyboard shortcuts work immediately

---

## Version 1.1.5 (Released)

**Release Date:** 2025-10-27

### New Features

#### Video Info Preview
- **Show Info Button**: New button next to URL input in Download tab
  - Fetches video metadata before downloading
  - Non-blocking UI with background worker thread
  - Shows status feedback while fetching

- **Video Info Dialog**: Beautiful modal dialog displaying:
  - Video thumbnail (automatically downloaded and displayed)
  - Full video title
  - Duration (formatted as HH:MM:SS or MM:SS)
  - Uploader/channel name
  - View count (formatted with commas)
  - Like count
  - Upload date (formatted as DD/MM/YYYY)
  - Platform/extractor (YouTube, Vimeo, etc.)
  - Description preview (scrollable, up to 500 characters)

### Technical Changes
- New `VideoInfoWorker` backend for async info fetching
- New `VideoInfoDialog` UI widget with dark theme
- Enhanced `DownloadTab` with Show Info integration
- Thumbnail download using urllib with 10-second timeout
- Proper error handling for failed fetches

### Improvements
- Better user feedback during info fetching
- Non-blocking UI during metadata extraction
- Beautiful dark-themed dialog matching app style
- Scalable thumbnail display with aspect ratio preservation

### Known Issues
- None reported

### Upgrade Notes
- No breaking changes from v1.1.0
- New "Show Info" button appears automatically
- Config file format unchanged

---

## Version 1.1.0 (Released)

**Release Date:** 2025-10-27

### New Features

#### Download Queue System
- **Queue Tab**: New dedicated tab for managing download queue
  - View all queued, active, completed, and failed downloads
  - Real-time statistics display (total, pending, active, completed, failed)
  - Color-coded status indicators
  - Progress and speed tracking for each task

#### Queue Management
- **Add to Queue**: New button in Download tab to add URLs to queue
- **Download Now**: Original instant download functionality preserved
- **Queue Controls**:
  - Start/Pause/Stop queue processing
  - Move tasks up/down in queue
  - Remove individual tasks
  - Clear completed tasks
  - Clear failed tasks

#### Concurrent Downloads
- Download up to 3 videos simultaneously (configurable)
- Automatic queue processing with capacity management
- Efficient worker thread coordination
- Auto-start next task when capacity becomes available

### Improvements
- Enhanced Download tab with dual download modes
- Better task status tracking (pending, downloading, completed, error, cancelled)
- Improved threading architecture with QueueManager
- More responsive UI with real-time updates

### Testing
- Comprehensive unit tests for DownloadQueue model
- Full test coverage for QueueManager backend
- UI tests for QueueTab widget (pytest-qt)
- 3 new test files with 80+ test cases

### Technical Changes
- New `DownloadQueue` model for queue management
- New `QueueManager` backend for worker coordination
- New `QueueTab` UI widget
- Modified `MainWindow` to support queue
- Modified `DownloadTab` to support dual modes
- Updated exports in `__init__.py` files

### Known Issues
- None reported

### Upgrade Notes
- No breaking changes from v1.0.0
- Queue functionality is optional (can still use "Download Now")
- Config file format unchanged

---

## Version 1.0.0

**Release Date:** 2024-10-26

### Initial Release

#### Core Features
- Basic video download functionality
- URL input with validation
- Quality selection (Best, 1080p, 720p, 480p, Audio Only)
- Output directory selection
- Real-time progress tracking
- Download speed and ETA display
- Log output window with colored messages
- Settings persistence (JSON config)
- Settings tab for configuration

#### Technical Features
- Bundled yt-dlp engine
- PySide6 (Qt) GUI
- QThread-based non-blocking downloads
- Modern dark theme UI
- Comprehensive error handling
- Cross-platform architecture (Windows 10/11)

#### Files Included
- Windows executable (~16 MB)
- Complete source code
- Documentation (README, ARCHITECTURE, ROADMAP, etc.)
- Custom non-commercial license

#### Platform Support
- ✅ Windows 10
- ✅ Windows 11

#### Dependencies
- PySide6 6.8.1
- yt-dlp (bundled in yt_dlp_engine/)

#### Known Issues
- None reported

---

## Release Schedule

### Version Numbering
- **Major (X.0.0):** Breaking changes, major new features
- **Minor (1.X.0):** New features, no breaking changes
- **Patch (1.0.X):** Bug fixes, small improvements

### Release Cycle
1. Feature complete in main branch
2. Testing phase
3. Bug fixes and polish
4. Build and package
5. Release and documentation

---

## Upgrade Guide

### From v1.0.0 to v1.1.0

No special steps required. Simply:
1. Replace the old executable with the new one
2. Your config file (`config.json`) will be preserved
3. All settings will remain intact

The new Queue tab will appear automatically, but you can continue using the Download tab exactly as before.

---

## Deprecation Notices

None at this time.

---

## Security Notes

### v1.1.0
- No security vulnerabilities known
- All downloads use official yt-dlp library
- No external network calls except for video downloads

### v1.0.0
- No security vulnerabilities known
- Custom non-commercial license

---

## Performance Notes

### v1.1.0
- Concurrent downloads increase overall throughput
- Memory usage scales with number of active downloads (~200MB per active download)
- CPU usage remains low during downloads
- UI remains responsive even with 3 concurrent downloads

### v1.0.0
- Single download support
- ~16 MB executable size
- <200 MB RAM usage during download
- Instant UI response

---

## Acknowledgments

### Built With
- **yt-dlp**: The amazing command-line downloader
- **PySide6**: Professional Qt GUI framework
- **Python**: The language that makes it all possible

### Special Thanks
- yt-dlp developers for their incredible work
- Qt/PySide6 team for the excellent GUI framework
- All users who provided feedback

---

**Last Updated:** 2025-10-26
