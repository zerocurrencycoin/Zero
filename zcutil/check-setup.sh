#!/usr/bin/env bash
# Machine setup receipt: toolchain + Sapling params. Not git identity and not a compile.
# Other scripts call this (or run_check_setup) instead of repeating probes.
#   zcutil/check-setup.sh
#   zcutil/check-setup.sh --win
#   zcutil/check-setup.sh --levels=toolchain
set -euo pipefail
ME="check-setup"
# shellcheck disable=SC1091
. "$(dirname "${BASH_SOURCE[0]}")/fzero.sh"
cd "$REPO_ROOT"

LEVELS="toolchain,params"
CHECK_WIN=0
NO_WRITE=0
STEP_OS=""
STEP_TOOL=""
STEP_PARAMS=""

usage() {
  cat <<'EOF'
Usage: zcutil/check-setup.sh [options]

Stdout is READY or NOT READY plus one line per step. Full log: -v or .build/setup-latest.txt
Machine/setup check. Product/tree identity: zcutil/check-release.sh

  --levels=LIST      toolchain,params  (default: both)
  --win              MXE mingw g++ on PATH (Linux host)
  -v, --verbose      print the full receipt
  --no-write         do not write .build/setup-*.txt
  -h, --help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --levels=*) LEVELS="${1#--levels=}"; shift ;;
    --win) CHECK_WIN=1; shift ;;
    -v|--verbose) RECEIPT_VERBOSE=1; shift ;;
    --write) NO_WRITE=0; shift ;;
    --no-write) NO_WRITE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

has_level() { [[ ",$LEVELS," == *",$1,"* ]]; }

guess_build_host
ensure_darwin_deployment_target
OS="$(uname -s)"
ARCH="$(uname -m)"
MAKE_BIN="${MAKE:-make}"

receipt_init setup
receipt_log "=== setup $RECEIPT_UTC ==="
receipt_log "repo $REPO_ROOT"
receipt_log "cwd $(pwd)"
receipt_log "levels $LEVELS"
receipt_log "os $OS arch $ARCH"
receipt_log "HOST ${HOST:-unset} BUILD ${BUILD:-unset}"
receipt_log "FZERO_MAX_JOBS $FZERO_MAX_JOBS detect_jobs $(detect_jobs)"
STEP_OS="$OS $ARCH  HOST ${HOST:-unset}"

if has_level toolchain; then
  receipt_log "--- toolchain ---"
  TOOL_OK=1
  PY_VER=""
  PY_BIN=""
  CXX_BIN=""
  if [[ "$CHECK_WIN" -eq 1 ]]; then
    receipt_log "build.sh dispatcher: Linux -> build-win.sh (--win)"
  else
    receipt_log "build.sh dispatcher: $OS -> build-native.sh"
  fi
  if PY_BIN="$(find_python3)"; then
    PY_VER="$(python3_version)"
    receipt_pass "python $PY_VER (>= 3.10) ($PY_BIN)"
  else
    receipt_fail "Python 3.10+ required"
    TOOL_OK=0
  fi
  if command -v "$MAKE_BIN" >/dev/null 2>&1; then
    receipt_pass "make $($MAKE_BIN --version 2>/dev/null | head -1)"
  else
    receipt_fail "make not found (MAKE=$MAKE_BIN)"
    TOOL_OK=0
  fi
  if [[ "$CHECK_WIN" -eq 1 ]]; then
    if [[ "$OS" != "Linux" ]]; then
      receipt_fail "--win toolchain check is Linux-only (build.sh -win)"
      TOOL_OK=0
    fi
    MXE_ROOT="${MXE_ROOT:-$HOME/mxe}"
    receipt_log "MXE_ROOT $MXE_ROOT"
    if CXX_BIN="$(find_mingw_cxx)"; then
      receipt_pass "mingw CXX $CXX_BIN"
    else
      receipt_fail "MXE mingw g++ not on PATH (build.sh -win / MXE_ROOT)"
      TOOL_OK=0
    fi
  else
    case "$OS" in
      Darwin)
        receipt_log "MACOSX_DEPLOYMENT_TARGET=${MACOSX_DEPLOYMENT_TARGET}"
        if CXX_BIN="$(find_native_cxx)"; then
          receipt_pass "cxx $CXX_BIN"
        else
          receipt_fail "no C++ compiler (g++/clang++)"
          TOOL_OK=0
        fi
        ;;
      Linux)
        if CXX_BIN="$(find_native_cxx)"; then
          receipt_pass "cxx $CXX_BIN"
        else
          receipt_fail "no g++/c++"
          TOOL_OK=0
        fi
        ;;
      *)
        receipt_fail "unsupported uname $OS (build.sh: Linux or Darwin; -win from Linux)"
        TOOL_OK=0
        ;;
    esac
  fi
  if [[ "$TOOL_OK" -eq 1 ]]; then
    STEP_TOOL="PASS  python ${PY_VER:-?}  ${CXX_BIN:-cxx}  jobs $(detect_jobs)"
  else
    STEP_TOOL="FAIL  python ${PY_VER:-missing}  ${CXX_BIN:-no cxx}"
  fi
fi

if has_level params; then
  receipt_log "--- params ---"
  PDIR="$(zero_params_dir)"
  receipt_log "params_dir $PDIR"
  MISSING=""
  for f in sapling-spend.params sapling-output.params sprout-groth16.params; do
    if [[ -f "$PDIR/$f" ]]; then
      receipt_pass "$f"
    else
      receipt_fail "missing $f (zcutil/fetch-params.sh)"
      MISSING="$MISSING $f"
    fi
  done
  if [[ -z "$MISSING" ]]; then
    STEP_PARAMS="PASS  $PDIR"
  else
    STEP_PARAMS="FAIL  missing$MISSING"
  fi
fi

if [[ "$CHECK_FAIL" -eq 0 ]]; then
  receipt_log "READY exit=0"
else
  receipt_log "NOT READY exit=1"
fi
receipt_commit

if [[ "$CHECK_FAIL" -eq 0 ]]; then
  echo "READY"
else
  echo "NOT READY"
fi
echo "os         $STEP_OS"
[[ -n "$STEP_TOOL" ]] && echo "toolchain  $STEP_TOOL"
[[ -n "$STEP_PARAMS" ]] && echo "params     $STEP_PARAMS"
echo "receipt    $RECEIPT"

exit "$CHECK_FAIL"
