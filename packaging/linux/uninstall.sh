#!/usr/bin/env bash
#
# YT-DLP Studio - Linux desktop uninstaller (user-level).
#
# Removes the executable, icons, and .desktop launcher installed by
# install.sh. Does NOT touch user config/logs in
# ~/.config/YT-DLP Studio (delete that manually if you want a clean slate).
#
set -euo pipefail

APP_ID="yt-dlp-studio"
APP_NAME="YT-DLP Studio"

BIN_DIR="${HOME}/.local/bin"
DATA_DIR="${XDG_DATA_HOME:-${HOME}/.local/share}"
APPS_DIR="${DATA_DIR}/applications"
ICONS_DIR="${DATA_DIR}/icons/hicolor"

echo "Uninstalling ${APP_NAME}..."

rm -f "${BIN_DIR}/${APP_ID}" && echo "  - removed executable"

for size in 32 48 64 128 256; do
    rm -f "${ICONS_DIR}/${size}x${size}/apps/${APP_ID}.png"
done
echo "  - removed icons"

rm -f "${APPS_DIR}/${APP_ID}.desktop" && echo "  - removed launcher"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${APPS_DIR}" >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "${ICONS_DIR}" >/dev/null 2>&1 || true
fi

echo ""
echo "${APP_NAME} uninstalled."
echo "User settings/logs (if any) remain in: ${HOME}/.config/${APP_NAME}"
