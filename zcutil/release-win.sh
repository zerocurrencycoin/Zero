#!/usr/bin/env bash
# Copyright 2026 Zero Developers
# Package the Windows cross-build into artifacts/win-zero-v<ver>.zip and update SHA256SUMS. --help for options.
set -euo pipefail
# shellcheck disable=SC2034
ME="release-win"
# shellcheck disable=SC1091
. "$(dirname "${BASH_SOURCE[0]}")/fzero.sh"
cd "$REPO_ROOT"

show_help() {
  cat <<'USAGE'
Usage: zcutil/release-win.sh [ -L | --log PATH ] [ -v X.Y.Z[-rcN] ] [ -s ] [ -b DIR ] [ --sign-pkcs12 FILE ]

Stage zerod.exe, zero-cli.exe, zero-tx.exe, and README.md from the MXE build and
write artifacts/win-zero-v<ver>.zip, then rewrite artifacts/SHA256SUMS.
Run on the Linux build host after ./zcutil/build.sh -win.

  -v X.Y.Z[-rcN]      version for the artifact name (default: configured PACKAGE_VERSION)
  -s                  skip stripping (strip uses the MXE x86_64-w64-mingw32 strip when found)
  -b DIR              directory holding the .exe files (default: src)
  --sign-pkcs12 FILE  Authenticode-sign with osslsigncode using this PKCS#12 file; password
                      from ZERO_AUTHENTICODE_PASS, timestamp server from ZERO_AUTHENTICODE_TS
                      (default http://timestamp.digicert.com)
  -L, --log PATH      capture a log
  -h, --help          this text
USAGE
}

VERSION_OVERRIDE=""
SKIP_STRIP=""
BIN_DIR="src"
PKCS12=""
parse_log_opts ".build/release-win.log" "$@"
set -- "${REMAINING_ARGS[@]+"${REMAINING_ARGS[@]}"}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) show_help; exit 0 ;;
    -s) SKIP_STRIP=1; shift ;;
    -v) VERSION_OVERRIDE="${2:?}"; shift 2 ;;
    -b) BIN_DIR="${2:?}"; shift 2 ;;
    --sign-pkcs12) PKCS12="${2:?}"; shift 2 ;;
    *) show_help >&2; exit 2 ;;
  esac
done
init_logging

VERSION="${VERSION_OVERRIDE:-$(zero_package_version)}"
[ -n "$VERSION" ] || err "no version: configure the tree (./zcutil/build.sh -win) or pass -v"
EXES=(zerod.exe zero-cli.exe zero-tx.exe)
for f in "${EXES[@]}"; do
  [ -f "$BIN_DIR/$f" ] || err "$BIN_DIR/$f not found; run ./zcutil/build.sh -win first"
done
[ -f README.md ] || err "README.md not found"
NAME="win-zero-v${VERSION}"
section "Release package ($NAME)"

STAGE="bin/$NAME"
rm -rf "$STAGE"
mkdir -p "$STAGE" artifacts
for f in "${EXES[@]}"; do cp "$BIN_DIR/$f" "$STAGE/"; done
cp README.md "$STAGE/"
if [ -z "$SKIP_STRIP" ]; then
  STRIP_BIN="$(command -v x86_64-w64-mingw32.static-strip || command -v x86_64-w64-mingw32-strip || true)"
  if [ -n "$STRIP_BIN" ]; then
    (cd "$STAGE" && "$STRIP_BIN" "${EXES[@]}")
  else
    warn "no mingw strip on PATH; binaries left unstripped"
  fi
fi
step_done "Stage binaries"

for f in "${EXES[@]}"; do
  [ "$(head -c 2 "$STAGE/$f")" = "MZ" ] || err "$f is not a Windows PE file"
done
step_done "PE check"

if [ -n "$PKCS12" ]; then
  command -v osslsigncode >/dev/null || err "osslsigncode not found"
  [ -n "${ZERO_AUTHENTICODE_PASS:-}" ] || err "set ZERO_AUTHENTICODE_PASS for --sign-pkcs12"
  TS="${ZERO_AUTHENTICODE_TS:-http://timestamp.digicert.com}"
  for f in "${EXES[@]}"; do
    osslsigncode sign -pkcs12 "$PKCS12" -pass "$ZERO_AUTHENTICODE_PASS" -n "Zero" \
      -i "https://github.com/zerocurrencycoin/Zero" -t "$TS" -in "$STAGE/$f" -out "$STAGE/$f.signed"
    mv "$STAGE/$f.signed" "$STAGE/$f"
    osslsigncode verify "$STAGE/$f" >/dev/null || err "signature check failed for $f"
  done
  step_done "Authenticode"
else
  warn "unsigned: pass --sign-pkcs12 FILE for a distributable build"
fi

ZIP="artifacts/${NAME}.zip"
rm -f "$ZIP"
(cd bin && python3 -m zipfile -c "$REPO_ROOT/$ZIP" "$NAME")
LISTING="$(python3 -m zipfile -l "$ZIP")"
for f in "${EXES[@]}" README.md; do
  grep -q "${NAME}/${f}" <<<"$LISTING" || err "zip missing $f"
done
step_done "Create zip"

"$REPO_ROOT/zcutil/checksums.sh" artifacts
notice "$ZIP"
