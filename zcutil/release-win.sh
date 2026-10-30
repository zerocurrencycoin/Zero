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
Usage: zcutil/release-win.sh [ -L | --log PATH ] [ -v X.Y.Z[-rcN] ] [ -s ] [ -b DIR ] [ --sign-pkcs12 FILE ] [ --no-smoke ]

Stage zerod.exe, zero-cli.exe, zero-tx.exe, and README.md from the MXE build and
write artifacts/win-zero-v<ver>.zip, start the zipped binaries once under wine,
then rewrite artifacts/SHA256SUMS.
Run on the Linux build host after ./zcutil/build.sh -win.

Smoke check: in a temporary WINEPREFIX and datadir, zerod.exe -version must report
v<ver>, zerod.exe -regtest must log "Done loading", zero-cli.exe getblockchaininfo
must answer regtest, and stop must end with "Shutdown: done". Needs wine and the
proving parameters in ~/.zcash-params. --no-smoke skips it; then start zerod.exe
from the zip on Windows instead.

  -v X.Y.Z[-rcN]      version for the artifact name (default: configured PACKAGE_VERSION)
  -s                  skip stripping (strip uses the MXE x86_64-w64-mingw32 strip when found)
  --no-smoke          skip the wine smoke check
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
NO_SMOKE=""
parse_log_opts ".build/release-win.log" "$@"
set -- "${REMAINING_ARGS[@]+"${REMAINING_ARGS[@]}"}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) show_help; exit 0 ;;
    -s) SKIP_STRIP=1; shift ;;
    -v) VERSION_OVERRIDE="${2:?}"; shift 2 ;;
    -b) BIN_DIR="${2:?}"; shift 2 ;;
    --sign-pkcs12) PKCS12="${2:?}"; shift 2 ;;
    --no-smoke) NO_SMOKE=1; shift ;;
    *) show_help >&2; exit 2 ;;
  esac
done
init_logging
# The MXE tree build-win.sh uses comes first, so strip matches the compiler.
export PATH="${MXE_ROOT:-$HOME/mxe}/usr/bin:$PATH"
if [ -z "$NO_SMOKE" ] && ! command -v wine >/dev/null; then
  err "wine not found: install wine, or pass --no-smoke and start zerod.exe on Windows"
fi

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

# --- Smoke check under wine; everything wine needs stays in this block ---
free_port() { python3 -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])'; }
smoke_fail() {
  [ -f "$SMOKE_DIR/data/regtest/debug.log" ] && tail -20 "$SMOKE_DIR/data/regtest/debug.log" >&2
  [ -n "${ZPID:-}" ] && kill "$ZPID" 2>/dev/null
  wineserver -k 2>/dev/null || true
  err "smoke: $1 (files kept in $SMOKE_DIR)"
}
if [ -n "$NO_SMOKE" ]; then
  printf '%s: %-24s [SKIP]\n' "$ME" "Smoke (wine)"
  notice "start zerod.exe from $ZIP on Windows before release"
else
  SMOKE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/zero-smoke.XXXXXX")"
  export WINEPREFIX="$SMOKE_DIR/prefix" WINEDEBUG=-all
  wineboot -i >/dev/null 2>&1 || smoke_fail "wineboot failed"
  ROAMING="$WINEPREFIX/drive_c/users/${USER:-$(id -un)}/AppData/Roaming"
  mkdir -p "$ROAMING" "$SMOKE_DIR/data"
  ln -s "$(zero_params_dir)" "$ROAMING/ZcashParams"
  (cd "$SMOKE_DIR" && python3 -m zipfile -e "$REPO_ROOT/$ZIP" .)
  : > "$SMOKE_DIR/data/zero.conf"
  WDIR="$SMOKE_DIR/$NAME"
  DATADIR_W="$(winepath -w "$SMOKE_DIR/data" 2>/dev/null)"
  RPCPORT="$(free_port)"
  P2PPORT="$(free_port)"
  CLI=(wine "$WDIR/zero-cli.exe" -regtest "-datadir=$DATADIR_W" "-rpcport=$RPCPORT")

  ZVER="$(wine "$WDIR/zerod.exe" -version 2>/dev/null | head -1 | tr -d '\r' || true)"
  [[ "$ZVER" == *" v${VERSION}" ]] || smoke_fail "zerod.exe -version: '$ZVER', want v$VERSION"
  wine "$WDIR/zerod.exe" -regtest "-datadir=$DATADIR_W" "-rpcport=$RPCPORT" "-port=$P2PPORT" \
    > "$SMOKE_DIR/zerod.out" 2>&1 &
  ZPID=$!
  for _ in $(seq 180); do
    grep -q "Done loading" "$SMOKE_DIR/data/regtest/debug.log" 2>/dev/null && break
    kill -0 "$ZPID" 2>/dev/null || smoke_fail "zerod.exe exited during startup"
    sleep 1
  done
  grep -q "Done loading" "$SMOKE_DIR/data/regtest/debug.log" || smoke_fail "no 'Done loading' within 180 s"
  CHAININFO="$("${CLI[@]}" getblockchaininfo 2>/dev/null || true)"
  grep -q '"chain": "regtest"' <<<"$CHAININFO" || smoke_fail "getblockchaininfo did not answer regtest"
  "${CLI[@]}" stop >/dev/null 2>&1 || smoke_fail "stop failed"
  for _ in $(seq 60); do
    kill -0 "$ZPID" 2>/dev/null || break
    sleep 1
  done
  kill -0 "$ZPID" 2>/dev/null && smoke_fail "zerod.exe still running 60 s after stop"
  ZPID=""
  grep -q "Shutdown: done" "$SMOKE_DIR/data/regtest/debug.log" || smoke_fail "no 'Shutdown: done'"
  wineserver -k 2>/dev/null || true
  rm -rf "$SMOKE_DIR"
  step_done "Smoke (wine)"
fi

"$REPO_ROOT/zcutil/checksums.sh" artifacts
notice "$ZIP"
