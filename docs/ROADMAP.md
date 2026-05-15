# YT-DLP Studio Roadmap

Development roadmap and future plans for YT-DLP Studio.

---

## Version 1.0.0 (Released)

**Status:** ✅ Complete and tested

**Release Date:** 2024-10-26

### Features ✅

- [x] Basic download functionality
- [x] URL input validation
- [x] Quality selection (Best, 1080p, 720p, 480p, Audio Only)
- [x] Output directory selection
- [x] Real-time progress tracking
- [x] Download speed and ETA display
- [x] Log output window
- [x] Settings persistence (JSON config)
- [x] Settings tab for configuration
- [x] Bundled yt-dlp engine
- [x] Windows 10/11 support
- [x] Modern dark theme UI
- [x] Error handling and user feedback
- [x] Executable built and tested
- [x] Custom non-commercial license

---

## Version 1.1.0 (✅ RELEASED)

**Focus:** Enhanced download management

**Status:** ✅ Complete and Released

**Release Date:** 2025-10-27

### Completed Features ✅

- [x] **Download Queue System**
  - Add multiple URLs to queue before starting
  - View list of pending/active/completed downloads in Queue tab
  - Real-time queue statistics display
  - Task status tracking (pending, downloading, completed, error, cancelled)

- [x] **Queue Management Controls**
  - Reorder queue (move up/down)
  - Remove items from queue
  - Start/Pause/Stop queue controls
  - Clear completed/failed tasks

- [x] **Concurrent Downloads**
  - Download multiple videos simultaneously
  - Configurable max concurrent downloads (default: 3)
  - Automatic queue processing with capacity management
  - Worker thread coordination

- [x] **Dual Download Modes**
  - "Download Now" button for instant downloads
  - "Add to Queue" button for batch queueing
  - Both modes coexist in Download tab

- [x] **Comprehensive Testing**
  - Unit tests for DownloadQueue model (test_download_queue.py)
  - Unit tests for QueueManager backend (test_queue_manager.py)
  - UI tests for QueueTab widget (test_queue_tab.py)
  - Application startup testing completed

**Priority:** HIGH

---

## Version 1.1.5 (✅ RELEASED)

**Focus:** UX improvements - Video Info Preview

**Status:** ✅ Released (Partial)

**Release Date:** 2025-10-27

### Completed Features ✅

- [x] **Video Info Preview**
  - "Show Info" button next to URL input
  - Display video title before download
  - Show thumbnail preview (with image download)
  - Display duration and uploader/channel name
  - Show view count and upload date
  - Description preview in scrollable area
  - Beautiful modal dialog with dark theme
  - Background fetching using QThread (non-blocking UI)
  - Platform information display
  - Formatted date display

---

## Version 1.2.0 (✅ RELEASED)

**Focus:** UX Improvements - Keyboard Shortcuts & Better Feedback

**Status:** ✅ Released

**Release Date:** 2025-10-27

### Completed Features ✅

- [x] **Keyboard Shortcuts**
  - Ctrl+V to paste URL from clipboard
  - Enter to download (when URL field focused)
  - Ctrl+D for Download Now
  - Ctrl+Shift+Q for Add to Queue
  - Ctrl+Shift+I for Show Video Info
  - Ctrl+Q to quit application
  - F1 for keyboard shortcuts help dialog
  - Delete to remove queue task
  - Ctrl+Up/Down to move tasks in queue
  - Space to toggle queue start/pause

- [x] **URL from Clipboard**
  - Auto-detect URL in clipboard on app startup
  - "Paste" button next to URL input
  - Auto-fill URL field if valid URL detected
  - Smart logic: only fills if field is empty or has old URL

- [x] **Enhanced Progress Display**
  - Shows total file size (MB/GB)
  - Shows downloaded amount in real-time
  - Better 2-row layout
    - Row 1: File size + Downloaded amount
    - Row 2: Speed + ETA
  - Improved formatting using FileHelper

- [x] **Better Error Messages**
  - Error categorization system (9 categories)
    - Network errors
    - Invalid URLs
    - Video unavailable
    - Geo-blocked content
    - Copyright issues
    - Private videos
    - Format errors
    - Disk space issues
    - Permission errors
  - Helpful, actionable suggestions for each error type
  - Beautiful HTML-formatted error dialogs
  - Technical details included for debugging

**Priority:** HIGH

---

## Version 1.3.0 (✅ RELEASED)

**Focus:** Playlist and batch download support

**Status:** ✅ Complete and Released

**Release Date:** 2025-10-27

### Completed Features ✅

- [x] **Playlist Detection**
  - Detect playlist URLs automatically (YouTube, Vimeo, Dailymotion)
  - Show platform-specific detection messages
  - Extract playlist metadata using yt-dlp
  - Pattern-based detection for multiple platforms

- [x] **Playlist Viewer**
  - Show list of videos in playlist (beautiful table)
  - Display #, title, duration, uploader for each
  - Checkboxes to select specific videos (all selected by default)
  - Select all/none buttons
  - Quality selection dropdown
  - Total selected videos count

- [x] **Batch Download from Playlists**
  - Add selected videos to queue
  - Bulk quality setting for playlist
  - Progress tracking in Queue tab
  - Smart playlist/video routing logic

- [x] **Channel Downloads**
  - Download all videos from a YouTube channel
  - Detects `/@channel/videos` URLs
  - Works with playlist viewer

**Priority:** HIGH (Completed)

**Actual Time:** ~4 hours

---

## Version 2.0.0 (🔄 IN PROGRESS - Hebrew Translation)

**Focus:** Complete Hebrew translation and RTL support

**Status:** 🔄 In Progress

**Est. Release:** TBD

### In Progress Features

- [x] **Translation Framework**
  - translations.py framework exists
  - Language detection system
  - JSON-based translation files

- [ ] **Hebrew Translation (IN PROGRESS)**
  - Complete UI translation to Hebrew
  - RTL (Right-to-Left) layout support
  - Hebrew language file (he.json)
  - Testing of all translated strings
  - Cultural localization (date/time formats)
  - Language switcher in Settings

**Priority:** HIGH

**Estimated Time:** 6-8 hours

---

## Version 1.5.0 (Planned - Quick Wins)

**Focus:** High-impact features with existing code integration

**Status:** 🔄 Planned

**Est. Release:** TBD

### Features Ready to Activate (Code exists, needs integration)

- [ ] **Thumbnail Download**
  - Checkbox exists, backend ready
  - Minimal UI hookup needed
  - **Priority:** HIGH | **Time:** 30 min

- [ ] **Subtitle Download**
  - UI + yt-dlp integration ready
  - Language selection dropdown
  - Auto-embed option
  - **Priority:** HIGH | **Time:** 1 hour

- [ ] **Speed Limiter**
  - SpinBox UI ready
  - Rate limiting for bandwidth control
  - **Priority:** MEDIUM | **Time:** 30 min

- [ ] **Batch URL Input**
  - Dialog created (batch_input_dialog.py)
  - Paste multiple URLs at once
  - **Priority:** HIGH | **Time:** 1 hour

- [ ] **Desktop Notifications**
  - notification_manager.py exists
  - Download complete/failed alerts
  - Settings toggle needed
  - **Priority:** MEDIUM | **Time:** 1 hour

- [ ] **Bandwidth Monitor**
  - bandwidth_monitor.py and bandwidth_widget.py exist
  - Real-time bandwidth usage display
  - Add tab/widget to UI
  - **Priority:** MEDIUM | **Time:** 1-2 hours

- [ ] **Auto-Update System**
  - update_checker.py and update_dialog.py exist
  - Check for app updates on startup
  - One-click update process
  - **Priority:** HIGH | **Time:** 2 hours

- [ ] **Video Player**
  - video_player_widget.py exists
  - Preview downloaded videos in-app
  - Add to history tab
  - **Priority:** LOW | **Time:** 2 hours

- [ ] **Download Filters**
  - filter_dialog.py exists
  - Filter by duration, view count, date
  - **Priority:** MEDIUM | **Time:** 1-2 hours

**Priority:** HIGH (Quick wins)

**Estimated Time:** 10-12 hours total

---

## Version 1.6.0 (Planned - Smart Management)

**Focus:** Format profiles and intelligent downloading

**Status:** 🔄 Planned

**Est. Release:** TBD

### Planned Features

- [ ] **Format Templates & Profiles**
  - Preset download profiles:
    - "Music Videos" → 720p video + 320kbps audio + subtitles + thumbnail
    - "Podcasts" → Audio only + thumbnail
    - "Archive Quality" → Best video/audio + metadata + all subtitles
  - Custom user-defined profiles
  - Quick profile switcher in UI
  - **Priority:** HIGH | **Time:** 2-3 hours

- [ ] **Smart Filename Templates**
  - Customizable output patterns:
    - `{uploader} - {title} [{resolution}].{ext}`
    - `{upload_date} - {title}.{ext}`
    - `{playlist} - {playlist_index} - {title}.{ext}`
  - Safe character handling
  - Length limits
  - Preview before download
  - **Priority:** HIGH | **Time:** 3-4 hours

- [ ] **Smart Playlist Management**
  - Custom range selection (videos 5-20, every 3rd video)
  - Reverse order downloading
  - Resume interrupted playlists
  - Playlist "diff" detection (download only new videos)
  - **Priority:** HIGH | **Time:** 2-4 hours

- [ ] **Download Archive Management**
  - Use yt-dlp's --download-archive feature
  - Prevent re-downloading same video
  - Track downloaded video IDs
  - Export/import archive files
  - **Priority:** HIGH | **Time:** 4-5 hours

**Priority:** HIGH

**Estimated Time:** 12-16 hours

---

## Version 1.7.0 (Planned - Workflow Enhancements)

**Focus:** User experience and workflow improvements

**Status:** 🔄 Planned

**Est. Release:** TBD

### Planned Features

- [ ] **Drag & Drop URLs**
  - Drag video URL from browser
  - Drop into app window
  - Auto-fill URL field
  - **Priority:** MEDIUM | **Time:** 1-2 hours

- [ ] **Clipboard Auto-Detect**
  - Auto-populate URL if valid URL in clipboard
  - On app focus detection
  - Smart logic (only if field empty)
  - **Priority:** MEDIUM | **Time:** 1 hour

- [ ] **Retry Failed Downloads**
  - One-click retry button
  - Exponential backoff
  - Auto-retry option (configurable)
  - **Priority:** HIGH | **Time:** 2 hours

- [ ] **Post-Download Actions**
  - Open file after download
  - Open folder location
  - Play in default player
  - Convert format (using ffmpeg)
  - Move to category folder
  - **Priority:** MEDIUM | **Time:** 3-4 hours

- [ ] **Download Statistics Dashboard**
  - Total downloads (today/week/month/all-time)
  - Total data downloaded
  - Average speed
  - Most downloaded channels
  - Favorite quality settings
  - Beautiful charts
  - **Priority:** LOW | **Time:** 4-5 hours

**Priority:** MEDIUM

**Estimated Time:** 11-14 hours

---

## Version 1.8.0 (Planned - Subscription System)

**Focus:** Channel/user subscription and automation

**Status:** 🔄 Planned

**Est. Release:** TBD

### Planned Features

- [ ] **Channel Subscription Manager**
  - Save favorite channels/users
  - One-click "download new videos"
  - Track already downloaded videos
  - Subscription library view
  - **Priority:** KILLER FEATURE | **Time:** 6-8 hours

- [ ] **Download Scheduler**
  - Schedule downloads for specific times
  - Night-time downloading (cheaper internet)
  - Bandwidth-friendly hours
  - One-time or recurring schedules
  - **Priority:** HIGH | **Time:** 4-5 hours

- [ ] **Auto-Download from Subscriptions**
  - Auto-download new uploads
  - Check interval (daily/weekly)
  - Filter by criteria (duration, keywords)
  - Notification of new downloads
  - **Priority:** HIGH | **Time:** 4-6 hours

**Priority:** VERY HIGH (Killer feature)

**Estimated Time:** 14-19 hours

---

## Version 1.9.0 (Planned - UI Polish)

**Focus:** Professional UI appearance and icons

**Status:** 🔄 Planned

**Est. Release:** TBD

### Planned Features

- [ ] **Custom Application Icon**
  - Design/generate custom app icon
  - Add to Windows executable
  - Professional branding
  - **Priority:** MEDIUM | **Time:** 2-3 hours

- [ ] **UI Icons**
  - Download button icons
  - Settings icons
  - Folder browser icons
  - Queue control icons (play/pause/stop)
  - **Priority:** MEDIUM | **Time:** 2-3 hours

- [ ] **Format Previewer**
  - "Show Formats" button
  - Display all available formats for URL
  - Show resolution, codec, file size estimate
  - Let user pick specific format
  - **Priority:** LOW | **Time:** 3-4 hours

**Priority:** MEDIUM

**Estimated Time:** 7-10 hours

---

## Version 1.5.0 (Planned - Advanced Features)

**Focus:** Advanced features and customization

**Status:** 🔄 Planned

**Est. Release:** TBD

### Planned Features

- [ ] **Pause/Resume Support**
  - Pause active downloads
  - Resume paused downloads
  - Better cancellation handling
  - Partial download recovery

- [ ] **Download History**
  - View previously downloaded videos
  - Re-download from history
  - Clear history option
  - Export history to file

- [ ] **Dark/Light Theme Toggle**
  - Dark theme (default)
  - Light theme option
  - System theme detection

- [ ] **Scheduled Downloads**
  - Schedule downloads for specific time
  - Recurring downloads (daily/weekly)
  - Auto-shutdown after completion

- [ ] **Enhanced Quality Options**
  - More video quality options (2K, 4K, 8K)
  - More audio bitrate options (128kbps, 192kbps, 256kbps, 320kbps)
  - Separate video/audio quality control
  - Custom quality presets

- [ ] **Custom Format Selection**
  - Advanced format selector
  - Separate video/audio format choice
  - Custom yt-dlp arguments

- [ ] **Subtitle Support**
  - Download subtitles
  - Auto-embed subtitles
  - Language selection

**Priority:** LOW-MEDIUM

---

## Version 2.0.0 (Future)

**Focus:** Platform expansion and automation

**Est. Release:** TBD

### Planned Features

- [ ] **Linux Support**
  - Ubuntu/Debian packages
  - AppImage distribution
  - Full platform testing

- [ ] **Auto-Update System**
  - Check for app updates
  - Check for yt-dlp updates
  - One-click update process

- [ ] **Browser Integration**
  - Browser extension
  - Right-click context menu
  - Auto-detect video URLs

- [ ] **Cloud Integration** (maybe)
  - Save to cloud storage
  - Google Drive/Dropbox support
  - Direct uploads

**Priority:** LOW

---

## Feature Requests

Have a feature idea? Add it to `FUTURE_FEATURES.md`!

---

## Non-Goals

Things we WON'T implement:

- ❌ Built-in video player
- ❌ Video editing features
- ❌ Streaming/live download
- ❌ Torrent support
- ❌ Ad injection or monetization
- ❌ DRM breaking or illegal features

---

## Contribution Guidelines

### How to Propose Features

1. Check `FUTURE_FEATURES.md` first
2. Open GitHub issue (when repo is public)
3. Discuss in community
4. Create pull request

### Development Priorities

1. **Bug fixes** - Always first priority
2. **v1.x features** - Core functionality
3. **v2.x features** - Nice-to-have
4. **Community requests** - Based on popularity

---

## Release Cycle

### Version Numbering

- **Major (X.0.0):** Breaking changes, major new features
- **Minor (1.X.0):** New features, no breaking changes
- **Patch (1.0.X):** Bug fixes, small improvements

### Release Process

1. Feature complete in main branch
2. Create release branch
3. Testing phase (2 weeks)
4. Bug fixes and polish
5. Final build and packaging
6. Release and announcement
7. Update documentation

---

## Dependencies Roadmap

### yt-dlp Updates

- Monitor yt-dlp releases
- Test compatibility
- Update bundled version
- Release new YT-DLP Studio version

**Frequency:** Every major yt-dlp release or as needed

### PySide6 Updates

- Monitor PySide6 releases
- Test compatibility
- Update if beneficial
- Document breaking changes

**Frequency:** As needed, conservative approach

---

## Platform Support Timeline

### Current

- ✅ Windows 10
- ✅ Windows 11

### Version 2.0.0

- 🔄 Ubuntu 20.04+
- 🔄 Debian 11+
- 🔄 Other Linux (untested)

### Future (maybe)

- ❓ macOS (if demand exists)
- ❓ Portable version
- ❓ Web version (unlikely)

---

## Performance Goals

### Current (v1.0)

- Single download support
- ~100MB app size
- <500MB RAM usage
- Instant UI response

### Future Targets

- 3-5 concurrent downloads (v1.1)
- <150MB app size (v2.0)
- <1GB RAM usage (v2.0)
- Same UI responsiveness

---

## Testing Strategy

### v1.0

- Manual testing only
- Developer testing
- Limited user testing

### v1.1+

- Automated UI tests
- Unit tests for backend
- Continuous integration
- Beta testing program

---

## Documentation Goals

### Current

- ✅ Architecture docs
- ✅ Development guide
- ✅ Roadmap
- ✅ Code comments

### Future

- User manual
- Video tutorials
- FAQ
- Troubleshooting guide
- API documentation (if needed)

---

## Community Building

### v1.0

- Initial release
- GitHub repository
- Basic README

### v1.1+

- Discord server (maybe)
- Contributing guidelines
- Code of conduct
- Issue templates

---

## Monetization (Future Consideration)

### Current

- Free and open source (decision pending)

### Future Options (if needed)

- Donations (Ko-fi, Patreon)
- Pro version with extra features
- Commercial licensing
- Support contracts

**Note:** Will always have a free version!

---

## Questions and Feedback

- Check `docs/` for more information
- See `FUTURE_FEATURES.md` for feature ideas
- Follow development progress in commits

---

**Last Updated:** 2025-11-09
**Current Version:** 1.9.0 (released)
**Next Version:** 2.0.0 (Hebrew Translation)
