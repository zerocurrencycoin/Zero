#!/usr/bin/env bash
# Copyright 2026 Zero Developers
# Windows cross-compile from Linux. Output: src/zerod.exe, zero-cli.exe, zero-tx.exe
set -e -u -o pipefail
# shellcheck disable=SC2034
ME="build-win"
# shellcheck disable=SC1091
. "$(dirname "${BASH_SOURCE[0]}")/fzero.sh"
cd "$REPO_ROOT"

show_build_win_help() {
  local log="${1:-logs/build-win.log}"
  cat <<EOF
Usage: $ME [ -L | --log PATH ] [ MAKEARGS... ]
  Cross-compile zerod for Windows (x86_64) from Linux.
  Output: src/zerod.exe, src/zero-cli.exe, src/zero-tx.exe

  -h, --help      show this help and exit
  -L, --log PATH  capture build log (default: $log)

  MAKEARGS: -jN parallel jobs, capped at 4. Default: -j\$(detect_jobs).
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
  CXX=x86_64-w64-mingw32-g++-posix
  CC=x86_64-w64-mingw32-gcc-posix
  PREFIX="$PWD/depends/$HOST"
}

build_depends_win() {
  run_log make -C depends HOST="$HOST" V=1 "${MAKEARGS[@]}"
}

run_configure_win() {
  export_config_site
  run_log env CXXFLAGS="-DPTW32_STATIC_LIB -DCURVE_ALT_BN128 -fopenmp -pthread" \
    ./configure --prefix="$PREFIX" --host="$HOST" --enable-static --disable-shared --disable-zmq --disable-rust
  sed -i.bak 's/-lboost_system-mt /-lboost_system-mt-s /' configure && rm -f configure.bak
}

run_make_win() {
  cd src
  run_log env CC="$CC" CXX="$CXX" make V=1 "${MAKEARGS[@]}" zerod.exe zero-cli.exe zero-tx.exe
}

parse_build_win_args "logs/build-win.log" "$@"
resolve_host_win
trap 'build_fail "build failed"' ERR
set -x
notice "HOST=$HOST ${MAKEARGS[*]}"
[ -n "${LOG_FILE:-}" ] && notice "Log: $LOG_FILE"

section "Build depends"
build_depends_win

section "Configure"
run_autogen
run_configure_win

section "Build"
run_make_win
step_done "Build complete"
