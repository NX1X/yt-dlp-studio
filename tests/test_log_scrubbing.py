"""Tests for ``SecretScrubbingFormatter`` in ``src/utils/logger.py``.

The formatter is what stops credentials from leaking into the rolling log
file when an exception traceback is rendered via ``logger.exception()`` or
``exc_info=``. These tests construct synthetic LogRecord objects and prove
the formatter scrubs URL userinfo, key=value pairs, Bearer tokens, and AWS
access key IDs in both the plain message AND in exc_info-rendered
tracebacks.
"""

from __future__ import annotations

import logging

from src.utils.logger import SecretScrubbingFormatter


def _record(msg: str, *args, **kwargs) -> logging.LogRecord:
    return logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=args,
        exc_info=kwargs.get("exc_info"),
    )


def test_formatter_redacts_url_userinfo():
    fmt = SecretScrubbingFormatter("%(message)s")
    out = fmt.format(_record("connecting to https://alice:hunter2@example.com/api"))
    assert "hunter2" not in out
    assert "alice" not in out
    assert "[REDACTED]" in out
    assert "https://" in out
    assert "@example.com/api" in out


def test_formatter_redacts_kv_pairs():
    fmt = SecretScrubbingFormatter("%(message)s")
    out = fmt.format(_record("api_key=sk_live_abc123XYZ failed"))
    assert "sk_live_abc123XYZ" not in out
    assert "api_key=" in out
    assert "[REDACTED]" in out


def test_formatter_redacts_bearer_token():
    """An ``Authorization: Bearer <token>`` line should never leak the token.

    Both the ``authorization`` key=value pattern AND the ``Bearer X``
    pattern fire here, so the literal word "Bearer" itself is also
    replaced. That is double-scrubbing, not a bug; the assertion below
    only requires that the secret token is gone and that ``[REDACTED]``
    appears.
    """
    fmt = SecretScrubbingFormatter("%(message)s")
    out = fmt.format(_record("headers: Authorization: Bearer eyJabc.def.ghijklmn"))
    assert "eyJabc.def.ghijklmn" not in out
    assert "[REDACTED]" in out


def test_formatter_redacts_aws_access_key_id():
    fmt = SecretScrubbingFormatter("%(message)s")
    out = fmt.format(_record("boto3 uses AKIAIOSFODNN7EXAMPLE for signing"))
    assert "AKIAIOSFODNN7EXAMPLE" not in out
    assert "[REDACTED]" in out


def test_formatter_scrubs_exc_info_traceback():
    """A traceback rendered from exc_info= must also be scrubbed."""
    fmt = SecretScrubbingFormatter("%(message)s")
    try:
        bad_url = "https://bob:secret123@host/data"  # NOSONAR test fixture
        raise ValueError(f"fetch failed for {bad_url}")
    except ValueError:
        import sys

        rec = _record("exception during fetch", exc_info=sys.exc_info())

    out = fmt.format(rec)
    assert "secret123" not in out
    assert "bob" not in out
    assert "[REDACTED]" in out
    # The traceback should still be visible structurally.
    assert "ValueError" in out
    assert "Traceback" in out


def test_formatter_passes_clean_text_through():
    fmt = SecretScrubbingFormatter("%(message)s")
    msg = "ConfigManager initialized with path: C:/Users/user/AppData/Roaming/foo.json"
    out = fmt.format(_record(msg))
    assert out == msg


def test_formatter_handles_args_interpolation():
    """%-style args should be interpolated BEFORE scrubbing."""
    fmt = SecretScrubbingFormatter("%(message)s")
    out = fmt.format(_record("token=%s leaked", "secret_value_XYZ"))
    assert "secret_value_XYZ" not in out
    assert "token=" in out
    assert "[REDACTED]" in out
