"""
Advanced download preferences for YT-DLP Studio.

The Settings tab stores four advanced choices in the config: browser cookies,
a proxy, the file name template and the format options (codecs or a custom
format string). ``DownloadPreferences`` holds them, checked, in one frozen
value. ``ConfigManager`` publishes a new value each time the config is loaded
or saved (``set_download_preferences``). Every download and every info,
subtitle or playlist look-up reads the current value when it starts, so a
change applies to the next download without a restart.

The validators return a translation key (``tr(key)`` gives the message), or
None if the value is good. They are pure and do no I/O.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

from ..utils.logger import get_logger
from .download_options import (
    AUDIO_CODEC_SORT,
    CODEC_ANY,
    FILENAME_PRESET_CUSTOM,
    FILENAME_PRESET_TITLE_QUALITY,
    FILENAME_PRESETS,
    VIDEO_CODEC_SORT,
    network_opts,
)

logger = get_logger()

# ---------- browser cookies ----------

# Browsers whose cookies yt-dlp can read with what the app ships (sqlite3,
# ctypes and yt-dlp's own AES code), by platform. Kept out on purpose:
# - Chromium-based browsers on Linux: on GNOME and similar desktops yt-dlp
#   needs the `secretstorage` package to read the key, and that package fails
#   the project's software-origin policy. Without the key yt-dlp reads no
#   cookies and says nothing clear, so the browsers are not offered.
# - Opera: owned by a company from a banned country (origin policy).
# - Safari: macOS only, and the app does not ship for macOS.
# Chrome 127 and later on Windows encrypt cookies with an app-bound key that
# yt-dlp cannot read. The app then shows cookie_error_app_bound.
_WINDOWS_COOKIE_BROWSERS = ("firefox", "chrome", "edge", "brave")
_OTHER_COOKIE_BROWSERS = ("firefox",)

BROWSER_NAMES = {
    "firefox": "Firefox",
    "chrome": "Chrome",
    "edge": "Microsoft Edge",
    "brave": "Brave",
}


def cookie_browsers(platform: str | None = None) -> tuple[str, ...]:
    """Browsers the cookie option offers on ``platform`` (default: this one)."""
    platform = sys.platform if platform is None else platform
    if platform in ("win32", "cygwin"):
        return _WINDOWS_COOKIE_BROWSERS
    return _OTHER_COOKIE_BROWSERS


def browser_display_name(browser: str) -> str:
    """Name of ``browser`` for messages ("chrome" gives "Chrome")."""
    return BROWSER_NAMES.get(browser, browser)


# ---------- proxy ----------

PROXY_SCHEMES = ("http", "https", "socks5", "socks5h")
_MAX_PROXY_LENGTH = 2048


def validate_proxy_url(url: str) -> str | None:
    """Check a proxy URL. Empty means no proxy and is valid."""
    if not url:
        return None
    if len(url) > _MAX_PROXY_LENGTH or any(ch.isspace() or ord(ch) < 32 for ch in url):
        return "error_proxy_invalid"
    try:
        parts = urlsplit(url)
        port = parts.port  # raises ValueError for a bad port
    except ValueError:
        return "error_proxy_invalid"
    if parts.scheme.lower() not in PROXY_SCHEMES:
        return "error_proxy_scheme"
    if not parts.hostname or parts.path not in ("", "/") or parts.query or parts.fragment:
        return "error_proxy_invalid"
    if port is not None and port == 0:
        return "error_proxy_invalid"
    return None


# ---------- file name templates ----------

_MAX_TEMPLATE_LENGTH = 200
_EXT_SUFFIX = ".%(ext)s"

# yt-dlp output template fields the custom template may use. Lists and long
# texts (description, tags) are left out: they make poor file names.
TEMPLATE_FIELDS = frozenset(
    {
        "title",
        "fulltitle",
        "alt_title",
        "id",
        "display_id",
        "ext",
        "uploader",
        "uploader_id",
        "channel",
        "channel_id",
        "creator",
        "upload_date",
        "release_date",
        "modified_date",
        "timestamp",
        "release_timestamp",
        "release_year",
        "epoch",
        "duration",
        "duration_string",
        "height",
        "width",
        "resolution",
        "fps",
        "dynamic_range",
        "vcodec",
        "acodec",
        "abr",
        "vbr",
        "tbr",
        "asr",
        "audio_channels",
        "format_id",
        "format_note",
        "quality",
        "language",
        "view_count",
        "like_count",
        "comment_count",
        "age_limit",
        "playlist",
        "playlist_id",
        "playlist_title",
        "playlist_index",
        "playlist_count",
        "playlist_uploader",
        "extractor",
        "extractor_key",
        "webpage_url_domain",
        "autonumber",
        "series",
        "season",
        "season_number",
        "episode",
        "episode_number",
        "track",
        "track_number",
        "artist",
        "album",
        "album_artist",
        "genre",
        "chapter",
        "chapter_number",
        "location",
    }
)

# One "%(...)X" field, or "%%". The type letters are the ones yt-dlp accepts.
_FIELD_RE = re.compile(r"%(?:%|\((?P<expr>[^()]*)\)(?P<conv>[-#0+ ]*\d*(?:\.\d+)?[diouxXeEfFgGcrsaBjhlqDSU]))")
# Inside the parentheses: name, optional >strftime, optional ,alternates,
# optional |default. Field arithmetic, &replacement and object traversal are
# not accepted, to keep the check simple.
_FIELD_EXPR_RE = re.compile(
    r"^(?P<name>[a-z_][a-z0-9_]*)"
    r"(?:>(?P<strf>[%A-Za-z0-9 _.:-]+))?"
    r"(?P<alts>(?:,[a-z_][a-z0-9_]*)*)"
    r"(?:\|(?P<default>[^/\\<>:\"|?*%$]*))?$"
)
# Characters Windows does not allow in file names, and "$" (yt-dlp expands
# environment variables in the final path).
_BAD_FILENAME_CHARS = set('<>:"|?*$')
_DRIVE_RE = re.compile(r"^[A-Za-z]:")


def validate_filename_template(template: str) -> str | None:
    """Check a custom file name template.

    The template must be a file name only (no folders, ``..``, drive letters
    or absolute paths), end with ``.%(ext)s`` (duplicate numbering adds
    `` (1)`` before it) and use only fields from ``TEMPLATE_FIELDS``.
    """
    if not template or not template.strip():
        return "error_template_empty"
    if len(template) > _MAX_TEMPLATE_LENGTH:
        return "error_template_too_long"
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in template):
        return "error_template_invalid_char"
    if "/" in template or "\\" in template or ".." in template or template.startswith("~"):
        return "error_template_path"
    if _DRIVE_RE.match(template):
        return "error_template_path"
    if not template.endswith(_EXT_SUFFIX) or template == _EXT_SUFFIX:
        return "error_template_ext"
    return _check_template_fields(template)


def _check_template_fields(template: str) -> str | None:
    literal_parts = []
    position = 0
    for match in _FIELD_RE.finditer(template):
        literal_parts.append(template[position : match.start()])
        position = match.end()
        expr = match.group("expr")
        if expr is None:
            continue  # "%%", a literal percent sign
        error = _check_field_expression(expr)
        if error:
            return error
    literal_parts.append(template[position:])
    literal = "".join(literal_parts)
    if "%" in literal:
        return "error_template_field_syntax"
    if any(ch in _BAD_FILENAME_CHARS for ch in literal):
        return "error_template_invalid_char"
    return None


def _check_field_expression(expr: str) -> str | None:
    parsed = _FIELD_EXPR_RE.match(expr)
    if not parsed:
        return "error_template_field_syntax"
    names = [parsed.group("name")]
    names += [name for name in parsed.group("alts").split(",") if name]
    if any(name not in TEMPLATE_FIELDS for name in names):
        return "error_template_unknown_field"
    return None


# ---------- format options ----------

_MAX_FORMAT_LENGTH = 500


def validate_custom_format(format_string: str) -> str | None:
    """Check a custom yt-dlp format string. Empty means not used and is valid.

    yt-dlp format strings are not run by a shell, so only control
    characters (newlines included) and unbalanced brackets are rejected
    here. ``YtDlpWrapper.format_selector_error`` also parses it with yt-dlp.
    """
    if not format_string:
        return None
    if len(format_string) > _MAX_FORMAT_LENGTH:
        return "error_format_too_long"
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in format_string):
        return "error_format_invalid_char"
    if not format_string.strip():
        return "error_format_syntax"
    if format_string.count("[") != format_string.count("]") or format_string.count("(") != format_string.count(")"):
        return "error_format_syntax"
    return None


# ---------- the preferences value ----------


@dataclass(frozen=True)
class DownloadPreferences:
    """The advanced download choices from the config, all checked."""

    cookies_browser: str = ""
    cookies_profile: str = ""
    proxy: str = ""
    filename_preset: str = FILENAME_PRESET_TITLE_QUALITY
    custom_filename_template: str = ""
    video_codec: str = CODEC_ANY
    audio_codec: str = CODEC_ANY
    custom_format: str = ""
    # Not compared: it only records which values were replaced.
    rejected: tuple[str, ...] = field(default=(), compare=False)

    @classmethod
    def from_config(cls, config: Any) -> DownloadPreferences:
        """Build the value from an ``AppConfig``.

        A value that fails its check (for example a hand-edited config file)
        is replaced by its default. Its name is logged, never the value.
        """
        values = {
            "cookies_browser": _text(getattr(config, "cookies_browser", "")),
            "cookies_profile": _text(getattr(config, "cookies_profile", "")),
            "proxy": _text(getattr(config, "proxy_url", "")),
            "filename_preset": _text(getattr(config, "filename_template_preset", "")),
            "custom_filename_template": _text(getattr(config, "custom_filename_template", "")),
            "video_codec": _text(getattr(config, "video_codec_preference", "")),
            "audio_codec": _text(getattr(config, "audio_codec_preference", "")),
            "custom_format": _text(getattr(config, "custom_format", "")),
        }
        defaults = cls()
        rejected = [name for name, ok in _checks(values).items() if not ok]
        for name in rejected:
            values[name] = getattr(defaults, name)
        if rejected:
            logger.warning(f"Ignoring invalid advanced download settings: {', '.join(rejected)}")
        return cls(**values, rejected=tuple(rejected))

    def network_opts(self) -> dict[str, Any]:
        """The proxy and cookie options for any ``YoutubeDL`` call."""
        return network_opts(self.proxy, self.cookies_browser, self.cookies_profile)


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _checks(values: dict[str, str]) -> dict[str, bool]:
    preset = values["filename_preset"]
    custom_template = values["custom_filename_template"]
    return {
        "cookies_browser": values["cookies_browser"] in ("", *cookie_browsers()),
        "cookies_profile": validate_cookies_profile(values["cookies_profile"]) is None,
        "proxy": validate_proxy_url(values["proxy"]) is None,
        "filename_preset": preset in FILENAME_PRESETS,
        "custom_filename_template": (
            validate_filename_template(custom_template) is None
            if custom_template or preset == FILENAME_PRESET_CUSTOM
            else True
        ),
        "video_codec": values["video_codec"] in VIDEO_CODEC_SORT,
        "audio_codec": values["audio_codec"] in AUDIO_CODEC_SORT,
        "custom_format": validate_custom_format(values["custom_format"]) is None,
    }


_MAX_PROFILE_LENGTH = 260


def validate_cookies_profile(profile: str) -> str | None:
    """Check a browser profile name or folder. Empty means the default profile."""
    if len(profile) > _MAX_PROFILE_LENGTH or any(ord(ch) < 32 or ord(ch) == 127 for ch in profile):
        return "error_cookies_profile"
    return None


_current = DownloadPreferences()


def get_download_preferences() -> DownloadPreferences:
    """The preferences from the last loaded or saved config."""
    return _current


def set_download_preferences(preferences: DownloadPreferences) -> None:
    """Publish new preferences. Downloads that start later use them."""
    global _current
    _current = preferences


# ---------- clear messages for cookie and sign-in failures ----------


def explain_download_error(messages: list[str | None], *, cookies_browser: str = "", proxy: str = "") -> str | None:
    """Return a translated explanation for a cookie, sign-in or proxy failure.

    Args:
        messages: Error texts for the failure (the exception text and the
            last yt-dlp error). None entries are skipped.
        cookies_browser: The browser the download read cookies from, or "".
        proxy: The proxy the download used, or "".

    Returns:
        The message for the user, or None if the failure is of another kind.
    """
    from ..utils.translations import tr

    text = " ".join(m for m in messages if m).lower()
    if not text:
        return None
    browser = cookies_browser
    if browser:
        key = _cookie_error_key(text)
        if key:
            return tr(key, browser=browser_display_name(browser))
    if "sign in" in text or "cookies-from-browser" in text or "--cookies" in text:
        if browser:
            return tr("cookies_hint_signed_in_browser", browser=browser_display_name(browser))
        return tr("cookies_hint_sign_in")
    if proxy and "proxy" in text:
        return tr("proxy_error_connect")
    return None


def _cookie_error_key(text: str) -> str | None:
    # Chrome 127+ app-bound encryption: yt-dlp's DPAPI call fails.
    if "dpapi" in text or "issues/10927" in text:
        return "cookies_error_app_bound"
    # The browser holds a lock on its cookie database (Windows).
    if "could not copy" in text and "cookie database" in text:
        return "cookies_error_locked"
    if "could not find" in text and "cookies database" in text:
        return "cookies_error_not_found"
    if "failed to load cookies" in text:
        return "cookies_error_generic"
    return None
