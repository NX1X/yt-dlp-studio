#!/usr/bin/env bash
#
# Build the Linux packages from one PyInstaller binary:
#
#   YT-DLP-Studio-<version>-x86_64.AppImage   runs with no install
#   yt-dlp-studio_<version>_amd64.deb         installed and removed by apt
#   yt-dlp-studio-<version>-1.x86_64.rpm      installed and removed by dnf
#
# All three wrap the same binary that goes into the .tar.gz, so the payload
# is built once. Usage:
#
#     packaging/linux/build_packages.sh <version> <binary> <out-dir>
#
# Needs: dpkg-deb, rpmbuild (apt package "rpm"), curl, sha256sum.
# appimagetool and the AppImage runtime are downloaded here and verified by
# SHA-256 before use. Both come from the AppImage project (maintainers in
# Germany), checked against the software-origin rule.
#
# Removing a package never removes user data: settings and history live in
# ~/.config/YT-DLP Studio, which no package script touches.
#
set -euo pipefail
# Packaged files get 0644/0755 whatever the caller's umask is.
umask 022

APPIMAGETOOL_VERSION="1.9.1"
APPIMAGETOOL_SHA256="ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0"
APPIMAGE_RUNTIME_VERSION="20251108"
APPIMAGE_RUNTIME_SHA256="2fca8b443c92510f1483a883f60061ad09b46b978b2631c807cd873a47ec260d"

APP_ID="yt-dlp-studio"
MAINTAINER="NX1X <NX1X@users.noreply.github.com>"
HOMEPAGE="https://github.com/NX1X/yt-dlp-studio"
SUMMARY="Desktop GUI for yt-dlp"
DESCRIPTION="A user-friendly desktop GUI for yt-dlp. Download videos and audio from YouTube and 1000+ sites without the command line."
ICON_SIZES=(32 48 64 128 256)

if [[ $# -ne 3 ]]; then
    echo "Usage: $0 <version> <binary> <out-dir>" >&2
    exit 2
fi
VERSION="$1"
BINARY="$(realpath "$2")"
OUT_DIR="$(realpath -m "$3")"

if [[ ! "${VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.+-][A-Za-z0-9.+-]+)?$ ]]; then
    echo "Error: '${VERSION}' is not a version like 0.3.1 or 0.3.1-beta.1" >&2
    exit 2
fi
if [[ ! -x "${BINARY}" ]]; then
    echo "Error: binary '${BINARY}' is missing or not executable" >&2
    exit 2
fi

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT
mkdir -p "${OUT_DIR}"

# Debian and RPM sort "~" before anything, so 0.3.1~beta.1 < 0.3.1. The file
# names keep the plain version: GitHub rewrites "~" in release asset names.
PKG_VERSION="${VERSION//-/\~}"

fetch_verified() {
    local url="$1" sha="$2" dest="$3"
    curl --fail --silent --show-error --location --retry 3 --proto '=https' --output "${dest}" "${url}"
    echo "${sha}  ${dest}" | sha256sum --check --strict --quiet
    echo "verified: $(basename "${dest}") ${sha}"
}

# Lay out the files every installed form shares under a root directory:
#   <root>/opt/yt-dlp-studio/yt-dlp-studio      the binary
#   <root>/opt/yt-dlp-studio/install.ini        install marker (kind=$2)
#   <root>/usr/bin/yt-dlp-studio                symlink to the binary
#   <root>/usr/share/applications/...desktop    launcher
#   <root>/usr/share/icons/hicolor/NxN/apps     icons
stage_system_root() {
    local root="$1" kind="$2"
    install -D -m 0755 "${BINARY}" "${root}/opt/${APP_ID}/${APP_ID}"
    printf '[Install]\nkind=%s\nversion=%s\n' "${kind}" "${VERSION}" > "${root}/opt/${APP_ID}/install.ini"
    chmod 0644 "${root}/opt/${APP_ID}/install.ini"
    mkdir -p "${root}/usr/bin"
    ln -s "/opt/${APP_ID}/${APP_ID}" "${root}/usr/bin/${APP_ID}"
    install -D -m 0644 "${SRC_DIR}/${APP_ID}.desktop" "${root}/usr/share/applications/${APP_ID}.desktop"
    for size in "${ICON_SIZES[@]}"; do
        install -D -m 0644 "${SRC_DIR}/${APP_ID}-${size}.png" \
            "${root}/usr/share/icons/hicolor/${size}x${size}/apps/${APP_ID}.png"
    done
}

build_deb() {
    local root="${WORK}/deb"
    local out="${OUT_DIR}/${APP_ID}_${VERSION}_amd64.deb"
    stage_system_root "${root}" deb
    mkdir -p "${root}/DEBIAN"
    local size_kb
    size_kb="$(du -sk "${root}" | cut -f1)"
    # The binary bundles Qt but needs these system libraries (the same set the
    # CI smoke test installs). Ubuntu 24.04 renamed libglib2.0-0 in the
    # 64-bit time_t transition, hence the alternative.
    cat > "${root}/DEBIAN/control" <<EOF
Package: ${APP_ID}
Version: ${PKG_VERSION}
Section: video
Priority: optional
Architecture: amd64
Maintainer: ${MAINTAINER}
Installed-Size: ${size_kb}
Depends: ffmpeg, libc6 (>= 2.35), libegl1, libgl1, libxkbcommon0, libdbus-1-3, libxcb-cursor0, libfontconfig1, libglib2.0-0t64 | libglib2.0-0
Homepage: ${HOMEPAGE}
Description: ${SUMMARY}
 A user-friendly desktop GUI for yt-dlp. Download videos and audio from
 YouTube and 1000+ sites without the command line.
 .
 Removing or purging this package keeps your settings and download history
 in ~/.config/YT-DLP Studio. Delete that folder by hand to remove them.
EOF
    # Refresh the menu and icon caches. No script deletes user data: they run
    # as root and cannot know which user's files to remove.
    cat > "${root}/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
fi
EOF
    cat > "${root}/DEBIAN/postrm" <<'EOF'
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if [ "$1" = "purge" ]; then
    echo "YT-DLP Studio: settings and history in ~/.config/YT-DLP Studio were kept."
fi
EOF
    chmod 0755 "${root}/DEBIAN/postinst" "${root}/DEBIAN/postrm"
    dpkg-deb --root-owner-group -Zxz --build "${root}" "${out}"
    echo "built: ${out}"
}

build_rpm() {
    local top="${WORK}/rpmbuild"
    local root="${WORK}/rpmroot"
    local out="${OUT_DIR}/${APP_ID}-${VERSION}-1.x86_64.rpm"
    stage_system_root "${root}" rpm
    mkdir -p "${top}"/{BUILD,RPMS,SPECS,SRPMS,SOURCES}
    # Fedora ships FFmpeg as "ffmpeg-free"; RPM Fusion and others as "ffmpeg".
    # Never strip the binary or build debug info: stripping a PyInstaller
    # one-file binary cuts off the archive appended to it. AutoReqProv is off
    # so rpmbuild does not scan the bundled libraries for dependencies.
    cat > "${top}/SPECS/${APP_ID}.spec" <<EOF
%global debug_package %{nil}
%global __os_install_post %{nil}
%global _build_id_links none
Name:           ${APP_ID}
Version:        ${PKG_VERSION}
Release:        1
Summary:        ${SUMMARY}
License:        Apache-2.0
URL:            ${HOMEPAGE}
BuildArch:      x86_64
AutoReqProv:    no
Requires:       (ffmpeg or ffmpeg-free)
Requires:       glibc >= 2.35

%description
${DESCRIPTION}

Removing this package keeps your settings and download history in
~/.config/YT-DLP Studio. Delete that folder by hand to remove them.

%install
cp -a "${root}/." "%{buildroot}/"

%post
update-desktop-database -q /usr/share/applications >/dev/null 2>&1 || :
gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor >/dev/null 2>&1 || :

%postun
update-desktop-database -q /usr/share/applications >/dev/null 2>&1 || :

%files
%dir /opt/${APP_ID}
/opt/${APP_ID}/${APP_ID}
/opt/${APP_ID}/install.ini
/usr/bin/${APP_ID}
/usr/share/applications/${APP_ID}.desktop
$(for size in "${ICON_SIZES[@]}"; do echo "/usr/share/icons/hicolor/${size}x${size}/apps/${APP_ID}.png"; done)
EOF
    rpmbuild --quiet --define "_topdir ${top}" -bb "${top}/SPECS/${APP_ID}.spec"
    cp "${top}/RPMS/x86_64/${APP_ID}-${PKG_VERSION}-1.x86_64.rpm" "${out}"
    echo "built: ${out}"
}

build_appimage() {
    local appdir="${WORK}/AppDir"
    local out="${OUT_DIR}/YT-DLP-Studio-${VERSION}-x86_64.AppImage"
    local tool="${WORK}/appimagetool"
    local runtime="${WORK}/runtime-x86_64"
    fetch_verified \
        "https://github.com/AppImage/appimagetool/releases/download/${APPIMAGETOOL_VERSION}/appimagetool-x86_64.AppImage" \
        "${APPIMAGETOOL_SHA256}" "${tool}"
    fetch_verified \
        "https://github.com/AppImage/type2-runtime/releases/download/${APPIMAGE_RUNTIME_VERSION}/runtime-x86_64" \
        "${APPIMAGE_RUNTIME_SHA256}" "${runtime}"
    chmod +x "${tool}"

    install -D -m 0755 "${BINARY}" "${appdir}/usr/bin/${APP_ID}"
    install -D -m 0644 "${SRC_DIR}/${APP_ID}.desktop" "${appdir}/${APP_ID}.desktop"
    install -D -m 0644 "${SRC_DIR}/${APP_ID}-256.png" "${appdir}/${APP_ID}.png"
    for size in "${ICON_SIZES[@]}"; do
        install -D -m 0644 "${SRC_DIR}/${APP_ID}-${size}.png" \
            "${appdir}/usr/share/icons/hicolor/${size}x${size}/apps/${APP_ID}.png"
    done
    ln -s "${APP_ID}.png" "${appdir}/.DirIcon"
    cat > "${appdir}/AppRun" <<EOF
#!/bin/sh
HERE="\$(dirname "\$(readlink -f "\$0")")"
exec "\${HERE}/usr/bin/${APP_ID}" "\$@"
EOF
    chmod 0755 "${appdir}/AppRun"

    # Extract-and-run: CI runners and containers have no FUSE. --no-appstream:
    # the app ships no AppStream metainfo yet.
    ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "${tool}" --no-appstream \
        --runtime-file "${runtime}" "${appdir}" "${out}"
    chmod 0755 "${out}"
    echo "built: ${out}"
}

build_deb
build_rpm
build_appimage

(cd "${OUT_DIR}" && sha256sum -- *.AppImage *.deb *.rpm)
