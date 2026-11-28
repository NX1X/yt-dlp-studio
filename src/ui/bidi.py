"""
Bidirectional text helpers for the Hebrew (right-to-left) UI.

A number with a unit ("12.3 MB", "3.2 MB/s") or a link inside Hebrew text
is reordered by the Unicode bidi algorithm ("MB 12.3"). Wrapping it in a
left-to-right isolate keeps it in reading order in both languages, and does
nothing visible in English.
"""

LRI = "⁦"  # LEFT-TO-RIGHT ISOLATE
PDI = "⁩"  # POP DIRECTIONAL ISOLATE


def ltr(text: str) -> str:
    """Return ``text`` wrapped in a left-to-right isolate."""
    return f"{LRI}{text}{PDI}"
