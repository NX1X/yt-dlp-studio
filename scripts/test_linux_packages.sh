#!/usr/bin/env bash
#
# CI end-to-end test for the Linux packages built by
# packaging/linux/build_packages.sh. Runs on an Ubuntu runner with sudo:
#
#   AppImage  launch headless (extract-and-run, runners have no FUSE)
#   .deb      apt install, check files and marker, launch, purge, check that
#             user data survives
#   .rpm      check metadata, extract, launch the extracted binary
#
# Every payload must be byte-identical to the PyInstaller binary: a changed
# hash means a tool stripped or rewrote it.
#
#     scripts/test_linux_packages.sh <binary> <packages-dir>
#
set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <binary> <packages-dir>" >&2
    exit 2
fi
BINARY="$(realpath "$1")"
PKG_DIR="$(realpath "$2")"
EXPECTED_SHA="$(sha256sum "${BINARY}" | cut -d' ' -f1)"
export QT_QPA_PLATFORM=offscreen

fail() { echo "FAIL: $*" >&2; exit 1; }
ok() { echo "ok: $*"; }

one_file() {
    # shellcheck disable=SC2206  # $1 is a glob on purpose
    local matches=("${PKG_DIR}"/$1)
    [[ ${#matches[@]} -eq 1 && -f "${matches[0]}" ]] || fail "expected one $1 in ${PKG_DIR}"
    echo "${matches[0]}"
}

same_payload() {
    local got
    got="$(sha256sum "$1" | cut -d' ' -f1)"
    [[ "${got}" == "${EXPECTED_SHA}" ]] || fail "$1 differs from the built binary (${got})"
}

# Start a command, wait up to 30 s for the "started successfully" log line,
# then stop it.
smoke_launch() {
    local label="$1"; shift
    local log
    log="$(mktemp)"
    "$@" >"${log}" 2>&1 &
    local pid=$! started=0
    for _ in $(seq 1 30); do
        if grep -q "started successfully" "${log}"; then started=1; break; fi
        kill -0 "${pid}" 2>/dev/null || break
        sleep 1
    done
    kill "${pid}" 2>/dev/null || true
    wait "${pid}" 2>/dev/null || true
    if [[ ${started} -ne 1 ]]; then
        cat "${log}" >&2
        fail "${label} did not reach 'started successfully'"
    fi
    ok "${label} started (log reached 'started successfully')"
}

# ---------- AppImage ----------
appimage="$(one_file '*.AppImage')"
[[ -x "${appimage}" ]] || fail "AppImage is not executable"
extract_dir="$(mktemp -d)"
(cd "${extract_dir}" && "${appimage}" --appimage-extract >/dev/null)
same_payload "${extract_dir}/squashfs-root/usr/bin/yt-dlp-studio"
ok "AppImage payload matches the built binary"
smoke_launch "AppImage" env APPIMAGE_EXTRACT_AND_RUN=1 "${appimage}"

# ---------- .deb ----------
deb="$(one_file '*.deb')"
sudo apt-get install -y --no-install-recommends "${deb}" >/dev/null
ok ".deb installed with apt (dependencies resolved, FFmpeg included)"
[[ "$(readlink -f /usr/bin/yt-dlp-studio)" == /opt/yt-dlp-studio/yt-dlp-studio ]] || fail "/usr/bin/yt-dlp-studio link"
same_payload /opt/yt-dlp-studio/yt-dlp-studio
grep -qx "kind=deb" /opt/yt-dlp-studio/install.ini || fail "install marker kind=deb"
[[ -f /usr/share/applications/yt-dlp-studio.desktop ]] || fail "desktop entry"
[[ -f /usr/share/icons/hicolor/256x256/apps/yt-dlp-studio.png ]] || fail "icon"
command -v ffmpeg >/dev/null || fail "ffmpeg not pulled in by the package"
ok ".deb files, marker, desktop entry, icon and FFmpeg in place"
smoke_launch ".deb install" yt-dlp-studio

data_dir="${HOME}/.config/YT-DLP Studio"
[[ -d "${data_dir}" ]] || fail "the app did not create ${data_dir}"
echo "keep me" > "${data_dir}/purge-test.txt"
sudo apt-get purge -y yt-dlp-studio >/dev/null
[[ ! -e /opt/yt-dlp-studio && ! -e /usr/bin/yt-dlp-studio ]] || fail "purge left program files"
[[ ! -e /usr/share/applications/yt-dlp-studio.desktop ]] || fail "purge left the desktop entry"
[[ -f "${data_dir}/purge-test.txt" ]] || fail "purge deleted user data"
rm -f "${data_dir}/purge-test.txt"
ok ".deb purge removed the program and kept user data"

# ---------- .rpm ----------
rpm_file="$(one_file '*.rpm')"
requires="$(rpm -qp --requires "${rpm_file}" 2>/dev/null)"
grep -q "ffmpeg" <<<"${requires}" || fail ".rpm does not require FFmpeg"
rpm -qpl "${rpm_file}" 2>/dev/null | grep -qx /opt/yt-dlp-studio/yt-dlp-studio || fail ".rpm file list"
rpm_root="$(mktemp -d)"
(cd "${rpm_root}" && rpm2cpio "${rpm_file}" | cpio -idm --quiet)
same_payload "${rpm_root}/opt/yt-dlp-studio/yt-dlp-studio"
grep -qx "kind=rpm" "${rpm_root}/opt/yt-dlp-studio/install.ini" || fail "install marker kind=rpm"
ok ".rpm metadata, file list, marker and payload are correct"
smoke_launch ".rpm payload" "${rpm_root}/opt/yt-dlp-studio/yt-dlp-studio"

echo "Linux package test passed."
