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
from urllib.parse import urlsplit, urlunsplit

from ..utils.photo_posts import supports_photo_posts

# Output file names. The quality part keeps different qualities of one video
# apart. "%(height&_{}p|)s" gives "_720p", or nothing when the format has no
# height (Facebook sd/hd, Instagram progressive files), so the name never
# holds "_NAp". Duplicate numbering adds " (1)" before ".%(ext)s".
VIDEO_FILENAME_TEMPLATE = "%(title)s%(height&_{}p|)s.%(ext)s"
AUDIO_FILENAME_TEMPLATE = "%(title)s_%(quality)s.%(ext)s"
# A photo has no height or quality in its name. The id keeps the photos of one
# post apart (they often share the title).
IMAGE_FILENAME_TEMPLATE = "%(title)s [%(id)s].%(ext)s"
UPLOADER_TITLE_TEMPLATE = "%(uploader)s - %(title)s.%(ext)s"
DATE_TITLE_TEMPLATE = "%(upload_date>%Y-%m-%d)s - %(title)s.%(ext)s"

# File name presets. "title_quality" is the template the app always used.
FILENAME_PRESET_TITLE_QUALITY = "title_quality"
FILENAME_PRESET_UPLOADER_TITLE = "uploader_title"
FILENAME_PRESET_DATE_TITLE = "date_title"
FILENAME_PRESET_CUSTOM = "custom"
FILENAME_PRESETS = (
    FILENAME_PRESET_TITLE_QUALITY,
    FILENAME_PRESET_UPLOADER_TITLE,
    FILENAME_PRESET_DATE_TITLE,
    FILENAME_PRESET_CUSTOM,
)
_FIXED_PRESET_TEMPLATES = {
    FILENAME_PRESET_UPLOADER_TITLE: UPLOADER_TITLE_TEMPLATE,
    FILENAME_PRESET_DATE_TITLE: DATE_TITLE_TEMPLATE,
}

# Codec preferences, mapped to yt-dlp ``format_sort`` fields. A "codec:x"
# entry prefers x (and codecs that yt-dlp ranks below it) over the others,
# so a format with that codec wins when one exists, and the download still
# works when none does.
CODEC_ANY = "any"
VIDEO_CODEC_SORT = {
    CODEC_ANY: None,
    "h264": "vcodec:h264",
    "h265": "vcodec:h265",
    "vp9": "vcodec:vp9",
    "av1": "vcodec:av01",
}
AUDIO_CODEC_SORT = {
    CODEC_ANY: None,
    "aac": "acodec:aac",
    "opus": "acodec:opus",
    "vorbis": "acodec:vorbis",
}

# YouTube rate-limits subtitle requests. A 2 s gap between subtitle downloads
# avoids the HTTP 429 cascade that would otherwise abort the video download.
SUBTITLE_SLEEP_SECONDS = 2
# With subtitles and comments (or metadata, which also fetches comments), the
# comment phase uses up YouTube's per-IP budget before the subtitle request
# goes out. A 1 s gap between all requests lets the subtitles land. It costs
# about 10-30 s extra during the comment phase.
REQUEST_SLEEP_SECONDS = 1

# Text that replaces a secret in the logged options.
MASK = "***"


@dataclass(frozen=True)
class DownloadOptions:
    """Everything the user chose for one download.

    Attributes:
        url: Video URL.
        output_dir: Folder for the downloaded files.
        format_string: yt-dlp format selector, for example
            ``"bestvideo+bestaudio/best"``. Not used for audio-only downloads,
            which always use ``"bestaudio"``, or when ``custom_format`` is set.
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
            metadata text file, and embed the metadata in the file.
        download_comments: Save the comments as a text file.
        speed_limit: Download speed limit in KB/s. 0 or less means unlimited.
        auto_number_duplicates: If the final file exists, save the new one as
            "name (1).ext", "name (2).ext" and so on. If False, yt-dlp skips a
            file that exists. An existing file is never overwritten.
        cookies_browser: Browser to read cookies from (yt-dlp's
            ``cookiesfrombrowser``), for example ``"firefox"``. Empty means
            no cookies.
        cookies_profile: Browser profile name or folder. Empty means the
            browser's default profile.
        proxy: Proxy URL (http, https or socks5). Empty means no proxy.
        filename_preset: One of ``FILENAME_PRESETS``.
        custom_filename_template: The template for the "custom" preset.
            It must pass ``download_preferences.validate_filename_template``.
        video_codec: Preferred video codec, a key of ``VIDEO_CODEC_SORT``.
            Not used for audio-only downloads.
        audio_codec: Preferred audio codec for video downloads, a key of
            ``AUDIO_CODEC_SORT``. Not used for audio-only downloads.
        custom_format: A yt-dlp format string. When set, it is used instead
            of the quality preset and the codec preferences.
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
    cookies_browser: str = ""
    cookies_profile: str = ""
    proxy: str = ""
    filename_preset: str = FILENAME_PRESET_TITLE_QUALITY
    custom_filename_template: str = ""
    video_codec: str = CODEC_ANY
    audio_codec: str = CODEC_ANY
    custom_format: str = ""

    @property
    def filename_template(self) -> str:
        """File name template, without the folder.

        An unknown preset, or the custom preset without a template, gives
        the default template.
        """
        if self.filename_preset == FILENAME_PRESET_CUSTOM and self.custom_filename_template:
            return self.custom_filename_template
        fixed = _FIXED_PRESET_TEMPLATES.get(self.filename_preset)
        if fixed:
            return fixed
        return AUDIO_FILENAME_TEMPLATE if self.audio_only else VIDEO_FILENAME_TEMPLATE

    @property
    def image_filename_template(self) -> str:
        """File name template for a photo of a post, without the folder.

        The presets that name by quality (the default and the audio one) give
        ``IMAGE_FILENAME_TEMPLATE``. A template the user chose is kept.
        """
        if self.filename_preset == FILENAME_PRESET_CUSTOM and self.custom_filename_template:
            return self.custom_filename_template
        return _FIXED_PRESET_TEMPLATES.get(self.filename_preset, IMAGE_FILENAME_TEMPLATE)

    @property
    def output_template(self) -> str:
        """Full output template (folder and file name) for yt-dlp's ``outtmpl``."""
        return os.path.join(self.output_dir, self.filename_template)

    @property
    def image_output_template(self) -> str:
        """Full output template for a photo of a post."""
        return os.path.join(self.output_dir, self.image_filename_template)

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

    @property
    def writes_info_json(self) -> bool:
        """True if yt-dlp writes a ``.info.json`` file next to the download."""
        return self.download_metadata or self.download_comments


def build_ydl_opts(
    options: DownloadOptions,
    *,
    progress_hooks: Sequence[Callable[[dict[str, Any]], None]] = (),
    ffmpeg_location: str | None = None,
    deno_path: str | None = None,
) -> dict[str, Any]:
    """Return the ``YoutubeDL`` options for ``options``.

    The key order is stable, because the dict is written to the log as JSON
    (through ``redact_ydl_opts``, which hides the secrets).

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
    ydl_opts.update(_photo_opts(options.url))
    ydl_opts.update(_format_sort_opts(options))
    ydl_opts.update(network_opts(options.proxy, options.cookies_browser, options.cookies_profile))
    postprocessors = build_postprocessors(options)
    if postprocessors:
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
    if options.download_metadata:
        # Last, so the tags go into the final file (after audio extraction).
        postprocessors.append({"key": "FFmpegMetadata", "add_infojson": "if_exists"})
    return postprocessors


def network_opts(proxy: str, cookies_browser: str, cookies_profile: str = "") -> dict[str, Any]:
    """Return the proxy and browser-cookie options for any ``YoutubeDL`` call.

    Used for downloads and for the info, subtitle and playlist look-ups, so
    every request goes through the same proxy with the same cookies.
    """
    opts: dict[str, Any] = {}
    if proxy:
        opts["proxy"] = proxy
    if cookies_browser:
        # (browser, profile, keyring, container). None picks yt-dlp's default.
        opts["cookiesfrombrowser"] = (cookies_browser, cookies_profile or None, None, None)
    return opts


def mask_proxy_url(proxy: str) -> str:
    """Return ``proxy`` with any user name and password replaced by ``***``."""
    if not proxy or "@" not in proxy:
        return proxy
    try:
        parts = urlsplit(proxy)
    except ValueError:
        return MASK
    host = parts.netloc.rpartition("@")[2]
    return urlunsplit((parts.scheme, f"{MASK}@{host}", parts.path, parts.query, parts.fragment))


def redact_ydl_opts(ydl_opts: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``ydl_opts`` that is safe to write to the log.

    Drops the progress hooks, masks the proxy credentials and keeps only the
    browser name of the cookie source (the profile is replaced by ``***``).
    yt-dlp reads the cookies itself; they are never in the options.
    """
    safe = {k: v for k, v in ydl_opts.items() if k != "progress_hooks"}
    if "proxy" in safe:
        safe["proxy"] = mask_proxy_url(safe["proxy"])
    if "cookiesfrombrowser" in safe:
        browser, profile = safe["cookiesfrombrowser"][:2]
        safe["cookiesfrombrowser"] = [browser, MASK if profile else None]
    return safe


def _base_opts(options: DownloadOptions, progress_hooks: Sequence[Callable]) -> dict[str, Any]:
    return {
        "format": _format_selector(options),
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


def _format_selector(options: DownloadOptions) -> str:
    if options.custom_format:
        return options.custom_format
    # Audio-only downloads always take the best audio stream.
    return "bestaudio" if options.audio_only else options.format_string


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
    # The FFmpegMetadata post-processor is added by build_postprocessors.
    return {
        "writeinfojson": True,  # Save video metadata as JSON
        "clean_infojson": False,  # Keep all fields in JSON
        "writedescription": True,  # Save video description as separate file
        "getcomments": True,  # Download comments (can be slow for popular videos)
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


def _photo_opts(url: str) -> dict[str, Any]:
    # A photo post has no formats. Without this, yt-dlp stops with "No video
    # formats found" before the app can download the photo. Only the sites
    # with photo support get it: on others, that error must stay an error.
    return {"ignore_no_formats_error": True} if supports_photo_posts(url) else {}


def _format_sort_opts(options: DownloadOptions) -> dict[str, Any]:
    # A custom format string replaces the presets, codecs included. Audio
    # extraction converts the codec anyway, so no preference there either.
    if options.custom_format or options.audio_only:
        return {}
    fields = [
        VIDEO_CODEC_SORT.get(options.video_codec),
        AUDIO_CODEC_SORT.get(options.audio_codec),
    ]
    sort = [field for field in fields if field]
    return {"format_sort": sort} if sort else {}
