"""
yt-dlp wrapper for YT-DLP Studio.

This module provides a wrapper interface to the yt-dlp library.
It handles video information extraction and downloading.
"""

import json
import os
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..models.video_info import VideoInfo
from ..utils.logger import get_logger
from .download_options import DownloadOptions, build_ydl_opts
from .side_files import write_side_files

logger = get_logger()

# Add vendored yt_dlp_engine to Python path
# This allows us to import the bundled yt-dlp.
# In a PyInstaller bundle the engine is extracted to <_MEIPASS>/yt_dlp_engine
# (see packaging/build.spec datas); running from source it lives at
# <project_root>/vendor/yt_dlp_engine.
# Project root is resolved unconditionally. A source run keeps an
# auto-installed Deno in <project_root>/deno/ (see _get_deno_location). A
# frozen build that does not bundle Deno (the Linux build) downloads it to
# the app data folder instead, never next to the executable.
_current_dir = Path(__file__).resolve().parent
_project_root = _current_dir.parent.parent

if getattr(sys, "frozen", False):
    _bundle_dir = getattr(sys, "_MEIPASS", None)
    _engine_path = Path(_bundle_dir) / "yt_dlp_engine" if _bundle_dir else None
else:
    _engine_path = _project_root / "vendor" / "yt_dlp_engine"

if _engine_path is not None and str(_engine_path) not in sys.path:
    sys.path.insert(0, str(_engine_path))
    logger.debug(f"Added yt_dlp_engine to path: {_engine_path}")

# Now import yt_dlp
try:
    from yt_dlp import YoutubeDL
    from yt_dlp import version as ytdlp_version
    from yt_dlp.postprocessor.common import PostProcessor
    from yt_dlp.postprocessor.ffmpeg import ACODECS
    from yt_dlp.utils import replace_extension

    logger.info(f"yt-dlp imported successfully. Version: {ytdlp_version.__version__}")
except ImportError as e:
    logger.exception("Failed to import yt-dlp")
    raise ImportError("Could not import yt-dlp. Please ensure yt_dlp_engine is properly set up.") from e


# Browser impersonation is deliberately not used. yt-dlp implements it through
# curl_cffi, which this project does not ship (see the curl_cffi entry in the
# 0.2.1 CHANGELOG and the `excludes` list in packaging/build*.spec). YouTube
# rate limits are handled instead by sleep_interval_subtitles,
# sleep_interval_requests and _make_subtitles_non_fatal below.


# yt-dlp warnings that are expected in this app and harmless. They go to the
# log at DEBUG instead of WARNING. Each entry is a stable substring of one
# yt-dlp message, so other warnings are not affected.
_QUIET_WARNING_MARKERS = (
    # Some extractors ask for impersonation. It needs curl_cffi, which is not
    # shipped (see the note above), so yt-dlp warns on every such download.
    # Downloads still work without it. Full message: "The extractor specified
    # to use impersonation for this download, but no impersonate target is
    # available. ..."
    "no impersonate target is available",
)


class _YtDlpLogBridge:
    """Route yt-dlp's own messages into the app log.

    Without a ``logger`` option yt-dlp prints to stdout/stderr, which the
    windowed EXE discards, so yt-dlp's errors never reached the log file.
    The last error is kept so a failed download can show the real reason.
    """

    def __init__(self) -> None:
        self.last_error: str | None = None

    def debug(self, msg: str) -> None:
        # yt-dlp sends both debug and ordinary progress lines here; keep them
        # below INFO so download progress does not flood the log file.
        logger.debug(msg)

    def info(self, msg: str) -> None:
        logger.debug(msg)

    def warning(self, msg: str) -> None:
        if any(marker in msg for marker in _QUIET_WARNING_MARKERS):
            logger.debug(f"yt-dlp: {msg}")
            return
        logger.warning(f"yt-dlp: {msg}")

    def error(self, msg: str) -> None:
        self.last_error = msg
        logger.error(f"yt-dlp: {msg}")


def _existing_output_files(info_dict: dict | None) -> list[str]:
    """Return the final files yt-dlp reports writing that exist on disk.

    With ``ignoreerrors='only_download'`` a failed download does not raise:
    ``extract_info`` returns ``None`` (or an entry without output), so the
    only reliable success signal is the output file itself. ``filepath`` in
    ``requested_downloads`` is the post-processed path (merged .mp4,
    converted .mp3).
    """
    if not info_dict:
        return []
    paths = (d.get("filepath") for d in info_dict.get("requested_downloads") or [])
    return [p for p in paths if p and os.path.exists(p)]


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
            ydl.report_warning(f"Subtitle download failed ({e}); continuing without subtitles.")
            return []

    ydl._write_subtitles = _safe_write_subtitles


# ---------- auto-numbering of duplicate output files ----------
#
# yt-dlp has no auto-numbering of its own. When the setting is on, the
# wrapper picks the final file name itself, just before yt-dlp computes its
# output path, and switches the output template for that one download to
# "<name> (1).%(ext)s", "<name> (2).%(ext)s" and so on.
#
# Paths that a running download in this process has chosen are reserved, so
# two queue workers that download the same video at the same moment get two
# different names. The check is not atomic against other processes: a second
# app instance can still pick the same name in the same instant.

_EXT_FIELD = ".%(ext)s"
_MAX_DUPLICATE_NUMBER = 9999

_reserved_outputs_lock = threading.Lock()
_reserved_outputs: set[str] = set()


def _output_key(path: str) -> str:
    """Normalise a path for the reservation set (case-insensitive on Windows)."""
    return os.path.normcase(os.path.abspath(path))


def _numbered_template(template: str, number: int) -> str:
    """Return ``template`` with `` (number)`` added before the extension field.

    Only the literal suffix is added. The title and the other fields stay
    template fields, so yt-dlp still fills and sanitises them (including
    ``windowsfilenames``) exactly as for the plain name. The suffix holds no
    ``%`` or ``$``, so it needs no escaping.
    """
    if number <= 0 or not template.endswith(_EXT_FIELD):
        return template
    return f"{template[: -len(_EXT_FIELD)]} ({number}){_EXT_FIELD}"


def _final_extension(info: dict[str, Any], audio_format: str | None) -> str | None:
    """Extension of the file the user ends up with.

    For a merged video, ``info['ext']`` already holds the merge container
    (``merge_output_format`` or the compatible one yt-dlp picked). Audio
    extraction then renames the file to the codec's extension (``vorbis``
    gives ``.ogg``, ``m4a`` gives ``.m4a``), see ``ACODECS`` in yt-dlp.
    """
    if audio_format:
        codec = ACODECS.get(audio_format)
        if codec:
            return codec[0]
    return info.get("ext")


def _reserve_output_template(
    ydl: Any, info: dict[str, Any], template: str, audio_format: str | None
) -> tuple[str, str] | None:
    """Pick the first free output template for ``info`` and reserve its path.

    The candidate names come from ``ydl.prepare_filename``, so the check uses
    the sanitised path yt-dlp will really write, with the final extension.

    Returns:
        ``(template, final_path)``, or None if no name could be computed.
    """
    ext = info.get("ext")
    final_ext = _final_extension(info, audio_format)
    with _reserved_outputs_lock:
        for number in range(_MAX_DUPLICATE_NUMBER + 1):
            candidate = _numbered_template(template, number)
            if number and candidate == template:
                return None  # template cannot be numbered
            filename = ydl.prepare_filename(info, outtmpl=candidate)
            if not filename:
                return None
            if final_ext and ext and final_ext != ext:
                filename = replace_extension(filename, final_ext, ext)
            key = _output_key(filename)
            if key in _reserved_outputs or os.path.exists(filename):
                continue
            _reserved_outputs.add(key)
            return candidate, filename
    return None


def _release_outputs(keys: list[str]) -> None:
    """Drop reservations made by ``_reserve_output_template``."""
    with _reserved_outputs_lock:
        for key in keys:
            _reserved_outputs.discard(key)
    keys.clear()


class _DuplicateNumberingPP(PostProcessor):
    """Set a numbered output template when the final file already exists.

    Registered at yt-dlp's ``video`` stage, which runs in ``process_info``
    after format selection and just before yt-dlp computes the output path.
    So the temporary files (``.part``, ``.fNNN``), the thumbnail, the
    subtitles and the post-processors all use the chosen name.
    """

    def __init__(self, downloader: Any, template: str, audio_format: str | None, reserved: list[str]):
        super().__init__(downloader)
        self._template = template
        self._audio_format = audio_format
        self._reserved = reserved

    def run(self, info: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
        ydl = self._downloader
        template = self._template
        try:
            choice = _reserve_output_template(ydl, info, self._template, self._audio_format)
        except Exception:
            # Fall back to the plain name. nooverwrites makes yt-dlp skip an
            # existing file instead of replacing it.
            logger.exception("Could not pick a numbered file name; using the plain name")
            choice = None
        if choice:
            template, final_path = choice
            self._reserved.append(_output_key(final_path))
            if template != self._template:
                logger.info(f"✓ File exists, saving as: {os.path.basename(final_path)}")
        ydl.params["outtmpl"]["default"] = template
        return [], info


# ---------- download flow helpers ----------


def _audio_quality_label(audio_quality: str) -> str:
    return "Best (VBR)" if audio_quality == "0" else f"{audio_quality}kbps"


def _log_download_start(options: DownloadOptions) -> None:
    """Log the banner with the main settings of a download."""
    logger.info("=" * 80)
    logger.info("STARTING DOWNLOAD")
    logger.info("=" * 80)
    logger.info(f"URL: {options.url}")
    logger.info(f"Output Directory: {options.output_dir}")
    logger.info(f"Format String: {options.format_string}")
    logger.info(f"Audio Only: {options.audio_only}")
    logger.info(f"Audio Quality: {_audio_quality_label(options.audio_quality)}")
    logger.info(f"Audio Format: {options.audio_format}")
    logger.info(f"Video Container: {options.video_container}")
    logger.info(f"Download Thumbnail: {options.download_thumbnail}")
    logger.info(f"Download Subtitles: {options.download_subtitles}")
    logger.info(f"Subtitle Languages: {options.subtitle_languages}")
    logger.info(f"Speed Limit: {options.speed_limit}KB/s")
    logger.info("=" * 80)


def _log_enabled_options(options: DownloadOptions, ydl_opts: dict[str, Any]) -> None:
    """Log one line for each option that is switched on."""
    o = options
    if o.auto_number_duplicates:
        logger.info("✓ Auto-numbering duplicates enabled")
    else:
        logger.info("✓ Skip duplicates enabled (won't overwrite)")
    lines = [
        ("merge_output_format" in ydl_opts, f"Video container format set: {o.video_container}"),
        ("ratelimit" in ydl_opts, f"Speed limit applied: {o.speed_limit}KB/s"),
        (o.download_thumbnail, "Thumbnail download enabled (converted to JPG)"),
        (o.download_subtitles, f"Subtitle download enabled: {ydl_opts.get('subtitleslangs')} (2s spacing)"),
        (o.download_metadata, "Metadata download enabled (JSON, description, annotations, comments)"),
        (o.download_comments, "Comments download enabled (will be saved as .txt file)"),
        ("sleep_interval_requests" in ydl_opts, "Inter-request spacing: 1s (subtitles + comments/metadata combo)"),
        (o.audio_only, f"Audio extraction enabled ({o.audio_format.upper()}, {_audio_quality_label(o.audio_quality)})"),
    ]
    for enabled, text in lines:
        if enabled:
            logger.info(f"✓ {text}")
    logger.info(f"✓ Total postprocessors: {len(ydl_opts.get('postprocessors', []))}")


def _configure_ydl(ydl: Any, options: DownloadOptions, reserved_outputs: list[str]) -> None:
    """Add the duplicate-numbering hook and make subtitle failures non-fatal."""
    if options.auto_number_duplicates:
        numbering_pp = _DuplicateNumberingPP(
            ydl,
            options.output_template,
            options.extract_audio_format,
            reserved_outputs,
        )
        ydl.add_post_processor(numbering_pp, when="video")

    # A YouTube 429 on subtitles must not abort the video download.
    if options.download_subtitles:
        _make_subtitles_non_fatal(ydl)


def _require_output_files(info_dict: dict | None, log_bridge: _YtDlpLogBridge) -> list[str]:
    """Return the written files, or raise if there are none.

    Success is never reported without a file on disk (see
    ``_existing_output_files``). Raising routes this through the normal
    failure path, so the UI shows the error.
    """
    output_files = _existing_output_files(info_dict)
    if not output_files:
        reason = log_bridge.last_error or "no error was reported"
        raise RuntimeError(f"yt-dlp finished without writing a file: {reason}")
    return output_files


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
        # Result of the last successful download() (reset on every call)
        self._last_output_files: list[str] = []
        self._last_title: str | None = None
        logger.debug("YtDlpWrapper initialized")

    @property
    def last_error(self) -> str | None:
        """Error message of the last failed download, or None."""
        return self._last_error

    @property
    def last_output_files(self) -> list[str]:
        """Final file paths of the last successful download.

        These are the post-processed paths yt-dlp reports (merged .mp4,
        converted .mp3), and each one existed when the download finished.
        The list is empty before a download and after a failed one.
        """
        return list(self._last_output_files)

    @property
    def last_title(self) -> str | None:
        """Video title of the last successful download, or None."""
        return self._last_title

    def _get_ffmpeg_location(self) -> str | None:
        """
        Find FFmpeg executable location (cached after first lookup).

        Checks multiple locations:
        1. PyInstaller bundled location (when running from a frozen build)
        2. System PATH (the primary source on Linux/macOS)
        3. Current directory

        The executable name is platform-aware: ``ffmpeg.exe`` on Windows,
        ``ffmpeg`` elsewhere. On Linux the app relies on a system FFmpeg
        installed via the package manager (``apt install ffmpeg``); the
        binary is not bundled.

        Returns:
            Path to directory containing ffmpeg, or None if not found
        """
        # Return cached result if already checked
        if YtDlpWrapper._ffmpeg_cache_checked:
            return YtDlpWrapper._ffmpeg_cache

        import shutil

        result = None
        ffmpeg_binary = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"

        # Method 1: Check if running from PyInstaller bundle
        if getattr(sys, "frozen", False):
            bundle_dir = getattr(sys, "_MEIPASS", None)
            if bundle_dir:
                ffmpeg_path = os.path.join(bundle_dir, ffmpeg_binary)
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
            ffmpeg_path = os.path.join(current_dir, ffmpeg_binary)
            if os.path.exists(ffmpeg_path):
                logger.debug(f"Found FFmpeg in current dir: {current_dir}")
                result = current_dir

        if result is None:
            logger.warning("FFmpeg not found in any location")

        # Cache the result
        YtDlpWrapper._ffmpeg_cache = result
        YtDlpWrapper._ffmpeg_cache_checked = True
        return result

    @classmethod
    def reset_deno_cache(cls) -> None:
        """Forget the cached Deno lookup, so the next call searches again.

        Called after the startup thread has downloaded Deno, because a lookup
        that ran before the download finished has cached "not found".
        """
        cls._deno_cache = None
        cls._deno_cache_checked = False

    @staticmethod
    def _bundled_deno(deno_binary: str) -> str | None:
        """Return the Deno copy in the PyInstaller folder (``sys._MEIPASS``), or None."""
        bundle_dir = getattr(sys, "_MEIPASS", None)
        if not bundle_dir:
            return None
        deno_path = os.path.join(bundle_dir, deno_binary)
        if not os.path.exists(deno_path):
            return None
        logger.debug(f"Found Deno in bundle: {deno_path}")
        return deno_path

    def _get_deno_location(self) -> str | None:
        """
        Find Deno executable location (cached after first lookup).

        Precedence (the first match wins):
        1. Bundled copy in the PyInstaller folder (``sys._MEIPASS``). Only
           the frozen Windows build bundles Deno.
        2. Project-local ``deno/`` folder. Source runs only, where the
           auto-installer puts its download.
        3. System PATH (``shutil.which("deno")``).
        4. The copy downloaded to the app data folder,
           ``<APP_DATA_DIR>/deno/<DENO_VERSION>/``. This is where a frozen
           build without a bundled Deno (Linux) puts its download.

        A system deno wins over the app data copy, the same order the
        installer uses (utils/deno_installer.py). The executable name is
        platform-aware: ``deno.exe`` on Windows, ``deno`` elsewhere.

        Returns:
            Path to deno executable, or None if not found
        """
        # Return cached result if already checked
        if YtDlpWrapper._deno_cache_checked:
            return YtDlpWrapper._deno_cache

        import shutil

        from ..utils.deno_installer import get_app_data_deno_dir

        result = None
        frozen = getattr(sys, "frozen", False)
        deno_binary = "deno.exe" if os.name == "nt" else "deno"

        # Method 1: Check if running from PyInstaller bundle
        if frozen:
            result = YtDlpWrapper._bundled_deno(deno_binary)

        # Method 2: Check project-local deno/ folder (source runs)
        if result is None and not frozen:
            deno_local = _project_root / "deno" / deno_binary
            if deno_local.exists():
                logger.debug(f"Found Deno locally: {deno_local}")
                result = str(deno_local)

        # Method 3: Check system PATH
        if result is None:
            deno_exe = shutil.which("deno")
            if deno_exe:
                logger.debug(f"Found Deno in PATH: {deno_exe}")
                result = deno_exe

        # Method 4: Check the copy downloaded to the app data folder
        if result is None:
            deno_downloaded = get_app_data_deno_dir() / deno_binary
            if deno_downloaded.is_file():
                logger.debug(f"Found downloaded Deno: {deno_downloaded}")
                result = str(deno_downloaded)

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

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=False)

                if info_dict is None:
                    logger.error("No information extracted from URL")
                    return None

                video_info = VideoInfo.from_yt_dlp_dict(info_dict)
                logger.info(f"Video info extracted: {video_info.title}")
                return video_info

        except Exception:
            logger.exception("Error extracting video info")
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
            "noplaylist": True,  # Never process the full playlist, only the single video
        }

        if ffmpeg_location:
            ydl_opts["ffmpeg_location"] = ffmpeg_location

        # Set Deno JS runtime path if found
        deno_path = self._get_deno_location()
        if deno_path:
            ydl_opts["js_runtimes"] = {"deno": {"path": deno_path}}

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

        except Exception:
            logger.exception("Error fetching subtitles")
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

    def download(self, options: DownloadOptions) -> bool:
        """
        Download one video with the given options.

        Args:
            options: The user's choices for this download.

        Returns:
            True if the download wrote at least one file, False otherwise.
            On success, ``last_output_files`` and ``last_title`` hold the
            result. On failure, ``last_error`` holds the reason (it stays
            None after a cancel).

        Example:
            >>> wrapper = YtDlpWrapper(progress_callback=my_callback)
            >>> success = wrapper.download(
            ...     DownloadOptions(
            ...         "https://youtube.com/watch?v=...",
            ...         "/downloads",
            ...         "bestvideo+bestaudio/best",
            ...         download_subtitles=True,
            ...         selected_subtitles=["en", "es"],
            ...         video_container="mp4",
            ...     )
            ... )
        """
        _log_download_start(options)
        self._reset_result()
        ydl_opts = self._prepare_ydl_opts(options)

        # Added after the options were logged: the bridge is an object, not config.
        log_bridge = _YtDlpLogBridge()
        ydl_opts["logger"] = log_bridge

        # Output paths this download reserved for auto-numbering; released
        # in the finally block below.
        reserved_outputs: list[str] = []
        try:
            return self._run_download(options, ydl_opts, log_bridge, reserved_outputs)
        except Exception as e:
            self._record_failure(e)
            return False
        finally:
            # The file exists now (or the download failed), so the
            # reservation is no longer needed.
            _release_outputs(reserved_outputs)

    def _reset_result(self) -> None:
        """Clear the cancel flag and the result of the previous download."""
        self._download_cancelled = False
        self._last_error = None
        self._last_error_type = None
        self._last_output_files = []
        self._last_title = None

    def _prepare_ydl_opts(self, options: DownloadOptions) -> dict[str, Any]:
        """Find FFmpeg and Deno, build the yt-dlp options and log them."""
        logger.info("\n[STEP 1/5] Detecting FFmpeg location...")
        ffmpeg_location = self._get_ffmpeg_location()
        if ffmpeg_location:
            logger.info(f"✓ FFmpeg found at: {ffmpeg_location}")
        else:
            logger.warning("⚠ FFmpeg not found - some downloads may fail")

        logger.info("\n[STEP 2/5] Building yt-dlp options...")
        logger.info(f"✓ Filename template: {options.filename_template}")
        ydl_opts = build_ydl_opts(
            options,
            progress_hooks=[self._progress_hook],
            ffmpeg_location=ffmpeg_location,
            deno_path=self._get_deno_location(),
        )
        logger.info("\n[STEP 3/5] Enabled options and postprocessors:")
        _log_enabled_options(options, ydl_opts)

        logger.info("\n[STEP 4/5] Final yt-dlp configuration:")
        ydl_opts_log = {k: v for k, v in ydl_opts.items() if k != "progress_hooks"}
        logger.info(json.dumps(ydl_opts_log, indent=2, default=str))
        return ydl_opts

    def _run_download(
        self,
        options: DownloadOptions,
        ydl_opts: dict[str, Any],
        log_bridge: _YtDlpLogBridge,
        reserved_outputs: list[str],
    ) -> bool:
        """Run yt-dlp and record the result. Raises on a failed download."""
        logger.info("\n[STEP 5/5] Initializing yt-dlp and starting download...")
        with YoutubeDL(ydl_opts) as ydl:
            if self._download_cancelled:
                logger.info("Download cancelled before starting")
                return False

            _configure_ydl(ydl, options, reserved_outputs)
            logger.info("✓ yt-dlp initialized successfully")
            logger.info(f"✓ Starting download from: {options.url}")

            info_dict = ydl.extract_info(options.url, download=True)

            if self._download_cancelled:
                logger.info("Download was cancelled")
                return False

            output_files = _require_output_files(info_dict, log_bridge)
            write_side_files(
                options.output_dir,
                info_dict,
                metadata=options.download_metadata,
                comments=options.download_comments,
            )
            self._record_success(output_files, info_dict)
            return True

    def _record_success(self, output_files: list[str], info_dict: dict[str, Any]) -> None:
        """Store the result of a finished download."""
        logger.info("\n" + "=" * 80)
        logger.info("✓✓✓ DOWNLOAD COMPLETED SUCCESSFULLY ✓✓✓")
        logger.info("=" * 80)
        # Set only on success, so a failure never leaves stale paths.
        self._last_output_files = output_files
        title = info_dict.get("title")
        self._last_title = title if isinstance(title, str) and title else None

    def _record_failure(self, error: Exception) -> None:
        """Store the error for the UI and log it with its traceback."""
        self._last_error = str(error)
        self._last_error_type = type(error).__name__

        # logger.exception() records the error type, message, and full
        # traceback in one entry; the banner lines keep it easy to spot.
        logger.error("\n" + "=" * 80)
        logger.error("✗✗✗ DOWNLOAD FAILED ✗✗✗")
        logger.error("=" * 80)
        logger.exception("Download failed")
        logger.error("=" * 80)

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

            # yt-dlp sanitizes filenames (windowsfilenames=True), so locate the
            # written files by their height suffix rather than the title.
            height = info_dict.get("height", "NA")
            matching_files = glob.glob(os.path.join(output_dir, f"*{height}p.*"))

            base_filename = self._find_metadata_base(matching_files)
            if not base_filename:
                logger.debug("Could not find base filename for metadata post-processing")
                return

            self._format_info_json(f"{base_filename}.info.json")
            self._rename_description_to_txt(base_filename)
        except Exception:
            logger.exception("Error during metadata post-processing")

    @staticmethod
    def _find_metadata_base(matching_files: list[str]) -> str | None:
        """Return the common base path of the downloaded metadata files."""
        for file_path in matching_files:
            if file_path.endswith(".info.json"):
                return os.path.splitext(file_path)[0]
        for file_path in matching_files:
            if file_path.endswith((".description", ".webp", ".jpg")):
                return os.path.splitext(file_path)[0]
        return None

    @staticmethod
    def _format_info_json(json_file: str) -> None:
        """Rewrite the .info.json with human-readable indentation."""
        if not os.path.exists(json_file):
            return
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info("✓ Formatted JSON file with proper indentation")
        except Exception:
            logger.exception("Could not format JSON file")

    @staticmethod
    def _rename_description_to_txt(base_filename: str) -> None:
        """Rename the .description sidecar to .txt for readability."""
        desc_file = f"{base_filename}.description"
        txt_file = f"{base_filename}.txt"
        if not os.path.exists(desc_file):
            return
        try:
            if os.path.exists(txt_file):
                os.remove(txt_file)
            os.rename(desc_file, txt_file)
            logger.info("✓ Renamed .description to .txt for better readability")
        except Exception:
            logger.exception("Could not rename description file")

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
            except Exception:
                logger.exception("Error in progress callback")

    @staticmethod
    def get_ytdlp_version() -> str:
        """
        Get yt-dlp version string.

        Returns:
            Version string
        """
        try:
            return ytdlp_version.__version__
        except Exception:
            return "Unknown"
