#!/usr/bin/env bash
# Copyright 2026 Zero Developers
# Package Zero node binaries (from src/) into artifacts: .tgz and .deb.
# Staging in bin/; bin subdirectories cleaned, artifacts left persistent.
# Assumes build already done (./zcutil/build.sh or build-native.sh).
# Usage: ./zcutil/release-linux.sh [ -L | --log PATH ] [ -v X.Y.Z ] [ -s ]
set -e -u -o pipefail
# shellcheck disable=SC2034
ME="release-linux"
# shellcheck disable=SC1091
. "$(dirname "${BASH_SOURCE[0]}")/fzero.sh"
cd "$REPO_ROOT"

show_help() {
  local log="${1:-logs/release-linux.log}"
  cat <<EOF
Usage: $ME [ -L | --log PATH ] [ -v X.Y.Z ] [ -s ]
  Package zerod, zero-cli, zero-tx and README into artifacts/linux-zero-vX.Y.Z.tgz and .deb.

  -h, --help   show this help and exit
  -L, --log    capture log (default: $log)
  -s           skip stripping binaries (default: strip copies in bin)
  -v X.Y.Z     version for artifact names (default: from src/zerod --version, semver only)
EOF
}

parse_args() {
  local default_log="${1:-logs/release-linux.log}"
  shift
  VERSION_OVERRIDE=""
  SKIP_STRIP=""
  parse_log_opts "$default_log" "$@"
  set -- "${REMAINING_ARGS[@]}"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -h|--help) show_help "$default_log"; exit 0 ;;
      -s) SKIP_STRIP=1; shift ;;
      -v) VERSION_OVERRIDE="$2"; shift 2 ;;
      *) shift ;;
    esac
  done
}

# Semver only from zerod --version (e.g. 4.0.0-4a68975fa -> 4.0.0).
get_version_from_zerod() {
  "$REPO_ROOT/src/zerod" --version 2>/dev/null | sed -n 's/.*version v\([^ ]*\).*/\1/p' | head -1 | sed 's/-.*$//'
}

parse_args "logs/release-linux.log" "$@"
init_logging

if [ -n "$VERSION_OVERRIDE" ]; then
  VERSION="$VERSION_OVERRIDE"
else
  VERSION="$(get_version_from_zerod)"
  [ -z "$VERSION" ] && err "Could not get version from src/zerod --version. Build first or pass -v X.Y.Z"
fi

[ -f "src/zerod" ]    || err "src/zerod not found. Run ./zcutil/build.sh first."
[ -f "src/zero-cli" ] || err "src/zero-cli not found. Run ./zcutil/build.sh first."
[ -f "src/zero-tx" ]  || err "src/zero-tx not found. Run ./zcutil/build.sh first."
[ -f "README.md" ]    || err "README.md not found."

section "Release package (linux-zero-v${VERSION})"

# Clean only bin staging dirs; leave artifacts persistent
rm -rf bin/zero-v"${VERSION}"
rm -rf bin/deb/zero-v"${VERSION}"

# --- Tarball: stage in bin/zero-vX.Y.Z, strip copies, roll into artifacts ---
PKGDIR="bin/zero-v${VERSION}"
mkdir -p "$PKGDIR"
cp src/zerod     "$PKGDIR/"
cp src/zero-cli  "$PKGDIR/"
cp src/zero-tx   "$PKGDIR/"
cp README.md     "$PKGDIR/"
[ -z "${SKIP_STRIP:-}" ] && strip "$PKGDIR/zerod" "$PKGDIR/zero-cli" "$PKGDIR/zero-tx" 2>/dev/null || true
step_done "Copy and strip (tarball)"

mkdir -p artifacts
(cd "bin/zero-v${VERSION}" && tar czf "$REPO_ROOT/artifacts/linux-zero-v${VERSION}.tgz" zerod zero-cli zero-tx README.md) || err "tar failed"
step_done "Create tarball"

[ ! -f "artifacts/linux-zero-v${VERSION}.tgz" ] && err "Tarball not created"
TAR_LIST="$(tar tzf "artifacts/linux-zero-v${VERSION}.tgz")"
for f in zerod zero-cli zero-tx README.md; do
  echo "$TAR_LIST" | grep -qxF "$f" || err "package missing $f"
done
step_done "Package contents"

# --- Debian: stage in bin/deb/zero-vX.Y.Z, strip copies, roll into artifacts ---
debdir="bin/deb/zero-v${VERSION}"
mkdir -p "$debdir/DEBIAN"
mkdir -p "$debdir/usr/bin"
# Minimal control for dpkg-deb (no dpkg-shlibdeps)
DEB_ARCH="$(dpkg --print-architecture 2>/dev/null)" || DEB_ARCH="amd64"
case "$(uname -m)" in
  x86_64) DEB_ARCH="amd64" ;;
  aarch64|arm64) DEB_ARCH="arm64" ;;
  *) DEB_ARCH="${DEB_ARCH:-amd64}" ;;
esac
cat > "$debdir/DEBIAN/control" <<EOF
Package: zero
Version: ${VERSION}
Architecture: ${DEB_ARCH}
Maintainer: Zero Developers
Description: Zero node daemon and CLI
 zerod, zero-cli, zero-tx and zero-fetch-params.
Depends: libc6 (>= 2.27)
EOF

cp src/zerod    "$debdir/usr/bin/"
cp src/zero-cli "$debdir/usr/bin/"
cp src/zero-tx  "$debdir/usr/bin/"
[ -f "zcutil/fetch-params.sh" ] && cp zcutil/fetch-params.sh "$debdir/usr/bin/zero-fetch-params" && chmod +x "$debdir/usr/bin/zero-fetch-params"
[ -z "${SKIP_STRIP:-}" ] && strip "$debdir/usr/bin/zerod" "$debdir/usr/bin/zero-cli" "$debdir/usr/bin/zero-tx" 2>/dev/null || true
step_done "Copy and strip (deb)"

dpkg-deb --build "$debdir" >/dev/null
mv "${debdir}.deb" "artifacts/linux-zero-v${VERSION}.deb"
step_done "Building deb"

notice "artifacts/linux-zero-v${VERSION}.tgz"
notice "artifacts/linux-zero-v${VERSION}.deb"
