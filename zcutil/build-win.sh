#!/usr/bin/env bash
# Copyright 2026 Zero Developers
# Windows cross-compile from Linux. Output: src/zerod.exe, zero-cli.exe, zero-tx.exe
# Requires MXE with x86_64-w64-mingw32.static-gcc. Set MXE_ROOT or pass -m/--mxe.
set -e -u -o pipefail

# MXE path must be on PATH before sourcing fzero.sh (depends/configure resolve the cross gcc
# via command -v), so -m/--mxe is parsed here, ahead of the main arg parse. Env MXE_ROOT wins.
while [[ $# -gt 0 ]]; do
  case "$1" in
    -m|--mxe) MXE_ROOT="${MXE_ROOT:-$2}"; shift 2 ;;
    -m=*|--mxe=*) MXE_ROOT="${MXE_ROOT:-${1#*=}}"; shift ;;
    *) break ;;
  esac
done
MXE_ROOT="${MXE_ROOT:-$HOME/mxe}"
MXE_PATH="${MXE_ROOT}/usr/bin"
export PATH="$MXE_PATH:$PATH"

# shellcheck disable=SC2034
ME="build-win"
# shellcheck disable=SC1091
. "$(dirname "${BASH_SOURCE[0]}")/fzero.sh"
cd "$REPO_ROOT"

show_build_win_help() {
  local log="${1:-logs/build-win.log}"
  cat <<EOF
Usage: $ME [ -m/--mxe PATH ] [ -L | --log PATH ] [ MAKEARGS... ]
  Cross-compile zerod for Windows (x86_64) from Linux.
  Output: src/zerod.exe, src/zero-cli.exe, src/zero-tx.exe

  -h, --help      show this help and exit
  -m, --mxe PATH  MXE root (default: $HOME/mxe)
  -L, --log PATH  capture build log (default: $log)

  MAKEARGS: -jN optional; auto job count capped at FZERO_MAX_JOBS (see zcutil/fzero.sh)
EOF
}

# shellcheck disable=SC2034
parse_build_win_args() {
  local default_log="${1:-logs/build-win.log}"
  shift
  parse_log_opts "$default_log" "$@"
  if [[ ${#REMAINING_ARGS[@]} -gt 0 ]] && { [[ "x${REMAINING_ARGS[0]}" == "x--help" ]] || [[ "x${REMAINING_ARGS[0]}" == "x-h" ]]; }; then
    show_build_win_help "$default_log"
    exit 0
  fi
  makeargs_from_argv "${REMAINING_ARGS[@]}"
}

resolve_host_win() {
  HOST=x86_64-w64-mingw32
  CC=$(command -v x86_64-w64-mingw32.static-gcc 2>/dev/null) || err "x86_64-w64-mingw32.static-gcc not found. Set MXE_ROOT (e.g. export MXE_ROOT=\$HOME/mxe) or pass -m/--mxe."
  CXX="${CC%gcc}g++"
  WINDRES=$(command -v x86_64-w64-mingw32.static-windres 2>/dev/null) || err "x86_64-w64-mingw32.static-windres not found (MXE incomplete?)."
  PREFIX="$PWD/depends/$HOST"
  if [[ -z "${MAKE:-}" ]]; then MAKE=make; fi
  if [[ -z "${BUILD:-}" ]]; then BUILD="$(./depends/config.guess)"; fi
}

build_depends_win() {
  # Proton off: NO_PROTON=1 matches depends/Makefile (same convention as build-native.sh without --enable-proton).
  env NO_PROTON=1 HOST="$HOST" BUILD="$BUILD" "$MAKE" "${MAKEARGS[@]}" -C ./depends/ V=1
}

run_configure_win() {
  export_config_site
  env CXXFLAGS="-DPTW32_STATIC_LIB -DCURVE_ALT_BN128 -fopenmp -pthread" \
    ./configure --prefix="$PREFIX" --host="$HOST" --enable-static --disable-shared --disable-zmq --disable-rust --disable-proton
  # Portable in-place edit: GNU sed wants -i or -i''; BSD sed requires a backup suffix. -i.bak works on both; then drop .bak.
  sed -i.bak 's/-lboost_system-mt /-lboost_system-mt-s /' configure && rm -f configure.bak
}

run_make_win() {
  cd src
  env CC="$CC" CXX="$CXX" WINDRES="$WINDRES" "$MAKE" V=1 "${MAKEARGS[@]}" zerod.exe zero-cli.exe zero-tx.exe
}

parse_build_win_args "logs/build-win.log" "$@"
init_logging
resolve_host_win
trap 'build_fail "build failed"' ERR
set -x
notice "HOST=$HOST ${MAKEARGS[*]}"

section "Build depends"
build_depends_win
cleanup_secp256k1_la

section "Configure"
run_autogen
run_configure_win

section "Build"
run_make_win
step_done "Build complete"
