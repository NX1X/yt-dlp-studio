# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec file for yt-dlp-studio (Linux)
#
# Build with: pyinstaller packaging/build_linux.spec
# Output: dist/yt-dlp-studio
#
# Note: Linux build does NOT bundle FFmpeg or Deno.
# Users must install FFmpeg via their package manager (e.g., apt install ffmpeg).
# Deno is optional (for YouTube JS challenges).
#

import os
from pathlib import Path

# Spec lives in packaging/, project root is one level up
project_root = Path(SPECPATH).parent

block_cipher = None

a = Analysis(
    [str(project_root / 'launcher.py')],
    pathex=[str(project_root)],
    binaries=[],  # No bundled binaries on Linux - rely on system FFmpeg/Deno
    datas=[
        # Include yt_dlp engine (vendored)
        (str(project_root / 'vendor' / 'yt_dlp_engine'), 'yt_dlp_engine'),
        # Include resources
        (str(project_root / 'src' / 'resources'), 'src/resources'),
    ],
    hiddenimports=[
        # SSL/TLS support
        'certifi',
        # yt-dlp core
        'yt_dlp',
        # PySide6 GUI framework
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        # Python stdlib modules needed by yt-dlp
        'optparse',
        'xml.etree',
        'xml.etree.ElementTree',
        'xml.dom',
        'xml.dom.minidom',
        'xml.parsers',
        'xml.parsers.expat',
        'email',
        'email.mime',
        'email.mime.text',
        'http',
        'http.client',
        'http.cookiejar',
        'urllib',
        'urllib.parse',
        'urllib.request',
        'urllib.error',
        'html',
        'html.entities',
        'html.parser',
        'ctypes',
        'ctypes.util',
        # Note: ctypes.wintypes excluded on Linux
        'uuid',
        'base64',
        'hashlib',
        'hmac',
        'struct',
        'socket',
        'ssl',
        'select',
        'threading',
        'multiprocessing',
        'queue',
        'tempfile',
        'shutil',
        'zipfile',
        'gzip',
        'bz2',
        'lzma',
        'calendar',
        'datetime',
        'time',
        'random',
        'secrets',
        'binascii',
        'io',
        'codecs',
        'locale',
        'platform',
        'copy',
        'functools',
        'weakref',
        'contextlib',
        'decimal',
        'fractions',
        'math',
        'cmath',
        'numbers',
        'fileinput',
        'glob',
        'fnmatch',
        'linecache',
        'pathlib',
        'stat',
        'filecmp',
        'string',
        'textwrap',
        'unicodedata',
        're',
        'difflib',
        'collections.abc',
        'itertools',
        'heapq',
        'bisect',
        'array',
        'enum',
        'os',
        'os.path',
        'sys',
        'argparse',
        'getopt',
        'getpass',
        'sysconfig',
        'logging',
        'warnings',
        'traceback',
        'atexit',
        'signal',
        'ipaddress',
        'socketserver',
        'pickle',
        'shelve',
        'dbm',
        'sqlite3',
        'json',
        'csv',
        'configparser',
        'tarfile',
        'subprocess',
        'sched',
        'requests',
        'packaging',
    ],
    hookspath=[str(Path(SPECPATH))],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'PIL',
        'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='yt-dlp-studio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # Strip debug symbols on Linux for smaller binary
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
