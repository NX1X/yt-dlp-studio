#!/usr/bin/env bash
#
# YT-DLP Studio - Linux desktop installer (user-level, no root required).
#
# Installs the bundled executable, icons, and a .desktop launcher into the
# per-user XDG locations so YT-DLP Studio appears in the application menu /
# dock. Run from inside the extracted release archive:
#
#     ./install.sh
#
# Uninstall with ./uninstall.sh (same directory) or see the paths printed at
# the end of this script.
#
set -euo pipefail

APP_ID="yt-dlp-studio"
APP_NAME="YT-DLP Studio"

# Directory this script lives in (the extracted archive root).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# XDG user directories (honour overrides, fall back to the defaults).
BIN_DIR="${HOME}/.local/bin"
DATA_DIR="${XDG_DATA_HOME:-${HOME}/.local/share}"
APPS_DIR="${DATA_DIR}/applications"
ICONS_DIR="${DATA_DIR}/icons/hicolor"

BIN_SRC="${SCRIPT_DIR}/${APP_ID}"
if [ ! -f "${BIN_SRC}" ]; then
    echo "Error: executable '${APP_ID}' not found next to this script." >&2
    echo "Run install.sh from inside the extracted release archive." >&2
    exit 1
fi

echo "Installing ${APP_NAME}..."

# 1. Executable -> ~/.local/bin (usually on PATH on modern Ubuntu).
mkdir -p "${BIN_DIR}"
install -m 0755 "${BIN_SRC}" "${BIN_DIR}/${APP_ID}"
echo "  - executable: ${BIN_DIR}/${APP_ID}"

# 2. Icons -> hicolor theme at every size we ship.
for size in 32 48 64 128 256; do
    src="${SCRIPT_DIR}/icons/${APP_ID}-${size}.png"
    if [ -f "${src}" ]; then
        dst_dir="${ICONS_DIR}/${size}x${size}/apps"
        mkdir -p "${dst_dir}"
        install -m 0644 "${src}" "${dst_dir}/${APP_ID}.png"
    fi
done
echo "  - icons: ${ICONS_DIR}/<size>/apps/${APP_ID}.png"

# 3. .desktop launcher -> ~/.local/share/applications, with an absolute
#    Exec/Icon so it works regardless of whether ~/.local/bin is on PATH.
mkdir -p "${APPS_DIR}"
DESKTOP_DST="${APPS_DIR}/${APP_ID}.desktop"
cat > "${DESKTOP_DST}" <<EOF
[Desktop Entry]
Type=Application
Version=1.5
Name=${APP_NAME}
GenericName=Video Downloader
Comment=A user-friendly GUI for yt-dlp - download videos and audio from YouTube and 1000+ sites
Exec=${BIN_DIR}/${APP_ID} %U
Icon=${APP_ID}
Terminal=false
Categories=AudioVideo;Video;Network;Utility;
Keywords=youtube;video;download;yt-dlp;audio;converter;
StartupNotify=true
StartupWMClass=${APP_ID}
EOF
chmod 0644 "${DESKTOP_DST}"
echo "  - launcher: ${DESKTOP_DST}"

# 4. Refresh the desktop/icon caches (best-effort; non-fatal if missing).
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${APPS_DIR}" >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "${ICONS_DIR}" >/dev/null 2>&1 || true
fi

echo ""
echo "${APP_NAME} installed successfully."
echo "Launch it from your application menu, or run: ${APP_ID}"
echo ""
echo "Requirements:"
echo "  - FFmpeg (required):   sudo apt install ffmpeg"
echo "  - Deno (optional):     auto-downloaded on first run, or install from https://deno.land"
echo ""
if ! printf '%s' ":${PATH}:" | grep -q ":${BIN_DIR}:"; then
    echo "Note: ${BIN_DIR} is not on your PATH. The menu launcher still works;"
    echo "to run '${APP_ID}' from a terminal, add this to your ~/.bashrc:"
    echo "  export PATH=\"\${HOME}/.local/bin:\${PATH}\""
    echo ""
fi
echo "To uninstall, run ./uninstall.sh from this folder."
