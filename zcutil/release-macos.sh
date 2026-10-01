#!/usr/bin/env bash
# Copyright 2026 Zero Developers
# Package macOS node binaries into artifacts/macos-zero-v<ver>-<arch>.zip and update SHA256SUMS. --help for options.
set -euo pipefail
# shellcheck disable=SC2034
ME="release-macos"
# shellcheck disable=SC1091
. "$(dirname "${BASH_SOURCE[0]}")/fzero.sh"
cd "$REPO_ROOT"

show_help() {
  cat <<'USAGE'
Usage: zcutil/release-macos.sh [ -L | --log PATH ] [ -v X.Y.Z[-rcN] ] [ -s ] [ --sign IDENTITY ] [ --notarize PROFILE ]

Stage zerod, zero-cli, zero-tx, README.md, and zero-fetch-params from src/ and
write artifacts/macos-zero-v<ver>-<arch>.zip, then rewrite artifacts/SHA256SUMS.
Run on macOS after ./zcutil/build.sh.

  -v X.Y.Z[-rcN]      version for the artifact name (default: configured PACKAGE_VERSION)
  -s                  skip stripping the staged binaries
  --sign IDENTITY     codesign the binaries with this Developer ID Application identity,
                      hardened runtime and secure timestamp (env: ZERO_CODESIGN_ID)
  --notarize PROFILE  submit the zip with xcrun notarytool using this keychain profile
                      and wait for the result; requires --sign (env: ZERO_NOTARY_PROFILE)
  -L, --log PATH      capture a log
  -h, --help          this text

A zip of command-line binaries cannot be stapled; notarized binaries are checked
online by Gatekeeper on first run.
USAGE
}

VERSION_OVERRIDE=""
SKIP_STRIP=""
SIGN_ID="${ZERO_CODESIGN_ID:-}"
NOTARY_PROFILE="${ZERO_NOTARY_PROFILE:-}"
parse_log_opts ".build/release-macos.log" "$@"
set -- "${REMAINING_ARGS[@]+"${REMAINING_ARGS[@]}"}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) show_help; exit 0 ;;
    -s) SKIP_STRIP=1; shift ;;
    -v) VERSION_OVERRIDE="${2:?}"; shift 2 ;;
    --sign) SIGN_ID="${2:?}"; shift 2 ;;
    --notarize) NOTARY_PROFILE="${2:?}"; shift 2 ;;
    *) show_help >&2; exit 2 ;;
  esac
done
init_logging

[ "$(uname -s)" = "Darwin" ] || err "run on macOS"
[ -n "$NOTARY_PROFILE" ] && [ -z "$SIGN_ID" ] && err "--notarize requires --sign"
VERSION="${VERSION_OVERRIDE:-$(zero_package_version)}"
[ -n "$VERSION" ] || err "no version: configure the tree (./zcutil/build.sh) or pass -v"
for f in src/zerod src/zero-cli src/zero-tx README.md zcutil/fetch-params.sh; do
  [ -f "$f" ] || err "$f not found; run ./zcutil/build.sh first"
done
ARCH="$(lipo -archs src/zerod 2>/dev/null | tr ' ' '+')"
[ -n "$ARCH" ] || ARCH="$(uname -m)"
NAME="macos-zero-v${VERSION}-${ARCH}"
section "Release package ($NAME)"

STAGE="bin/$NAME"
rm -rf "$STAGE"
mkdir -p "$STAGE" artifacts
cp src/zerod src/zero-cli src/zero-tx README.md "$STAGE/"
cp zcutil/fetch-params.sh "$STAGE/zero-fetch-params"
chmod +x "$STAGE/zero-fetch-params"
# Strip before signing: stripping a signed binary invalidates the signature.
[ -z "$SKIP_STRIP" ] && strip -x "$STAGE/zerod" "$STAGE/zero-cli" "$STAGE/zero-tx"
step_done "Stage binaries"

# Capture output first: grep -q under pipefail can fail when the writer gets SIGPIPE.
ZEROD_VERSION="$("$STAGE/zerod" --version)"
[[ "$ZEROD_VERSION" == *"version v${VERSION}"* ]] || err "staged zerod does not report v${VERSION}"
step_done "Version check"

if [ -n "$SIGN_ID" ]; then
  for b in zerod zero-cli zero-tx; do
    codesign --force --options runtime --timestamp --sign "$SIGN_ID" "$STAGE/$b"
    codesign --verify --strict --verbose=2 "$STAGE/$b"
  done
  step_done "Codesign"
else
  warn "unsigned: pass --sign IDENTITY for a distributable build"
fi

ZIP="artifacts/${NAME}.zip"
rm -f "$ZIP"
ditto -c -k --keepParent "$STAGE" "$ZIP"
LISTING="$(unzip -l "$ZIP")"
for f in zerod zero-cli zero-tx README.md zero-fetch-params; do
  grep -q "${NAME}/${f}$" <<<"$LISTING" || err "zip missing $f"
done
step_done "Create zip"

if [ -n "$NOTARY_PROFILE" ]; then
  xcrun notarytool submit "$ZIP" --keychain-profile "$NOTARY_PROFILE" --wait
  step_done "Notarize"
fi

"$REPO_ROOT/zcutil/checksums.sh" artifacts
notice "$ZIP"
