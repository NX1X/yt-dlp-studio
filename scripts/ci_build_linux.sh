#!/usr/bin/env bash
#
# CI build of the Linux binary and packages. Runs as root INSIDE an
# ubuntu:22.04 container (see the build-linux job in build.yml and the
# build-linux job in release.yml), with the repository mounted as the working
# directory. Both jobs call this one script, so they cannot drift apart.
#
# Why a container: a PyInstaller binary only runs on a glibc at least as new
# as the build host's. Ubuntu 22.04 has glibc 2.35, and that is the floor the
# packages declare (libc6 >= 2.35, glibc >= 2.35). The container keeps that
# floor on a newer runner image.
#
# Python: Ubuntu 22.04 ships 3.10, but the app needs 3.11 or newer. uv
# (Astral, US) installs a python-build-standalone CPython. uv itself is
# downloaded here and checked by SHA-256 before use.
#
# Steps: apt packages, Python, dependencies, PyInstaller build, bundle check,
# smoke test, .deb/.rpm/AppImage build, package test. At the end the files
# written as root are handed back to the runner user (HOST_UID and HOST_GID).
#
#   VERSION     package version (no leading "v"); default: __version__ from
#               src/__init__.py
#   HOST_UID    owner of the output files (default 0, no chown)
#   HOST_GID    group of the output files (default 0)
#
set -euo pipefail

PYTHON_VERSION="3.14.10"
UV_VERSION="0.13.8"
UV_SHA256="5acfd9177cfecf0bf87578f059728215ccc884388988f55f7a65041b57387d91"
GLIBC_FLOOR="2.35"

HOST_UID="${HOST_UID:-0}"
HOST_GID="${HOST_GID:-0}"
export DEBIAN_FRONTEND=noninteractive
export QT_QPA_PLATFORM=offscreen

hand_back() {
    if [[ "${HOST_UID}" != "0" ]]; then
        chown -R "${HOST_UID}:${HOST_GID}" . || true
    fi
}
trap hand_back EXIT

# 1. The glibc floor. Fail early if the image is not 22.04.
glibc="$(getconf GNU_LIBC_VERSION)"
if [[ "${glibc}" != "glibc ${GLIBC_FLOOR}" ]]; then
    echo "Build host has '${glibc}', expected 'glibc ${GLIBC_FLOOR}'." >&2
    exit 1
fi
echo "Build host: ${glibc}"

# 2. System packages. binutils is needed by PyInstaller, file by appimagetool, sudo by
#    scripts/test_linux_packages.sh. rpm, rpm2cpio and cpio build and inspect
#    the .rpm package.
apt-get update
apt-get install -y --no-install-recommends \
    ca-certificates curl file sudo binutils \
    libegl1 libxkbcommon0 libdbus-1-3 libxcb-cursor0 libglib2.0-0 libgl1 \
    libfontconfig1 rpm rpm2cpio cpio

# 3. uv, checked by SHA-256, then Python and a virtual environment.
uv_dir="$(mktemp -d)"
curl --fail --silent --show-error --location --retry 3 --proto '=https' \
    --output "${uv_dir}/uv.tar.gz" \
    "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-x86_64-unknown-linux-gnu.tar.gz"
echo "${UV_SHA256}  ${uv_dir}/uv.tar.gz" | sha256sum --check --strict --quiet
tar -xzf "${uv_dir}/uv.tar.gz" -C "${uv_dir}" --strip-components=1
export PATH="${uv_dir}:${PATH}"
uv --version
uv venv --seed --python "${PYTHON_VERSION}" /opt/venv
export PATH="/opt/venv/bin:${PATH}"
python --version

# 4. Dependencies, all hash-locked, as in the other CI jobs.
python -m pip install --require-hashes -r requirements/pip.txt --only-binary :all:
python -m pip install --require-hashes -r requirements/lock.txt --only-binary :all:
python -m pip install --require-hashes -r requirements/build-tools.txt --only-binary :all:

# 5. Build.
python scripts/sync_version.py
pyinstaller packaging/build_linux.spec
python scripts/check_bundle.py dist/yt-dlp-studio

if [[ ! -f dist/yt-dlp-studio ]]; then
    echo "Build failed: dist/yt-dlp-studio not found!" >&2
    exit 1
fi
chmod +x dist/yt-dlp-studio
ls -lh dist/yt-dlp-studio

# 6. Smoke test: launch the frozen binary headless, wait for the "started
#    successfully" log line, then stop it. The Deno download runs on a
#    background thread, so this needs no network to pass.
./dist/yt-dlp-studio > smoke.log 2>&1 &
app_pid=$!
started=0
for _ in $(seq 1 30); do
    if grep -q "started successfully" smoke.log 2>/dev/null; then started=1; break; fi
    if ! kill -0 "${app_pid}" 2>/dev/null; then break; fi
    sleep 1
done
kill "${app_pid}" 2>/dev/null || true
wait "${app_pid}" 2>/dev/null || true
echo "----- smoke.log -----"
cat smoke.log || true
if [[ "${started}" -ne 1 ]]; then
    echo "Smoke test FAILED: app did not reach 'started successfully'." >&2
    exit 1
fi
echo "Smoke test passed: the frozen binary launched and initialized."

# 7. AppImage, .deb and .rpm, then the end-to-end package test.
version="${VERSION:-$(sed -n 's/^__version__ = "\(.*\)"$/\1/p' src/__init__.py)}"
test -n "${version}"
bash packaging/linux/build_packages.sh "${version}" dist/yt-dlp-studio dist/packages
bash scripts/test_linux_packages.sh dist/yt-dlp-studio dist/packages
