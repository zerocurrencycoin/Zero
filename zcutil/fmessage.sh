# shellcheck shell=bash
# Copyright 2026 Zero Developers
# Messaging helpers for scripts. Source from fzero.sh or standalone.
# Provides: err, warn, info, notice, step_done
# Usage: ME="script-name"; . "$(dirname "${BASH_SOURCE[0]}")/fmessage.sh"

err()   { echo "${ME:-script}: ERROR: $*" >&2; exit 1; }
warn()  { echo "${ME:-script}: WARN: $*" >&2; }
info()  { echo "${ME:-script}: $*"; }
notice() { echo "${ME:-script}: $*"; }
step_done() { printf "%s: %-24s [OK]\n" "${ME:-script}" "$1"; }
