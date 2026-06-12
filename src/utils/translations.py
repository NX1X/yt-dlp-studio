"""
Multi-Language Translation System for YT-DLP Studio.

Supports Hebrew and English with automatic language detection.
Includes RTL (Right-to-Left) support for Hebrew.
"""

import locale

from ..utils.logger import get_logger

logger = get_logger()


# Translation dictionaries
TRANSLATIONS = {
    "en": {
        # Main Window
        "app_title": "YT-DLP Studio",
        "menu_file": "File",
        "menu_help": "Help",
        "menu_settings": "Settings",
        "menu_exit": "Exit",
        "menu_about": "About",
        # Tabs
        "tab_download": "Download",
        "tab_queue": "Queue",
        "tab_history": "History",
        "tab_settings": "Settings",
        "tab_about": "About",
        # Download Tab
        "label_url": "URL:",
        "download_url_placeholder": "Enter YouTube URL or drag & drop here...",
        "placeholder_url": "Paste YouTube URL here",
        "label_quality": "Quality:",
        "label_output": "Output Directory:",
        "label_save_to": "Save to:",
        "button_browse": "Browse",
        "button_download": "Download",
        "button_download_now": "Download Now",
        "button_add_to_queue": "Add to Queue",
        "button_batch": "Batch Input",
        "button_batch_input": "Batch Input",
        "button_paste": "Paste",
        "button_show_info": "Show Info",
        "button_open_dir": "Open",
        "button_clear_log": "Clear Log",
        "checkbox_thumbnail": "Download Thumbnail",
        "checkbox_subtitles": "Download Subtitles",
        "label_subtitle_langs": "Languages:",
        "placeholder_subtitle_langs": "en,es,he",
        "label_speed_limit": "Speed Limit:",
        "label_unlimited": "0 = Unlimited",
        "text_unlimited": "Unlimited",
        "button_get_info": "Get Video Info",
        # Download tab - type/format selectors (added in UI parity pass)
        "label_download_type": "Download Type:",
        "download_type_video": "Video",
        "download_type_audio": "Audio Only",
        "tooltip_download_type": "Choose whether to download video or extract audio only",
        "label_video_format": "Video Format:",
        "tooltip_video_format": "Choose video container format (MP4 recommended for compatibility)",
        "label_audio_format": "Audio Format:",
        "tooltip_audio_format": "Choose audio format for audio-only downloads (MP3 recommended for compatibility)",
        "quality_audio_320": "Audio 320kbps",
        "quality_audio_256": "Audio 256kbps",
        "quality_audio_192": "Audio 192kbps",
        "quality_audio_128": "Audio 128kbps",
        "dialog_no_subs_available": "No Subtitles Available",
        "msg_no_subs_available": "This video doesn't have any subtitles available.",
        "tooltip_select_subs": "Fetch and select specific subtitle languages",
        "text_fetching_subs": "Fetching…",
        "tooltip_paste": "Paste URL from clipboard (Ctrl+V)",
        "tooltip_open_dir": "Open download directory in file explorer",
        "tooltip_thumbnail": "Download video thumbnail as JPG",
        "tooltip_subtitles": "Download and embed subtitles",
        "tooltip_subtitle_langs": "Comma-separated language codes (e.g., en,es,he)",
        "tooltip_speed_limit": "Download speed limit (0 = unlimited)",
        "tooltip_batch": "Add multiple URLs at once",
        "group_progress": "Progress",
        "group_log": "Log",
        "button_show_log": "Show Advanced Log",
        "button_hide_log": "Hide Advanced Log",
        "error_invalid_url": "Invalid URL",
        "error_invalid_dir": "Invalid Directory",
        "duplicate_download": "Duplicate Download?",
        "duplicate_download_message": "This exact download (same URL, quality, and format) is already in the queue.\n\nDo you want to add it again?",
        # Batch Input Dialog
        "batch_title": "Batch URL Input",
        "batch_instructions": "Enter video URLs (one per line):\nYou can paste multiple URLs or import from a text file.",
        "batch_placeholder": "https://youtube.com/watch?v=...\nhttps://youtube.com/watch?v=...\nhttps://youtube.com/playlist?list=...",
        "batch_import": "Import from File",
        "batch_validate": "Validate URLs",
        "batch_clear": "Clear",
        "batch_add": "Add URLs",
        "batch_cancel": "Cancel",
        "batch_count": "URLs: {count}",
        "batch_no_urls": "No URLs",
        "batch_no_urls_msg": "Please enter at least one URL.",
        "batch_no_valid_urls": "No Valid URLs",
        "batch_no_valid_urls_msg": "No valid URLs found. Please check your input.",
        "batch_invalid_found": "Invalid URLs Found",
        "batch_invalid_found_msg": "Found {valid} valid URLs and {invalid} invalid entries.\nDo you want to proceed with the valid URLs only?",
        "batch_validation_results": "Validation Results",
        "batch_validation_msg": "Found {valid} valid URLs and {invalid} invalid entries:",
        "batch_validation_success": "Validation Successful",
        "batch_validation_success_msg": "All {count} URLs are valid!",
        # Queue Tab
        "queue_empty": "No downloads in queue",
        "queue_empty_hint": "Go to the Download tab to add a video.",
        # Settings tab - Storage group (paths users may want for bug reports)
        "settings_storage": "Storage",
        "label_log_file_path": "Log file:",
        "label_crash_dir_path": "Crash reports:",
        "label_config_file_path": "Config file:",
        "button_copy": "Copy",
        "tooltip_copy_path": "Copy this path to the clipboard",
        "msg_path_copied": "Path copied to clipboard.",
        # About tab - sections and labels
        "about_description": "is a user-friendly graphical interface for yt-dlp, making it easy to download videos from YouTube.",
        "group_about_details": "Details",
        "group_about_developer": "About the Developer",
        "group_about_system_info": "System Information",
        "label_app_version": "Application version:",
        "label_yt_dlp_version": "yt-dlp engine:",
        "label_ffmpeg_version": "FFmpeg:",
        "label_python_version": "Python runtime:",
        "label_pyside_version": "PySide6 (Qt):",
        "text_about_developer_intro": "This tool is part of <b>NXtools</b> - a collection of productivity tools.",
        "label_website": "Website:",
        "label_support_development": "Support development:",
        "text_buy_me_a_coffee_blurb": "If you find this tool useful, consider buying me a coffee!",
        "button_view_on_github": "View on GitHub",
        "tooltip_view_on_github": "Open the project repository in your browser",
        "header_credits_core_deps": "Core dependencies",
        "header_credits_dev_framework": "Development framework",
        "header_credits_build_dist": "Build &amp; distribution",
        "text_credits_thanks": "Thank you to all the developers and contributors of these open-source projects. This application would not be possible without your work.",
        "text_ffmpeg_not_found": "Not found in PATH",
        "text_ffmpeg_unknown": "Installed (version unknown)",
        "text_ffmpeg_error": "Error detecting version",
        "text_version_unknown": "Unknown",
        "dialog_crash_title": "YT-DLP Studio has crashed",
        "dialog_crash_body": "An unexpected error occurred and the application must close.\n\nA crash report has been saved to:\n{path}\n\nPlease attach this file to a GitHub issue at https://github.com/NX1X/yt-dlp-studio/issues so the bug can be fixed.",
        "dialog_crash_body_no_path": "An unexpected error occurred and the application must close.\n\n(The crash report could not be written to disk.)",
        "queue_statistics": "Queue Statistics",
        "queue_download_queue": "Download Queue",
        "stat_total": "Total",
        "stat_pending": "Pending",
        "stat_active": "Active",
        "stat_completed": "Completed",
        "stat_failed": "Failed",
        "col_video_name": "Video Name",
        "col_url": "URL",
        "col_quality": "Quality",
        "col_status": "Status",
        "col_progress": "Progress",
        "col_speed": "Speed",
        "col_output": "Output",
        "col_actions": "Actions",
        "col_select": "Select",
        "col_index": "#",
        "col_duration": "Duration",
        "col_uploader": "Uploader",
        "button_start_queue": "Start Queue",
        "button_pause_queue": "Pause Queue",
        "button_stop_all": "Stop All",
        "button_move_up": "Move Up",
        "button_move_down": "Move Down",
        "button_remove": "Remove",
        "button_open_file": "Open File",
        "button_clear_completed": "Clear Completed",
        "button_clear_failed": "Clear Failed",
        "tooltip_open_file": "Open the downloaded file (select completed download)",
        "text_fetching": "Fetching...",
        "msg_no_selection": "No Selection",
        "msg_select_download": "Please select a completed download to open.",
        "msg_not_completed": "Not Completed",
        "msg_not_completed_desc": "This download is not completed yet.\nOnly completed downloads can be opened.",
        "msg_file_not_found": "File Not Found",
        "msg_file_path_unknown": "Could not determine the file path for this download.",
        "msg_file_not_found_desc": "The downloaded file could not be found",
        "msg_failed_open_file": "Failed to open file",
        # History Tab
        "history_empty": "No download history",
        "history_empty_hint": "Downloads will appear here once completed.",
        "history_statistics": "Statistics",
        "history_download_history": "Download History",
        "label_search": "Search:",
        "placeholder_search_history": "Search by title or URL...",
        "col_datetime": "Date/Time",
        "col_title": "Title",
        "col_size": "Size",
        "button_refresh": "Refresh",
        "button_export_csv": "Export CSV",
        "button_open_directory": "Open Directory",
        "button_clear_all": "Clear All",
        "tooltip_open_downloads_dir": "Open downloads directory in file explorer",
        "stat_total_downloads": "Total Downloads",
        "stat_cancelled": "Cancelled",
        "stat_success_rate": "Success Rate",
        "stat_total_downloaded": "Total Downloaded",
        "stat_average_speed": "Average Speed",
        "dialog_export_history": "Export History",
        "filter_csv_files": "CSV Files (*.csv)",
        "msg_success": "Success",
        "msg_history_exported": "History exported to",
        "msg_export_failed": "Failed to export history",
        "dialog_confirm_clear": "Confirm Clear",
        "dialog_confirm_clear_all": "Confirm Clear All",
        "msg_clear_status_confirm": "Clear all {status} downloads from history?",
        "msg_clear_all_confirm": "Clear ALL download history? This cannot be undone!",
        "msg_cleared_entries": "Cleared {count} history entries",
        "msg_dir_not_found": "Directory Not Found",
        "msg_download_dir_not_exist": "The download directory does not exist",
        "msg_failed_open_dir": "Failed to open directory",
        # Settings Tab
        "settings_general": "General Settings",
        "settings_appearance": "Appearance",
        "settings_download": "Download Settings",
        "settings_notifications": "Notifications",
        "settings_language": "Language",
        "settings_features": "Features",
        "settings_about": "About",
        "settings_version_info": "Version Information",
        "label_default_folder": "Default Download Folder:",
        "label_default_quality": "Default Quality:",
        "label_language": "Language:",
        "label_theme": "Theme:",
        "button_toggle_theme": "Toggle Theme (Dark/Light)",
        "dialog_theme_switched": "Theme Changed",
        "checkbox_notifications": "Enable Desktop Notifications",
        "checkbox_auto_update": "Notify me about new versions on startup",
        "tooltip_notifications": "Show desktop notifications for download events",
        "tooltip_auto_update": "Checks GitHub on startup and shows a notification if a newer version is available. Does not install automatically.",
        "button_check_update": "Check for Updates Now",
        "button_reset_defaults": "Reset to Defaults",
        "button_save_settings": "Save Settings",
        # Notifications
        "notif_download_complete": "Download Complete",
        "notif_download_error": "Download Error",
        "notif_batch_complete": "Batch Download Complete",
        "notif_update_available": "Update Available",
        # Update Dialog
        "update_title": "Update Available",
        "update_message": "Version {version} is available!\n\nCurrent version: {current}\nNew version: {new}\n\nWould you like to download the update?",
        "update_download": "Download Update",
        "update_later": "Later",
        "update_downloading": "Downloading Update",
        "update_installing": "Installing Update",
        "update_success": "Update Successful",
        "update_error": "Update Error",
        # Video Info
        "info_title": "Video Information",
        "info_duration": "Duration:",
        "info_uploader": "Uploader:",
        "info_views": "Views:",
        "info_upload_date": "Upload Date:",
        # Filter Dialog
        "filter_title": "Download Filters",
        "filter_duration": "Duration Filter",
        "filter_min_duration": "Min Duration (seconds):",
        "filter_max_duration": "Max Duration (seconds):",
        "filter_date": "Date Filter",
        "filter_after_date": "After Date:",
        "filter_before_date": "Before Date:",
        "filter_keyword": "Keyword Filter",
        "filter_include_keywords": "Include Keywords:",
        "filter_exclude_keywords": "Exclude Keywords:",
        "filter_apply": "Apply Filters",
        "filter_reset": "Reset Filters",
        # Bandwidth Monitor
        "bandwidth_title": "Bandwidth Monitor",
        "bandwidth_current_speed": "Current Speed:",
        "bandwidth_avg_speed": "Average Speed:",
        "bandwidth_peak_speed": "Peak Speed:",
        "bandwidth_total_downloaded": "Total Downloaded:",
        # Status Messages
        "status_pending": "Pending",
        "status_downloading": "Downloading...",
        "status_completed": "Completed",
        "status_error": "Error",
        "status_cancelled": "Cancelled",
        "status_preparing": "Preparing your download...",
        "status_ready": "Ready to download",
        "status_complete": "Download complete!",
        "status_success": "Download completed successfully!",
        # Common
        "yes": "Yes",
        "no": "No",
        "ok": "OK",
        "cancel": "Cancel",
        "close": "Close",
        "error": "Error",
        "warning": "Warning",
        "info": "Information",
        # Additional Main Window
        "status_bar_ready": "Ready",
        "tooltip_exit_application": "Exit application",
        "menu_view": "View",
        "menu_toggle_theme": "Toggle Theme (Dark/Light)",
        "tooltip_toggle_theme": "Switch between Dark and Light themes",
        "menu_keyboard_shortcuts": "Keyboard Shortcuts",
        "tooltip_keyboard_shortcuts": "View keyboard shortcuts",
        "dialog_about": "About",
        "dialog_download_in_progress": "Download in Progress",
        "msg_download_in_progress_exit": "A download is currently in progress. Are you sure you want to exit?",
        "dialog_keyboard_shortcuts": "Keyboard Shortcuts",
        "theme_dark": "Dark",
        "theme_light": "Light",
        "msg_theme_switched": "Theme switched to: {theme}",
        # Additional Download Tab
        "dialog_select_download_dir": "Select Download Directory",
        "error_generic": "Error",
        "msg_dir_not_exist": "The directory does not exist:\n{directory}",
        "button_downloading": "Downloading...",
        "dialog_download_failed": "Download Failed",
        "button_fetching": "Fetching...",
        "button_fetching_playlist": "Fetching Playlist...",
        "dialog_failed_fetch_video_info": "Failed to Fetch Video Info",
        "dialog_failed_fetch_playlist_info": "Failed to Fetch Playlist Info",
        "error_invalid_directory": "Invalid Directory",
        "dialog_playlist_detected": "Playlist Detected",
        "msg_playlist_detected_options": "This appears to be a {platform} playlist.\n\nDo you want to view and select specific videos?\n\nClick 'Yes' to view playlist, or 'No' to add the entire playlist URL directly.",
        "dialog_added_to_queue": "Added to Queue",
        "msg_video_added_to_queue": "Video added to download queue at position {position}.\n\nGo to the Queue tab to monitor progress.",
        "dialog_download_complete": "Download Complete",
        "msg_download_complete": "Video downloaded successfully!\n\nSaved to: {filename}",
        "dialog_playlist_added_to_queue": "Playlist Added to Queue",
        "msg_playlist_added_to_queue": "Successfully added {count} videos to the download queue.\n\nGo to the Queue tab to monitor progress.",
        "dialog_batch_added": "Batch Added",
        "msg_batch_added_to_queue": "Successfully added {count} URLs to the download queue.\n\nGo to the Queue tab to monitor progress.",
        # Batch Input Dialog
        "dialog_batch_url_input": "Batch URL Input",
        "msg_batch_input_instructions": "Enter video URLs (one per line):\nYou can paste multiple URLs or import from a text file.",
        "button_import_from_file": "Import from File",
        "label_urls_count": "URLs: {count}",
        "button_validate_urls": "Validate URLs",
        "button_add_urls": "Add URLs",
        "dialog_import_urls_from_file": "Import URLs from File",
        "dialog_import_error": "Import Error",
        "msg_failed_import_file": "Failed to import file:\n{error}",
        "msg_enter_at_least_one_url": "Please enter at least one URL.",
        "dialog_validation_results": "Validation Results",
        "dialog_validation_successful": "Validation Successful",
        "dialog_no_valid_urls": "No Valid URLs",
        "msg_no_valid_urls_found": "No valid URLs found. Please check your input.",
        "dialog_invalid_urls_found": "Invalid URLs Found",
        # Filter Dialog
        "dialog_download_filters": "Download Filters",
        "button_reset_filters": "Reset Filters",
        "button_apply_filters": "Apply Filters",
        "group_duration_filter": "Duration Filter",
        "label_min_duration": "Min Duration (seconds):",
        "text_no_minimum": "No minimum",
        "label_max_duration": "Max Duration (seconds):",
        "text_no_maximum": "No maximum",
        "group_upload_date_filter": "Upload Date Filter",
        "label_uploaded_after": "Uploaded After:",
        "label_uploaded_before": "Uploaded Before:",
        "group_keyword_filter": "Keyword Filter",
        "label_include_keywords": "Include Keywords (comma-separated):",
        "label_exclude_keywords": "Exclude Keywords (comma-separated):",
        # Settings Tab
        "dialog_select_default_download_dir": "Select Default Download Directory",
        "dialog_settings_saved_restart_required": "Settings Saved - Restart Required",
        "msg_language_changed_restart_required": "Settings saved successfully!\n\nLanguage changed to: {language}\n\n⚠️ Please restart the application for the language change to take effect.",
        "dialog_settings_saved": "Settings Saved",
        "msg_settings_saved": "Your settings have been saved successfully!",
        "msg_failed_save_settings": "Failed to save settings. Please check the log for details.",
        "dialog_reset_settings": "Reset Settings",
        "msg_confirm_reset_settings": "Are you sure you want to reset all settings to defaults?",
        "dialog_settings_reset": "Settings Reset",
        "msg_all_settings_reset": "All settings have been reset to defaults.",
        "button_checking": "Checking...",
        "dialog_no_updates": "No Updates",
        "msg_already_latest_version": "You are already using the latest version ({version}).",
        "dialog_update_check_failed": "Update Check Failed",
        "msg_update_check_failed": "Could not check for updates:\n{error}\n\nPlease check your internet connection.",
        "button_check_for_updates_now": "Check for Updates Now",
        # Log Widget
        "placeholder_log_messages": "Log messages will appear here...",
        # Video Info Dialog
        "dialog_video_information": "Video Information",
        "group_thumbnail": "Thumbnail",
        "text_loading_thumbnail": "Loading thumbnail...",
        "group_details": "Details",
        "label_channel": "Channel:",
        "label_duration": "Duration:",
        "label_uploaded": "Uploaded:",
        "label_views": "Views:",
        "label_likes": "Likes:",
        "label_platform": "Platform:",
        "group_description": "Description",
        "button_close": "Close",
        "text_no_thumbnail_available": "No thumbnail available",
        "text_failed_load_thumbnail": "Failed to load thumbnail",
        # Playlist Dialog
        "dialog_playlist_viewer": "Playlist Viewer",
        "group_playlist_information": "Playlist Information",
        "label_videos_count": "Videos: {count}",
        "button_select_all": "Select All",
        "button_select_none": "Select None",
        "label_quality_playlist": "Quality:",
        "quality_best": "Best Quality",
        "quality_1080p": "1080p (Full HD)",
        "quality_720p": "720p (HD)",
        "quality_480p": "480p (SD)",
        "quality_audio_only": "Audio Only",
        "dialog_no_videos_selected": "No Videos Selected",
        "msg_select_at_least_one_video": "Please select at least one video to download.",
        # Playlist Dialog - Subtitles section
        "group_playlist_subtitles": "Subtitles (overrides Download tab)",
        "checkbox_playlist_download_subtitles": "Download subtitles for every selected video",
        "label_playlist_subtitle_override_hint": "When off, subtitle settings from the Download tab apply. When on, only the languages below are downloaded for every video.",
        "tooltip_playlist_download_subtitles": "When enabled, each video in the playlist will have subtitles downloaded in the languages selected below.",
        "label_playlist_subtitle_languages": "Languages:",
        "checkbox_subtitle_lang_he": "Hebrew (he + iw)",
        "checkbox_subtitle_lang_en": "English (en)",
        "checkbox_subtitle_lang_ar": "Arabic (ar)",
        "checkbox_subtitle_lang_es": "Spanish (es)",
        "checkbox_subtitle_lang_fr": "French (fr)",
        "checkbox_subtitle_lang_ru": "Russian (ru)",
        "checkbox_subtitle_lang_de": "German (de)",
        "label_playlist_subtitle_other": "Other codes:",
        "placeholder_playlist_subtitle_other": "e.g. pt,it,zh-Hans",
        "tooltip_playlist_subtitle_other": "Comma-separated language codes for languages not in the list above.",
        "msg_playlist_no_subtitle_langs": "Subtitle download is enabled but no languages are selected. Tick at least one language or untick the subtitles checkbox.",
        # Progress Bar
        "text_error_prefix": "Error:",
        "label_size": "Size:",
        "label_downloaded": "Downloaded:",
        "label_speed": "Speed:",
        "label_eta": "ETA:",
        "text_unknown": "--",
        # Bandwidth Widget
        "title_bandwidth_monitor": "Bandwidth Monitor",
        "group_statistics": "Statistics",
        "group_speed_graph": "Speed Graph",
        # Video Player Widget
        "label_volume": "Volume:",
        "text_no_file_loaded": "No file loaded",
        "dialog_file_not_found": "File Not Found",
        "msg_file_not_found_details": "Could not find file:\n{file_path}",
        "dialog_playback_error": "Playback Error",
        "msg_error_playing_video": "Error playing video:\n{error}",
        # Update Dialog
        "dialog_update_available": "Update Available",
        "text_version_available": "Version {version} is available!",
        "label_current_version": "Current version:",
        "label_new_version": "New version:",
        "label_release_notes": "Release Notes:",
        "text_no_release_notes": "No release notes available.",
        "button_view_on_github": "View on GitHub",
        "button_visit_website": "Visit Website",
        "button_download_update": "Download Update",
        "button_remind_me_later": "Remind Me Later",
        "dialog_download_error": "Download Error",
        "msg_no_download_url": "No download URL available. Please visit GitHub to download manually.",
        "dialog_confirm_download": "Confirm Download",
        "msg_confirm_download_text": "This will download the installer to your Downloads folder.\n\nFile: {filename}\nSize: {size}\n\nThe download will start in the background.\n\nContinue?",
        "text_downloading_update": "Downloading update...",
        "text_download_complete": "Download complete!",
        "text_download_failed": "Download failed!",
        "dialog_download_complete_update": "Download Complete",
        "dialog_installing_update": "Installing Update",
        "msg_installer_confirmation": "The installer has been downloaded to:\n{path}\n\nWould you like to run the installer now?\n\nThe application will close when you click 'Yes'.",
        "dialog_installer_error": "Installer Error",
        "button_skip_version": "Skip This Version",
        "text_unknown_size": "Unknown size",
        "text_download_verified": "Download verified.",
        "msg_download_verified_install": "Update downloaded and verified successfully.\n\nFile: {path}\n\nWould you like to run the installer now?\n(This will close the application.)",
        "msg_installer_saved": "The verified installer has been saved to:\n{path}\n\nYou can run it later to update the application.",
        "dialog_verify_failed": "Verification Failed",
        "msg_verify_failed": "The downloaded installer failed integrity verification and was deleted for your safety.\n\nExpected: {expected}\nActual: {actual}\n\nPlease try again, or download manually from GitHub.",
        "dialog_unverified_download": "Unverified Download",
        "msg_unverified_download": "This release does not publish a checksum, so the download could not be verified automatically.\n\nThe file was saved to:\n{path}\n\nFor your safety it will not be launched automatically. Only run it manually if you trust the source.",
        "msg_download_failed_retry": "Failed to download the update.\n\nPlease try again, or download manually from GitHub.",
        "msg_installer_launch_failed": "Failed to run the installer:\n{error}\n\nPlease run it manually:\n{path}",
        "msg_update_check_rate_limited": "GitHub's update server is rate-limiting requests. Please try again later.",
        # About Tab
        "label_bundled_ytdlp": "Bundled yt-dlp",
        "label_author": "Author",
        "label_credits": "Credits",
        "text_credits_description": "This application is built using the following open-source projects:",
        "button_documentation": "Documentation",
        # Keyboard Shortcuts
        "shortcuts_title": "Keyboard Shortcuts",
        "shortcuts_general": "General",
        "shortcuts_download_tab": "Download Tab",
        "shortcuts_queue_tab": "Queue Tab",
        "shortcut_quit_app": "Quit application",
        "shortcut_show_help": "Show this help",
        "shortcut_close_dialogs": "Close dialogs",
        "shortcut_paste_url": "Paste URL from clipboard",
        "shortcut_start_download": "Start download (when URL field is focused)",
        "shortcut_show_video_info": "Show video info",
        "shortcut_download_now": "Download Now",
        "shortcut_add_to_queue": "Add to Queue",
        "shortcut_remove_task": "Remove selected task",
        "shortcut_move_task_up": "Move task up",
        "shortcut_move_task_down": "Move task down",
        # v2.1.0 - New Features
        "button_select_subs": "Select Subs...",
        "checkbox_metadata": "Download Metadata",
        "checkbox_comments": "Download Comments",
        "tooltip_select_subs": "Browse available subtitles and select which to download",
        "tooltip_metadata": "Download video metadata (description, info.json, annotations)",
        "tooltip_comments": "Download video comments to a separate .txt file (may be slow for popular videos)",
        "subtitle_header_most_used": "──── MOST USED ────",
        "subtitle_header_all": "──── ALL LANGUAGES ────",
        "subtitle_type_manual": "Manual",
        "subtitle_type_auto": "Auto-generated",
        "subtitle_type_both": "Manual & Auto",
        "subtitle_select_all_visible": "Select All Visible",
        "subtitle_search_placeholder": "Type to filter languages (e.g., 'spanish', 'es', 'hebrew')...",
        "subtitle_search_label": "Search:",
        "subtitle_pinned_languages": "Select subtitle languages (English & Hebrew pinned to top):",
        "subtitle_no_available": "No subtitles available for this video",
        "subtitle_fetching_info": "Fetching subtitle information...",
        "button_loading": "Loading...",
        "button_download_selected": "Download Selected",
        "button_cancel": "Cancel",
        "button_retry": "Retry",
        "no_selection_title": "No Selection",
        "no_selection_msg": "Please select at least one subtitle language, or click Cancel.",
        "error_fetch_subs": "Could not fetch video information. Please check the URL and try again.",
        "no_subs_title": "No Subtitles",
        "no_subs_msg": "This video does not have any subtitles available.",
    },
    "he": {
        # Main Window
        "app_title": "YT-DLP Studio",
        "menu_file": "קובץ",
        "menu_help": "עזרה",
        "menu_settings": "הגדרות",
        "menu_exit": "יציאה",
        "menu_about": "אודות",
        # Tabs
        "tab_download": "הורדה",
        "tab_queue": "תור",
        "tab_history": "היסטוריה",
        "tab_settings": "הגדרות",
        "tab_about": "אודות",
        # Download Tab
        "label_url": "URL:",
        "download_url_placeholder": "הזן כתובת YouTube או גרור ושחרר כאן...",
        "placeholder_url": "הדבק כתובת YouTube כאן",
        "label_quality": "איכות:",
        "label_output": "תיקיית פלט:",
        "label_save_to": "שמור ב:",
        "button_browse": "עיון",
        "button_download": "הורד",
        "button_download_now": "הורד כעת",
        "button_add_to_queue": "הוסף לתור",
        "button_batch": "קלט קבוצתי",
        "button_batch_input": "קלט קבוצתי",
        "button_paste": "הדבק",
        "button_show_info": "הצג מידע",
        "button_open_dir": "פתח",
        "button_clear_log": "נקה יומן",
        "checkbox_thumbnail": "הורד תמונת רקע",
        "checkbox_subtitles": "הורד כתוביות",
        "label_subtitle_langs": "שפות:",
        "placeholder_subtitle_langs": "en,es,he",
        "label_speed_limit": "הגבלת מהירות:",
        "label_unlimited": "0 = ללא הגבלה",
        "text_unlimited": "ללא הגבלה",
        "button_get_info": "הצג מידע על הסרטון",
        # Download tab - type/format selectors (UI parity pass)
        "label_download_type": "סוג הורדה:",
        "download_type_video": "וידאו",
        "download_type_audio": "אודיו בלבד",
        "tooltip_download_type": "בחר אם להוריד וידאו או להפיק אודיו בלבד",
        "label_video_format": "פורמט וידאו:",
        "tooltip_video_format": "בחר פורמט מיכל וידאו (מומלץ MP4 לתאימות)",
        "label_audio_format": "פורמט אודיו:",
        "tooltip_audio_format": "בחר פורמט אודיו להורדות אודיו בלבד (מומלץ MP3 לתאימות)",
        "quality_audio_320": "אודיו 320kbps",
        "quality_audio_256": "אודיו 256kbps",
        "quality_audio_192": "אודיו 192kbps",
        "quality_audio_128": "אודיו 128kbps",
        "dialog_no_subs_available": "אין כתוביות זמינות",
        "msg_no_subs_available": "לסרטון זה אין כתוביות זמינות.",
        "tooltip_select_subs": "טען ובחר שפות כתוביות ספציפיות",
        "text_fetching_subs": "טוען…",
        "tooltip_paste": "הדבק URL מהלוח (Ctrl+V)",
        "tooltip_open_dir": "פתח תיקיית הורדות במנהל הקבצים",
        "tooltip_thumbnail": "הורד תמונה ממוזערת כ-JPG",
        "tooltip_subtitles": "הורד והטמע כתוביות",
        "tooltip_subtitle_langs": "קודי שפה מופרדים בפסיק (למשל: en,es,he)",
        "tooltip_speed_limit": "הגבלת מהירות הורדה (0 = ללא הגבלה)",
        "tooltip_batch": "הוסף מספר URLs בבת אחת",
        "group_progress": "התקדמות",
        "group_log": "יומן",
        "button_show_log": "הצג יומן מתקדם",
        "button_hide_log": "הסתר יומן מתקדם",
        "error_invalid_url": "URL לא תקין",
        "error_invalid_dir": "תיקייה לא תקינה",
        "duplicate_download": "הורדה כפולה?",
        "duplicate_download_message": "הורדה זהה (אותו URL, איכות, ופורמט) כבר נמצאת בתור.\n\nהאם להוסיף שוב?",
        # Batch Input Dialog
        "batch_title": "קלט קבוצתי של URLs",
        "batch_instructions": "הזן כתובות URL (אחת בכל שורה):\nניתן להדביק מספר URLs או לייבא מקובץ טקסט.",
        "batch_placeholder": "https://youtube.com/watch?v=...\nhttps://youtube.com/watch?v=...\nhttps://youtube.com/playlist?list=...",
        "batch_import": "ייבא מקובץ",
        "batch_validate": "אמת URLs",
        "batch_clear": "נקה",
        "batch_add": "הוסף URLs",
        "batch_cancel": "ביטול",
        "batch_count": "URLs: {count}",
        "batch_no_urls": "אין URLs",
        "batch_no_urls_msg": "אנא הזן לפחות URL אחד.",
        "batch_no_valid_urls": "אין URLs תקינים",
        "batch_no_valid_urls_msg": "לא נמצאו URLs תקינים. אנא בדוק את הקלט שלך.",
        "batch_invalid_found": "נמצאו URLs לא תקינים",
        "batch_invalid_found_msg": "נמצאו {valid} URLs תקינים ו-{invalid} ערכים לא תקינים.\nהאם ברצונך להמשיך רק עם ה-URLs התקינים?",
        "batch_validation_results": "תוצאות אימות",
        "batch_validation_msg": "נמצאו {valid} URLs תקינים ו-{invalid} ערכים לא תקינים:",
        "batch_validation_success": "האימות הצליח",
        "batch_validation_success_msg": "כל {count} ה-URLs תקינים!",
        # Queue Tab
        "queue_empty": "אין הורדות בתור",
        "queue_empty_hint": "עבור ללשונית ההורדה כדי להוסיף סרטון.",
        # Settings tab - Storage group
        "settings_storage": "אחסון",
        "label_log_file_path": "קובץ יומן:",
        "label_crash_dir_path": "דוחות קריסה:",
        "label_config_file_path": "קובץ הגדרות:",
        "button_copy": "העתק",
        "tooltip_copy_path": "העתק נתיב זה ללוח",
        "msg_path_copied": "הנתיב הועתק ללוח.",
        # About tab - sections and labels
        "about_description": "הוא ממשק גרפי ידידותי למשתמש עבור yt-dlp שמקל על הורדת סרטונים מ-YouTube.",
        "group_about_details": "פרטים",
        "group_about_developer": "אודות המפתח",
        "group_about_system_info": "מידע מערכת",
        "label_app_version": "גרסת אפליקציה:",
        "label_yt_dlp_version": "מנוע yt-dlp:",
        "label_ffmpeg_version": "FFmpeg:",
        "label_python_version": "סביבת Python:",
        "label_pyside_version": "PySide6 (Qt):",
        "text_about_developer_intro": "כלי זה הוא חלק מ-<b>NXtools</b> - אוסף של כלי פרודקטיביות.",
        "label_website": "אתר:",
        "label_support_development": "תמיכה בפיתוח:",
        "text_buy_me_a_coffee_blurb": "אם מצאת את הכלי מועיל, שקול לקנות לי קפה!",
        "button_view_on_github": "צפה ב-GitHub",
        "tooltip_view_on_github": "פתח את מאגר הפרויקט בדפדפן",
        "header_credits_core_deps": "תלויות מרכזיות",
        "header_credits_dev_framework": "סביבת פיתוח",
        "header_credits_build_dist": "בנייה והפצה",
        "text_credits_thanks": "תודה לכל המפתחים והתורמים של פרויקטי הקוד הפתוח הללו. האפליקציה הזו לא הייתה מתאפשרת בלי עבודתכם.",
        "text_ffmpeg_not_found": "לא נמצא ב-PATH",
        "text_ffmpeg_unknown": "מותקן (גרסה לא ידועה)",
        "text_ffmpeg_error": "שגיאה בזיהוי גרסה",
        "text_version_unknown": "לא ידוע",
        "dialog_crash_title": "YT-DLP Studio קרס",
        "dialog_crash_body": "אירעה שגיאה בלתי צפויה והאפליקציה חייבת להיסגר.\n\nדוח הקריסה נשמר אל:\n{path}\n\nאנא צרף קובץ זה לדיווח באג ב-https://github.com/NX1X/yt-dlp-studio/issues כדי שנוכל לתקן את הבעיה.",
        "dialog_crash_body_no_path": "אירעה שגיאה בלתי צפויה והאפליקציה חייבת להיסגר.\n\n(לא ניתן היה לכתוב את דוח הקריסה לדיסק.)",
        "queue_statistics": "סטטיסטיקת תור",
        "queue_download_queue": "תור הורדות",
        "stat_total": 'סה"כ',
        "stat_pending": "ממתין",
        "stat_active": "פעיל",
        "stat_completed": "הושלם",
        "stat_failed": "נכשל",
        "col_video_name": "שם הסרטון",
        "col_url": "URL",
        "col_quality": "איכות",
        "col_status": "מצב",
        "col_progress": "התקדמות",
        "col_speed": "מהירות",
        "col_output": "פלט",
        "col_actions": "פעולות",
        "col_select": "בחר",
        "col_index": "#",
        "col_duration": "משך",
        "col_uploader": "מעלה",
        "button_start_queue": "התחל תור",
        "button_pause_queue": "השהה תור",
        "button_stop_all": "עצור הכל",
        "button_move_up": "הזז למעלה",
        "button_move_down": "הזז למטה",
        "button_remove": "הסר",
        "button_open_file": "פתח קובץ",
        "button_clear_completed": "נקה הושלמו",
        "button_clear_failed": "נקה נכשלו",
        "tooltip_open_file": "פתח את הקובץ שהורד (בחר הורדה שהושלמה)",
        "text_fetching": "טוען...",
        "msg_no_selection": "אין בחירה",
        "msg_select_download": "אנא בחר הורדה שהושלמה לפתיחה.",
        "msg_not_completed": "לא הושלם",
        "msg_not_completed_desc": "הורדה זו עדיין לא הושלמה.\nניתן לפתוח רק הורדות שהושלמו.",
        "msg_file_not_found": "קובץ לא נמצא",
        "msg_file_path_unknown": "לא ניתן לקבוע את נתיב הקובץ להורדה זו.",
        "msg_file_not_found_desc": "הקובץ שהורד לא נמצא",
        "msg_failed_open_file": "נכשל בפתיחת הקובץ",
        # History Tab
        "history_empty": "אין היסטוריית הורדות",
        "history_empty_hint": "הורדות יופיעו כאן לאחר השלמתן.",
        "history_statistics": "סטטיסטיקות",
        "history_download_history": "היסטוריית הורדות",
        "label_search": "חיפוש:",
        "placeholder_search_history": "חפש לפי כותרת או URL...",
        "col_datetime": "תאריך/שעה",
        "col_title": "כותרת",
        "col_size": "גודל",
        "button_refresh": "רענן",
        "button_export_csv": "ייצא CSV",
        "button_open_directory": "פתח תיקייה",
        "button_clear_all": "נקה הכל",
        "tooltip_open_downloads_dir": "פתח תיקיית הורדות במנהל הקבצים",
        "stat_total_downloads": 'סה"כ הורדות',
        "stat_cancelled": "בוטל",
        "stat_success_rate": "אחוז הצלחה",
        "stat_total_downloaded": 'סה"כ הורד',
        "stat_average_speed": "מהירות ממוצעת",
        "dialog_export_history": "ייצא היסטוריה",
        "filter_csv_files": "קבצי CSV (*.csv)",
        "msg_success": "הצלחה",
        "msg_history_exported": "היסטוריה יוצאה אל",
        "msg_export_failed": "נכשל לייצא היסטוריה",
        "dialog_confirm_clear": "אישור ניקוי",
        "dialog_confirm_clear_all": "אישור ניקוי הכל",
        "msg_clear_status_confirm": "לנקות את כל הורדות ה-{status} מהיסטוריה?",
        "msg_clear_all_confirm": "לנקות את כל היסטוריית ההורדות? לא ניתן לבטל פעולה זו!",
        "msg_cleared_entries": "נוקו {count} רשומות היסטוריה",
        "msg_dir_not_found": "תיקייה לא נמצאה",
        "msg_download_dir_not_exist": "תיקיית ההורדות לא קיימת",
        "msg_failed_open_dir": "נכשל לפתוח תיקייה",
        # Settings Tab
        "settings_general": "הגדרות כלליות",
        "settings_appearance": "מראה",
        "settings_download": "הגדרות הורדה",
        "settings_notifications": "התראות",
        "settings_language": "שפה",
        "settings_features": "תכונות",
        "settings_about": "אודות",
        "settings_version_info": "מידע גרסה",
        "label_default_folder": "תיקיית הורדה ברירת מחדל:",
        "label_default_quality": "איכות ברירת מחדל:",
        "label_language": "שפה:",
        "label_theme": "ערכת נושא:",
        "button_toggle_theme": "החלף ערכת נושא (כהה/בהיר)",
        "dialog_theme_switched": "ערכת נושא שונתה",
        "checkbox_notifications": "הפעל התראות שולחן עבודה",
        "checkbox_auto_update": "הודע לי על גרסאות חדשות בהפעלה",
        "tooltip_notifications": "הצג התראות שולחן עבודה לאירועי הורדה",
        "tooltip_auto_update": "בודק את GitHub בהפעלה ומציג הודעה אם זמינה גרסה חדשה. אינו מתקין באופן אוטומטי.",
        "button_check_update": "בדוק עדכונים כעת",
        "button_reset_defaults": "אפס לברירת מחדל",
        "button_save_settings": "שמור הגדרות",
        # Notifications
        "notif_download_complete": "ההורדה הושלמה",
        "notif_download_error": "שגיאת הורדה",
        "notif_batch_complete": "הורדה קבוצתית הושלמה",
        "notif_update_available": "עדכון זמין",
        # Update Dialog
        "update_title": "עדכון זמין",
        "update_message": "גרסה {version} זמינה!\n\nגרסה נוכחית: {current}\nגרסה חדשה: {new}\n\nהאם ברצונך להוריד את העדכון?",
        "update_download": "הורד עדכון",
        "update_later": "מאוחר יותר",
        "update_downloading": "מוריד עדכון",
        "update_installing": "מתקין עדכון",
        "update_success": "העדכון הצליח",
        "update_error": "שגיאת עדכון",
        # Video Info
        "info_title": "מידע על הסרטון",
        "info_duration": "משך:",
        "info_uploader": "מעלה:",
        "info_views": "צפיות:",
        "info_upload_date": "תאריך העלאה:",
        # Filter Dialog
        "filter_title": "מסננים להורדה",
        "filter_duration": "מסנן משך",
        "filter_min_duration": "משך מינימלי (שניות):",
        "filter_max_duration": "משך מקסימלי (שניות):",
        "filter_date": "מסנן תאריך",
        "filter_after_date": "לאחר תאריך:",
        "filter_before_date": "לפני תאריך:",
        "filter_keyword": "מסנן מילות מפתח",
        "filter_include_keywords": "כלול מילות מפתח:",
        "filter_exclude_keywords": "לא לכלול מילות מפתח:",
        "filter_apply": "החל מסננים",
        "filter_reset": "אפס מסננים",
        # Bandwidth Monitor
        "bandwidth_title": "מוניטור רוחב פס",
        "bandwidth_current_speed": "מהירות נוכחית:",
        "bandwidth_avg_speed": "מהירות ממוצעת:",
        "bandwidth_peak_speed": "מהירות שיא:",
        "bandwidth_total_downloaded": 'סה"כ הורדה:',
        # Status Messages
        "status_pending": "ממתין",
        "status_downloading": "מוריד...",
        "status_completed": "הושלם",
        "status_error": "שגיאה",
        "status_cancelled": "בוטל",
        "status_preparing": "מכין את ההורדה שלך...",
        "status_ready": "מוכן להורדה",
        "status_complete": "ההורדה הושלמה!",
        "status_success": "ההורדה הושלמה בהצלחה!",
        # Common
        "yes": "כן",
        "no": "לא",
        "ok": "אישור",
        "cancel": "ביטול",
        "close": "סגור",
        "error": "שגיאה",
        "warning": "אזהרה",
        "info": "מידע",
        # Additional Main Window
        "status_bar_ready": "מוכן",
        "tooltip_exit_application": "יציאה מהתוכנה",
        "menu_view": "תצוגה",
        "menu_toggle_theme": "החלף ערכת נושא (כהה/בהיר)",
        "tooltip_toggle_theme": "החלף בין ערכות נושא כהות ובהירות",
        "menu_keyboard_shortcuts": "קיצורי מקלדת",
        "tooltip_keyboard_shortcuts": "הצג קיצורי מקלדת",
        "dialog_about": "אודות",
        "dialog_download_in_progress": "הורדה מתבצעת",
        "msg_download_in_progress_exit": "הורדה מתבצעת כעת. האם אתה בטוח שברצונך לצאת?",
        "dialog_keyboard_shortcuts": "קיצורי מקלדת",
        "theme_dark": "כהה",
        "theme_light": "בהיר",
        "msg_theme_switched": "ערכת הנושא שונתה ל: {theme}",
        # Additional Download Tab
        "dialog_select_download_dir": "בחר תיקיית הורדה",
        "error_generic": "שגיאה",
        "msg_dir_not_exist": "התיקייה אינה קיימת:\n{directory}",
        "button_downloading": "מוריד...",
        "dialog_download_failed": "ההורדה נכשלה",
        "button_fetching": "טוען...",
        "button_fetching_playlist": "טוען פלייליסט...",
        "dialog_failed_fetch_video_info": "נכשל בטעינת מידע על הסרטון",
        "dialog_failed_fetch_playlist_info": "נכשל בטעינת מידע על הפלייליסט",
        "error_invalid_directory": "תיקייה לא תקינה",
        "dialog_playlist_detected": "פלייליסט זוהה",
        "msg_playlist_detected_options": "זה נראה כמו פלייליסט {platform}.\n\nהאם ברצונך לצפות ולבחור סרטונים ספציפיים?\n\nלחץ 'כן' לצפייה בפלייליסט, או 'לא' להוספת כתובת הפלייליסט המלאה ישירות.",
        "dialog_added_to_queue": "נוסף לתור",
        "msg_video_added_to_queue": "הסרטון נוסף לתור ההורדות במיקום {position}.\n\nעבור ללשונית התור לניטור התקדמות.",
        "dialog_download_complete": "ההורדה הושלמה",
        "msg_download_complete": "הסרטון הורד בהצלחה!\n\nנשמר ב: {filename}",
        "dialog_playlist_added_to_queue": "הפלייליסט נוסף לתור",
        "msg_playlist_added_to_queue": "נוספו {count} סרטונים לתור ההורדות בהצלחה.\n\nעבור ללשונית התור לניטור התקדמות.",
        "dialog_batch_added": "נוסף בקבוצה",
        "msg_batch_added_to_queue": "נוספו {count} כתובות URL לתור ההורדות בהצלחה.\n\nעבור ללשונית התור לניטור התקדמות.",
        # Batch Input Dialog
        "dialog_batch_url_input": "קלט קבוצתי של כתובות URL",
        "msg_batch_input_instructions": "הזן כתובות URL של סרטונים (אחת בכל שורה):\nניתן להדביק מספר כתובות או לייבא מקובץ טקסט.",
        "button_import_from_file": "ייבא מקובץ",
        "label_urls_count": "כתובות URL: {count}",
        "button_validate_urls": "אמת כתובות URL",
        "button_add_urls": "הוסף כתובות URL",
        "dialog_import_urls_from_file": "ייבא כתובות URL מקובץ",
        "dialog_import_error": "שגיאת ייבוא",
        "msg_failed_import_file": "נכשל בייבוא הקובץ:\n{error}",
        "msg_enter_at_least_one_url": "אנא הזן לפחות כתובת URL אחת.",
        "dialog_validation_results": "תוצאות אימות",
        "dialog_validation_successful": "האימות הצליח",
        "dialog_no_valid_urls": "אין כתובות URL תקינות",
        "msg_no_valid_urls_found": "לא נמצאו כתובות URL תקינות. אנא בדוק את הקלט שלך.",
        "dialog_invalid_urls_found": "נמצאו כתובות URL לא תקינות",
        # Filter Dialog
        "dialog_download_filters": "מסננים להורדה",
        "button_reset_filters": "אפס מסננים",
        "button_apply_filters": "החל מסננים",
        "group_duration_filter": "מסנן משך",
        "label_min_duration": "משך מינימלי (שניות):",
        "text_no_minimum": "ללא מינימום",
        "label_max_duration": "משך מקסימלי (שניות):",
        "text_no_maximum": "ללא מקסימום",
        "group_upload_date_filter": "מסנן תאריך העלאה",
        "label_uploaded_after": "הועלה לאחר:",
        "label_uploaded_before": "הועלה לפני:",
        "group_keyword_filter": "מסנן מילות מפתח",
        "label_include_keywords": "כלול מילות מפתח (מופרדות בפסיק):",
        "label_exclude_keywords": "אל תכלול מילות מפתח (מופרדות בפסיק):",
        # Settings Tab
        "dialog_select_default_download_dir": "בחר תיקיית הורדה ברירת מחדל",
        "dialog_settings_saved_restart_required": "הגדרות נשמרו - נדרש אתחול",
        "msg_language_changed_restart_required": "ההגדרות נשמרו בהצלחה!\n\nהשפה שונתה ל: {language}\n\n⚠️ אנא הפעל מחדש את התוכנה כדי שהשינוי ייכנס לתוקף.",
        "dialog_settings_saved": "הגדרות נשמרו",
        "msg_settings_saved": "ההגדרות נשמרו בהצלחה!",
        "msg_failed_save_settings": "נכשל בשמירת הגדרות. אנא בדוק את היומן לפרטים.",
        "dialog_reset_settings": "אפס הגדרות",
        "msg_confirm_reset_settings": "האם אתה בטוח שברצונך לאפס את כל ההגדרות לברירת המחדל?",
        "dialog_settings_reset": "הגדרות אופסו",
        "msg_all_settings_reset": "כל ההגדרות אופסו לברירת המחדל.",
        "button_checking": "בודק...",
        "dialog_no_updates": "אין עדכונים",
        "msg_already_latest_version": "אתה כבר משתמש בגרסה העדכנית ביותר ({version}).",
        "dialog_update_check_failed": "בדיקת עדכון נכשלה",
        "msg_update_check_failed": "לא ניתן לבדוק עדכונים:\n{error}\n\nאנא בדוק את חיבור האינטרנט שלך.",
        "button_check_for_updates_now": "בדוק עדכונים כעת",
        # Log Widget
        "placeholder_log_messages": "הודעות יומן יופיעו כאן...",
        # Video Info Dialog
        "dialog_video_information": "מידע על הסרטון",
        "group_thumbnail": "תמונה ממוזערת",
        "text_loading_thumbnail": "טוען תמונה...",
        "group_details": "פרטים",
        "label_channel": "ערוץ:",
        "label_duration": "משך:",
        "label_uploaded": "הועלה:",
        "label_views": "צפיות:",
        "label_likes": "לייקים:",
        "label_platform": "פלטפורמה:",
        "group_description": "תיאור",
        "button_close": "סגור",
        "text_no_thumbnail_available": "אין תמונה ממוזערת זמינה",
        "text_failed_load_thumbnail": "נכשל בטעינת תמונה ממוזערת",
        # Playlist Dialog
        "dialog_playlist_viewer": "מציג פלייליסט",
        "group_playlist_information": "מידע על הפלייליסט",
        "label_videos_count": "סרטונים: {count}",
        "button_select_all": "בחר הכל",
        "button_select_none": "בטל בחירה",
        "label_quality_playlist": "איכות:",
        "quality_best": "איכות מיטבית",
        "quality_1080p": "1080p (Full HD)",
        "quality_720p": "720p (HD)",
        "quality_480p": "480p (SD)",
        "quality_audio_only": "אודיו בלבד",
        "dialog_no_videos_selected": "לא נבחרו סרטונים",
        "msg_select_at_least_one_video": "אנא בחר לפחות סרטון אחד להורדה.",
        # Playlist Dialog - Subtitles section
        "group_playlist_subtitles": "כתוביות (עוקף את לשונית ההורדה)",
        "checkbox_playlist_download_subtitles": "הורד כתוביות לכל סרטון שנבחר",
        "label_playlist_subtitle_override_hint": "כשהאפשרות מבוטלת, הגדרות הכתוביות מלשונית ההורדה תקפות. כשהאפשרות מופעלת, רק השפות הנבחרות למטה יורדו עבור כל סרטון.",
        "tooltip_playlist_download_subtitles": "כשהאפשרות מופעלת, כל סרטון בפלייליסט יוריד כתוביות בשפות שייבחרו למטה.",
        "label_playlist_subtitle_languages": "שפות:",
        "checkbox_subtitle_lang_he": "עברית (he + iw)",
        "checkbox_subtitle_lang_en": "אנגלית (en)",
        "checkbox_subtitle_lang_ar": "ערבית (ar)",
        "checkbox_subtitle_lang_es": "ספרדית (es)",
        "checkbox_subtitle_lang_fr": "צרפתית (fr)",
        "checkbox_subtitle_lang_ru": "רוסית (ru)",
        "checkbox_subtitle_lang_de": "גרמנית (de)",
        "label_playlist_subtitle_other": "קודים נוספים:",
        "placeholder_playlist_subtitle_other": "לדוגמה: pt,it,zh-Hans",
        "tooltip_playlist_subtitle_other": "קודי שפה מופרדים בפסיק עבור שפות שאינן ברשימה למעלה.",
        "msg_playlist_no_subtitle_langs": "הורדת כתוביות מופעלת אך לא נבחרה אף שפה. סמן לפחות שפה אחת או בטל את תיבת הסימון של הכתוביות.",
        # Progress Bar
        "text_error_prefix": "שגיאה:",
        "label_size": "גודל:",
        "label_downloaded": "הורד:",
        "label_speed": "מהירות:",
        "label_eta": "זמן משוער:",
        "text_unknown": "--",
        # Bandwidth Widget
        "title_bandwidth_monitor": "מוניטור רוחב פס",
        "group_statistics": "סטטיסטיקות",
        "group_speed_graph": "גרף מהירות",
        # Video Player Widget
        "label_volume": "עוצמת קול:",
        "text_no_file_loaded": "לא נטען קובץ",
        "dialog_file_not_found": "קובץ לא נמצא",
        "msg_file_not_found_details": "לא ניתן למצוא קובץ:\n{file_path}",
        "dialog_playback_error": "שגיאת השמעה",
        "msg_error_playing_video": "שגיאה בהשמעת סרטון:\n{error}",
        # Update Dialog
        "dialog_update_available": "עדכון זמין",
        "text_version_available": "גרסה {version} זמינה!",
        "label_current_version": "גרסה נוכחית:",
        "label_new_version": "גרסה חדשה:",
        "label_release_notes": "הערות שחרור:",
        "text_no_release_notes": "אין הערות שחרור זמינות.",
        "button_view_on_github": "צפה ב-GitHub",
        "button_visit_website": "בקר באתר",
        "button_download_update": "הורד עדכון",
        "button_remind_me_later": "הזכר לי מאוחר יותר",
        "dialog_download_error": "שגיאת הורדה",
        "msg_no_download_url": "אין כתובת הורדה זמינה. אנא בקר ב-GitHub להורדה ידנית.",
        "dialog_confirm_download": "אשר הורדה",
        "msg_confirm_download_text": "זה יוריד את המתקין לתיקיית ההורדות שלך.\n\nקובץ: {filename}\nגודל: {size}\n\nההורדה תתחיל ברקע.\n\nהמשך?",
        "text_downloading_update": "מוריד עדכון...",
        "text_download_complete": "ההורדה הושלמה!",
        "text_download_failed": "ההורדה נכשלה!",
        "dialog_download_complete_update": "הורדה הושלמה",
        "dialog_installing_update": "מתקין עדכון",
        "msg_installer_confirmation": "המתקין הורד אל:\n{path}\n\nהאם ברצונך להפעיל את המתקין כעת?\n\nהתוכנה תיסגר כאשר תלחץ 'כן'.",
        "dialog_installer_error": "שגיאת התקנה",
        "button_skip_version": "דלג על גרסה זו",
        "text_unknown_size": "גודל לא ידוע",
        "text_download_verified": "ההורדה אומתה.",
        "msg_download_verified_install": "העדכון הורד ואומת בהצלחה.\n\nקובץ: {path}\n\nהאם ברצונך להפעיל את המתקין כעת?\n(פעולה זו תסגור את התוכנה.)",
        "msg_installer_saved": "המתקין המאומת נשמר אל:\n{path}\n\nתוכל להפעיל אותו מאוחר יותר כדי לעדכן את התוכנה.",
        "dialog_verify_failed": "האימות נכשל",
        "msg_verify_failed": "המתקין שהורד נכשל באימות התקינות ונמחק לשם בטיחותך.\n\nצפוי: {expected}\nבפועל: {actual}\n\nאנא נסה שוב, או הורד ידנית מ-GitHub.",
        "dialog_unverified_download": "הורדה לא מאומתת",
        "msg_unverified_download": "גרסה זו אינה מפרסמת סכום ביקורת, ולכן לא ניתן היה לאמת את ההורדה אוטומטית.\n\nהקובץ נשמר אל:\n{path}\n\nלשם בטיחותך הוא לא יופעל אוטומטית. הפעל אותו ידנית רק אם אתה סומך על המקור.",
        "msg_download_failed_retry": "הורדת העדכון נכשלה.\n\nאנא נסה שוב, או הורד ידנית מ-GitHub.",
        "msg_installer_launch_failed": "הפעלת המתקין נכשלה:\n{error}\n\nאנא הפעל אותו ידנית:\n{path}",
        "msg_update_check_rate_limited": "שרת העדכונים של GitHub מגביל בקשות. אנא נסה שוב מאוחר יותר.",
        # About Tab
        "label_bundled_ytdlp": "yt-dlp מובנה",
        "label_author": "מחבר",
        "label_credits": "קרדיטים",
        "text_credits_description": "אפליקציה זו בנויה באמצעות הפרוייקטים הקוד-פתוח הבאים:",
        "button_documentation": "תיעוד",
        # Keyboard Shortcuts
        "shortcuts_title": "קיצורי מקלדת",
        "shortcuts_general": "כללי",
        "shortcuts_download_tab": "לשונית הורדה",
        "shortcuts_queue_tab": "לשונית תור",
        "shortcut_quit_app": "יציאה מהתוכנה",
        "shortcut_show_help": "הצג עזרה זו",
        "shortcut_close_dialogs": "סגור חלונות דו-שיח",
        "shortcut_paste_url": "הדבק URL מהלוח",
        "shortcut_start_download": "התחל הורדה (כאשר שדה URL ממוקד)",
        "shortcut_show_video_info": "הצג מידע על הסרטון",
        "shortcut_download_now": "הורד כעת",
        "shortcut_add_to_queue": "הוסף לתור",
        "shortcut_remove_task": "הסר משימה שנבחרה",
        "shortcut_move_task_up": "הזז משימה למעלה",
        "shortcut_move_task_down": "הזז משימה למטה",
        # v2.1.0 - תכונות חדשות
        "button_select_subs": "בחר כתוביות...",
        "checkbox_metadata": "הורד מטא-דאטה",
        "checkbox_comments": "הורד תגובות",
        "tooltip_select_subs": "עיין בכתוביות הזמינות ובחר אילו להוריד",
        "tooltip_metadata": "הורד מטא-דאטה של הסרטון (תיאור, info.json, הערות)",
        "tooltip_comments": "הורד תגובות הסרטון לקובץ .txt נפרד (עשוי להיות איטי עבור סרטונים פופולריים)",
        "subtitle_header_most_used": "──── הנפוצים ביותר ────",
        "subtitle_header_all": "──── כל השפות ────",
        "subtitle_type_manual": "ידני",
        "subtitle_type_auto": "מופק אוטומטית",
        "subtitle_type_both": "ידני ואוטומטי",
        "subtitle_select_all_visible": "בחר את כל הנראים",
        "subtitle_search_placeholder": "הקלד לסינון שפות (לדוגמה: 'spanish', 'es', 'עברית')...",
        "subtitle_search_label": "חיפוש:",
        "subtitle_pinned_languages": "בחר שפות כתוביות (אנגלית ועברית מוצמדות למעלה):",
        "subtitle_no_available": "אין כתוביות זמינות לסרטון זה",
        "subtitle_fetching_info": "מביא מידע על כתוביות...",
        "button_loading": "טוען...",
        "button_download_selected": "הורד את הנבחרים",
        "button_cancel": "ביטול",
        "button_retry": "נסה שוב",
        "no_selection_title": "לא נבחר",
        "no_selection_msg": "אנא בחר לפחות שפת כתוביות אחת, או לחץ על ביטול.",
        "error_fetch_subs": "לא ניתן לקבל מידע על הסרטון. אנא בדוק את הכתובת ונסה שוב.",
        "no_subs_title": "אין כתוביות",
        "no_subs_msg": "לסרטון זה אין כתוביות זמינות.",
    },
}


class TranslationManager:
    """
    Manages translations and language switching.

    Automatically detects system language and provides RTL support for Hebrew.
    """

    def __init__(self):
        """Initialize TranslationManager with auto-detected language."""
        self.current_language = self._detect_system_language()
        logger.info(f"Translation system initialized with language: {self.current_language}")

    def _detect_system_language(self) -> str:
        """
        Detect system language.

        First checks for saved language preference, then falls back to system locale.

        Returns:
            Language code ("en" or "he")
        """
        # Check for saved language preference (v1.7.0)
        try:
            import json
            from pathlib import Path

            config_dir = Path.home() / ".yt-dlp-studio"
            language_file = config_dir / "language.json"

            if language_file.exists():
                with open(language_file, encoding="utf-8") as f:
                    data = json.load(f)
                    saved_lang = data.get("language")
                    if saved_lang in ["en", "he"]:
                        logger.info(f"Loaded saved language preference: {saved_lang}")
                        return saved_lang
        except Exception as e:
            logger.debug(f"No saved language preference found: {e}")

        # Fall back to system locale detection
        try:
            # Get system locale
            system_locale = locale.getdefaultlocale()[0]

            if system_locale:
                lang_code = system_locale.split("_")[0].lower()

                # Check if Hebrew
                if lang_code == "he" or lang_code == "iw":  # iw is old Hebrew code
                    logger.info("Detected Hebrew system language")
                    return "he"

            # Default to English
            logger.info("Defaulting to English language")
            return "en"

        except Exception as e:
            logger.warning(f"Could not detect system language: {e}, defaulting to English")
            return "en"

    def set_language(self, language_code: str):
        """
        Set the current language.

        Args:
            language_code: Language code ("en" or "he")
        """
        if language_code in TRANSLATIONS:
            self.current_language = language_code
            logger.info(f"Language set to: {language_code}")
        else:
            logger.warning(f"Unknown language code: {language_code}, keeping current language")

    def get_language(self) -> str:
        """
        Get current language code.

        Returns:
            Current language code
        """
        return self.current_language

    def is_rtl(self) -> bool:
        """
        Check if current language is RTL (Right-to-Left).

        Returns:
            True if RTL (Hebrew), False otherwise
        """
        return self.current_language == "he"

    def translate(self, key: str, **kwargs) -> str:
        """
        Get translated string for key.

        Args:
            key: Translation key
            **kwargs: Format parameters for string formatting

        Returns:
            Translated string with format parameters applied

        Example:
            >>> tm = TranslationManager()
            >>> tm.translate("batch_count", count=5)
            "URLs: 5"
        """
        try:
            text = TRANSLATIONS[self.current_language].get(key, key)

            # Apply formatting if kwargs provided
            if kwargs:
                text = text.format(**kwargs)

            return text
        except Exception as e:
            logger.warning(f"Translation error for key '{key}': {e}")
            return key

    def get_available_languages(self) -> dict[str, str]:
        """
        Get list of available languages.

        Returns:
            Dict mapping language codes to display names
        """
        return {"en": "English / אנגלית", "he": "עברית / Hebrew"}

    def get_language_name(self, language_code: str) -> str:
        """
        Get display name for language code.

        Args:
            language_code: Language code

        Returns:
            Display name
        """
        return self.get_available_languages().get(language_code, language_code)


# Global translation manager instance
_translation_manager = None


def get_translation_manager() -> TranslationManager:
    """
    Get global TranslationManager instance.

    Returns:
        TranslationManager instance
    """
    global _translation_manager
    if _translation_manager is None:
        _translation_manager = TranslationManager()
    return _translation_manager


def tr(key: str, **kwargs) -> str:
    """
    Shorthand function for translation.

    Args:
        key: Translation key
        **kwargs: Format parameters

    Returns:
        Translated string

    Example:
        >>> from src.utils.translations import tr
        >>> label = tr("label_url")
    """
    return get_translation_manager().translate(key, **kwargs)
