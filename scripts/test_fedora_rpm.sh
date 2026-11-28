#!/usr/bin/env bash
#
# CI install test for the .rpm built by packaging/linux/build_packages.sh,
# on a real Fedora system. Runs as root INSIDE a Fedora container (see the
# test-fedora-rpm job in .github/workflows/build.yml):
#
#   1. dnf install the .rpm (FFmpeg comes from Fedora as ffmpeg-free)
#   2. check the files, the /usr/bin link and the install marker kind=rpm
#   3. launch the installed app headless until it logs "started successfully"
#   4. dnf remove the package and check that user data survives
#
#     scripts/test_fedora_rpm.sh <path-to-rpm>
#
# dnf uses ONE https mirror (FEDORA_MIRROR, default mirrors.kernel.org)
# instead of the metalink, so the CI egress allowlist stays small and fixed.
# The stock repo definitions are kept, so packages are still checked against
# the Fedora GPG keys that ship in the image.
#
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <path-to-rpm>" >&2
    exit 2
fi
RPM_FILE="$(realpath "$1")"
FEDORA_MIRROR="${FEDORA_MIRROR:-https://mirrors.kernel.org/fedora}"
export QT_QPA_PLATFORM=offscreen

fail() { echo "FAIL: $*" >&2; exit 1; }
ok() { echo "ok: $*"; }

[[ -f "${RPM_FILE}" ]] || fail "no such file: ${RPM_FILE}"
# shellcheck source=/dev/null
. /etc/os-release
[[ "${ID}" == "fedora" ]] || fail "this test runs on Fedora, not ${ID}"
releasever="${VERSION_ID}"
ok "Fedora ${releasever} ($(uname -m))"

dnf_opts=(
    -y
    --setopt=install_weak_deps=False
    --disablerepo=fedora-cisco-openh264
    --setopt=fedora.metalink=
    "--setopt=fedora.baseurl=${FEDORA_MIRROR}/releases/${releasever}/Everything/\$basearch/os/"
    --setopt=updates.metalink=
    "--setopt=updates.baseurl=${FEDORA_MIRROR}/updates/${releasever}/Everything/\$basearch/"
)

# The .rpm sets AutoReqProv: no and requires only FFmpeg and glibc. The
# bundled Qt still needs these system libraries (the Fedora names of the set
# the .deb depends on). A desktop Fedora has them; the container does not.
qt_libs=(libglvnd-egl libglvnd-glx libxkbcommon dbus-libs xcb-util-cursor glib2 fontconfig)

# ---------- install ----------
dnf "${dnf_opts[@]}" install "${RPM_FILE}" "${qt_libs[@]}"
rpm -q yt-dlp-studio >/dev/null || fail "yt-dlp-studio is not installed"
ok ".rpm installed with dnf ($(rpm -q yt-dlp-studio))"
rpm -q ffmpeg-free >/dev/null || rpm -q ffmpeg >/dev/null || fail "no FFmpeg package was pulled in"
command -v ffmpeg >/dev/null || fail "ffmpeg is not on PATH"
ok "FFmpeg pulled in: $(ffmpeg -hide_banner -version | head -1)"

# ---------- files ----------
[[ -x /opt/yt-dlp-studio/yt-dlp-studio ]] || fail "/opt/yt-dlp-studio/yt-dlp-studio missing or not executable"
[[ "$(readlink -f /usr/bin/yt-dlp-studio)" == /opt/yt-dlp-studio/yt-dlp-studio ]] || fail "/usr/bin/yt-dlp-studio link"
grep -qx "kind=rpm" /opt/yt-dlp-studio/install.ini || fail "install marker kind=rpm"
[[ -f /usr/share/applications/yt-dlp-studio.desktop ]] || fail "desktop entry"
[[ -f /usr/share/icons/hicolor/256x256/apps/yt-dlp-studio.png ]] || fail "icon"
rpm -V yt-dlp-studio || fail "rpm -V reports changed files"
ok "files, link, marker kind=rpm, desktop entry and icon in place"

# ---------- launch ----------
# Start the installed app, wait up to 30 s for the "started successfully"
# log line, then stop it.
log="$(mktemp)"
yt-dlp-studio >"${log}" 2>&1 &
pid=$!
started=0
for _ in $(seq 1 30); do
    if grep -q "started successfully" "${log}"; then started=1; break; fi
    kill -0 "${pid}" 2>/dev/null || break
    sleep 1
done
kill "${pid}" 2>/dev/null || true
wait "${pid}" 2>/dev/null || true
if [[ ${started} -ne 1 ]]; then
    cat "${log}" >&2
    fail "the installed app did not reach 'started successfully'"
fi
ok "installed app started (log reached 'started successfully')"

# ---------- remove ----------
data_dir="${HOME}/.config/YT-DLP Studio"
[[ -d "${data_dir}" ]] || fail "the app did not create ${data_dir}"
echo "keep me" > "${data_dir}/remove-test.txt"
dnf "${dnf_opts[@]}" remove yt-dlp-studio
! rpm -q yt-dlp-studio >/dev/null 2>&1 || fail "yt-dlp-studio is still installed"
[[ ! -e /opt/yt-dlp-studio/yt-dlp-studio && ! -e /usr/bin/yt-dlp-studio ]] || fail "remove left program files"
[[ ! -e /usr/share/applications/yt-dlp-studio.desktop ]] || fail "remove left the desktop entry"
[[ -f "${data_dir}/remove-test.txt" ]] || fail "remove deleted user data"
ok "dnf remove removed the program and kept user data in ${data_dir}"

echo "Fedora .rpm test passed."
