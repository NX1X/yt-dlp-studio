"""
yt-dlp wrapper for YT-DLP Studio.

This module provides a wrapper interface to the yt-dlp library.
It handles video information extraction and downloading.
"""

import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..models.video_info import VideoInfo
from ..utils.logger import get_logger

logger = get_logger()

# Add vendored yt_dlp_engine to Python path
# This allows us to import the bundled yt-dlp.
# In a PyInstaller bundle the engine is extracted to <_MEIPASS>/yt_dlp_engine
# (see packaging/build.spec datas); running from source it lives at
# <project_root>/vendor/yt_dlp_engine.
if getattr(sys, "frozen", False):
    _bundle_dir = getattr(sys, "_MEIPASS", None)
    _engine_path = Path(_bundle_dir) / "yt_dlp_engine" if _bundle_dir else None
else:
    _current_dir = Path(__file__).resolve().parent
    _project_root = _current_dir.parent.parent
    _engine_path = _project_root / "vendor" / "yt_dlp_engine"

if _engine_path is not None and str(_engine_path) not in sys.path:
    sys.path.insert(0, str(_engine_path))
    logger.debug(f"Added yt_dlp_engine to path: {_engine_path}")

# Now import yt_dlp
try:
    from yt_dlp import YoutubeDL
    from yt_dlp import version as ytdlp_version

    logger.info(f"yt-dlp imported successfully. Version: {ytdlp_version.__version__}")
except ImportError as e:
    logger.error(f"Failed to import yt-dlp: {e}")
    raise ImportError("Could not import yt-dlp. Please ensure yt_dlp_engine is properly set up.") from e


# Resolve the impersonation target once. yt-dlp wants an ImpersonateTarget
# instance, not a string. We default to "chrome" because YouTube has the
# best behavior with a Chrome fingerprint (no 429 on subtitle endpoints
# in practice). If curl_cffi is not installed the import below will fail,
# in which case we simply do not pass `impersonate` to yt-dlp and the
# original "no impersonate target is available" warning resurfaces.
try:
    from yt_dlp.networking.impersonate import ImpersonateTarget

    _DEFAULT_IMPERSONATE_TARGET: "ImpersonateTarget | None" = ImpersonateTarget.from_str("chrome")
    logger.info(f"Impersonation target resolved: {_DEFAULT_IMPERSONATE_TARGET}")
except Exception as e:
    _DEFAULT_IMPERSONATE_TARGET = None
    logger.warning(f"Could not resolve impersonation target ({e}); falling back to no impersonation.")


def _make_subtitles_non_fatal(ydl: "YoutubeDL") -> None:
    """Patch a YoutubeDL instance so subtitle download failures cannot abort the video.

    yt-dlp's ``_write_subtitles`` raises ``DownloadError`` whenever a subtitle HTTP
    request fails (e.g. HTTP 429 from YouTube's per-IP rate limiter). With
    ``ignoreerrors='only_download'`` this still propagates and aborts the whole
    video. Setting ``ignoreerrors=True`` would silence the subtitle error but
    also mask real video download errors, which we want to surface.

    This wraps the instance method so a subtitle failure becomes a warning,
    returns ``[]``, and lets the video download proceed.
    """
    _original_write_subtitles = ydl._write_subtitles

    def _safe_write_subtitles(info_dict, filename):
        try:
            return _original_write_subtitles(info_dict, filename)
        except Exception as e:
            ydl.report_warning(
                f"Subtitle download failed ({e}); continuing without subtitles."
            )
            return []

    ydl._write_subtitles = _safe_write_subtitles


class YtDlpWrapper:
    """
    Wrapper for yt-dlp functionality.

    Provides a simplified interface for extracting video information
    and downloading videos using yt-dlp.

    Attributes:
        progress_callback: Optional callback function for progress updates
    """

    # Class-level caches for FFmpeg and Deno paths (avoid repeated filesystem scans)
    _ffmpeg_cache = None
    _ffmpeg_cache_checked = False
    _deno_cache = None
    _deno_cache_checked = False

    def __init__(self, progress_callback: Callable[[dict[str, Any]], None] | None = None):
        """
        Initialize YtDlpWrapper.

        Args:
            progress_callback: Function to call with progress updates
                              Receives dict with progress data from yt-dlp
        """
        self.progress_callback = progress_callback
        self._download_cancelled = False
        self._last_error = None
        self._last_error_type = None
        logger.debug("YtDlpWrapper initialized")

    def _get_ffmpeg_location(self) -> str | None:
        """
        Find FFmpeg executable location (cached after first lookup).

        Checks multiple locations:
        1. PyInstaller bundled location (when running from .exe)
        2. System PATH
        3. Current directory

        Returns:
            Path to directory containing ffmpeg, or None if not found
        """
        # Return cached result if already checked
        if YtDlpWrapper._ffmpeg_cache_checked:
            return YtDlpWrapper._ffmpeg_cache

        import shutil

        result = None

        # Method 1: Check if running from PyInstaller bundle
        if getattr(sys, "frozen", False):
            bundle_dir = getattr(sys, "_MEIPASS", None)
            if bundle_dir:
                ffmpeg_path = os.path.join(bundle_dir, "ffmpeg.exe")
                if os.path.exists(ffmpeg_path):
                    logger.debug(f"Found FFmpeg in bundle: {bundle_dir}")
                    result = bundle_dir

        # Method 2: Check system PATH
        if result is None:
            ffmpeg_exe = shutil.which("ffmpeg")
            if ffmpeg_exe:
                ffmpeg_dir = os.path.dirname(ffmpeg_exe)
                logger.debug(f"Found FFmpeg in PATH: {ffmpeg_dir}")
                result = ffmpeg_dir

        # Method 3: Check current directory
        if result is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            ffmpeg_path = os.path.join(current_dir, "ffmpeg.exe")
            if os.path.exists(ffmpeg_path):
                logger.debug(f"Found FFmpeg in current dir: {current_dir}")
                result = current_dir

        if result is None:
            logger.warning("FFmpeg not found in any location")

        # Cache the result
        YtDlpWrapper._ffmpeg_cache = result
        YtDlpWrapper._ffmpeg_cache_checked = True
        return result

    def _get_deno_location(self) -> str | None:
        """
        Find Deno executable location (cached after first lookup).

        Checks multiple locations:
        1. PyInstaller bundled location (when running from .exe)
        2. Project-local deno/ folder (development)
        3. System PATH

        Returns:
            Path to deno executable, or None if not found
        """
        # Return cached result if already checked
        if YtDlpWrapper._deno_cache_checked:
            return YtDlpWrapper._deno_cache

        import shutil

        result = None

        # Method 1: Check if running from PyInstaller bundle
        if getattr(sys, "frozen", False):
            bundle_dir = getattr(sys, "_MEIPASS", None)
            if bundle_dir:
                deno_path = os.path.join(bundle_dir, "deno.exe")
                if os.path.exists(deno_path):
                    logger.debug(f"Found Deno in bundle: {deno_path}")
                    result = deno_path

        # Method 2: Check project-local deno/ folder
        if result is None:
            deno_local = _project_root / "deno" / "deno.exe"
            if deno_local.exists():
                logger.debug(f"Found Deno locally: {deno_local}")
                result = str(deno_local)

        # Method 3: Check system PATH
        if result is None:
            deno_exe = shutil.which("deno")
            if deno_exe:
                logger.debug(f"Found Deno in PATH: {deno_exe}")
                result = deno_exe

        if result is None:
            logger.warning("Deno not found - YouTube JS challenges may be limited")

        # Cache the result
        YtDlpWrapper._deno_cache = result
        YtDlpWrapper._deno_cache_checked = True
        return result

    def get_video_info(self, url: str) -> VideoInfo | None:
        """
        Extract video information without downloading.

        Args:
            url: Video URL

        Returns:
            VideoInfo object with metadata, or None on error

        Example:
            >>> wrapper = YtDlpWrapper()
            >>> info = wrapper.get_video_info("https://youtube.com/watch?v=...")
            >>> print(info.title)
        """
        logger.info(f"Extracting video info: {url}")

        # Detect FFmpeg location (may be needed for some extractors)
        ffmpeg_location = self._get_ffmpeg_location()

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "skip_download": True,
            "noplaylist": True,  # Never process the full playlist - only the single video
        }

        # Set FFmpeg location if found
        if ffmpeg_location:
            ydl_opts["ffmpeg_location"] = ffmpeg_location

        # Set Deno JS runtime path if found (for YouTube JS challenge solving)
        deno_path = self._get_deno_location()
        if deno_path:
            ydl_opts["js_runtimes"] = {"deno": {"path": deno_path}}

        # Browser impersonation (curl_cffi). Set when available so YouTube
        # treats us like a real browser and stops 429'ing subtitle/metadata
        # endpoints.
        if _DEFAULT_IMPERSONATE_TARGET is not None:
            ydl_opts["impersonate"] = _DEFAULT_IMPERSONATE_TARGET

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=False)

                if info_dict is None:
                    logger.error("No information extracted from URL")
                    return None

                video_info = VideoInfo.from_yt_dlp_dict(info_dict)
                logger.info(f"Video info extracted: {video_info.title}")
                return video_info

        except Exception as e:
            logger.error(f"Error extracting video info: {e}")
            return None

    def get_available_subtitles(self, url: str) -> dict:
        """
        Get available subtitle languages for a video.

        Args:
            url: Video URL

        Returns:
            Dictionary of {lang_code: {'name': lang_name, 'auto': is_auto_generated}}

        Example:
            >>> wrapper = YtDlpWrapper()
            >>> subs = wrapper.get_available_subtitles("https://youtube.com/watch?v=...")
            >>> print(subs)
            {'en': {'name': 'English', 'auto': False}, 'es': {'name': 'Spanish', 'auto': True}}
        """
        logger.info(f"Fetching available subtitles: {url}")

        # Detect FFmpeg location
        ffmpeg_location = self._get_ffmpeg_location()

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "listsubtitles": False,  # Don't print to console
            "noplaylist": True,  # Never process the full playlist — only the single video
        }

        if ffmpeg_location:
            ydl_opts["ffmpeg_location"] = ffmpeg_location

        # Set Deno JS runtime path if found
        deno_path = self._get_deno_location()
        if deno_path:
            ydl_opts["js_runtimes"] = {"deno": {"path": deno_path}}

        # Browser impersonation (curl_cffi). Subtitle listings are an HTTPS
        # endpoint that is particularly aggressive about rate-limiting clients
        # that do not impersonate a browser.
        if _DEFAULT_IMPERSONATE_TARGET is not None:
            ydl_opts["impersonate"] = _DEFAULT_IMPERSONATE_TARGET

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=False)

                if info_dict is None:
                    logger.warning("No information extracted from URL")
                    return {}

                result = {}

                # Get manual subtitles
                manual_subs = info_dict.get("subtitles", {})
                for lang_code, _sub_list in manual_subs.items():
                    result[lang_code] = {"name": self._get_language_name(lang_code), "auto": False}

                # Get automatic subtitles
                auto_subs = info_dict.get("automatic_captions", {})
                for lang_code, _sub_list in auto_subs.items():
                    if lang_code not in result:  # Prefer manual over auto
                        result[lang_code] = {"name": self._get_language_name(lang_code), "auto": True}

                logger.info(
                    f"Found {len(result)} subtitle languages ({len(manual_subs)} manual, {len(auto_subs)} auto)"
                )

                # Debug: Log first 20 language codes to help troubleshoot
                if result:
                    sample_langs = list(result.keys())[:20]
                    logger.debug(f"Sample of available languages: {', '.join(sample_langs)}")

                    # Check if Hebrew is available (YouTube uses both 'he' and 'iw' for Hebrew)
                    if "he" in result or "iw" in result:
                        logger.info("✓ Hebrew subtitles are available!")
                    else:
                        logger.warning("⚠ Hebrew subtitles NOT found in available languages")

                return result

        except Exception as e:
            logger.error(f"Error fetching subtitles: {e}")
            return {}

    def _get_language_name(self, lang_code: str) -> str:
        """
        Convert language code to display name.

        Args:
            lang_code: ISO language code (e.g., 'en', 'es', 'fr')

        Returns:
            Human-readable language name
        """
        # Common language codes mapping
        language_names = {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "ja": "Japanese",
            "ko": "Korean",
            "zh": "Chinese",
            "zh-Hans": "Chinese (Simplified)",
            "zh-Hant": "Chinese (Traditional)",
            "ar": "Arabic",
            "hi": "Hindi",
            "he": "Hebrew",
            "iw": "Hebrew",  # Old ISO 639 code for Hebrew (still used by YouTube)
            "nl": "Dutch",
            "pl": "Polish",
            "tr": "Turkish",
            "sv": "Swedish",
            "da": "Danish",
            "no": "Norwegian",
            "fi": "Finnish",
            "cs": "Czech",
            "el": "Greek",
            "hu": "Hungarian",
            "ro": "Romanian",
            "th": "Thai",
            "vi": "Vietnamese",
            "id": "Indonesian",
            "uk": "Ukrainian",
        }

        return language_names.get(lang_code, lang_code.upper())

    def download(
        self,
        url: str,
        output_dir: str,
        format_string: str,
        audio_only: bool = False,
        audio_quality: str = "192",
        download_thumbnail: bool = True,
        download_subtitles: bool = False,
        subtitle_languages: str = "en",
        speed_limit: int = 0,
        video_container: str | None = None,
        audio_format: str = "mp3",
        selected_subtitles: list | None = None,
        download_metadata: bool = False,
        download_comments: bool = False,
        auto_number_duplicates: bool = True,
    ) -> bool:
        """
        Download video from URL with advanced options.

        Args:
            url: Video URL
            output_dir: Directory to save the file
            format_string: yt-dlp format string (e.g., "best", "bestvideo+bestaudio")
            audio_only: If True, extract audio only as MP3
            audio_quality: Audio quality in kbps (e.g., "128", "192", "256", "320")
            download_thumbnail: If True, download and convert thumbnail to JPG
            download_subtitles: If True, download subtitles
            subtitle_languages: Comma-separated language codes (e.g., "en,es,he")
            speed_limit: Download speed limit in KB/s (0 = unlimited)
            video_container: Video container format (e.g., "mp4", "mkv", "webm", None for auto)
            audio_format: Audio format for extraction (e.g., "mp3", "m4a", "opus", "flac", "wav", "vorbis")
            selected_subtitles: List of specific subtitle languages (overrides subtitle_languages if provided)
            download_metadata: If True, download metadata (description, comments, etc.) as separate files
            download_comments: If True, download comments to a separate .txt file (v2.0.0)
            auto_number_duplicates: If True, add (1), (2) etc. to duplicate files instead of failing

        Returns:
            True if download successful, False otherwise

        Example:
            >>> wrapper = YtDlpWrapper(progress_callback=my_callback)
            >>> success = wrapper.download(
            ...     "https://youtube.com/watch?v=...",
            ...     "/downloads",
            ...     "bestvideo+bestaudio/best",
            ...     audio_only=False,
            ...     audio_quality="192",
            ...     download_thumbnail=True,
            ...     download_subtitles=True,
            ...     selected_subtitles=["en", "es"],
            ...     speed_limit=1024,
            ...     video_container="mp4",
            ...     audio_format="mp3",
            ...     download_metadata=True,
            ...     auto_number_duplicates=True
            ... )
        """
        logger.info("=" * 80)
        logger.info("STARTING DOWNLOAD")
        logger.info("=" * 80)
        logger.info(f"URL: {url}")
        logger.info(f"Output Directory: {output_dir}")
        logger.info(f"Format String: {format_string}")
        logger.info(f"Audio Only: {audio_only}")
        audio_quality_label = "Best (VBR)" if audio_quality == "0" else f"{audio_quality}kbps"
        logger.info(f"Audio Quality: {audio_quality_label}")
        logger.info(f"Audio Format: {audio_format}")
        logger.info(f"Video Container: {video_container}")
        logger.info(f"Download Thumbnail: {download_thumbnail}")
        logger.info(f"Download Subtitles: {download_subtitles}")
        logger.info(f"Subtitle Languages: {subtitle_languages}")
        logger.info(f"Speed Limit: {speed_limit}KB/s")
        logger.info("=" * 80)

        self._download_cancelled = False

        # Detect FFmpeg location (for PyInstaller bundled exe)
        logger.info("\n[STEP 1/5] Detecting FFmpeg location...")
        ffmpeg_location = self._get_ffmpeg_location()
        if ffmpeg_location:
            logger.info(f"✓ FFmpeg found at: {ffmpeg_location}")
        else:
            logger.warning("⚠ FFmpeg not found - some downloads may fail")

        # Build yt-dlp options
        logger.info("\n[STEP 2/5] Building yt-dlp options...")

        # Smart filename template with quality
        if audio_only:
            filename_template = "%(title)s_%(quality)s.%(ext)s"
        else:
            filename_template = "%(title)s_%(height)sp.%(ext)s"

        ydl_opts = {
            "format": format_string if not audio_only else "bestaudio",  # Force audio-only for audio downloads
            "outtmpl": os.path.join(output_dir, filename_template),
            "progress_hooks": [self._progress_hook],
            "quiet": False,
            "no_warnings": False,
            "windowsfilenames": True,  # Use Windows-safe filenames (removes invalid characters)
            # IMPORTANT: yt-dlp's "only_download" does NOT silence subtitle errors.
            # YoutubeDL._write_subtitles raises DownloadError unless ignoreerrors is
            # literally True, which would also mask real video download errors. We
            # keep "only_download" here and instead wrap _write_subtitles below so
            # that a subtitle HTTP 429 cannot abort the video download itself.
            "ignoreerrors": "only_download",
            "noplaylist": True,  # Never download a full playlist - always download the single video
        }

        # Handle duplicate files
        if auto_number_duplicates:
            # yt-dlp will automatically add (1), (2), etc. to duplicates
            ydl_opts["nooverwrites"] = False  # Allow yt-dlp to handle numbering
            logger.info("✓ Auto-numbering duplicates enabled")
        else:
            # Don't overwrite existing files (will skip if exists)
            ydl_opts["nooverwrites"] = True
            logger.info("✓ Skip duplicates enabled (won't overwrite)")

        logger.info("✓ Base options created")
        logger.info(f"✓ Filename template: {filename_template}")

        # Set FFmpeg location if found
        if ffmpeg_location:
            ydl_opts["ffmpeg_location"] = ffmpeg_location

        # Set Deno JS runtime path if found (for YouTube JS challenge solving)
        deno_path = self._get_deno_location()
        if deno_path:
            ydl_opts["js_runtimes"] = {"deno": {"path": deno_path}}

        # Browser impersonation (curl_cffi). Without this, YouTube's
        # subtitle and comments endpoints return HTTP 429 on what looks like
        # an automated client, which in turn would have aborted the whole
        # video download (see ignoreerrors comment above).
        if _DEFAULT_IMPERSONATE_TARGET is not None:
            ydl_opts["impersonate"] = _DEFAULT_IMPERSONATE_TARGET
            logger.info(f"✓ Browser impersonation enabled: {_DEFAULT_IMPERSONATE_TARGET}")
        else:
            logger.warning("⚠ Browser impersonation unavailable (curl_cffi missing); some endpoints may 429")

        # Set video container format if specified (only for video downloads - not audio-only)
        if video_container is not None and not audio_only:
            ydl_opts["merge_output_format"] = video_container
            logger.info(f"✓ Video container format set: {video_container}")

        # Speed limit (convert KB/s to bytes/s)
        if speed_limit > 0:
            ydl_opts["ratelimit"] = speed_limit * 1024
            logger.info(f"✓ Speed limit applied: {speed_limit}KB/s")

        # Thumbnail download
        if download_thumbnail:
            ydl_opts["writethumbnail"] = True
            logger.info("✓ Thumbnail download enabled")

        # Subtitle download
        if download_subtitles:
            ydl_opts["writesubtitles"] = True
            ydl_opts["writeautomaticsub"] = True  # Fallback to auto-generated

            # Use selected_subtitles if provided, otherwise use subtitle_languages
            if selected_subtitles:
                langs = selected_subtitles
                logger.info(f"✓ Using selected subtitles: {langs}")
            else:
                langs = [lang.strip() for lang in subtitle_languages.split(",") if lang.strip()]
                logger.info(f"✓ Using manual subtitle languages: {langs}")

            ydl_opts["subtitleslangs"] = langs
            ydl_opts["subtitlesformat"] = "srt"
            # YouTube rate-limits subtitle requests aggressively without browser
            # impersonation. Sleeping ~2s between subtitle downloads avoids the
            # HTTP 429 cascade that would otherwise abort the video download.
            ydl_opts["sleep_interval_subtitles"] = 2
            logger.info(f"✓ Subtitle download enabled: {len(langs)} languages (2s spacing)")

        # Metadata download (v2.0.0)
        if download_metadata:
            ydl_opts["writeinfojson"] = True  # Save video metadata as JSON
            ydl_opts["clean_infojson"] = False  # Keep all fields in JSON
            ydl_opts["writedescription"] = True  # Save video description as separate file
            ydl_opts["writeannotations"] = True  # Save annotations if available
            ydl_opts["getcomments"] = True  # Download comments (can be slow for popular videos)

            # Add postprocessor to format JSON with proper indentation
            if "postprocessors" not in ydl_opts:
                ydl_opts["postprocessors"] = []

            ydl_opts["postprocessors"].insert(0, {"key": "FFmpegMetadata", "add_infojson": "if_exists"})

            logger.info("✓ Metadata download enabled (JSON, description, annotations, comments)")
        else:
            logger.info("Metadata download: disabled")

        # Comments download (v2.0.0 - separate from metadata)
        if download_comments:
            ydl_opts["getcomments"] = True  # Fetch comments from video
            ydl_opts["writeinfojson"] = True  # Need JSON to extract comments
            logger.info("✓ Comments download enabled (will be saved as .txt file)")
        else:
            logger.info("Comments download: disabled")

        # When subtitles AND comments are both enabled, the comment phase
        # burns through YouTube's per-IP rate-limit budget BEFORE the
        # subtitle HTTP request goes out, so the subtitle download gets
        # 429'd even with Chrome impersonation. Adding a 1s gap between
        # every API request pre-empts that 429 cascade. It costs ~10-30s
        # extra during the comment phase but lets subtitles actually land.
        # Single-flag scenarios do not need this (no rate-limit pressure).
        if download_subtitles and (download_comments or download_metadata):
            ydl_opts["sleep_interval_requests"] = 1
            logger.info("✓ Inter-request spacing: 1s (subtitles + comments/metadata combo)")

        # Build postprocessors list
        logger.info("\n[STEP 3/5] Configuring postprocessors...")
        postprocessors = []

        # Audio extraction
        if audio_only:
            postprocessors.append(
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": audio_format,
                    "preferredquality": audio_quality,
                    "nopostoverwrites": False,  # Always convert, even if already in target format
                }
            )
            # Force post-processing to always run
            ydl_opts["keepvideo"] = False  # Remove video after extracting audio
            quality_display = "Best (VBR)" if audio_quality == "0" else f"{audio_quality}kbps"
            logger.info(f"✓ Audio extraction enabled ({audio_format.upper()}, {quality_display})")
            logger.info(f"✓ Forcing conversion to {audio_format} format")

        # Thumbnail converter
        if download_thumbnail:
            postprocessors.append(
                {
                    "key": "FFmpegThumbnailsConvertor",
                    "format": "jpg",
                }
            )
            logger.info("✓ Thumbnail converter enabled (JPG)")

        # Subtitle embedder (only if not audio-only)
        if download_subtitles and not audio_only:
            postprocessors.append(
                {
                    "key": "FFmpegEmbedSubtitle",
                }
            )
            logger.info("✓ Subtitle embedder enabled")

        if postprocessors:
            ydl_opts["postprocessors"] = postprocessors
            logger.info(f"✓ Total postprocessors: {len(postprocessors)}")
        else:
            logger.info("✓ No postprocessors required")

        # Log complete ydl_opts (excluding progress_hooks for readability)
        logger.info("\n[STEP 4/5] Final yt-dlp configuration:")
        ydl_opts_log = {k: v for k, v in ydl_opts.items() if k != "progress_hooks"}
        logger.info(json.dumps(ydl_opts_log, indent=2, default=str))

        try:
            logger.info("\n[STEP 5/5] Initializing yt-dlp and starting download...")
            with YoutubeDL(ydl_opts) as ydl:
                # Check if cancelled before starting
                if self._download_cancelled:
                    logger.info("Download cancelled before starting")
                    return False

                # Make subtitle write failures non-fatal so a YouTube 429 on
                # subtitles cannot abort the video download.
                if download_subtitles:
                    _make_subtitles_non_fatal(ydl)

                logger.info("✓ yt-dlp initialized successfully")
                logger.info(f"✓ Starting download from: {url}")

                # Download the video
                info_dict = ydl.extract_info(url, download=True)

                # Check if cancelled during download
                if self._download_cancelled:
                    logger.info("Download was cancelled")
                    return False

                # Post-process metadata files to make them user-friendly
                if download_metadata and info_dict:
                    try:
                        import glob
                        import time
                        from datetime import datetime

                        # Search for recently created metadata files (within last 60 seconds)
                        pattern = os.path.join(output_dir, "*.info.json")
                        json_files = glob.glob(pattern)
                        recent_files = [f for f in json_files if time.time() - os.path.getmtime(f) < 60]

                        if recent_files:
                            json_file = max(recent_files, key=os.path.getmtime)
                            base_filename = os.path.splitext(json_file)[0]

                            logger.info(f"Post-processing metadata files for: {os.path.basename(base_filename)}")

                            # 1. Read JSON data
                            with open(json_file, encoding="utf-8") as f:
                                data = json.load(f)

                            # 2. Create human-readable metadata.txt file
                            metadata_txt = f"{base_filename}_metadata.txt"
                            with open(metadata_txt, "w", encoding="utf-8") as f:
                                f.write("=" * 80 + "\n")
                                f.write("VIDEO METADATA\n")
                                f.write("=" * 80 + "\n\n")

                                # Essential information
                                f.write("[ESSENTIAL INFORMATION]\n")
                                f.write(f"Title: {data.get('title', 'N/A')}\n")
                                f.write(f"Uploader: {data.get('uploader', 'N/A')}\n")
                                f.write(f"Channel: {data.get('channel', 'N/A')}\n")
                                f.write(f"Channel ID: {data.get('channel_id', 'N/A')}\n")
                                f.write(f"Video ID: {data.get('id', 'N/A')}\n")
                                f.write(f"URL: {data.get('webpage_url', 'N/A')}\n\n")

                                # Upload date
                                upload_date = data.get("upload_date", "")
                                if upload_date and len(upload_date) == 8:
                                    try:
                                        date_obj = datetime.strptime(upload_date, "%Y%m%d")
                                        formatted_date = date_obj.strftime("%B %d, %Y")
                                        f.write(f"[UPLOAD DATE]\n{formatted_date}\n\n")
                                    except:
                                        f.write(f"[UPLOAD DATE]\n{upload_date}\n\n")

                                # Duration
                                duration = data.get("duration", 0)
                                if duration:
                                    minutes, seconds = divmod(int(duration), 60)
                                    hours, minutes = divmod(minutes, 60)
                                    if hours > 0:
                                        duration_str = f"{hours}h {minutes}m {seconds}s"
                                    else:
                                        duration_str = f"{minutes}m {seconds}s"
                                    f.write(f"[DURATION]\n{duration_str}\n\n")

                                # Statistics
                                f.write("[STATISTICS]\n")
                                views = data.get("view_count", 0)
                                likes = data.get("like_count", 0)
                                comments = data.get("comment_count", 0)
                                if views:
                                    f.write(f"Views: {views:,}\n")
                                if likes:
                                    f.write(f"Likes: {likes:,}\n")
                                if comments:
                                    f.write(f"Comments: {comments:,}\n")
                                f.write("\n")

                                # Video quality
                                f.write("[VIDEO QUALITY]\n")
                                f.write(f"Resolution: {data.get('width', 'N/A')}x{data.get('height', 'N/A')}\n")
                                f.write(f"FPS: {data.get('fps', 'N/A')}\n")
                                f.write(f"Format: {data.get('format', 'N/A')}\n")
                                f.write(f"Video Codec: {data.get('vcodec', 'N/A')}\n")
                                f.write(f"Audio Codec: {data.get('acodec', 'N/A')}\n\n")

                                # Categories and tags
                                categories = data.get("categories", [])
                                if categories:
                                    f.write("[CATEGORIES]\n")
                                    f.write(", ".join(categories) + "\n\n")

                                tags = data.get("tags", [])
                                if tags:
                                    f.write("[TAGS]\n")
                                    # Write tags in rows of 3-4 for readability
                                    for i in range(0, len(tags), 4):
                                        f.write(", ".join(tags[i : i + 4]) + "\n")
                                    f.write("\n")

                                # Thumbnail URL
                                thumbnail = data.get("thumbnail", "")
                                if thumbnail:
                                    f.write(f"[THUMBNAIL URL]\n{thumbnail}\n\n")

                                f.write("=" * 80 + "\n")
                                f.write("End of Metadata\n")
                                f.write("=" * 80 + "\n")

                            logger.info(f"✓ Created human-readable metadata: {os.path.basename(metadata_txt)}")

                            # 3. Rename .description file to .txt for better Windows compatibility
                            desc_file = f"{base_filename}.description"
                            desc_txt_file = f"{base_filename}_description.txt"
                            if os.path.exists(desc_file):
                                os.rename(desc_file, desc_txt_file)
                                logger.info(f"✓ Renamed description file to: {os.path.basename(desc_txt_file)}")

                            # 4. Format JSON file with proper indentation (keep for technical users)
                            with open(json_file, "w", encoding="utf-8") as f:
                                json.dump(data, f, indent=2, ensure_ascii=False)
                            logger.info("✓ Formatted JSON file with 2-space indentation")

                        else:
                            logger.warning("Could not find recently created JSON metadata file")

                    except Exception as e:
                        logger.error(f"Error post-processing metadata files: {e}", exc_info=True)

                # Post-process comments to TXT file (v2.0.0)
                if download_comments and info_dict:
                    try:
                        import glob
                        import time

                        logger.info("Post-processing comments to .txt file...")

                        # Wait a moment for yt-dlp to finish writing the JSON file
                        time.sleep(1)

                        # Search for recently created JSON files (within last 120 seconds to be safe)
                        pattern = os.path.join(output_dir, "*.info.json")
                        json_files = glob.glob(pattern)
                        recent_files = [f for f in json_files if time.time() - os.path.getmtime(f) < 120]

                        if recent_files:
                            json_file = max(recent_files, key=os.path.getmtime)
                            logger.info(f"Found JSON file: {os.path.basename(json_file)}")
                            base_filename = os.path.splitext(json_file)[0]

                            # Read JSON data to extract comments
                            with open(json_file, encoding="utf-8") as f:
                                data = json.load(f)

                            comments_list = data.get("comments", [])
                            logger.info(f"Found {len(comments_list)} comments in JSON file")

                            if comments_list:
                                # Add "Comments" to the filename (v3.0.0)
                                comments_txt = f"{base_filename} Comments.txt"
                                with open(comments_txt, "w", encoding="utf-8") as f:
                                    f.write("=" * 80 + "\n")
                                    f.write("VIDEO COMMENTS\n")
                                    f.write("=" * 80 + "\n\n")
                                    f.write(f"Video Title: {data.get('title', 'N/A')}\n")
                                    f.write(f"Total Comments: {len(comments_list):,}\n")
                                    f.write("=" * 80 + "\n\n")

                                    for i, comment in enumerate(comments_list, 1):
                                        author = comment.get("author", "Unknown")
                                        text = comment.get("text", "")
                                        likes = comment.get("like_count", 0)
                                        timestamp = comment.get("timestamp", 0)

                                        # Format timestamp if available
                                        time_str = ""
                                        if timestamp:
                                            try:
                                                from datetime import datetime

                                                dt = datetime.fromtimestamp(timestamp)
                                                time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                                            except:
                                                time_str = str(timestamp)

                                        f.write(f"[Comment #{i}]\n")
                                        f.write(f"Author: {author}\n")
                                        if time_str:
                                            f.write(f"Date: {time_str}\n")
                                        if likes > 0:
                                            f.write(f"Likes: {likes:,}\n")
                                        f.write(f"\n{text}\n")
                                        f.write("-" * 80 + "\n\n")

                                comments_name = os.path.basename(comments_txt)
                                logger.info(f"✓ Comments saved to: {comments_name} ({len(comments_list):,} comments)")

                                # If not downloading full metadata, delete the JSON file
                                if not download_metadata:
                                    try:
                                        os.remove(json_file)
                                        logger.info("✓ Cleaned up temporary JSON file")
                                    except OSError as cleanup_error:
                                        logger.debug(f"Could not remove temporary JSON file: {cleanup_error}")
                            else:
                                logger.warning("⚠ No comments found in video (comments may be disabled)")
                        else:
                            logger.warning("Could not find recently created JSON file for comments")

                    except Exception as e:
                        logger.error(f"Error extracting comments to TXT: {e}", exc_info=True)

                logger.info("\n" + "=" * 80)
                logger.info("✓✓✓ DOWNLOAD COMPLETED SUCCESSFULLY ✓✓✓")
                logger.info("=" * 80)
                return True

        except Exception as e:
            # Log detailed error information for debugging
            import traceback

            logger.error("\n" + "=" * 80)
            logger.error("✗✗✗ DOWNLOAD FAILED ✗✗✗")
            logger.error("=" * 80)
            logger.error(f"Error Type: {type(e).__name__}")
            logger.error(f"Error Message: {str(e)}")
            logger.error("-" * 80)
            logger.error("Full Traceback:")
            error_trace = traceback.format_exc()
            logger.error(error_trace)
            logger.error("=" * 80)

            # Store the error for UI to display
            self._last_error = str(e)
            self._last_error_type = type(e).__name__

            return False

    def cancel_download(self) -> None:
        """
        Cancel the current download.

        Note: This sets a flag but may not immediately stop the download.
        yt-dlp doesn't support graceful cancellation easily.
        """
        logger.info("Download cancellation requested")
        self._download_cancelled = True

    def _postprocess_metadata_files(self, output_dir: str, info_dict: dict[str, Any]) -> None:
        """
        Post-process metadata files to make them more readable.

        Changes:
        1. Format .info.json with proper indentation (instead of single line)
        2. Rename .description to .txt (more user-friendly extension)

        Args:
            output_dir: Directory where files were downloaded
            info_dict: Video info dictionary from yt-dlp
        """
        try:
            import glob

            # Since yt-dlp uses windowsfilenames=True, we need to find files by pattern
            # Get the height from info_dict
            height = info_dict.get("height", "NA")

            # Search for files with the title in the name (sanitized by yt-dlp)
            # Use glob to find actual files since filename may be sanitized differently
            search_pattern = os.path.join(output_dir, f"*{height}p.*")
            matching_files = glob.glob(search_pattern)

            # Find the base filename from actual files
            base_filename = None
            for file_path in matching_files:
                if file_path.endswith(".info.json"):
                    base_filename = os.path.splitext(file_path)[0]
                    break

            if not base_filename:
                # Try to find any metadata file
                for file_path in matching_files:
                    if file_path.endswith(".description") or file_path.endswith(".webp") or file_path.endswith(".jpg"):
                        base_filename = os.path.splitext(file_path)[0]
                        break

            if base_filename:
                # 1. Format .info.json file with proper indentation
                json_file = f"{base_filename}.info.json"
                if os.path.exists(json_file):
                    try:
                        with open(json_file, encoding="utf-8") as f:
                            data = json.load(f)

                        # Rewrite with beautiful formatting
                        with open(json_file, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)

                        logger.info("✓ Formatted JSON file with proper indentation")
                    except Exception as e:
                        logger.warning(f"Could not format JSON file: {e}")

                # 2. Rename .description to .txt
                desc_file = f"{base_filename}.description"
                txt_file = f"{base_filename}.txt"

                if os.path.exists(desc_file):
                    try:
                        # Remove existing .txt file if it exists
                        if os.path.exists(txt_file):
                            os.remove(txt_file)

                        os.rename(desc_file, txt_file)
                        logger.info("✓ Renamed .description to .txt for better readability")
                    except Exception as e:
                        logger.warning(f"Could not rename description file: {e}")
            else:
                logger.debug("Could not find base filename for metadata post-processing")

        except Exception as e:
            logger.warning(f"Error during metadata post-processing: {e}")

    def _progress_hook(self, d: dict[str, Any]) -> None:
        """
        Internal progress hook called by yt-dlp.

        Args:
            d: Progress dictionary from yt-dlp
        """
        # Check if download was cancelled
        if self._download_cancelled:
            logger.debug("Progress hook detected cancellation")
            # Note: yt-dlp doesn't have a clean way to stop mid-download
            # This flag is mainly for post-download checking

        # Call user's progress callback if provided
        if self.progress_callback:
            try:
                self.progress_callback(d)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")

    @staticmethod
    def get_ytdlp_version() -> str:
        """
        Get yt-dlp version string.

        Returns:
            Version string
        """
        try:
            return ytdlp_version.__version__
        except:
            return "Unknown"
