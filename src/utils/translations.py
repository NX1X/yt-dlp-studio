"""
Multi-Language Translation System for YT-DLP Studio.

Supports Hebrew and English with automatic language detection.
Includes RTL (Right-to-Left) support for Hebrew.
"""

import json
import locale
from pathlib import Path

from ..utils.constants import APP_DATA_DIR
from ..utils.file_formats import LANGUAGE_FORMAT, load_json_file, save_json_file
from ..utils.logger import get_logger

logger = get_logger()


# Translation dictionaries
TRANSLATIONS = {
    "en": {
        # Tabs
        "tab_download": "Download",
        "tab_queue": "Queue",
        "tab_history": "History",
        "tab_settings": "Settings",
        "tab_about": "About",
        # Download Tab
        "label_url": "URL:",
        "download_url_placeholder": "Enter YouTube URL or drag & drop here...",
        "label_quality": "Quality:",
        "label_save_to": "Save to:",
        "button_browse": "Browse",
        "button_download_now": "Download Now",
        "button_add_to_queue": "Add to Queue",
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
        "text_unlimited": "Unlimited",
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
        # tooltip_select_subs lives lower in this dict; do not redeclare here.
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
        "batch_count": "URLs: {count}",
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
        # Settings tab - Advanced Download Options (0.5.0)
        "settings_advanced_download": "Advanced Download Options",
        "button_show_advanced_download": "Show Advanced Download Options",
        "button_hide_advanced_download": "Hide Advanced Download Options",
        "tooltip_toggle_advanced_download": "Browser cookies, proxy, file names and format options",
        "label_cookies_browser": "Use cookies from:",
        "cookies_browser_none": "None",
        "tooltip_cookies_browser": (
            "Read the cookies of a browser, so that private and age-restricted videos can be downloaded. "
            "Sign in to the site in that browser first."
        ),
        "label_cookies_profile": "Browser profile:",
        "placeholder_cookies_profile": "Optional: profile name or folder",
        "tooltip_cookies_profile": "Leave empty to use the default profile of the browser.",
        "text_cookies_privacy": (
            "Cookies stay on this computer. The app reads them only to give them to yt-dlp for the download. "
            "It does not save them or write them to the log."
        ),
        "label_proxy": "Proxy:",
        "placeholder_proxy": "socks5://host:1080 (empty = no proxy)",
        "tooltip_proxy": (
            "Used for downloads and for video, subtitle and playlist info. Supported types: http, https, "
            "socks5 and socks5h. A user name and password in the address are saved in the settings file, "
            "but never written to the log."
        ),
        "label_filename_template": "File name:",
        "filename_preset_title_quality": "Title_Quality (default)",
        "filename_preset_uploader_title": "Uploader - Title",
        "filename_preset_date_title": "Date - Title",
        "filename_preset_custom": "Custom template",
        "tooltip_filename_template": "How downloaded files are named. A number such as (1) is added if the file exists.",
        "label_custom_template": "Custom template:",
        "placeholder_custom_template": "%(title)s [%(id)s].%(ext)s",
        "tooltip_custom_template": (
            "A yt-dlp output template. It must end with .%(ext)s and must be a file name only, without folders."
        ),
        "label_video_codec": "Video codec:",
        "label_audio_codec": "Audio codec:",
        "codec_any": "Any",
        "tooltip_video_codec": (
            "Prefer this video codec when the site has it. To get it, the download can use a lower "
            "resolution, within the chosen quality."
        ),
        "tooltip_audio_codec": (
            "Prefer this audio codec for video downloads. Audio-only downloads use the audio format "
            "from the Download tab."
        ),
        "label_custom_format": "Custom format:",
        "placeholder_custom_format": "Example: bestvideo[height<=720]+bestaudio",
        "tooltip_custom_format": (
            "A yt-dlp format string for advanced users. When set, it replaces the quality and codec choices."
        ),
        "text_advanced_applies": "These settings apply to downloads that start after you save.",
        "error_invalid_advanced_settings": "Invalid Advanced Download Setting",
        "error_proxy_invalid": (
            "The proxy address is not valid. Use the form type://host:port, for example socks5://127.0.0.1:1080."
        ),
        "error_proxy_scheme": "This proxy type is not supported. Use http, https, socks5 or socks5h.",
        "error_cookies_profile": "The browser profile is not valid. Use a profile name or folder of at most 260 characters.",
        "error_template_empty": "The custom file name template is empty.",
        "error_template_too_long": "The custom file name template is too long. Use at most 200 characters.",
        "error_template_invalid_char": (
            "The custom file name template has a character that is not allowed in file names "
            '(< > : " | ? * $ or a control character).'
        ),
        "error_template_path": (
            'The custom file name template must be a file name only: no folders, "..", drive letters or absolute paths.'
        ),
        "error_template_ext": "The custom file name template must end with .%(ext)s.",
        "error_template_field_syntax": (
            "The custom file name template has a field that is not written correctly. Write a field as "
            "%(name)s, and a percent sign as %%."
        ),
        "error_template_unknown_field": (
            "The custom file name template uses a field that the app does not support. Use fields such as "
            "title, id, uploader, upload_date or height."
        ),
        "error_format_too_long": "The custom format is too long. Use at most 500 characters.",
        "error_format_invalid_char": "The custom format must be one line, without control characters.",
        "error_format_syntax": "yt-dlp cannot read the custom format. Check the brackets and parentheses.",
        "cookies_error_app_bound": (
            "Could not read the cookies from {browser}. Chrome 127 and later (and some other Chromium-based "
            "browsers) protect their cookies with app-bound encryption, which yt-dlp cannot read. Use Firefox "
            "for cookies, or set the cookie option in Settings to None."
        ),
        "cookies_error_locked": (
            "Could not read the cookies from {browser}, because {browser} keeps its cookie database locked. "
            "Close {browser} completely, then try again."
        ),
        "cookies_error_not_found": (
            "No cookies from {browser} were found. Make sure that {browser} is installed, and check the "
            "browser profile in Settings."
        ),
        "cookies_error_generic": "Could not read the cookies from {browser}. The log file has the details.",
        "cookies_hint_sign_in": (
            "This video needs a signed-in account (for example a private or age-restricted video). Sign in to "
            'the site in your browser. Then, in Settings > Advanced Download Options, set "Use cookies from" '
            "to that browser."
        ),
        "cookies_hint_signed_in_browser": (
            "The site still asks you to sign in. Make sure that you are signed in to the site in {browser}, "
            "with the profile set in Settings, then try again."
        ),
        "proxy_error_connect": (
            "Could not connect through the proxy. Check the proxy address in Settings > Advanced Download Options."
        ),
        "error_no_video_in_post": ("This post has no video. Downloading photo posts is planned for a later version."),
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
        "text_about_developer_intro": "This tool is part of <b>NXTools</b> - a collection of productivity tools.",
        "label_website": "Website:",
        # button_view_on_github lives lower in this dict; do not redeclare here.
        "tooltip_view_on_github": "Open the project repository in your browser",
        "header_credits_core_deps": "Core dependencies",
        "header_credits_dev_framework": "Development framework",
        "header_credits_build_dist": "Build &amp; distribution",
        "text_credits_thanks": "Thank you to all the developers and contributors of these open-source projects. This application would not be possible without your work.",
        "text_ffmpeg_not_found": "Not found in PATH",
        "text_ffmpeg_unknown": "Installed (version unknown)",
        "text_ffmpeg_error": "Error detecting version",
        "text_ffmpeg_checking": "Checking...",
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
        "button_retry_all_failed": "Retry All Failed",
        "tooltip_retry_all_failed": "Retry every failed download in the queue",
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
        "msg_clear_status_confirm": 'Clear all downloads with status "{status}" from history?',
        "msg_clear_all_confirm": "Clear ALL download history? This cannot be undone!",
        "msg_cleared_entries": "Cleared {count} history entries",
        "msg_dir_not_found": "Directory Not Found",
        "msg_download_dir_not_exist": "The download directory does not exist",
        "msg_failed_open_dir": "Failed to open directory",
        # Settings Tab
        "settings_general": "General Settings",
        "settings_appearance": "Appearance",
        "settings_features": "Features",
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
        "notif_download_complete_msg": "Download completed",
        "notif_download_complete_msg_size": "Download completed ({size})",
        "notif_download_error_msg": "Download failed",
        "notif_download_error_msg_reason": "Download failed: {error}",
        "notif_batch_completed_count": "Completed: {successful}/{total}",
        "notif_batch_failed_count": "Failed: {failed}",
        "notif_update_available_msg": "Version {version} is available.",
        # System Tray
        "tray_show_window": "Show Window",
        "tray_quit": "Quit",
        "checkbox_close_to_tray": "Keep running in the tray when I close the window",
        "tooltip_close_to_tray": "Closing the window hides it to the system tray. Downloads keep running. Use Quit in the tray menu to exit.",
        "tooltip_close_to_tray_unavailable": "Your desktop has no system tray, so this option is not available.",
        "tray_still_running": "Still running in the tray. Downloads keep going. Use Quit in the tray menu to exit.",
        "tray_tooltip_busy": "{app} - {active} downloading, {pending} waiting",
        # Status Messages
        "status_pending": "Pending",
        "status_downloading": "Downloading...",
        "status_completed": "Completed",
        "status_error": "Error",
        "status_cancelled": "Cancelled",
        "status_failed": "Failed",
        "status_preparing": "Preparing your download...",
        "status_ready": "Ready to download",
        "status_complete": "Download complete!",
        "status_success": "Download completed successfully!",
        # Common
        "yes": "Yes",
        "no": "No",
        "cancel": "Cancel",
        "error": "Error",
        "warning": "Warning",
        "info": "Information",
        # Additional Main Window
        "status_bar_ready": "Ready",
        "tooltip_toggle_theme": "Switch between Dark and Light themes",
        "dialog_download_in_progress": "Download in Progress",
        "msg_download_in_progress_exit": "A download is currently in progress. Are you sure you want to exit?",
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
        "msg_confirm_download_text": "This will download the update to your Downloads folder.\n\nFile: {filename}\nSize: {size}\n\nThe download runs in the background.\n\nContinue?",
        "text_downloading_update": "Downloading update...",
        "text_download_failed": "Download failed!",
        "dialog_download_complete_update": "Download Complete",
        "dialog_installer_error": "Installer Error",
        "button_skip_version": "Skip This Version",
        "text_unknown_size": "Unknown size",
        "text_download_verified": "Download verified.",
        "msg_download_verified_reveal": "Update downloaded and verified successfully.\n\nFile: {path}\n\nOpen the download folder now? Extract the archive and run install.sh to update.",
        "msg_download_verified_reveal_package": "Update downloaded and verified successfully.\n\nFile: {path}\n\nOpen the download folder now? Open the package with your software installer to update. Your settings and history are kept.",
        "msg_download_verified_reveal_appimage": "Update downloaded and verified successfully.\n\nFile: {path}\n\nOpen the download folder now? Make the new AppImage executable and start it. You can delete the old AppImage afterwards.",
        "msg_installer_saved": "The verified installer has been saved to:\n{path}\n\nYou can run it later to update the application.",
        "msg_update_install_restart": "The update is downloaded and verified.\n\nInstall it now? YT-DLP Studio closes, installs version {version} and starts again. Your settings and history are kept.",
        "msg_portable_update_ready": "The new version is downloaded and verified:\n{path}\n\nThis is a portable copy. It runs from where it is saved and does not replace the copy you are using now.\n\nStart the new version now? This copy closes. You can delete it afterwards.",
        "msg_portable_update_saved": "The new version is saved at:\n{path}\n\nStart it from there when you are ready. It does not replace the copy you are using now.",
        "dialog_verify_failed": "Verification Failed",
        "msg_verify_failed": "The downloaded installer failed integrity verification and was deleted for your safety.\n\nExpected: {expected}\nActual: {actual}\n\nPlease try again, or download manually from GitHub.",
        "dialog_unverified_download": "Unverified Download",
        "msg_unverified_download": "This release does not publish a checksum, so the download could not be verified automatically.\n\nThe file was saved to:\n{path}\n\nFor your safety it will not be launched automatically. Only run it manually if you trust the source.",
        "msg_download_failed_retry": "Failed to download the update.\n\nPlease try again, or download manually from GitHub.",
        "msg_installer_launch_failed": "Failed to run the installer:\n{error}\n\nPlease run it manually:\n{path}",
        "msg_update_check_rate_limited": "GitHub's update server is rate-limiting requests. Please try again later.",
        # About Tab
        "label_credits": "Credits",
        "text_credits_description": "This application is built using the following open-source projects:",
        # Site tiers (label next to the URL field)
        "site_tier_tested": "Tested site",
        "site_tier_experimental": "Experimental site: may not work",
        "tooltip_site_tier_tested": (
            "YT-DLP Studio checks downloads from YouTube, Instagram, TikTok, Facebook and X before every release."
        ),
        "tooltip_site_tier_experimental": (
            "YT-DLP Studio does not test this site. yt-dlp may support it, so the download can work, "
            "but it can also fail. You can still download."
        ),
        # Keyboard Shortcuts
        "shortcuts_title": "Keyboard Shortcuts",
        "shortcuts_general": "General",
        "shortcuts_download_tab": "Download Tab",
        "shortcuts_queue_tab": "Queue Tab",
        "shortcut_quit_app": "Quit application",
        "shortcut_show_help": "Open the online help",
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
        "tooltip_metadata": "Download video metadata (description, info.json)",
        "tooltip_comments": "Download video comments to a separate .txt file (may be slow for popular videos)",
        "button_cancel": "Cancel",
        "button_retry": "Retry",
        # --- UI overhaul A ---
        # Settings tab
        "settings_downloads": "Downloads",
        "settings_behavior": "Behavior",
        "settings_bug_report_files": "Files for bug reports",
        "label_language_restart_hint": "Restart the app to apply a language change.",
        "tooltip_theme_combo": "Applies at once and is saved",
        "button_settings_open_folder": "Open folder",
        "tooltip_settings_open_folder": "Open the folder in the file manager",
        "status_settings_saved": "Settings saved.",
        # About tab
        "about_tagline": "A desktop app for yt-dlp: download video and audio from YouTube and many other sites.",
        "button_copy_bug_report": "Copy for bug report",
        "tooltip_copy_bug_report": "Copy the versions above and your system details, to paste into a bug report",
        "msg_bug_report_copied": "System information copied. Paste it into your bug report.",
        "label_license": "License:",
        # Update dialog
        "text_update_download_progress": "Downloading: {done} of {total} ({percent})",
        # Subtitle dialog
        "dialog_select_subtitle_languages": "Choose subtitle languages",
        "text_subtitle_dialog_help": "Check the subtitle languages to download. Some may be auto-generated.",
        "group_subtitle_languages": "Subtitle languages",
        "placeholder_filter_languages": "Type to filter languages...",
        "text_auto_generated": "auto-generated",
        "button_use_selected_languages": "Use selected languages",
        "dialog_no_subtitles_selected": "No subtitles selected",
        "msg_continue_without_subtitles": "You did not select a subtitle language.\n\nContinue without subtitles?",
        # Batch dialog
        "button_clear": "Clear",
        "dialog_no_urls": "No URLs",
        "label_batch_counts": "Valid URLs: {valid}    Invalid lines: {invalid}",
        "msg_validation_invalid_lines": "{valid} valid URLs, {invalid} invalid lines:",
        "text_line_number": "Line {line}: {text}",
        "text_and_more": "... and {count} more",
        "msg_all_urls_valid": "All {count} URLs are valid.",
        "msg_proceed_with_valid_urls": "Found {valid} valid URLs and {invalid} invalid lines.\n\nAdd only the valid URLs?",
        # Playlist dialog
        "label_uploader": "Uploader",
        "label_selected_count": "{selected} of {total} selected",
        "button_add_videos_to_queue": "Add to queue ({count})",
        # Download error dialog
        "header_error_suggestions": "Suggestions:",
        "header_error_technical_details": "Technical details:",
        "button_copy_details": "Copy details",
        "text_copied": "Copied",
        # --- end UI overhaul A ---
        # --- UI overhaul B ---
        # Download tab
        "label_link": "Link",
        "placeholder_link": "Paste a video or playlist link (YouTube and many other sites)",
        "button_info": "Info",
        "tooltip_info": "Show the title, length and formats of the link without downloading (Ctrl+Shift+I)",
        "label_get": "Get",
        "label_quality_short": "Quality",
        "label_format": "Format",
        "label_save_to_short": "Save to",
        "action_open_folder": "Open folder",
        "section_more_options": "More options",
        "more_options_default": "All off, no speed limit",
        "summary_subtitles": "Subtitles ({langs})",
        "summary_metadata": "Metadata",
        "summary_speed_limit": "Speed limit {speed}",
        "checkbox_subtitles_short": "Subtitles",
        "label_languages": "Languages",
        "button_choose_subs": "Choose...",
        "checkbox_thumbnail_short": "Thumbnail",
        "checkbox_metadata_short": "Metadata (description, info.json)",
        "checkbox_comments_short": "Comments",
        "label_speed_limit_short": "Speed limit",
        "text_advanced_in_settings": "Browser cookies, proxy, file names and format options are in the Settings tab.",
        "button_open_settings": "Open Settings",
        "button_batch_links": "Batch links...",
        "button_add_to_queue_short": "Add to queue",
        "button_download": "Download",
        "tooltip_download_button": "Download this link now (Enter or Ctrl+D). It starts at once, also when the queue is paused. If the maximum number of downloads already runs, it starts next.",
        "tooltip_add_to_queue_button": "Add this link to the end of the queue (Ctrl+Shift+Q). It waits its turn and does not start while the queue is paused.",
        "error_link_empty": "Paste a link first.",
        "error_link_invalid": "This is not a valid link. A link starts with {http} or {https}.",
        "error_folder_invalid": "This folder does not exist or is not writable. Choose another folder with Browse.",
        "status_download_started": "Download started.",
        "status_download_next": "The download starts as soon as a running download finishes.",
        "status_added_to_queue": "Added to the queue at position {position}.",
        "status_added_paused": "Added to the queue at position {position}. The queue is paused: press Start in the Queue tab.",
        "status_videos_added": "Added {count} videos to the queue.",
        "status_batch_added": "Added {count} links to the queue.",
        "msg_playlist_choice": "This link is a {platform} playlist.\n\nChoose videos to pick the ones you want, or add the whole playlist as one download.",
        "button_choose_videos": "Choose videos...",
        "button_whole_playlist": "Whole playlist",
        "section_activity_log": "Activity log",
        # Now downloading panel
        "group_now_downloading": "Now downloading",
        "now_empty": "Nothing is downloading. Paste a link above to start.",
        "now_empty_paused": "Nothing is downloading. The queue is paused, {count} waiting.",
        "now_starting": "Starting...",
        "now_processing": "Processing...",
        "now_time_left": "{time} left",
        "now_progress_accessible": "{title}: {percent}",
        "button_open_queue": "Open queue",
        "tooltip_open_queue": "Go to the Queue tab",
        "summary_downloading": "{count} downloading",
        "summary_waiting": "{count} waiting",
        "summary_failed": "{count} failed",
        "summary_done": "{count} done",
        "summary_paused": "queue paused",
        "summary_queue_empty": "The queue is empty",
        # Status bar
        "status_bar_idle": "Idle",
        "status_bar_downloading": "Downloading {active} of {total}",
        "status_bar_paused": "Queue paused, {count} waiting",
        # Queue tab
        "button_start": "Start",
        "button_pause": "Pause",
        "button_stop_all_short": "Stop all",
        "tooltip_start_queue": "Start the waiting downloads. New links then start on their own.",
        "tooltip_pause_queue": "Let the running downloads finish, but start no new ones. Use Start to continue.",
        "tooltip_stop_all": "Cancel the running downloads and pause the queue. Waiting downloads stay in the queue.",
        "dialog_stop_all": "Stop all downloads?",
        "msg_stop_all_confirm": "Downloads running: {count}.\n\nCancel them and pause the queue?",
        "col_time_left": "Time left",
        "action_open_file": "Open file",
        "tooltip_open_task_folder": "Open the folder of the selected download",
        "tooltip_retry_task": "Try the selected failed download again",
        "tooltip_cancel_task": "Cancel the selected download. A waiting download is removed.",
        "button_move_up_short": "Up",
        "button_move_down_short": "Down",
        "tooltip_move_up": "Move the selected download up (Ctrl+Up)",
        "tooltip_move_down": "Move the selected download down (Ctrl+Down)",
        "tooltip_remove_task": "Remove the selected download from the queue (Delete)",
        "button_retry_failed": "Retry failed",
        "button_clear_finished": "Clear finished",
        "tooltip_clear_finished": "Remove finished downloads from the queue. The files stay on disk.",
        "menu_clear_completed": "Completed downloads",
        "menu_clear_failed": "Failed downloads",
        "menu_clear_cancelled": "Cancelled downloads",
        "menu_copy_link": "Copy link",
        "menu_show_error": "Show error details",
        "dialog_remove_task": "Remove download?",
        "msg_remove_downloading": "This download is running. Cancel it and remove it from the queue?",
        "msg_remove_waiting": "Remove this waiting download from the queue?",
        "status_removing": "Cancelling the download. It leaves the queue when it has stopped.",
        "status_removed": "Removed from the queue.",
        "status_cleared_tasks": "Removed {count} downloads from the queue.",
        "status_retrying": "Trying {count} downloads again.",
        "status_link_copied": "Link copied.",
        "tooltip_queue_task": "{title}\nLink: {url}\nFolder: {folder}\nQuality: {quality}",
        "text_title_unknown": "Title not known yet",
        "tooltip_task_failed": "{reason}\nDouble-click or right-click for details.",
        "tooltip_waiting_paused": "Waiting. The queue is paused.",
        "button_go_to_download": "Go to Download",
        # History tab
        "history_summary": "{total} downloads: {done} done, {failed} failed, {cancelled} cancelled, {size} in total",
        "history_summary_tooltip": "Success rate: {rate}\nAverage speed: {speed}",
        "placeholder_search_title_link": "Search title or link...",
        "filter_status": "Status filter",
        "filter_all_statuses": "All statuses",
        "history_no_matches": "No matches",
        "history_no_matches_hint": "Try another search word or status.",
        "tooltip_history_link": "Link: {url}",
        "tooltip_history_error": "Error: {reason}",
        "menu_download_again": "Download again",
        "button_open_downloads_folder": "Open downloads folder",
        "button_clear_menu": "Clear",
        "tooltip_clear_history": "Remove entries from the history. Downloaded files stay on disk.",
        "menu_clear_history_completed": "Clear completed",
        "menu_clear_history_failed": "Clear failed",
        "menu_clear_history_all": "Clear all history",
        "status_history_exported": "History saved to {path}.",
        "status_history_cleared": "Removed {count} entries from the history.",
        "status_link_in_download_tab": "The link is in the Download tab. Check the options, then press Download.",
        # Video and audio format names (Download tab)
        "format_video_mp4": "MP4 (Best Compatibility)",
        "format_video_mkv": "MKV (Matroska)",
        "format_video_webm": "WebM",
        "format_video_auto": "Auto (Best Quality)",
        "format_audio_mp3": "MP3 (Most Compatible)",
        "format_audio_m4a": "M4A/AAC (High Quality)",
        "format_audio_opus": "OPUS (Best Quality/Size)",
        "format_audio_flac": "FLAC (Lossless)",
        "format_audio_wav": "WAV (Uncompressed)",
        "format_audio_vorbis": "Vorbis/OGG",
        # Activity log lines (Download tab)
        "log_started": "Started: {title}",
        "log_finished": "Finished: {filename}",
        "log_stopped": "Stopped: {error}",
        "log_pasted": "Pasted from clipboard: {text}...",
        "log_auto_detected_url": "Auto-detected URL from clipboard",
        "log_mode_audio": "Audio-only mode: select quality and format",
        "log_mode_video": "Video mode: select quality and format",
        "log_quality_selected": "Quality selected: {quality} - {description}",
        "log_output_dir_changed": "Output directory changed to: {directory}",
        "log_opened_dir": "Opened directory: {directory}",
        "log_added_to_queue": "Added to queue at position {position}: {url}",
        "log_already_fetching_video": "Already fetching video info, please wait...",
        "log_already_fetching_playlist": "Already fetching playlist info, please wait...",
        "log_fetching_video_info": "Fetching video info: {url}",
        "log_detected_playlist": "Detected {platform} playlist, fetching info...",
        "log_video_info_fetched": "Video info fetched: {title}",
        "log_video_info_failed": "Failed to fetch video info: {error}",
        "log_playlist_fetched": "Playlist fetched: {title} ({count} videos)",
        "log_playlist_fetched_one": "Playlist fetched: {title} (1 video)",
        "log_playlist_failed": "Failed to fetch playlist info: {error}",
        "log_no_videos_selected": "No videos selected from playlist",
        "log_added_videos": "Added {count} videos to queue",
        "log_added_videos_one": "Added 1 video to queue",
        "log_added_videos_subs": "Added {count} videos to queue (subtitles: {langs})",
        "log_added_videos_subs_one": "Added 1 video to queue (subtitles: {langs})",
        "log_fetching_subs": "Fetching available subtitles for: {url}",
        "log_no_subs_found": "No subtitles found for this video",
        "log_selected_subs": "Selected {count} subtitle languages: {langs}",
        "log_selected_subs_one": "Selected 1 subtitle language: {langs}",
        "log_no_subs_selected": "No subtitles selected",
        "log_batch_added": "Batch: Added {count} URLs to queue",
        "log_batch_added_one": "Batch: Added 1 URL to queue",
        "log_url_dropped": "URL dropped: {text}...",
        "log_level_error": "ERROR",
        "log_level_success": "SUCCESS",
        "log_level_info": "INFO",
        "log_level_warning": "WARNING",
        # Singular forms for texts with a number (see tr_count)
        "summary_waiting_one": "{count} waiting",
        "summary_failed_one": "{count} failed",
        "summary_done_one": "{count} done",
        "status_bar_paused_one": "Queue paused, {count} waiting",
        "now_empty_paused_one": "Nothing is downloading. The queue is paused, {count} waiting.",
        "status_cleared_tasks_one": "Removed {count} download from the queue.",
        "status_retrying_one": "Trying {count} download again.",
        "status_history_cleared_one": "Removed {count} entry from the history.",
        "msg_all_urls_valid_one": "The URL is valid.",
        "status_videos_added_one": "Added {count} video to the queue.",
        "status_batch_added_one": "Added {count} link to the queue.",
        "history_summary_one": "{total} download: {done} done, {failed} failed, {cancelled} cancelled, {size} in total",
        # Download error texts (ErrorHandler)
        "errcat_network_title": "Network Error",
        "errcat_network_message": "Unable to connect to the internet or the video server.",
        "errcat_network_suggestions": "• Check your internet connection\n• Verify the URL is accessible in your browser\n• Try again in a few moments\n• Check if a firewall or VPN is blocking access",
        "errcat_url_invalid_title": "Invalid URL",
        "errcat_url_invalid_message": "The URL you entered is not valid or not supported.",
        "errcat_url_invalid_suggestions": "• Make sure you copied the complete URL\n• Check if the URL starts with http:// or https://\n• Verify the site is supported by yt-dlp\n• Try clicking 'Show Info' to test the URL first",
        "errcat_video_unavailable_title": "Video Unavailable",
        "errcat_video_unavailable_message": "The video is no longer available or doesn't exist.",
        "errcat_video_unavailable_suggestions": "• The video may have been deleted by the uploader\n• The URL might be incorrect or expired\n• Try refreshing the page in your browser\n• Check if the video is still accessible online",
        "errcat_geo_blocked_title": "Geo-Restricted Content",
        "errcat_geo_blocked_message": "This video is not available in your region.",
        "errcat_geo_blocked_suggestions": "• The video may be restricted to certain countries\n• You might need a VPN to access this content\n• Check if the video is available in your browser\n• Try a different video or source",
        "errcat_copyright_title": "Copyright Restriction",
        "errcat_copyright_message": "This video has been removed due to copyright claims.",
        "errcat_copyright_suggestions": "• The video violated copyright or terms of service\n• It has been removed by the platform or uploader\n• This content cannot be downloaded\n• Look for alternative sources",
        "errcat_private_title": "Private or Login Required",
        "errcat_private_message": "This video is private or requires authentication.",
        "errcat_private_suggestions": "• The video may be set to private\n• You might need to be logged in to access it\n• Check if you can view it in your browser when logged in\n• Contact the video owner for access",
        "errcat_format_title": "Format Error",
        "errcat_format_message": "There was an issue with the video or audio format.",
        "errcat_format_suggestions": "• Try a different quality setting\n• The video format may not be compatible\n• Check if 'Best Quality' works better\n• Try downloading audio only first",
        "errcat_disk_space_title": "Insufficient Disk Space",
        "errcat_disk_space_message": "There is not enough space to download this file.",
        "errcat_disk_space_suggestions": "• Free up disk space on your drive\n• Choose a different download location\n• Delete unnecessary files\n• Try downloading a lower quality version",
        "errcat_permission_title": "Permission Denied",
        "errcat_permission_message": "Cannot write to the selected download directory.",
        "errcat_permission_suggestions": "• Choose a different download folder\n• Check folder permissions\n• Try saving to your Downloads folder\n• Run the application as administrator (Windows)",
        "errcat_unknown_title": "Download Failed",
        "errcat_unknown_message": "An error occurred during download:\n\n{detail}",
        "errcat_unknown_suggestions": "• Try downloading again\n• Check the log for more details\n• Try a different quality setting\n• Verify the URL is still valid",
        # Quality descriptions (shown in the Activity log)
        "quality_desc_best": "Best available quality (video+audio or VBR audio) - No limits",
        "quality_desc_8k": "Ultra HD 8K (7680x4320) - Extreme quality, very large files",
        "quality_desc_4k": "Ultra HD 4K (3840x2160) - Excellent quality, large files",
        "quality_desc_2k": "Quad HD (2560x1440) - Great quality, moderate file size",
        "quality_desc_1080p": "Full HD (1920x1080) - Recommended for most devices",
        "quality_desc_720p": "HD (1280x720) - Good quality, smaller file size",
        "quality_desc_480p": "Standard definition (854x480) - Faster downloads",
        "quality_desc_360p": "Low resolution (640x360) - Smallest file size",
        "quality_desc_audio_320": "Highest fixed quality - Near CD quality (320kbps)",
        "quality_desc_audio_256": "Very high quality - Excellent for music (256kbps)",
        "quality_desc_audio_192": "High quality - Good balance (192kbps)",
        "quality_desc_audio_128": "Standard quality - Smaller file size (128kbps)",
        "quality_desc_none": "No description available",
        # Fallback texts, file dialog filter and download stopped message
        "text_unknown_title": "Unknown Title",
        "text_unknown_playlist": "Unknown Playlist",
        "text_unknown_label": "Unknown",
        "filter_text_files": "Text Files (*.txt);;All Files (*.*)",
        "error_download_stopped": "Download stopped unexpectedly",
        # Language names (subtitle list)
        "language_name_en": "English",
        "language_name_es": "Spanish",
        "language_name_fr": "French",
        "language_name_de": "German",
        "language_name_it": "Italian",
        "language_name_pt": "Portuguese",
        "language_name_ru": "Russian",
        "language_name_ja": "Japanese",
        "language_name_ko": "Korean",
        "language_name_zh": "Chinese",
        "language_name_zh_hans": "Chinese (Simplified)",
        "language_name_zh_hant": "Chinese (Traditional)",
        "language_name_ar": "Arabic",
        "language_name_hi": "Hindi",
        "language_name_he": "Hebrew",
        "language_name_nl": "Dutch",
        "language_name_pl": "Polish",
        "language_name_tr": "Turkish",
        "language_name_sv": "Swedish",
        "language_name_da": "Danish",
        "language_name_no": "Norwegian",
        "language_name_fi": "Finnish",
        "language_name_cs": "Czech",
        "language_name_el": "Greek",
        "language_name_hu": "Hungarian",
        "language_name_ro": "Romanian",
        "language_name_th": "Thai",
        "language_name_vi": "Vietnamese",
        "language_name_id": "Indonesian",
        "language_name_uk": "Ukrainian",
    },
    "he": {
        # Tabs
        "tab_download": "הורדה",
        "tab_queue": "תור",
        "tab_history": "היסטוריה",
        "tab_settings": "הגדרות",
        "tab_about": "אודות",
        # Download Tab
        "label_url": "URL:",
        "download_url_placeholder": "הזן כתובת YouTube או גרור ושחרר כאן...",
        "label_quality": "איכות:",
        "label_save_to": "שמור ב:",
        "button_browse": "עיון",
        "button_download_now": "הורד כעת",
        "button_add_to_queue": "הוסף לתור",
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
        "text_unlimited": "ללא הגבלה",
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
        # tooltip_select_subs lives lower in this dict; do not redeclare here.
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
        "batch_count": "כתובות URL: {count}",
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
        # לשונית הגדרות - אפשרויות הורדה מתקדמות (0.5.0)
        "settings_advanced_download": "אפשרויות הורדה מתקדמות",
        "button_show_advanced_download": "הצג אפשרויות הורדה מתקדמות",
        "button_hide_advanced_download": "הסתר אפשרויות הורדה מתקדמות",
        "tooltip_toggle_advanced_download": "עוגיות דפדפן, פרוקסי, שמות קבצים ואפשרויות פורמט",
        "label_cookies_browser": "השתמש בעוגיות מ:",
        "cookies_browser_none": "ללא",
        "tooltip_cookies_browser": (
            "קרא את העוגיות של דפדפן, כדי שאפשר יהיה להוריד סרטונים פרטיים וסרטונים עם הגבלת גיל. "
            "התחבר קודם לאתר בדפדפן הזה."
        ),
        "label_cookies_profile": "פרופיל דפדפן:",
        "placeholder_cookies_profile": "רשות: שם פרופיל או תיקייה",
        "tooltip_cookies_profile": "השאר ריק כדי להשתמש בפרופיל ברירת המחדל של הדפדפן.",
        "text_cookies_privacy": (
            "העוגיות נשארות במחשב הזה. התוכנה קוראת אותן רק כדי להעביר אותן ל-yt-dlp עבור ההורדה. "
            "היא לא שומרת אותן ולא כותבת אותן ליומן."
        ),
        "label_proxy": "פרוקסי:",
        "placeholder_proxy": "socks5://host:1080 (ריק = ללא פרוקסי)",
        "tooltip_proxy": (
            "משמש להורדות ולמידע על סרטונים, כתוביות ורשימות השמעה. סוגים נתמכים: http, https, "
            "socks5 ו-socks5h. שם משתמש וסיסמה בכתובת נשמרים בקובץ ההגדרות, אבל לעולם לא נכתבים ליומן."
        ),
        "label_filename_template": "שם קובץ:",
        "filename_preset_title_quality": "כותרת_איכות (ברירת מחדל)",
        "filename_preset_uploader_title": "מעלה - כותרת",
        "filename_preset_date_title": "תאריך - כותרת",
        "filename_preset_custom": "תבנית מותאמת אישית",
        "tooltip_filename_template": "איך קבצים שהורדו נקראים. אם הקובץ קיים, נוסף מספר כמו (1).",
        "label_custom_template": "תבנית מותאמת:",
        "placeholder_custom_template": "%(title)s [%(id)s].%(ext)s",
        "tooltip_custom_template": (
            "תבנית פלט של yt-dlp. היא חייבת להסתיים ב-.%(ext)s ולהיות שם קובץ בלבד, בלי תיקיות."
        ),
        "label_video_codec": "קידוד וידאו:",
        "label_audio_codec": "קידוד שמע:",
        "codec_any": "כלשהו",
        "tooltip_video_codec": (
            "העדף את קידוד הווידאו הזה כשהאתר מציע אותו. כדי לקבל אותו, ההורדה יכולה להשתמש ברזולוציה "
            "נמוכה יותר, בתוך האיכות שנבחרה."
        ),
        "tooltip_audio_codec": (
            "העדף את קידוד השמע הזה בהורדות וידאו. הורדות שמע בלבד משתמשות בפורמט השמע מלשונית ההורדה."
        ),
        "label_custom_format": "פורמט מותאם:",
        "placeholder_custom_format": "לדוגמה: bestvideo[height<=720]+bestaudio",
        "tooltip_custom_format": (
            "מחרוזת פורמט של yt-dlp למשתמשים מתקדמים. כשהיא מוגדרת, היא מחליפה את בחירת האיכות והקידוד."
        ),
        "text_advanced_applies": "ההגדרות האלה חלות על הורדות שמתחילות אחרי השמירה.",
        "error_invalid_advanced_settings": "הגדרת הורדה מתקדמת לא תקינה",
        "error_proxy_invalid": (
            "כתובת הפרוקסי לא תקינה. השתמש בצורה type://host:port, לדוגמה socks5://127.0.0.1:1080."
        ),
        "error_proxy_scheme": "סוג הפרוקסי הזה לא נתמך. השתמש ב-http, https, socks5 או socks5h.",
        "error_cookies_profile": "פרופיל הדפדפן לא תקין. השתמש בשם פרופיל או בתיקייה של 260 תווים לכל היותר.",
        "error_template_empty": "תבנית שם הקובץ המותאמת ריקה.",
        "error_template_too_long": "תבנית שם הקובץ המותאמת ארוכה מדי. השתמש ב-200 תווים לכל היותר.",
        "error_template_invalid_char": (
            'בתבנית שם הקובץ המותאמת יש תו שאסור בשמות קבצים (< > : " | ? * $ או תו בקרה).'
        ),
        "error_template_path": (
            'תבנית שם הקובץ המותאמת חייבת להיות שם קובץ בלבד: בלי תיקיות, "..", אותיות כונן או נתיבים מלאים.'
        ),
        "error_template_ext": "תבנית שם הקובץ המותאמת חייבת להסתיים ב-.%(ext)s.",
        "error_template_field_syntax": (
            "בתבנית שם הקובץ המותאמת יש שדה שלא נכתב נכון. כתוב שדה בצורה %(name)s, וסימן אחוז בצורה %%."
        ),
        "error_template_unknown_field": (
            "תבנית שם הקובץ המותאמת משתמשת בשדה שהתוכנה לא תומכת בו. השתמש בשדות כמו "
            "title, id, uploader, upload_date או height."
        ),
        "error_format_too_long": "הפורמט המותאם ארוך מדי. השתמש ב-500 תווים לכל היותר.",
        "error_format_invalid_char": "הפורמט המותאם חייב להיות שורה אחת, בלי תווי בקרה.",
        "error_format_syntax": "yt-dlp לא יכול לקרוא את הפורמט המותאם. בדוק את הסוגריים.",
        "cookies_error_app_bound": (
            "לא ניתן לקרוא את העוגיות מ-{browser}. Chrome 127 ומעלה (וכמה דפדפנים אחרים מבוססי Chromium) "
            "מגינים על העוגיות שלהם בהצפנה קשורת-אפליקציה, ש-yt-dlp לא יכול לקרוא. השתמש ב-Firefox "
            "לעוגיות, או קבע את אפשרות העוגיות בהגדרות ל'ללא'."
        ),
        "cookies_error_locked": (
            "לא ניתן לקרוא את העוגיות מ-{browser}, כי {browser} נועל את מסד הנתונים של העוגיות. "
            "סגור את {browser} לגמרי, ואז נסה שוב."
        ),
        "cookies_error_not_found": (
            "לא נמצאו עוגיות של {browser}. ודא ש-{browser} מותקן, ובדוק את פרופיל הדפדפן בהגדרות."
        ),
        "cookies_error_generic": "לא ניתן לקרוא את העוגיות מ-{browser}. הפרטים נמצאים בקובץ היומן.",
        "cookies_hint_sign_in": (
            "הסרטון הזה דורש חשבון מחובר (לדוגמה סרטון פרטי או סרטון עם הגבלת גיל). התחבר לאתר בדפדפן "
            "שלך. אחר כך, בהגדרות > אפשרויות הורדה מתקדמות, קבע את 'השתמש בעוגיות מ' לדפדפן הזה."
        ),
        "cookies_hint_signed_in_browser": (
            "האתר עדיין מבקש להתחבר. ודא שאתה מחובר לאתר ב-{browser}, עם הפרופיל שהוגדר בהגדרות, ואז נסה שוב."
        ),
        "proxy_error_connect": ("לא ניתן להתחבר דרך הפרוקסי. בדוק את כתובת הפרוקסי בהגדרות > אפשרויות הורדה מתקדמות."),
        "error_no_video_in_post": ("בפוסט הזה אין סרטון. הורדת פוסטים של תמונות מתוכננת לגרסה עתידית."),
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
        "text_about_developer_intro": "כלי זה הוא חלק מ-<b>NXTools</b> - אוסף של כלי פרודקטיביות.",
        "label_website": "אתר:",
        # button_view_on_github lives lower in this dict; do not redeclare here.
        "tooltip_view_on_github": "פתח את מאגר הפרויקט בדפדפן",
        "header_credits_core_deps": "תלויות מרכזיות",
        "header_credits_dev_framework": "סביבת פיתוח",
        "header_credits_build_dist": "בנייה והפצה",
        "text_credits_thanks": "תודה לכל המפתחים והתורמים של פרויקטי הקוד הפתוח הללו. האפליקציה הזו לא הייתה מתאפשרת בלי עבודתכם.",
        "text_ffmpeg_not_found": "לא נמצא ב-PATH",
        "text_ffmpeg_unknown": "מותקן (גרסה לא ידועה)",
        "text_ffmpeg_error": "שגיאה בזיהוי גרסה",
        "text_ffmpeg_checking": "בודק...",
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
        "button_retry_all_failed": "נסה שוב את כל הנכשלים",
        "tooltip_retry_all_failed": "נסה שוב את כל ההורדות שנכשלו בתור",
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
        "msg_clear_status_confirm": 'לנקות מההיסטוריה את כל ההורדות במצב "{status}"?',
        "msg_clear_all_confirm": "לנקות את כל היסטוריית ההורדות? לא ניתן לבטל פעולה זו!",
        "msg_cleared_entries": "נוקו {count} רשומות היסטוריה",
        "msg_dir_not_found": "תיקייה לא נמצאה",
        "msg_download_dir_not_exist": "תיקיית ההורדות לא קיימת",
        "msg_failed_open_dir": "נכשל לפתוח תיקייה",
        # Settings Tab
        "settings_general": "הגדרות כלליות",
        "settings_appearance": "מראה",
        "settings_features": "תכונות",
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
        "notif_download_complete_msg": "ההורדה הסתיימה",
        "notif_download_complete_msg_size": "ההורדה הסתיימה ({size})",
        "notif_download_error_msg": "ההורדה נכשלה",
        "notif_download_error_msg_reason": "ההורדה נכשלה: {error}",
        "notif_batch_completed_count": "הושלמו: {successful}/{total}",
        "notif_batch_failed_count": "נכשלו: {failed}",
        "notif_update_available_msg": "גרסה {version} זמינה.",
        # System Tray
        "tray_show_window": "הצג חלון",
        "tray_quit": "יציאה",
        "checkbox_close_to_tray": "המשך לפעול במגש המערכת כשאני סוגר את החלון",
        "tooltip_close_to_tray": "סגירת החלון מסתירה אותו במגש המערכת. ההורדות ממשיכות. ליציאה, בחר יציאה בתפריט המגש.",
        "tooltip_close_to_tray_unavailable": "בשולחן העבודה שלך אין מגש מערכת, לכן אפשרות זו אינה זמינה.",
        "tray_still_running": "התוכנה ממשיכה לפעול במגש המערכת וההורדות ממשיכות. ליציאה, בחר יציאה בתפריט המגש.",
        "tray_tooltip_busy": "{app} - {active} בהורדה, {pending} בהמתנה",
        # Status Messages
        "status_pending": "ממתין",
        "status_downloading": "מוריד...",
        "status_completed": "הושלם",
        "status_error": "שגיאה",
        "status_cancelled": "בוטל",
        "status_failed": "נכשל",
        "status_preparing": "מכין את ההורדה שלך...",
        "status_ready": "מוכן להורדה",
        "status_complete": "ההורדה הושלמה!",
        "status_success": "ההורדה הושלמה בהצלחה!",
        # Common
        "yes": "כן",
        "no": "לא",
        "cancel": "ביטול",
        "error": "שגיאה",
        "warning": "אזהרה",
        "info": "מידע",
        # Additional Main Window
        "status_bar_ready": "מוכן",
        "tooltip_toggle_theme": "החלף בין ערכות נושא כהות ובהירות",
        "dialog_download_in_progress": "הורדה מתבצעת",
        "msg_download_in_progress_exit": "הורדה מתבצעת כעת. האם אתה בטוח שברצונך לצאת?",
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
        "msg_confirm_download_text": "פעולה זו תוריד את העדכון לתיקיית ההורדות שלך.\n\nקובץ: {filename}\nגודל: {size}\n\nההורדה תתבצע ברקע.\n\nלהמשיך?",
        "text_downloading_update": "מוריד עדכון...",
        "text_download_failed": "ההורדה נכשלה!",
        "dialog_download_complete_update": "הורדה הושלמה",
        "dialog_installer_error": "שגיאת התקנה",
        "button_skip_version": "דלג על גרסה זו",
        "text_unknown_size": "גודל לא ידוע",
        "text_download_verified": "ההורדה אומתה.",
        "msg_download_verified_reveal": "העדכון הורד ואומת בהצלחה.\n\nקובץ: {path}\n\nלפתוח את תיקיית ההורדות כעת? חלץ את הארכיון והרץ את install.sh כדי לעדכן.",
        "msg_download_verified_reveal_package": "העדכון הורד ואומת בהצלחה.\n\nקובץ: {path}\n\nלפתוח את תיקיית ההורדות כעת? פתח את החבילה במנהל התוכנה כדי לעדכן. ההגדרות וההיסטוריה שלך יישמרו.",
        "msg_download_verified_reveal_appimage": "העדכון הורד ואומת בהצלחה.\n\nקובץ: {path}\n\nלפתוח את תיקיית ההורדות כעת? הפוך את קובץ ה-AppImage החדש להרצה והפעל אותו. לאחר מכן תוכל למחוק את ה-AppImage הישן.",
        "msg_installer_saved": "המתקין המאומת נשמר אל:\n{path}\n\nתוכל להפעיל אותו מאוחר יותר כדי לעדכן את התוכנה.",
        "msg_update_install_restart": "העדכון הורד ואומת.\n\nלהתקין אותו עכשיו? YT-DLP Studio ייסגר, יתקין את גרסה {version} ויופעל מחדש. ההגדרות וההיסטוריה שלך יישמרו.",
        "msg_portable_update_ready": "הגרסה החדשה הורדה ואומתה:\n{path}\n\nזו גרסה ניידת. היא פועלת מהמקום שבו נשמרה ואינה מחליפה את העותק שבו אתה משתמש כעת.\n\nלהפעיל את הגרסה החדשה עכשיו? העותק הנוכחי ייסגר. תוכל למחוק אותו לאחר מכן.",
        "msg_portable_update_saved": "הגרסה החדשה נשמרה ב:\n{path}\n\nהפעל אותה משם כשתהיה מוכן. היא אינה מחליפה את העותק שבו אתה משתמש כעת.",
        "dialog_verify_failed": "האימות נכשל",
        "msg_verify_failed": "המתקין שהורד נכשל באימות התקינות ונמחק לשם בטיחותך.\n\nצפוי: {expected}\nבפועל: {actual}\n\nאנא נסה שוב, או הורד ידנית מ-GitHub.",
        "dialog_unverified_download": "הורדה לא מאומתת",
        "msg_unverified_download": "גרסה זו אינה מפרסמת סכום ביקורת, ולכן לא ניתן היה לאמת את ההורדה אוטומטית.\n\nהקובץ נשמר אל:\n{path}\n\nלשם בטיחותך הוא לא יופעל אוטומטית. הפעל אותו ידנית רק אם אתה סומך על המקור.",
        "msg_download_failed_retry": "הורדת העדכון נכשלה.\n\nאנא נסה שוב, או הורד ידנית מ-GitHub.",
        "msg_installer_launch_failed": "הפעלת המתקין נכשלה:\n{error}\n\nאנא הפעל אותו ידנית:\n{path}",
        "msg_update_check_rate_limited": "שרת העדכונים של GitHub מגביל בקשות. אנא נסה שוב מאוחר יותר.",
        # About Tab
        "label_credits": "קרדיטים",
        "text_credits_description": "אפליקציה זו בנויה באמצעות הפרוייקטים הקוד-פתוח הבאים:",
        # אתרים שנבדקו (תווית ליד שדה הכתובת)
        "site_tier_tested": "אתר שנבדק",
        "site_tier_experimental": "אתר ניסיוני: ייתכן שלא יעבוד",
        "tooltip_site_tier_tested": (
            "YT-DLP Studio בודק הורדות מהאתרים YouTube, Instagram, TikTok, Facebook ו-X לפני כל גרסה."
        ),
        "tooltip_site_tier_experimental": (
            "YT-DLP Studio לא בודק את האתר הזה. ייתכן ש-yt-dlp תומך בו, כך שההורדה עשויה לעבוד, "
            "אבל היא עלולה גם להיכשל. אפשר עדיין להוריד."
        ),
        # Keyboard Shortcuts
        "shortcuts_title": "קיצורי מקלדת",
        "shortcuts_general": "כללי",
        "shortcuts_download_tab": "לשונית הורדה",
        "shortcuts_queue_tab": "לשונית תור",
        "shortcut_quit_app": "יציאה מהתוכנה",
        "shortcut_show_help": "פתח את העזרה המקוונת",
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
        "tooltip_metadata": "הורד מטא-דאטה של הסרטון (תיאור, info.json)",
        "tooltip_comments": "הורד תגובות הסרטון לקובץ .txt נפרד (עשוי להיות איטי עבור סרטונים פופולריים)",
        "button_cancel": "ביטול",
        "button_retry": "נסה שוב",
        # --- UI overhaul A ---
        # Settings tab
        "settings_downloads": "הורדות",
        "settings_behavior": "התנהגות",
        "settings_bug_report_files": "קבצים לדיווח על באג",
        "label_language_restart_hint": "שינוי השפה ייכנס לתוקף אחרי הפעלה מחדש של האפליקציה.",
        "tooltip_theme_combo": "מוחל מיד ונשמר",
        "button_settings_open_folder": "פתח תיקייה",
        "tooltip_settings_open_folder": "פתח את התיקייה במנהל הקבצים",
        "status_settings_saved": "ההגדרות נשמרו.",
        # About tab
        "about_tagline": "אפליקציית שולחן עבודה ל-yt-dlp: הורדת וידאו ואודיו מ-YouTube ומאתרים רבים אחרים.",
        "button_copy_bug_report": "העתק לדיווח על באג",
        "tooltip_copy_bug_report": "העתק את הגרסאות שלמעלה ואת פרטי המערכת, כדי להדביק אותם בדיווח על באג",
        "msg_bug_report_copied": "פרטי המערכת הועתקו. הדבק אותם בדיווח על הבאג.",
        "label_license": "רישיון:",
        # Update dialog
        "text_update_download_progress": "מוריד: {done} מתוך {total} ({percent})",
        # Subtitle dialog
        "dialog_select_subtitle_languages": "בחירת שפות כתוביות",
        "text_subtitle_dialog_help": "סמן את שפות הכתוביות להורדה. חלקן עשויות להיות כתוביות שנוצרו אוטומטית.",
        "group_subtitle_languages": "שפות כתוביות",
        "placeholder_filter_languages": "הקלד כדי לסנן שפות...",
        "text_auto_generated": "נוצרו אוטומטית",
        "button_use_selected_languages": "השתמש בשפות שנבחרו",
        "dialog_no_subtitles_selected": "לא נבחרו כתוביות",
        "msg_continue_without_subtitles": "לא בחרת שפת כתוביות.\n\nלהמשיך בלי כתוביות?",
        # Batch dialog
        "button_clear": "נקה",
        "dialog_no_urls": "אין כתובות URL",
        "label_batch_counts": "כתובות URL תקינות: {valid}    שורות לא תקינות: {invalid}",
        "msg_validation_invalid_lines": "{valid} כתובות URL תקינות, {invalid} שורות לא תקינות:",
        "text_line_number": "שורה {line}: {text}",
        "text_and_more": "... ועוד {count}",
        "msg_all_urls_valid": "כל {count} כתובות ה-URL תקינות.",
        "msg_proceed_with_valid_urls": "נמצאו {valid} כתובות URL תקינות ו-{invalid} שורות לא תקינות.\n\nלהוסיף רק את הכתובות התקינות?",
        # Playlist dialog
        "label_uploader": "מעלה",
        "label_selected_count": "{selected} מתוך {total} נבחרו",
        "button_add_videos_to_queue": "הוסף לתור ({count})",
        # Download error dialog
        "header_error_suggestions": "הצעות:",
        "header_error_technical_details": "פרטים טכניים:",
        "button_copy_details": "העתק פרטים",
        "text_copied": "הועתק",
        # --- end UI overhaul A ---
        # --- UI overhaul B ---
        # לשונית הורדה
        "label_link": "קישור",
        "placeholder_link": "הדבק קישור לסרטון או לפלייליסט (YouTube ואתרים רבים נוספים)",
        "button_info": "מידע",
        "tooltip_info": "הצג את הכותרת, האורך והפורמטים של הקישור בלי להוריד (Ctrl+Shift+I)",
        "label_get": "מה להוריד",
        "label_quality_short": "איכות",
        "label_format": "פורמט",
        "label_save_to_short": "שמור אל",
        "action_open_folder": "פתח תיקייה",
        "section_more_options": "אפשרויות נוספות",
        "more_options_default": "הכול כבוי, ללא הגבלת מהירות",
        "summary_subtitles": "כתוביות ({langs})",
        "summary_metadata": "מטא-דאטה",
        "summary_speed_limit": "הגבלת מהירות {speed}",
        "checkbox_subtitles_short": "כתוביות",
        "label_languages": "שפות",
        "button_choose_subs": "בחר...",
        "checkbox_thumbnail_short": "תמונה ממוזערת",
        "checkbox_metadata_short": "מטא-דאטה (info.json, תיאור)",
        "checkbox_comments_short": "תגובות",
        "label_speed_limit_short": "הגבלת מהירות",
        "text_advanced_in_settings": "עוגיות מהדפדפן, פרוקסי, שמות קבצים ואפשרויות פורמט נמצאים בלשונית ההגדרות.",
        "button_open_settings": "פתח הגדרות",
        "button_batch_links": "קישורים מרובים...",
        "button_add_to_queue_short": "הוסף לתור",
        "button_download": "הורד",
        "tooltip_download_button": "הורד את הקישור עכשיו (Enter או Ctrl+D). ההורדה מתחילה מיד, גם כשהתור מושהה. אם כבר פועל המספר המרבי של הורדות, היא תתחיל ראשונה כשיתפנה מקום.",
        "tooltip_add_to_queue_button": "הוסף את הקישור לסוף התור (Ctrl+Shift+Q). ההורדה ממתינה לתורה ולא מתחילה כשהתור מושהה.",
        "error_link_empty": "הדבק קישור קודם.",
        "error_link_invalid": "זה לא קישור תקין. קישור מתחיל ב-{http} או ב-{https}.",
        "error_folder_invalid": "התיקייה לא קיימת או שאין הרשאה לכתוב בה. בחר תיקייה אחרת בעזרת עיון.",
        "status_download_started": "ההורדה התחילה.",
        "status_download_next": "ההורדה תתחיל מיד כשאחת ההורדות הפעילות תסתיים.",
        "status_added_to_queue": "נוסף לתור במקום {position}.",
        "status_added_paused": "נוסף לתור במקום {position}. התור מושהה: לחץ על התחל בלשונית התור.",
        "status_videos_added": "{count} סרטונים נוספו לתור.",
        "status_batch_added": "{count} קישורים נוספו לתור.",
        "msg_playlist_choice": "הקישור הזה הוא פלייליסט של {platform}.\n\nבחר סרטונים כדי לבחור רק את מה שאתה רוצה, או הוסף את כל הפלייליסט כהורדה אחת.",
        "button_choose_videos": "בחר סרטונים...",
        "button_whole_playlist": "כל הפלייליסט",
        "section_activity_log": "יומן פעילות",
        # חלונית מוריד עכשיו
        "group_now_downloading": "מוריד עכשיו",
        "now_empty": "אין הורדות פעילות. הדבק קישור למעלה כדי להתחיל.",
        "now_empty_paused": "אין הורדות פעילות. התור מושהה, {count} הורדות ממתינות.",
        "now_starting": "מתחיל...",
        "now_processing": "מעבד...",
        "now_time_left": "נותרו {time}",
        "now_progress_accessible": "{title}: {percent}",
        "button_open_queue": "פתח את התור",
        "tooltip_open_queue": "עבור ללשונית התור",
        "summary_downloading": "{count} בהורדה",
        "summary_waiting": "{count} ממתינות",
        "summary_failed": "{count} נכשלו",
        "summary_done": "{count} הושלמו",
        "summary_paused": "התור מושהה",
        "summary_queue_empty": "התור ריק",
        # שורת המצב
        "status_bar_idle": "לא פעיל",
        "status_bar_downloading": "מוריד {active} מתוך {total}",
        "status_bar_paused": "התור מושהה, {count} ממתינות",
        # לשונית תור
        "button_start": "התחל",
        "button_pause": "השהה",
        "button_stop_all_short": "עצור הכול",
        "tooltip_start_queue": "התחל את ההורדות הממתינות. מעכשיו קישורים חדשים יתחילו מעצמם.",
        "tooltip_pause_queue": "ההורדות הפעילות יסתיימו, אבל הורדות חדשות לא יתחילו. לחץ על התחל כדי להמשיך.",
        "tooltip_stop_all": "בטל את ההורדות הפעילות והשהה את התור. ההורדות הממתינות נשארות בתור.",
        "dialog_stop_all": "לעצור את כל ההורדות?",
        "msg_stop_all_confirm": "הורדות פעילות: {count}.\n\nלבטל אותן ולהשהות את התור?",
        "col_time_left": "זמן נותר",
        "action_open_file": "פתח קובץ",
        "tooltip_open_task_folder": "פתח את התיקייה של ההורדה שנבחרה",
        "tooltip_retry_task": "נסה שוב את ההורדה שנכשלה",
        "tooltip_cancel_task": "בטל את ההורדה שנבחרה. הורדה ממתינה תוסר מהתור.",
        "button_move_up_short": "למעלה",
        "button_move_down_short": "למטה",
        "tooltip_move_up": "הזז את ההורדה שנבחרה למעלה (Ctrl+Up)",
        "tooltip_move_down": "הזז את ההורדה שנבחרה למטה (Ctrl+Down)",
        "tooltip_remove_task": "הסר את ההורדה שנבחרה מהתור (Delete)",
        "button_retry_failed": "נסה שוב את הכושלות",
        "button_clear_finished": "נקה הורדות שהסתיימו",
        "tooltip_clear_finished": "הסר מהתור הורדות שהסתיימו. הקבצים נשארים בדיסק.",
        "menu_clear_completed": "הורדות שהושלמו",
        "menu_clear_failed": "הורדות שנכשלו",
        "menu_clear_cancelled": "הורדות שבוטלו",
        "menu_copy_link": "העתק קישור",
        "menu_show_error": "הצג פרטי שגיאה",
        "dialog_remove_task": "להסיר את ההורדה?",
        "msg_remove_downloading": "ההורדה הזאת פעילה. לבטל אותה ולהסיר אותה מהתור?",
        "msg_remove_waiting": "להסיר את ההורדה הממתינה מהתור?",
        "status_removing": "מבטל את ההורדה. היא תוסר מהתור כשתיעצר.",
        "status_removed": "הוסר מהתור.",
        "status_cleared_tasks": "{count} הורדות הוסרו מהתור.",
        "status_retrying": "מנסה שוב {count} הורדות.",
        "status_link_copied": "הקישור הועתק.",
        "tooltip_queue_task": "{title}\nקישור: {url}\nתיקייה: {folder}\nאיכות: {quality}",
        "text_title_unknown": "הכותרת עדיין לא ידועה",
        "tooltip_task_failed": "{reason}\nלחץ פעמיים או לחץ לחיצה ימנית לפרטים.",
        "tooltip_waiting_paused": "ממתין. התור מושהה.",
        "button_go_to_download": "עבור להורדה",
        # לשונית היסטוריה
        "history_summary": "{total} הורדות, הושלמו: {done}, נכשלו: {failed}, בוטלו: {cancelled}, בסך הכול: {size}",
        "history_summary_tooltip": "שיעור הצלחה: {rate}\nמהירות ממוצעת: {speed}",
        "placeholder_search_title_link": "חפש לפי כותרת או קישור...",
        "filter_status": "סינון לפי מצב",
        "filter_all_statuses": "כל המצבים",
        "history_no_matches": "אין תוצאות",
        "history_no_matches_hint": "נסה מילת חיפוש אחרת או מצב אחר.",
        "tooltip_history_link": "קישור: {url}",
        "tooltip_history_error": "שגיאה: {reason}",
        "menu_download_again": "הורד שוב",
        "button_open_downloads_folder": "פתח את תיקיית ההורדות",
        "button_clear_menu": "נקה",
        "tooltip_clear_history": "הסר רשומות מההיסטוריה. הקבצים שהורדו נשארים בדיסק.",
        "menu_clear_history_completed": "נקה הורדות שהושלמו",
        "menu_clear_history_failed": "נקה הורדות שנכשלו",
        "menu_clear_history_all": "נקה את כל ההיסטוריה",
        "status_history_exported": "ההיסטוריה נשמרה ב-{path}.",
        "status_history_cleared": "{count} רשומות הוסרו מההיסטוריה.",
        "status_link_in_download_tab": "הקישור נמצא בלשונית ההורדה. בדוק את האפשרויות ולחץ על הורד.",
        # Video and audio format names (Download tab)
        "format_video_mp4": "MP4 (תאימות מרבית)",
        "format_video_mkv": "MKV (Matroska)",
        "format_video_webm": "WebM",
        "format_video_auto": "אוטומטי (איכות מיטבית)",
        "format_audio_mp3": "MP3 (תאימות מרבית)",
        "format_audio_m4a": "M4A/AAC (איכות גבוהה)",
        "format_audio_opus": "OPUS (איכות וגודל מיטביים)",
        "format_audio_flac": "FLAC (ללא אובדן איכות)",
        "format_audio_wav": "WAV (ללא דחיסה)",
        "format_audio_vorbis": "Vorbis/OGG",
        # Activity log lines (Download tab)
        "log_started": "התחיל: {title}",
        "log_finished": "הסתיים: {filename}",
        "log_stopped": "נעצר: {error}",
        "log_pasted": "הודבק מהלוח: {text}...",
        "log_auto_detected_url": "זוהה קישור בלוח",
        "log_mode_audio": "מצב אודיו בלבד: בחר איכות ופורמט",
        "log_mode_video": "מצב וידאו: בחר איכות ופורמט",
        "log_quality_selected": "נבחרה איכות: {quality} - {description}",
        "log_output_dir_changed": "תיקיית ההורדה שונתה אל: {directory}",
        "log_opened_dir": "נפתחה התיקייה: {directory}",
        "log_added_to_queue": "נוסף לתור במקום {position}: {url}",
        "log_already_fetching_video": "מידע על סרטון כבר בהבאה, אנא המתן...",
        "log_already_fetching_playlist": "מידע על פלייליסט כבר בהבאה, אנא המתן...",
        "log_fetching_video_info": "מביא מידע על הסרטון: {url}",
        "log_detected_playlist": "זוהה פלייליסט של {platform}, מביא מידע...",
        "log_video_info_fetched": "המידע על הסרטון התקבל: {title}",
        "log_video_info_failed": "הבאת המידע על הסרטון נכשלה: {error}",
        "log_playlist_fetched": "הפלייליסט התקבל: {title} ({count} סרטונים)",
        "log_playlist_fetched_one": "הפלייליסט התקבל: {title} (סרטון אחד)",
        "log_playlist_failed": "הבאת המידע על הפלייליסט נכשלה: {error}",
        "log_no_videos_selected": "לא נבחרו סרטונים מהפלייליסט",
        "log_added_videos": "נוספו {count} סרטונים לתור",
        "log_added_videos_one": "נוסף סרטון אחד לתור",
        "log_added_videos_subs": "נוספו {count} סרטונים לתור (כתוביות: {langs})",
        "log_added_videos_subs_one": "נוסף סרטון אחד לתור (כתוביות: {langs})",
        "log_fetching_subs": "מביא כתוביות זמינות עבור: {url}",
        "log_no_subs_found": "לא נמצאו כתוביות לסרטון הזה",
        "log_selected_subs": "נבחרו {count} שפות כתוביות: {langs}",
        "log_selected_subs_one": "נבחרה שפת כתוביות אחת: {langs}",
        "log_no_subs_selected": "לא נבחרו כתוביות",
        "log_batch_added": "קישורים מרובים: נוספו {count} קישורים לתור",
        "log_batch_added_one": "קישורים מרובים: נוסף קישור אחד לתור",
        "log_url_dropped": "הקישור נגרר: {text}...",
        "log_level_error": "שגיאה",
        "log_level_success": "הצלחה",
        "log_level_info": "מידע",
        "log_level_warning": "אזהרה",
        # Singular forms for texts with a number (see tr_count)
        "summary_waiting_one": "{count} ממתינה",
        "summary_failed_one": "{count} נכשלה",
        "summary_done_one": "{count} הושלמה",
        "status_bar_paused_one": "התור מושהה, {count} ממתינה",
        "now_empty_paused_one": "אין הורדות פעילות. התור מושהה, הורדה אחת ממתינה.",
        "status_cleared_tasks_one": "הורדה אחת הוסרה מהתור.",
        "status_retrying_one": "מנסה שוב הורדה אחת.",
        "status_history_cleared_one": "רשומה אחת הוסרה מההיסטוריה.",
        "msg_all_urls_valid_one": "כתובת ה-URL תקינה.",
        "status_videos_added_one": "סרטון אחד נוסף לתור.",
        "status_batch_added_one": "קישור אחד נוסף לתור.",
        "history_summary_one": "הורדה אחת, הושלמו: {done}, נכשלו: {failed}, בוטלו: {cancelled}, בסך הכול: {size}",
        # Download error texts (ErrorHandler)
        "errcat_network_title": "שגיאת רשת",
        "errcat_network_message": "לא ניתן להתחבר לאינטרנט או לשרת הסרטון.",
        "errcat_network_suggestions": "• בדוק את חיבור האינטרנט\n• ודא שהכתובת נפתחת בדפדפן\n• נסה שוב בעוד כמה רגעים\n• בדוק אם חומת אש או VPN חוסמים את הגישה",
        "errcat_url_invalid_title": "כתובת לא תקינה",
        "errcat_url_invalid_message": "הכתובת שהזנת אינה תקינה או שאינה נתמכת.",
        "errcat_url_invalid_suggestions": "• ודא שהעתקת את הכתובת המלאה\n• בדוק שהכתובת מתחילה ב-http:// או ב-https://\n• ודא שהאתר נתמך על ידי yt-dlp\n• נסה ללחוץ על 'מידע' כדי לבדוק את הכתובת קודם",
        "errcat_video_unavailable_title": "הסרטון לא זמין",
        "errcat_video_unavailable_message": "הסרטון כבר לא זמין או שאינו קיים.",
        "errcat_video_unavailable_suggestions": "• ייתכן שהמעלה מחק את הסרטון\n• ייתכן שהכתובת שגויה או שפג תוקפה\n• נסה לרענן את הדף בדפדפן\n• בדוק אם הסרטון עדיין זמין באינטרנט",
        "errcat_geo_blocked_title": "תוכן מוגבל לפי אזור",
        "errcat_geo_blocked_message": "הסרטון הזה אינו זמין באזור שלך.",
        "errcat_geo_blocked_suggestions": "• ייתכן שהסרטון מוגבל למדינות מסוימות\n• ייתכן שתצטרך VPN כדי לגשת לתוכן הזה\n• בדוק אם הסרטון זמין בדפדפן\n• נסה סרטון או מקור אחר",
        "errcat_copyright_title": "הגבלת זכויות יוצרים",
        "errcat_copyright_message": "הסרטון הזה הוסר בעקבות תביעת זכויות יוצרים.",
        "errcat_copyright_suggestions": "• הסרטון הפר זכויות יוצרים או תנאי שירות\n• הפלטפורמה או המעלה הסירו אותו\n• אי אפשר להוריד את התוכן הזה\n• חפש מקורות חלופיים",
        "errcat_private_title": "פרטי או דורש התחברות",
        "errcat_private_message": "הסרטון הזה פרטי או דורש אימות.",
        "errcat_private_suggestions": "• ייתכן שהסרטון מוגדר כפרטי\n• ייתכן שתצטרך להתחבר כדי לגשת אליו\n• בדוק אם אפשר לצפות בו בדפדפן כשאתה מחובר\n• בקש גישה מבעל הסרטון",
        "errcat_format_title": "שגיאת פורמט",
        "errcat_format_message": "הייתה בעיה בפורמט הווידאו או האודיו.",
        "errcat_format_suggestions": "• נסה הגדרת איכות אחרת\n• ייתכן שפורמט הסרטון אינו תואם\n• בדוק אם 'איכות מיטבית' עובד טוב יותר\n• נסה להוריד קודם אודיו בלבד",
        "errcat_disk_space_title": "אין מספיק מקום בדיסק",
        "errcat_disk_space_message": "אין מספיק מקום להורדת הקובץ הזה.",
        "errcat_disk_space_suggestions": "• פנה מקום בכונן\n• בחר תיקיית הורדה אחרת\n• מחק קבצים מיותרים\n• נסה להוריד גרסה באיכות נמוכה יותר",
        "errcat_permission_title": "ההרשאה נדחתה",
        "errcat_permission_message": "אי אפשר לכתוב לתיקיית ההורדה שנבחרה.",
        "errcat_permission_suggestions": "• בחר תיקיית הורדה אחרת\n• בדוק את הרשאות התיקייה\n• נסה לשמור בתיקיית ההורדות שלך\n• הפעל את התוכנה כמנהל (Windows)",
        "errcat_unknown_title": "ההורדה נכשלה",
        "errcat_unknown_message": "אירעה שגיאה במהלך ההורדה:\n\n{detail}",
        "errcat_unknown_suggestions": "• נסה להוריד שוב\n• בדוק את היומן לפרטים נוספים\n• נסה הגדרת איכות אחרת\n• ודא שהכתובת עדיין תקינה",
        # Quality descriptions (shown in the Activity log)
        "quality_desc_best": "האיכות הטובה ביותר שזמינה (וידאו ואודיו, או אודיו VBR) - ללא הגבלה",
        "quality_desc_8k": "Ultra HD 8K (7680x4320) - איכות קיצונית, קבצים גדולים מאוד",
        "quality_desc_4k": "Ultra HD 4K (3840x2160) - איכות מצוינת, קבצים גדולים",
        "quality_desc_2k": "Quad HD (2560x1440) - איכות גבוהה מאוד, גודל קובץ בינוני",
        "quality_desc_1080p": "Full HD (1920x1080) - מומלץ לרוב המכשירים",
        "quality_desc_720p": "HD (1280x720) - איכות טובה, קובץ קטן יותר",
        "quality_desc_480p": "רזולוציה רגילה (854x480) - הורדות מהירות יותר",
        "quality_desc_360p": "רזולוציה נמוכה (640x360) - הקובץ הקטן ביותר",
        "quality_desc_audio_320": "האיכות הקבועה הגבוהה ביותר - קרוב לאיכות דיסק (320kbps)",
        "quality_desc_audio_256": "איכות גבוהה מאוד - מצוין למוזיקה (256kbps)",
        "quality_desc_audio_192": "איכות גבוהה - איזון טוב (192kbps)",
        "quality_desc_audio_128": "איכות רגילה - קובץ קטן יותר (128kbps)",
        "quality_desc_none": "אין תיאור זמין",
        # Fallback texts, file dialog filter and download stopped message
        "text_unknown_title": "כותרת לא ידועה",
        "text_unknown_playlist": "פלייליסט לא ידוע",
        "text_unknown_label": "לא ידוע",
        "filter_text_files": "קבצי טקסט (*.txt);;כל הקבצים (*.*)",
        "error_download_stopped": "ההורדה נעצרה באופן לא צפוי",
        # Language names (subtitle list)
        "language_name_en": "אנגלית",
        "language_name_es": "ספרדית",
        "language_name_fr": "צרפתית",
        "language_name_de": "גרמנית",
        "language_name_it": "איטלקית",
        "language_name_pt": "פורטוגזית",
        "language_name_ru": "רוסית",
        "language_name_ja": "יפנית",
        "language_name_ko": "קוריאנית",
        "language_name_zh": "סינית",
        "language_name_zh_hans": "סינית (מפושטת)",
        "language_name_zh_hant": "סינית (מסורתית)",
        "language_name_ar": "ערבית",
        "language_name_hi": "הינדית",
        "language_name_he": "עברית",
        "language_name_nl": "הולנדית",
        "language_name_pl": "פולנית",
        "language_name_tr": "טורקית",
        "language_name_sv": "שוודית",
        "language_name_da": "דנית",
        "language_name_no": "נורווגית",
        "language_name_fi": "פינית",
        "language_name_cs": "צ'כית",
        "language_name_el": "יוונית",
        "language_name_hu": "הונגרית",
        "language_name_ro": "רומנית",
        "language_name_th": "תאית",
        "language_name_vi": "וייטנאמית",
        "language_name_id": "אינדונזית",
        "language_name_uk": "אוקראינית",
    },
}


# The saved language choice, inside the app data folder (so the uninstaller
# purge removes it). Up to 0.4.0 it was in ~/.yt-dlp-studio/language.json;
# migrate_legacy_language_file() moves it.
LANGUAGE_FILE = "language.json"
LEGACY_LANGUAGE_DIR_NAME = ".yt-dlp-studio"


def get_language_file() -> Path:
    """Path of the file that holds the saved language choice."""
    return APP_DATA_DIR / LANGUAGE_FILE


def _legacy_language_dir() -> Path:
    """Folder of the language file before 0.4.1 (``~/.yt-dlp-studio``)."""
    return Path.home() / LEGACY_LANGUAGE_DIR_NAME


def _language_from_data(data: dict | None) -> str | None:
    """Return the language code in parsed file data, or None if it is invalid."""
    language = data.get("language") if isinstance(data, dict) else None
    return language if language in TRANSLATIONS else None


def _read_legacy_language_file(path: Path) -> str | None:
    """Return the language code in a file from before 0.4.1, or None if it is missing or invalid."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return _language_from_data(data)


def _read_language_file(path: Path) -> str | None:
    """
    Return the language code saved in ``path``, or None if it is missing or invalid.

    Version rules are in src/utils/file_formats.py (a damaged file is kept
    as ``<name>.bad``).
    """
    return _language_from_data(load_json_file(path, LANGUAGE_FORMAT).data)


def save_language(language_code: str) -> bool:
    """
    Save the language choice in the app data folder.

    Returns:
        True if the file was written
    """
    path = get_language_file()
    try:
        save_json_file(path, LANGUAGE_FORMAT, {"language": language_code}, indent=None)
    except (OSError, TypeError, ValueError):
        logger.exception("Failed to save language preference")
        return False
    logger.info(f"Language preference saved: {language_code}")
    return True


def migrate_legacy_language_file() -> None:
    """
    Move a language file from ``~/.yt-dlp-studio`` into the app data folder.

    The old file is read only when the app data folder has no language file
    yet. Then the old file is deleted, and its folder too if it is empty. If
    the new file cannot be written, the old file stays for the next start.
    """
    legacy_dir = _legacy_language_dir()
    legacy_file = legacy_dir / LANGUAGE_FILE
    if not legacy_file.is_file():
        return

    if not get_language_file().exists():
        language = _read_legacy_language_file(legacy_file)
        if language is not None and not save_language(language):
            return
        logger.info(f"Moved the language preference from {legacy_file} to {get_language_file()}")

    try:
        legacy_file.unlink()
    except OSError:
        logger.warning(f"Could not delete the old language file {legacy_file}", exc_info=True)
        return
    try:
        legacy_dir.rmdir()  # only succeeds when the folder is empty
    except OSError:
        pass


def load_saved_language() -> str | None:
    """
    Return the saved language choice, or None if there is none.

    Moves a language file from the old location first.
    """
    try:
        migrate_legacy_language_file()
    except Exception as e:  # noqa: BLE001 - startup must not fail here
        logger.debug(f"Language file migration failed: {e}")
    return _read_language_file(get_language_file())


# Languages the app knows how to describe: code -> (native name, English
# name, right-to-left). A language shows in Settings when it has a block in
# TRANSLATIONS; this table only gives its names and its reading direction.
# scripts/i18n_import.py --new adds a line here for a code that is not listed.
LANGUAGE_INFO: dict[str, tuple[str, str, bool]] = {
    "en": ("English", "English", False),
    "he": ("עברית", "Hebrew", True),
    "ar": ("العربية", "Arabic", True),
    "fa": ("فارسی", "Persian", True),
    "ur": ("اردو", "Urdu", True),
    "yi": ("ייִדיש", "Yiddish", True),
    "cs": ("Čeština", "Czech", False),
    "da": ("Dansk", "Danish", False),
    "de": ("Deutsch", "German", False),
    "el": ("Ελληνικά", "Greek", False),
    "es": ("Español", "Spanish", False),
    "fi": ("Suomi", "Finnish", False),
    "fr": ("Français", "French", False),
    "hi": ("हिन्दी", "Hindi", False),
    "hu": ("Magyar", "Hungarian", False),
    "id": ("Bahasa Indonesia", "Indonesian", False),
    "it": ("Italiano", "Italian", False),
    "ja": ("日本語", "Japanese", False),
    "ko": ("한국어", "Korean", False),
    "nl": ("Nederlands", "Dutch", False),
    "no": ("Norsk", "Norwegian", False),
    "pl": ("Polski", "Polish", False),
    "pt": ("Português", "Portuguese", False),
    "ro": ("Română", "Romanian", False),
    "ru": ("Русский", "Russian", False),
    "sv": ("Svenska", "Swedish", False),
    "th": ("ไทย", "Thai", False),
    "tr": ("Türkçe", "Turkish", False),
    "uk": ("Українська", "Ukrainian", False),
    "vi": ("Tiếng Việt", "Vietnamese", False),
    "zh": ("中文", "Chinese", False),
}

# Display names that the app has always used for the two first languages
_LEGACY_DISPLAY_NAMES = {"en": "English / אנגלית", "he": "עברית / Hebrew"}


def is_rtl_language(language_code: str) -> bool:
    """True if the language is written right to left (Hebrew, Arabic, ...)."""
    info = LANGUAGE_INFO.get(language_code) or LANGUAGE_INFO.get(language_code.split("-")[0])
    return bool(info and info[2])


def language_display_name(language_code: str) -> str:
    """Name for the language list: "Native / English", or the code if the language is not in the table."""
    if language_code in _LEGACY_DISPLAY_NAMES:
        return _LEGACY_DISPLAY_NAMES[language_code]
    info = LANGUAGE_INFO.get(language_code)
    if info is None:
        return language_code
    native, english, _rtl = info
    return native if native == english else f"{native} / {english}"


class TranslationManager:
    """
    Manages translations and language switching.

    Automatically detects system language and provides RTL support (Hebrew, Arabic, Persian, Urdu, Yiddish).
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
            Language code of a block in TRANSLATIONS
        """
        # Check for saved language preference (v1.7.0)
        saved_lang = load_saved_language()
        if saved_lang is not None:
            logger.info(f"Loaded saved language preference: {saved_lang}")
            return saved_lang

        # Fall back to system locale detection
        try:
            # Get system locale
            system_locale = locale.getdefaultlocale()[0]

            if system_locale:
                lang_code = system_locale.split("_")[0].lower()
                if lang_code == "iw":  # old Hebrew code
                    lang_code = "he"

                # Use the system language when the app has it
                if lang_code in TRANSLATIONS:
                    logger.info(f"Detected system language: {lang_code}")
                    return lang_code

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
            language_code: Language code of a block in TRANSLATIONS
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
            True if the language is RTL (Hebrew, Arabic, Persian, Urdu, Yiddish), False otherwise
        """
        return is_rtl_language(self.current_language)

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
            # A key that the language does not have yet falls back to English.
            text = TRANSLATIONS[self.current_language].get(key)
            if text is None:
                text = TRANSLATIONS["en"].get(key, key)

            # Apply formatting if kwargs provided
            if kwargs:
                text = text.format(**kwargs)

            if self.is_rtl():
                text = _end_rtl_paren(key, text)
            return text
        except Exception as e:
            logger.warning(f"Translation error for key '{key}': {e}")
            return key

    def get_available_languages(self) -> dict[str, str]:
        """
        Get the languages that have a block in TRANSLATIONS (English first, then Hebrew, then the rest by code).

        Returns:
            Dict mapping language codes to display names
        """
        codes = ["en"] + [code for code in ("he",) if code in TRANSLATIONS]
        codes += sorted(code for code in TRANSLATIONS if code not in codes)
        return {code: language_display_name(code) for code in codes}

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


# Right-to-left mark (all RTL languages). A ")", ":" or "." at the very end of a right-to-left
# string that comes after left-to-right text, as in "(info.json)", "(Ctrl+V)"
# or the Hebrew "yt-dlp engine:" label, takes the direction of that text and is
# drawn on the wrong side. One RLM after it fixes that and draws nothing. File
# dialog filters are left out, because Qt reads the "(*.csv)" part of a filter.
_RLM = "\u200f"

# Last characters that get the RLM
_RTL_END_MARKS = (")", ":", ".")


def _end_rtl_paren(key: str, text: str) -> str:
    """Add an RLM after a ")", ":" or "." at the end of an RTL string (not filter_* keys)."""
    if text.endswith(_RTL_END_MARKS) and not key.startswith("filter_"):
        return text + _RLM
    return text


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


def tr_count(key: str, count: int, **kwargs) -> str:
    """
    Translate a text that holds a number, with a separate text for exactly one.

    Hebrew needs another form for 1 ("הורדה אחת ממתינה", not "1 ממתינות").
    The singular text lives under ``<key>_one``. Without that key the plain
    ``key`` is used for every number. ``{count}`` is always available.

    Args:
        key: Translation key of the "many" text
        count: The number
        **kwargs: Format parameters

    Returns:
        Translated string
    """
    manager = get_translation_manager()
    one_key = f"{key}_one"
    if count == 1 and one_key in TRANSLATIONS.get(manager.get_language(), {}):
        return manager.translate(one_key, count=count, **kwargs)
    return manager.translate(key, count=count, **kwargs)
