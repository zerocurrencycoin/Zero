#!/usr/bin/env bash
# Copyright 2026 Zero Developers
# Windows cross-compile from Linux. Output: src/zerod.exe, zero-cli.exe, zero-tx.exe
# Requires MXE with x86_64-w64-mingw32.static-gcc. Set MXE_ROOT or pass -m/--mxe.
set -e -u -o pipefail

# Parse MXE path before other setup (depends and configure need it on PATH)
while [[ $# -gt 0 ]]; do
  case "$1" in
    -m|--mxe) MXE_ROOT="$2"; shift 2 ;;
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

  MAKEARGS: -jN optional, use only when overriding auto-detected number of CPU cores, capped at 4
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
  CC=$(command -v x86_64-w64-mingw32.static-gcc 2>/dev/null) || { echo "build-win: x86_64-w64-mingw32.static-gcc not found. Set MXE_ROOT (e.g. export MXE_ROOT=\$HOME/mxe)" >&2; exit 1; }
  CXX="${CC%gcc}g++"
  WINDRES=$(command -v x86_64-w64-mingw32.static-windres 2>/dev/null) || { echo "build-win: windres not found" >&2; exit 1; }
  PREFIX="$PWD/depends/$HOST"
  if [[ -z "${MAKE:-}" ]]; then MAKE=make; fi
  if [[ -z "${BUILD:-}" ]]; then BUILD="$(./depends/config.guess)"; fi
}

build_depends_win() {
  run_log env HOST="$HOST" BUILD="$BUILD" NO_PROTON=1 "$MAKE" "${MAKEARGS[@]}" -C ./depends/ V=1
}

run_configure_win() {
  export_config_site
  run_log env CXXFLAGS="-DPTW32_STATIC_LIB -DCURVE_ALT_BN128 -fopenmp -pthread" \
    ./configure --prefix="$PREFIX" --host="$HOST" --enable-static --disable-shared --disable-zmq --disable-rust
  sed -i.bak 's/-lboost_system-mt /-lboost_system-mt-s /' configure && rm -f configure.bak
}

run_make_win() {
  cd src
  run_log env CC="$CC" CXX="$CXX" WINDRES="$WINDRES" "$MAKE" V=1 "${MAKEARGS[@]}" zerod.exe zero-cli.exe zero-tx.exe
}

parse_build_win_args "logs/build-win.log" "$@"
resolve_host_win
trap 'build_fail "build failed"' ERR
set -x
notice "HOST=$HOST ${MAKEARGS[*]}"
if [ -n "${LOG_FILE:-}" ]; then notice "Log: $LOG_FILE"; fi

section "Build depends"
build_depends_win
cleanup_secp256k1_la

section "Configure"
run_autogen
run_configure_win

section "Build"
run_make_win
step_done "Build complete"
