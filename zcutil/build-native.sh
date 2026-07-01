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

  MAKEARGS: -jN optional; auto job count capped at FZERO_MAX_JOBS (see zcutil/fzero.sh, default 8; override with env)
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
  # Align with depends/Makefile: NO_PROTON=1 omits proton packages; empty includes them (same as build-win.sh when proton off).
  PROTON_CONFIGURE='--disable-proton'
  BUILD_PROTON_IN_DEPENDS=0
  DAEMON_ARG=''
  i=0
  while [[ $i -lt ${#REMAINING_ARGS[@]} ]]; do
    case "${REMAINING_ARGS[$i]}" in
      --enable-lcov)   LCOV_ARG='--enable-lcov'; HARDENING_ARG='--disable-hardening'; i=$((i+1)) ;;
      --disable-tests) TEST_ARG='--enable-tests=no'; i=$((i+1)) ;;
      --disable-mining) MINING_ARG='--enable-mining=no'; i=$((i+1)) ;;
      --enable-proton) PROTON_CONFIGURE=''; BUILD_PROTON_IN_DEPENDS=1; i=$((i+1)) ;;
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
  if [[ "$BUILD_PROTON_IN_DEPENDS" -eq 1 ]]; then
    env HOST="$HOST" BUILD="$BUILD" "$MAKE" "${MAKEARGS[@]}" -C ./depends/ V=1
  else
    env NO_PROTON=1 HOST="$HOST" BUILD="$BUILD" "$MAKE" "${MAKEARGS[@]}" -C ./depends/ V=1
  fi
}

run_configure_native() {
  export_config_site
  ./configure "$HARDENING_ARG" "$LCOV_ARG" "$TEST_ARG" "$MINING_ARG" $PROTON_CONFIGURE $DAEMON_ARG $CONFIGURE_FLAGS CXXFLAGS='-g'
}

run_make_native() {
  "$MAKE" "${MAKEARGS[@]}" V=1
}

parse_build_args "logs/build-native.log" "$@"
init_logging
resolve_host_native
trap 'build_fail "build failed"' ERR
set -x
notice "HOST=$HOST ${MAKEARGS[*]}"

section "Build depends"
build_depends_native
cleanup_secp256k1_la

section "Configure"
run_autogen
run_configure_native

section "Build"
run_make_native
step_done "Build complete"
