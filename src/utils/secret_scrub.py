"""
Secret-scrubbing helper shared by the crash handler and the logging
formatter.

This used to live inside ``src/utils/crash_handler.py`` as ``_scrub_secrets``
but is now a separate module so the logger can apply it to every log line
without creating a circular import (``crash_handler`` already depends on
``logger``).

The function ``scrub_secrets`` is best-effort - it catches the obvious shapes
that have shown up in real tracebacks and log lines on this project, not a
comprehensive DLP filter. The supported patterns are listed inline with the
regex table below.
"""

from __future__ import annotations

import re

REDACTED = "[REDACTED]"

# Patterns that catch the most common ways a credential ends up in a
# Python traceback, an exception message, or a log line:
#   1. Userinfo embedded in a URL: ``https://user:pass@host/...``
#   2. ``Bearer <token>`` / ``Basic <token>`` HTTP headers.
#   3. ``api_key`` / ``password`` / ``token`` / ``cookie`` / ``authorization``
#      key=value patterns, with either ``:`` or ``=`` as the separator.
#   4. AWS-style access key IDs (``AKIA...``).
_SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"(?P<scheme>https?://)[^/@\s]+:[^/@\s]+@", re.IGNORECASE),
        rf"\g<scheme>{REDACTED}@",
    ),
    # ``Bearer <token>`` / ``Basic <token>`` - the keyword is followed by
    # whitespace, not a ``:`` or ``=`` separator, so it needs its own rule.
    # Handled before the generic key=value pattern so the latter does not
    # half-match and leave the token visible. The ``-`` is placed FIRST in
    # the character class (where it is unambiguously literal regardless of
    # neighbouring chars); putting it at the end as ``=-`` still made Sonar
    # S5869 think it might be starting a range.
    (
        re.compile(
            r"(?P<keyword>\b(?:Bearer|Basic))\s+(?P<val>[-A-Za-z0-9._+/=]{8,})",
            re.IGNORECASE,
        ),
        rf"\g<keyword> {REDACTED}",
    ),
    (
        re.compile(
            r"(?P<key>(?:api[_-]?key|password|passwd|secret|token|cookie|authorization))"
            r"(?P<sep>\s*[:=]\s*)"
            r"(?P<val>['\"]?[^\s'\",;]+['\"]?)",
            re.IGNORECASE,
        ),
        rf"\g<key>\g<sep>{REDACTED}",
    ),
    (
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        REDACTED,
    ),
)


def scrub_secrets(text: str) -> str:
    """Replace anything that looks like a credential with ``[REDACTED]``.

    Used by:
      * ``src/utils/crash_handler.py`` to sanitize the fields written into
        the JSON crash report (``exception_message``, ``traceback``, and
        every line of ``log_tail``).
      * ``src/utils/logger.py`` to sanitize every formatted log record
        before it reaches a handler, so the rolling log file under
        ``%APPDATA%\\YT-DLP Studio\\yt-dlp-studio.log`` cannot leak
        credentials embedded in an ``exc_info=`` traceback.

    Best effort: designed to catch obvious cases. Not a comprehensive DLP.
    """
    if not text:
        return text
    for pattern, replacement in _SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text
