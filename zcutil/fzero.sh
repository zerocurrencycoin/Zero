# shellcheck shell=bash
# Copyright 2026 Zero Developers
# Shared helpers for Zero node scripts (build-native, build-win, check-setup, check-release).
# Usage: ME="script-name"; . "$(dirname "${BASH_SOURCE[0]}")/fzero.sh"
# Provides: SCRIPT_DIR, REPO_ROOT (via resolve_zero_repo), ZERO_BUILD_DIR, FZERO_MAX_JOBS,
#           section, init_logging, prune_logs, analyze_build_log, build_fail, parse_log_opts,
#           detect_jobs, makeargs_from_argv, guess_build_host, export_config_site, run_autogen,
#           cleanup_secp256k1_la, depends_config_site, zero_params_dir, python3_ok, find_python3,
#           find_native_cxx, find_mingw_cxx, run_check_setup, receipt_init, receipt_log,
#           receipt_pass, receipt_fail, receipt_warn

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Prefer git toplevel of cwd, then cwd if it looks like Zero, then this zcutil's parent.
# build.sh still uses this so `cd src && ../zcutil/build.sh` hits the repo root.
resolve_zero_repo() {
  local git_root="" cwd
  cwd="$(pwd -P)"
  git_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
  if [[ -n "$git_root" && -f "$git_root/zcutil/build.sh" ]]; then
    REPO_ROOT="$(cd "$git_root" && pwd)"
    return
  fi
  if [[ -f "$cwd/zcutil/build.sh" ]]; then
    REPO_ROOT="$cwd"
    return
  fi
  REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
}
resolve_zero_repo
: "${ZERO_BUILD_DIR:=$REPO_ROOT/.build}"
: "${ZERO_OSX_MIN:=15.0}"

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

# Start logging: tee all output to LOG_FILE. Default is a fresh timestamped file so prior
# runs are preserved; -L / --log overrides the path. Call once, right after parse.
#
# Log retention: .build/ is gitignored and not pruned. Once a build flow is reliable, keep
# only the newest N per script instead of accumulating (a depends build log is large):
#     ls -tp .build/<ME>-*.log | tail -n +6 | xargs -r rm --   # keep newest 5
# Or set ZERO_LOG_KEEP=N and call prune_logs after init_logging (see below). Default: no prune.
# Older runs may still live under gitignored logs/.
init_logging() {
  LOG_FILE="${LOG_FILE:-$REPO_ROOT/.build/${ME}-$(date +%Y%m%d-%H%M%S).log}"
  mkdir -p "$(dirname "$LOG_FILE")"
  exec > >(tee -a "$LOG_FILE") 2>&1
  notice "Log: $LOG_FILE"
  # Must not be the trailing statement: a false test returns 1 and, as the last command,
  # would make init_logging return 1 and abort the caller under set -e.
  if [ -n "${ZERO_LOG_KEEP:-}" ]; then prune_logs "${ZERO_LOG_KEEP}"; fi
}

# Keep only the newest N logs for this script (ME); opt-in via ZERO_LOG_KEEP or explicit call.
# Solves "huge accumulating logs once the build is reliable" without deleting a run mid-flight.
prune_logs() {
  local keep="${1:-5}" dir
  dir="$(dirname "${LOG_FILE:-$REPO_ROOT/.build/x}")"
  ls -tp "$dir/${ME}-"*.log 2>/dev/null | tail -n +"$((keep + 1))" | xargs -r rm -- 2>/dev/null || true
}

# init_logging tees the whole script (stdout+stderr) to LOG_FILE, so build commands are
# run directly — no per-command pipe. (A pipe here would double-log and reintroduce a
# pipefail-in-critical-path.) Failures are caught by the ERR trap in the entry scripts.

# Call on build failure: analyze log if set, then err.
build_fail() {
  [ -n "${LOG_FILE:-}" ] && [ -f "$LOG_FILE" ] && analyze_build_log "$LOG_FILE"
  err "${1:-build failed}"
}

# Consume -L/--log from args. Sets LOG_FILE, REMAINING_ARGS.
# Usage: parse_log_opts ".build/build-native.log" "$@"
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
  # Log dir is created by init_logging (called after parse); no mkdir here.
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

# Build MAKEARGS from argv. An explicit -jN is honored as-is (the user asked for it);
# the FZERO_MAX_JOBS cap applies only to the auto-detected default when -j is omitted.
makeargs_from_argv() {
  MAKEARGS=()
  HAS_JOBS=0
  for arg in "$@"; do
    if [[ "$arg" =~ ^-j([0-9]+)$ ]]; then
      MAKEARGS+=("$arg")   # explicit -jN honored (e.g. -j16 on a big host)
      HAS_JOBS=1
    else
      MAKEARGS+=("$arg")
    fi
  done
  if [[ $HAS_JOBS -eq 0 ]]; then
    MAKEARGS=("-j$(detect_jobs)" "${MAKEARGS[@]}")
  fi
}

# HOST/BUILD from depends/config.guess. Does not override a HOST already set (e.g. mingw).
guess_build_host() {
  if [[ -z "${BUILD:-}" ]]; then
    if [[ -x "$REPO_ROOT/depends/config.guess" ]]; then
      BUILD="$("$REPO_ROOT/depends/config.guess" 2>/dev/null || true)"
    elif [[ -x ./depends/config.guess ]]; then
      BUILD="$(./depends/config.guess 2>/dev/null || true)"
    fi
  fi
  if [[ -z "${HOST:-}" ]]; then
    HOST="${BUILD:-}"
  fi
}

depends_config_site() {
  guess_build_host
  printf '%s\n' "$REPO_ROOT/depends/${HOST}/share/config.site"
}

# Shared: set CONFIG_SITE for configure.
export_config_site() {
  guess_build_host
  CONFIG_SITE="$(depends_config_site)"
  export CONFIG_SITE
}

zero_params_dir() {
  case "$(uname -s)" in
    Darwin) printf '%s\n' "$HOME/Library/Application Support/ZcashParams" ;;
    *) printf '%s\n' "$HOME/.zcash-params" ;;
  esac
}

python3_ok() {
  local py
  py="$(find_python3 2>/dev/null)" || return 1
  "$py" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'
}

python3_version() {
  local py
  py="$(find_python3)" || return 1
  "$py" -c 'import sys; print(sys.version.split()[0])'
}

# Interpreter for 3.10+. Honors PYTHON if it meets the floor.
find_python3() {
  if [[ -n "${PYTHON:-}" ]]; then
    if "$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
      printf '%s\n' "$PYTHON"
      return 0
    fi
    return 1
  fi
  if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    printf '%s\n' python3
    return 0
  fi
  if command -v python >/dev/null 2>&1 && python -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    printf '%s\n' python
    return 0
  fi
  return 1
}

ensure_darwin_deployment_target() {
  if [[ "$(uname -s)" == "Darwin" ]]; then
    export MACOSX_DEPLOYMENT_TARGET="${MACOSX_DEPLOYMENT_TARGET:-$ZERO_OSX_MIN}"
  fi
}

run_check_setup() {
  "$SCRIPT_DIR/check-setup.sh" "$@"
}

find_native_cxx() {
  local c
  if [[ -n "${CXX:-}" ]] && command -v "$CXX" >/dev/null 2>&1; then
    command -v "$CXX"
    return 0
  fi
  for c in g++ clang++ c++; do
    if command -v "$c" >/dev/null 2>&1; then
      command -v "$c"
      return 0
    fi
  done
  return 1
}

find_mingw_cxx() {
  if command -v x86_64-w64-mingw32.static-g++ >/dev/null 2>&1; then
    command -v x86_64-w64-mingw32.static-g++
    return 0
  fi
  if command -v x86_64-w64-mingw32-g++ >/dev/null 2>&1; then
    command -v x86_64-w64-mingw32-g++
    return 0
  fi
  return 1
}

# Compact-check receipts under ZERO_BUILD_DIR. Do not use init_logging here (it tees all stdout).
CHECK_FAIL=0
RECEIPT_VERBOSE=0
RECEIPT_OUT=""
RECEIPT_LATEST=""
RECEIPT=""
RECEIPT_UTC=""

receipt_init() {
  local stem="${1:?}"
  mkdir -p "$ZERO_BUILD_DIR"
  RECEIPT_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  RECEIPT_OUT="$ZERO_BUILD_DIR/${stem}-$(date -u +%Y%m%dT%H%M%SZ).txt"
  RECEIPT_LATEST="$ZERO_BUILD_DIR/${stem}-latest.txt"
  : >"$RECEIPT_OUT"
}

receipt_cap() {
  if [[ "${RECEIPT_VERBOSE:-0}" -eq 1 ]]; then
    tee -a "$RECEIPT_OUT"
  else
    cat >> "$RECEIPT_OUT"
  fi
}

receipt_log() { printf '%s\n' "$*" | receipt_cap; }
receipt_pass() { receipt_log "PASS: $*"; }
receipt_fail() { receipt_log "FAIL: $*"; CHECK_FAIL=1; }
receipt_warn() { receipt_log "WARN: $*"; }

receipt_commit() {
  if [[ "${NO_WRITE:-0}" -eq 1 ]]; then
    rm -f "$RECEIPT_OUT"
    RECEIPT="(not written)"
  else
    cp "$RECEIPT_OUT" "$RECEIPT_LATEST"
    RECEIPT="$RECEIPT_LATEST"
  fi
}

# Run autogen. Call from repo root.
run_autogen() {
  ./autogen.sh
}

# Remove stale secp256k1 .la when HOST changed (e.g. native vs cross). Call from repo root.
cleanup_secp256k1_la() {
  guess_build_host
  if [[ -f "$REPO_ROOT/src/secp256k1/libsecp256k1.la" ]] && [[ -d "$REPO_ROOT/depends/$HOST" ]]; then
    local la_host
    la_host=$(grep 'dependency_libs' "$REPO_ROOT/src/secp256k1/libsecp256k1.la" 2>/dev/null | sed -n 's|.*depends/\([^/]*\)/.*|\1|p')
    if [[ -n "$la_host" ]] && [[ "$la_host" != "$HOST" ]]; then
      rm -f "$REPO_ROOT/src/secp256k1/libsecp256k1.la" "$REPO_ROOT/src/secp256k1/config.status"
    fi
  fi
}
