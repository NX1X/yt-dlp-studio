# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec file for yt-dlp-studio (Linux)
#
# Build with: pyinstaller packaging/build_linux.spec
# Output: dist/yt-dlp-studio
#
# Note: Linux build does NOT bundle FFmpeg or Deno.
# Users must install FFmpeg via their package manager (apt/dnf/pacman/zypper/...).
# Deno is optional (for YouTube JS challenges) and auto-downloads on first run.
#
# Portability: the shipped binary's glibc floor is the build host's glibc, so
# CI builds this on ubuntu-22.04 (glibc 2.35), not ubuntu-latest. It also relies
# on the standard Qt runtime libraries provided by any desktop environment
# (libglib-2.0, libGL, fontconfig); these are not bundled.
#

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

# Spec lives in packaging/, project root is one level up
project_root = Path(SPECPATH).parent

block_cipher = None

# curl_cffi ships native libcurl-impersonate binaries, cacert.pem, and
# CFFI-generated extension modules. PyInstaller's static analysis misses the
# data files and the native impersonation libs, so without collect_all() the
# frozen build imports curl_cffi fine but fails at download time with
# "Impersonate target 'chrome' is not available". Mirrors packaging/build.spec.
_curl_cffi_datas, _curl_cffi_binaries, _curl_cffi_hidden = collect_all('curl_cffi')

a = Analysis(
    [str(project_root / 'launcher.py')],
    pathex=[str(project_root)],
    binaries=[
        # curl_cffi native binaries (libcurl-impersonate). FFmpeg/Deno are NOT
        # bundled on Linux - the app uses system FFmpeg and auto-installs Deno.
        *_curl_cffi_binaries,
    ],
    datas=[
        # Include yt_dlp engine (vendored)
        (str(project_root / 'vendor' / 'yt_dlp_engine'), 'yt_dlp_engine'),
        # Include resources
        (str(project_root / 'src' / 'resources'), 'src/resources'),
        # curl_cffi data files (cacert.pem, CFFI headers)
        *_curl_cffi_datas,
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
        # Concurrency. yt-dlp's fragment downloader imports concurrent.futures;
        # the vendored engine is bundled as `datas` (not analysed for imports),
        # so these must be listed explicitly or the binary fails at run time
        # with "No module named 'concurrent'" (it happened to be pulled in
        # transitively on 3.11 but not on 3.10). Mirrors packaging/build.spec.
        'asyncio',
        'concurrent',
        'concurrent.futures',
        'requests',
        'packaging',
        # yt-dlp-ejs: the external JavaScript solver yt-dlp uses to pass
        # YouTube's JS challenges. Without it bundled, YouTube extraction on the
        # frozen Linux build silently loses formats / hits challenges.
        'yt_dlp_ejs',
        'yt_dlp_ejs.yt',
        'yt_dlp_ejs.yt.solver',
        # Browser-impersonation HTTP client. yt-dlp probes for it via
        # `from yt_dlp.dependencies import curl_cffi`; the full submodule set is
        # collected via collect_all() above.
        *_curl_cffi_hidden,
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
