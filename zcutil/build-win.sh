#!/usr/bin/env bash
# Copyright 2026 Zero Developers
# Windows cross-compile from Linux. Output: src/zerod.exe, zero-cli.exe, zero-tx.exe
set -e -u -o pipefail
# shellcheck disable=SC2034
ME="build-win"
# shellcheck disable=SC1091
. "$(dirname "${BASH_SOURCE[0]}")/fzero.sh"
cd "$REPO_ROOT"

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
