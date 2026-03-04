#!/usr/bin/env bash
# Copyright 2026 Zero Developers
# Native build for Linux/macOS. Output: zerod, zero-cli, zero-tx
set -e -u -o pipefail
# shellcheck disable=SC2034
ME="build-native"
# shellcheck disable=SC1091
. "$(dirname "${BASH_SOURCE[0]}")/fzero.sh"
cd "$REPO_ROOT"

show_build_help() {
  local log="${1:-logs/build-native.log}"
  cat <<EOF
Usage: $ME [ -L | --log PATH ] [ --enable-lcov | --disable-tests ] [ --disable-mining ] [ --enable-proton ] [ --daemon ] [ MAKEARGS... ]
  Build Zero and its dependencies from source.
  Output: zerod, zero-cli, zero-tx

  -h, --help      show this help and exit
  -L, --log PATH  capture build log (default: $log)
  --daemon        daemon/cli only, no zmq/rust (default: off)
  --enable-lcov   coverage instrumentation (default: off)
  --disable-tests omit test binaries (default: tests built)
  --disable-mining omit mining code (default: mining built)
  --enable-proton Apache Qpid Proton AMQP (default: off)

  MAKEARGS: -jN parallel jobs, capped at 4. Default: -j\$(detect_jobs).
EOF
}

# shellcheck disable=SC2034
parse_build_args() {
  local default_log="${1:-logs/build-native.log}"
  shift
  parse_log_opts "$default_log" "$@"
  if [[ ${#REMAINING_ARGS[@]} -gt 0 ]] && { [[ "x${REMAINING_ARGS[0]}" == "x--help" ]] || [[ "x${REMAINING_ARGS[0]}" == "x-h" ]]; }; then
    show_build_help "$default_log"
    exit 0
  fi
  LCOV_ARG=''
  HARDENING_ARG='--enable-hardening'
  TEST_ARG=''
  MINING_ARG=''
  PROTON_ARG='--enable-proton=no'
  DAEMON_ARG=''
  i=0
  while [[ $i -lt ${#REMAINING_ARGS[@]} ]]; do
    case "${REMAINING_ARGS[$i]}" in
      --enable-lcov)   LCOV_ARG='--enable-lcov'; HARDENING_ARG='--disable-hardening'; i=$((i+1)) ;;
      --disable-tests) TEST_ARG='--enable-tests=no'; i=$((i+1)) ;;
      --disable-mining) MINING_ARG='--enable-mining=no'; i=$((i+1)) ;;
      --enable-proton) PROTON_ARG=''; i=$((i+1)) ;;
      --daemon)        DAEMON_ARG='--disable-zmq --disable-rust'; i=$((i+1)) ;;
      *) break ;;
    esac
  done
  makeargs_from_argv "${REMAINING_ARGS[@]:$i}"
}

resolve_host_native() {
  if [[ -z "${CC:-}" ]]; then CC=gcc; fi
  if [[ -z "${CXX:-}" ]]; then CXX=g++; fi
  export CC CXX
  if [[ -z "${MAKE:-}" ]]; then MAKE=make; fi
  if [[ -z "${BUILD:-}" ]]; then BUILD="$(./depends/config.guess)"; fi
  if [[ -z "${HOST:-}" ]]; then HOST="$BUILD"; fi
  if [[ -z "${CONFIGURE_FLAGS:-}" ]]; then CONFIGURE_FLAGS=""; fi
  if [[ "$(uname -s)" == "Darwin" ]]; then export MACOSX_DEPLOYMENT_TARGET="${MACOSX_DEPLOYMENT_TARGET:-15.0}"; fi
}

build_depends_native() {
  eval "$MAKE" --version
  as --version
  ld -v
  run_log env HOST="$HOST" BUILD="$BUILD" NO_PROTON="$PROTON_ARG" "$MAKE" "${MAKEARGS[@]}" -C ./depends/ V=1
}

run_configure_native() {
  export_config_site
  run_log ./configure "$HARDENING_ARG" "$LCOV_ARG" "$TEST_ARG" "$MINING_ARG" $PROTON_ARG $DAEMON_ARG $CONFIGURE_FLAGS CXXFLAGS='-g'
}

run_make_native() {
  run_log "$MAKE" "${MAKEARGS[@]}" V=1
}

cleanup_secp256k1_la() {
  if [[ -f src/secp256k1/libsecp256k1.la ]] && [[ -d "depends/$HOST" ]]; then
    local la_host
    la_host=$(grep 'dependency_libs' src/secp256k1/libsecp256k1.la 2>/dev/null | sed -n 's|.*depends/\([^/]*\)/.*|\1|p')
    if [[ -n "$la_host" ]] && [[ "$la_host" != "$HOST" ]]; then
      rm -f src/secp256k1/libsecp256k1.la src/secp256k1/config.status
    fi
  fi
}

parse_build_args "logs/build-native.log" "$@"
resolve_host_native
trap 'build_fail "build failed"' ERR
set -x
notice "HOST=$HOST ${MAKEARGS[*]}"
[ -n "${LOG_FILE:-}" ] && notice "Log: $LOG_FILE"

section "Build depends"
build_depends_native
cleanup_secp256k1_la

section "Configure"
run_autogen
run_configure_native

section "Build"
run_make_native
step_done "Build complete"
