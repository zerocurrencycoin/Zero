#!/usr/bin/env bash
# Copyright 2026 Zero Developers
# Native build for Linux/macOS. Output: zerod, zero-cli, zero-tx
set -e -u -o pipefail
# shellcheck disable=SC2034
ME="build-native"
# shellcheck disable=SC1091
. "$(dirname "${BASH_SOURCE[0]}")/fzero.sh"
cd "$REPO_ROOT"

parse_build_args "logs/build-native.log" "$@"
resolve_host_native
trap 'build_fail "build failed"' ERR
set -x
notice "HOST=$HOST ${MAKEARGS[*]}"
[ -n "${LOG_FILE:-}" ] && notice "Log: $LOG_FILE"

section "Build depends"
build_depends_native

# Remove stale secp256k1 .la when host changed (native only).
cleanup_secp256k1_la() {
  if [[ -f src/secp256k1/libsecp256k1.la ]] && [[ -d "depends/$HOST" ]]; then
    local la_host
    la_host=$(grep 'dependency_libs' src/secp256k1/libsecp256k1.la 2>/dev/null | sed -n 's|.*depends/\([^/]*\)/.*|\1|p')
    if [[ -n "$la_host" ]] && [[ "$la_host" != "$HOST" ]]; then
      rm -f src/secp256k1/libsecp256k1.la src/secp256k1/config.status
    fi
  fi
}
cleanup_secp256k1_la

section "Configure"
run_autogen
run_configure_native

section "Build"
run_make_native
step_done "Build complete"
