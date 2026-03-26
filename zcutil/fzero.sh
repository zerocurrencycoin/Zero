# shellcheck shell=bash
# Copyright 2026 Zero Developers
# Shared build helpers for Zero node (build-native, build-win).
# Usage: ME="script-name"; . "$(dirname "${BASH_SOURCE[0]}")/fzero.sh"
# Provides: SCRIPT_DIR, REPO_ROOT, FZERO_MAX_JOBS, section, log_capture, analyze_build_log, build_fail,
#           run_log, parse_log_opts, detect_jobs, makeargs_from_argv, export_config_site, run_autogen, cleanup_secp256k1_la

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Max parallel jobs for depends + top-level make when -j is omitted or above this cap.
# Tune here for slow hosts (e.g. 2), or override per run: FZERO_MAX_JOBS=2 ./zcutil/build.sh
: "${FZERO_MAX_JOBS:=8}"

# shellcheck disable=SC1091
. "$SCRIPT_DIR/fmessage.sh"

section() { echo ""; notice "[$1]"; }

# Build log analysis (call when build fails and LOG_FILE is set)
analyze_build_log() {
  local f="${1:-$LOG_FILE}"
  [ -n "$f" ] && [ -f "$f" ] || return 0
  echo "" >&2
  echo "=== Build analysis (from $f) ===" >&2
  echo "--- Errors ---" >&2
  grep -iE "error:|fatal|undefined reference|cannot find|No such file" "$f" 2>/dev/null | tail -30 || echo "(none)" >&2
  echo "--- Warnings (last 15) ---" >&2
  grep -iE "warning:" "$f" 2>/dev/null | tail -15 || echo "(none)" >&2
}

# Log capture: tee to LOG_FILE or cat. Used when -L/--log passed.
log_capture() {
  if [ -n "${LOG_FILE:-}" ]; then tee -a "$LOG_FILE"; else cat; fi
}

# Run command; pipe to log_capture (tee when LOG_FILE set, else cat).
run_log() { "$@" 2>&1 | log_capture; }

# Call on build failure: analyze log if set, then err.
build_fail() {
  [ -n "${LOG_FILE:-}" ] && [ -f "$LOG_FILE" ] && analyze_build_log "$LOG_FILE"
  err "${1:-build failed}"
}

# Consume -L/--log from args. Sets LOG_FILE, REMAINING_ARGS.
# Usage: parse_log_opts "logs/build-native.log" "$@"
parse_log_opts() {
  local default_log="${1:-}"
  shift
  LOG_FILE=''
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -L) LOG_FILE="${LOG_FILE:-$REPO_ROOT/$default_log}"; shift ;;
      -L=*) LOG_FILE="${1#-L=}"; shift ;;
      --log)
        if [ -n "${2:-}" ] && [[ "$2" != -* ]]; then LOG_FILE="$2"; shift 2
        else LOG_FILE="${LOG_FILE:-$REPO_ROOT/$default_log}"; shift; fi
        ;;
      --log=*) LOG_FILE="${1#--log=}"; shift ;;
      *) break ;;
    esac
  done
  REMAINING_ARGS=("$@")
  if [ -n "$LOG_FILE" ]; then mkdir -p "$(dirname "$LOG_FILE")"; fi
}

# Optional -jN. Jobs auto-detected (nproc/gnproc/sysctl); capped at FZERO_MAX_JOBS (default 8 in this file).
detect_jobs() {
  local n=2
  if command -v nproc &>/dev/null; then
    n=$(nproc 2>/dev/null || echo 2)
  elif command -v gnproc &>/dev/null; then
    n=$(gnproc 2>/dev/null || echo 2)
  elif [[ "$(uname -s)" == "Darwin" ]] && command -v sysctl &>/dev/null; then
    n=$(sysctl -n hw.ncpu 2>/dev/null || echo 2)
  fi
  if [[ "$n" -gt "$FZERO_MAX_JOBS" ]]; then n="$FZERO_MAX_JOBS"; fi
  echo "$n"
}

makeargs_from_argv() {
  MAKEARGS=()
  HAS_JOBS=0
  for arg in "$@"; do
    if [[ "$arg" =~ ^-j([0-9]+)$ ]]; then
      n="${BASH_REMATCH[1]}"
      if [[ "$n" -gt "$FZERO_MAX_JOBS" ]]; then n="$FZERO_MAX_JOBS"; fi
      MAKEARGS+=("-j$n")
      HAS_JOBS=1
    else
      MAKEARGS+=("$arg")
    fi
  done
  if [[ $HAS_JOBS -eq 0 ]]; then
    MAKEARGS=("-j$(detect_jobs)" "${MAKEARGS[@]}")
  fi
}

# Shared: set CONFIG_SITE for configure. Call from repo root.
export_config_site() { export CONFIG_SITE="$PWD/depends/$HOST/share/config.site"; }

# Run autogen. Call from repo root.
run_autogen() {
  ./autogen.sh
}

# Remove stale secp256k1 .la when HOST changed (e.g. native vs cross). Call from repo root.
cleanup_secp256k1_la() {
  if [[ -f src/secp256k1/libsecp256k1.la ]] && [[ -d "depends/$HOST" ]]; then
    local la_host
    la_host=$(grep 'dependency_libs' src/secp256k1/libsecp256k1.la 2>/dev/null | sed -n 's|.*depends/\([^/]*\)/.*|\1|p')
    if [[ -n "$la_host" ]] && [[ "$la_host" != "$HOST" ]]; then
      rm -f src/secp256k1/libsecp256k1.la src/secp256k1/config.status
    fi
  fi
}
