# Live-datadir write guard for ZeroPerf launchers.
# Source from contrib/perf/*.sh and contrib/ops-validate.sh (after REPO_ROOT).
#
#   refuse_live_datadir LABEL PATH
#   is_default_datadir PATH   # exit 0 if any production datadir (perflib.sh)
#   is_live_datadir PATH      # exit 0 if runtime or Zero
#
# Override (can destroy the live node):
#   ZERO_PERF_ALLOW_LIVE_DATADIR=1
#
# shellcheck shell=bash

_DEBUGLOG_PY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/debuglog.py"

refuse_live_datadir() {
  local label="${1:-LAB}"
  local path="${2:?usage: refuse_live_datadir LABEL PATH}"
  # No arrays: bash 3.2 and zsh `set -u` both treat empty extra[@] as unbound.
  case "${ZERO_PERF_ALLOW_LIVE_DATADIR:-}" in
    1|true|yes|YES)
      python3 "$_DEBUGLOG_PY" --guard-write "$path" --label "$label" --allow-live-datadir
      ;;
    *)
      python3 "$_DEBUGLOG_PY" --guard-write "$path" --label "$label"
      ;;
  esac
}

# One implementation of "is this a production datadir": perflib.sh's, which
# covers every platform's datadir names (zeropaths.is_protected_datadir).
is_default_datadir() {
  if ! command -v _perflib_is_protected >/dev/null 2>&1; then
    # shellcheck source=/dev/null
    . "$(dirname "$_DEBUGLOG_PY")/perflib.sh"
  fi
  _perflib_is_protected "$1"
}

is_live_datadir() {
  python3 "$_DEBUGLOG_PY" --is-live "$1"
}
