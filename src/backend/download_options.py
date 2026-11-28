"""
Download options for YT-DLP Studio.

``DownloadOptions`` holds every user choice for one download, one typed field
per option. ``build_ydl_opts`` turns it into the options dict for yt-dlp's
``YoutubeDL``. It is a pure function: no file system, no network and no
logging, so each option can be unit-tested on its own.

To add an option:

1. Add a typed field with a default to ``DownloadOptions``.
2. Map it in ``build_ydl_opts`` (or in ``build_postprocessors`` for a
   post-processor), in a small helper of its own.
3. Fill the field where the download is started (``DownloadWorker``).
"""

from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from dataclasses import KW_ONLY, dataclass
from typing import Any

# Output file names. The quality part keeps different qualities of one video
# apart. Duplicate numbering adds " (1)" before ".%(ext)s".
VIDEO_FILENAME_TEMPLATE = "%(title)s_%(height)sp.%(ext)s"
AUDIO_FILENAME_TEMPLATE = "%(title)s_%(quality)s.%(ext)s"

# YouTube rate-limits subtitle requests. A 2 s gap between subtitle downloads
# avoids the HTTP 429 cascade that would otherwise abort the video download.
SUBTITLE_SLEEP_SECONDS = 2
# With subtitles and comments (or metadata, which also fetches comments), the
# comment phase uses up YouTube's per-IP budget before the subtitle request
# goes out. A 1 s gap between all requests lets the subtitles land. It costs
# about 10-30 s extra during the comment phase.
REQUEST_SLEEP_SECONDS = 1


@dataclass(frozen=True)
class DownloadOptions:
    """Everything the user chose for one download.

    Attributes:
        url: Video URL.
        output_dir: Folder for the downloaded files.
        format_string: yt-dlp format selector, for example
            ``"bestvideo+bestaudio/best"``. Not used for audio-only downloads,
            which always use ``"bestaudio"``.
        audio_only: Extract the audio track only.
        audio_quality: Audio bitrate in kbps (``"128"`` ... ``"320"``), or
            ``"0"`` for the best VBR quality.
        audio_format: Audio codec for extraction (mp3, m4a, opus, flac, wav,
            vorbis).
        video_container: Merge container (mp4, mkv, webm), or None to let
            yt-dlp choose. Not used for audio-only downloads.
        download_thumbnail: Save the thumbnail, converted to JPG.
        download_subtitles: Save subtitles (manual and automatic) as SRT.
        subtitle_languages: Comma-separated language codes, used when
            ``selected_subtitles`` is empty.
        selected_subtitles: Language codes picked in the UI. A non-empty list
            wins over ``subtitle_languages``.
        download_metadata: Save the info JSON, the description and a readable
            metadata text file.
        download_comments: Save the comments as a text file.
        speed_limit: Download speed limit in KB/s. 0 or less means unlimited.
        auto_number_duplicates: If the final file exists, save the new one as
            "name (1).ext", "name (2).ext" and so on. If False, yt-dlp skips a
            file that exists. An existing file is never overwritten.
    """

    url: str
    output_dir: str
    format_string: str
    _: KW_ONLY
    audio_only: bool = False
    audio_quality: str = "192"
    audio_format: str = "mp3"
    video_container: str | None = None
    download_thumbnail: bool = True
    download_subtitles: bool = False
    subtitle_languages: str = "en"
    selected_subtitles: list[str] | None = None
    download_metadata: bool = False
    download_comments: bool = False
    speed_limit: int = 0
    auto_number_duplicates: bool = True

    @property
    def filename_template(self) -> str:
        """File name template, without the folder."""
        return AUDIO_FILENAME_TEMPLATE if self.audio_only else VIDEO_FILENAME_TEMPLATE

    @property
    def output_template(self) -> str:
        """Full output template (folder and file name) for yt-dlp's ``outtmpl``."""
        return os.path.join(self.output_dir, self.filename_template)

    @property
    def extract_audio_format(self) -> str | None:
        """The audio codec the file is converted to, or None for a video."""
        return self.audio_format if self.audio_only else None

    @property
    def subtitle_language_list(self) -> list[str]:
        """Subtitle languages to download: the selection, else the text field."""
        if self.selected_subtitles:
            return self.selected_subtitles
        return [lang.strip() for lang in self.subtitle_languages.split(",") if lang.strip()]


def build_ydl_opts(
    options: DownloadOptions,
    *,
    progress_hooks: Sequence[Callable[[dict[str, Any]], None]] = (),
    ffmpeg_location: str | None = None,
    deno_path: str | None = None,
) -> dict[str, Any]:
    """Return the ``YoutubeDL`` options for ``options``.

    The key order is stable, because the dict is written to the log as JSON.

    Args:
        options: The user's choices for this download.
        progress_hooks: Callables for yt-dlp's ``progress_hooks``.
        ffmpeg_location: Folder that holds FFmpeg, or None if not found.
        deno_path: Path to the Deno executable, or None if not found.
    """
    ydl_opts = _base_opts(options, progress_hooks)
    ydl_opts.update(_runtime_opts(ffmpeg_location, deno_path))
    ydl_opts.update(_container_opts(options))
    ydl_opts.update(_rate_limit_opts(options))
    ydl_opts.update(_thumbnail_opts(options))
    ydl_opts.update(_subtitle_opts(options))
    ydl_opts.update(_metadata_opts(options))
    ydl_opts.update(_comment_opts(options))
    ydl_opts.update(_request_spacing_opts(options))
    ydl_opts.update(_audio_opts(options))
    postprocessors = build_postprocessors(options)
    if postprocessors:
        # Replaces the list _metadata_opts set (behavior kept as it was).
        ydl_opts["postprocessors"] = postprocessors
    return ydl_opts


def build_postprocessors(options: DownloadOptions) -> list[dict[str, Any]]:
    """Return the yt-dlp post-processors for ``options``, in run order."""
    postprocessors = []
    if options.audio_only:
        postprocessors.append(
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": options.audio_format,
                "preferredquality": options.audio_quality,
                "nopostoverwrites": False,  # Always convert, even if already in target format
            }
        )
    if options.download_thumbnail:
        postprocessors.append({"key": "FFmpegThumbnailsConvertor", "format": "jpg"})
    if options.download_subtitles and not options.audio_only:
        postprocessors.append({"key": "FFmpegEmbedSubtitle"})
    return postprocessors


def _base_opts(options: DownloadOptions, progress_hooks: Sequence[Callable]) -> dict[str, Any]:
    return {
        # Audio-only downloads always take the best audio stream.
        "format": "bestaudio" if options.audio_only else options.format_string,
        "outtmpl": options.output_template,
        "progress_hooks": list(progress_hooks),
        "quiet": False,
        "no_warnings": False,
        "windowsfilenames": True,  # Use Windows-safe filenames (removes invalid characters)
        # IMPORTANT: yt-dlp's "only_download" does NOT silence subtitle errors.
        # YoutubeDL._write_subtitles raises DownloadError unless ignoreerrors is
        # literally True, which would also mask real video download errors.
        # The wrapper keeps "only_download" and instead wraps _write_subtitles
        # (see _make_subtitles_non_fatal), so a subtitle HTTP 429 cannot abort
        # the video download itself.
        "ignoreerrors": "only_download",
        "noplaylist": True,  # Never download a full playlist - always the single video
        # Never overwrite. With auto-numbering on, the wrapper picks a free
        # name before the download starts; with it off, yt-dlp skips a file
        # that exists. This also lets yt-dlp reuse finished intermediate
        # files of an interrupted attempt.
        "nooverwrites": True,
    }


def _runtime_opts(ffmpeg_location: str | None, deno_path: str | None) -> dict[str, Any]:
    opts: dict[str, Any] = {}
    if ffmpeg_location:
        opts["ffmpeg_location"] = ffmpeg_location
    if deno_path:
        # Deno solves YouTube's JS challenges.
        opts["js_runtimes"] = {"deno": {"path": deno_path}}
    return opts


def _container_opts(options: DownloadOptions) -> dict[str, Any]:
    if options.video_container is None or options.audio_only:
        return {}
    return {"merge_output_format": options.video_container}


def _rate_limit_opts(options: DownloadOptions) -> dict[str, Any]:
    if options.speed_limit <= 0:
        return {}
    return {"ratelimit": options.speed_limit * 1024}  # KB/s to bytes/s


def _thumbnail_opts(options: DownloadOptions) -> dict[str, Any]:
    return {"writethumbnail": True} if options.download_thumbnail else {}


def _subtitle_opts(options: DownloadOptions) -> dict[str, Any]:
    if not options.download_subtitles:
        return {}
    return {
        "writesubtitles": True,
        "writeautomaticsub": True,  # Fall back to auto-generated subtitles
        "subtitleslangs": options.subtitle_language_list,
        "subtitlesformat": "srt",
        "sleep_interval_subtitles": SUBTITLE_SLEEP_SECONDS,
    }


def _metadata_opts(options: DownloadOptions) -> dict[str, Any]:
    if not options.download_metadata:
        return {}
    return {
        "writeinfojson": True,  # Save video metadata as JSON
        "clean_infojson": False,  # Keep all fields in JSON
        "writedescription": True,  # Save video description as separate file
        "writeannotations": True,  # Save annotations if available
        "getcomments": True,  # Download comments (can be slow for popular videos)
        "postprocessors": [{"key": "FFmpegMetadata", "add_infojson": "if_exists"}],
    }


def _comment_opts(options: DownloadOptions) -> dict[str, Any]:
    if not options.download_comments:
        return {}
    # The comments come from the info JSON.
    return {"getcomments": True, "writeinfojson": True}


def _request_spacing_opts(options: DownloadOptions) -> dict[str, Any]:
    fetches_comments = options.download_comments or options.download_metadata
    if options.download_subtitles and fetches_comments:
        return {"sleep_interval_requests": REQUEST_SLEEP_SECONDS}
    return {}


def _audio_opts(options: DownloadOptions) -> dict[str, Any]:
    # Remove the downloaded stream after the audio is extracted.
    return {"keepvideo": False} if options.audio_only else {}
