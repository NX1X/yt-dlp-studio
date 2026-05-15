# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec file for yt-dlp-studio
#
# Build with: pyinstaller packaging/build.spec
# Output: dist/yt-dlp-studio.exe (Windows) or dist/yt-dlp-studio (Linux)
#

import os
from pathlib import Path

# Spec lives in packaging/, project root is one level up
project_root = Path(SPECPATH).parent

block_cipher = None

a = Analysis(
    [str(project_root / 'launcher.py')],
    pathex=[str(project_root)],
    binaries=[
        # Bundle Deno JS runtime (required for YouTube JS challenge solving)
        (str(project_root / 'deno' / 'deno.exe'), '.'),
        # Bundle FFmpeg binaries (required for yt-dlp post-processing)
        # Main executables
        (str(project_root / 'ffmpeg' / 'bin' / 'ffmpeg.exe'), '.'),
        (str(project_root / 'ffmpeg' / 'bin' / 'ffprobe.exe'), '.'),
        (str(project_root / 'ffmpeg' / 'bin' / 'ffplay.exe'), '.'),
        # Required DLL dependencies
        (str(project_root / 'ffmpeg' / 'bin' / 'avcodec-62.dll'), '.'),
        (str(project_root / 'ffmpeg' / 'bin' / 'avdevice-62.dll'), '.'),
        (str(project_root / 'ffmpeg' / 'bin' / 'avfilter-11.dll'), '.'),
        (str(project_root / 'ffmpeg' / 'bin' / 'avformat-62.dll'), '.'),
        (str(project_root / 'ffmpeg' / 'bin' / 'avutil-60.dll'), '.'),
        (str(project_root / 'ffmpeg' / 'bin' / 'swresample-6.dll'), '.'),
        (str(project_root / 'ffmpeg' / 'bin' / 'swscale-9.dll'), '.'),
    ],
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
        # Notifications (plyer not installed — system tray used instead)
        # Python 3.13/3.14 compatibility - standard library modules not auto-detected
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
        'ctypes.wintypes',
        'ctypes.util',
        # More stdlib modules needed by yt-dlp
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
        # File I/O and processing modules
        'fileinput',
        'glob',
        'fnmatch',
        'linecache',
        'pathlib',
        'stat',
        'filecmp',
        # String and text processing
        'string',
        'textwrap',
        'unicodedata',
        're',
        'difflib',
        # Data structures and algorithms
        'collections.abc',
        'itertools',
        'heapq',
        'bisect',
        'array',
        'enum',
        # System and OS
        'os',
        'os.path',
        'sys',
        'argparse',
        'getopt',
        'getpass',  # Required by yt-dlp (v3.0.0 fix)
        'sysconfig',  # Required by yt-dlp 2026.02.04 (_jsruntime.py / Deno detection)
        'logging',
        'warnings',
        'traceback',
        'atexit',
        'signal',
        # Networking and internet
        'ipaddress',
        'socketserver',
        # Data persistence
        'pickle',
        'shelve',
        'dbm',
        'sqlite3',
        'json',
        'csv',
        'configparser',
        # Compression and archiving (already have some)
        'tarfile',
        # Cryptography and hashing (already have some)
        'secrets',
        # Concurrency (already have some)
        'asyncio',
        'concurrent',
        'concurrent.futures',
        'subprocess',
        'sched',
        # Additional dependencies
        'requests',
        'packaging',
    ],
    hookspath=[str(Path(SPECPATH))],  # Hooks live next to this spec, in packaging/
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
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / 'src' / 'resources' / 'icons' / 'favicon.ico'),
    # Professional Windows executable metadata (v1.7.0)
    version=str(Path(SPECPATH) / 'version_info.txt'),  # Version information resource
    uac_admin=False,  # Don't require admin privileges
    uac_uiaccess=False,
)

# For directory-based build (one-folder mode), use this instead:
# coll = COLLECT(
#     exe,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     name='yt-dlp-studio',
# )
