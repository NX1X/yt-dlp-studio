"""
Subprocess helpers for YT-DLP Studio.

The Windows build is a GUI program (PyInstaller ``console=False``). When a GUI
program starts a console program such as ``ffmpeg.exe``, Windows opens a
console window for it, which flashes on screen. ``CREATE_NO_WINDOW`` stops
that. Other platforms need no flag.
"""

from __future__ import annotations

import subprocess
import sys
from typing import Any

# Value from the Windows SDK. ``subprocess.CREATE_NO_WINDOW`` exists only in
# the Windows build of Python, so keep a fallback for tests on other systems.
_CREATE_NO_WINDOW = 0x08000000


def hidden_window_kwargs() -> dict[str, Any]:
    """Return extra ``subprocess`` keyword arguments that hide a console window.

    On Windows this is ``{"creationflags": CREATE_NO_WINDOW}``. On every other
    platform it is an empty dict, so callers can always splat the result:

        subprocess.run(args, **hidden_window_kwargs())
    """
    if sys.platform == "win32":
        return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", _CREATE_NO_WINDOW)}
    return {}
