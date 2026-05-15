# PyInstaller hook for yt-dlp
# This ensures all required standard library modules are included

from PyInstaller.utils.hooks import collect_all

# Collect all yt-dlp modules
datas, binaries, hiddenimports = collect_all('yt_dlp')

# Add standard library modules that yt-dlp needs but PyInstaller doesn't auto-detect
# with Python 3.13+
hiddenimports += [
    'optparse',
    'getpass',  # Required by yt-dlp (v3.0.0 fix)
    'xml.etree',
    'xml.etree.ElementTree',
    'xml.etree.cElementTree',
    'xml.dom',
    'xml.dom.minidom',
    'xml.parsers',
    'xml.parsers.expat',
    'email',
    'email.mime',
    'email.mime.text',
    'email.mime.multipart',
    'email.mime.base',
    'http',
    'http.client',
    'http.cookiejar',
    'http.server',
    'urllib',
    'urllib.parse',
    'urllib.request',
    'urllib.error',
    'urllib.response',
    'html',
    'html.entities',
    'html.parser',
    'ctypes',
    'ctypes.wintypes',
    'ctypes.util',
    'json',
    'base64',
    'hashlib',
    'hmac',
    'uuid',
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
]
