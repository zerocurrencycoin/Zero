# Shared helpers for ZeroPerf launchers.
#
# Source after REPO_ROOT is known:
#   . "$REPO_ROOT/contrib/perf/perflib.sh"
#
# Provides, in place of copies that had drifted between scripts:
#   log MSG                       timestamped line, tee'd to $DRIVER_LOG if set
#   warn MSG / die MSG            stderr; die exits 1
#   utc_stamp / run_id PREFIX     UTC timestamp helpers
#   require_num NAME VAL          numeric guard (see "Value guards")
#   safe_div NUM DEN [DEFAULT]    division that cannot divide by zero
#   nonneg NAME VAL               reject negative where negative is meaningless
#   dispose_datadir PATH [LABEL]  existing-datadir policy (see below)
#   stop_node CLI DATADIR PORT    graceful stop, then escalate
#
# shellcheck shell=bash

# Guard against double-sourcing: these are idempotent, but a second source
# would re-run the shellcheck directives and re-declare readonlys.
# shellcheck disable=SC2317  # reached only on a second source
if [ -n "${_PERFLIB_SOURCED:-}" ]; then return 0 2>/dev/null || true; fi
_PERFLIB_SOURCED=1

# Resolve this file's directory in bash AND zsh. BASH_SOURCE is unset under
# zsh, where it silently resolved to $PWD -- so the guard file was "not found"
# and every call fell into the fail-closed branch.
if [ -n "${BASH_SOURCE:-}" ]; then
  _PERFLIB_SELF="${BASH_SOURCE[0]}"
elif [ -n "${ZSH_VERSION:-}" ]; then
  # shellcheck disable=SC2296  # zsh-only expansion, guarded above
  _PERFLIB_SELF="${(%):-%N}"
else
  _PERFLIB_SELF="$0"
fi
_PERFLIB_DIR="$(cd "$(dirname "$_PERFLIB_SELF")" && pwd)"
export _PERFLIB_DIR
if [ ! -f "$_PERFLIB_DIR/datadir_guard.sh" ]; then
  echo "ERROR: perflib.sh cannot locate its own directory (got '$_PERFLIB_DIR')." >&2
  echo "       Source it by full path, e.g. . \"\$REPO_ROOT/contrib/perf/perflib.sh\"" >&2
  return 1 2>/dev/null || exit 1
fi

# ---------------------------------------------------------------- logging ---

utc_stamp() { date -u '+%Y-%m-%d %H:%M:%S UTC'; }

# Identical in six scripts before this. $DRIVER_LOG is optional; without it the
# line still goes to stdout, so sourcing this never silently swallows output.
log() {
  if [ -n "${DRIVER_LOG:-}" ]; then
    echo "$(utc_stamp) $*" | tee -a "$DRIVER_LOG"
  else
    echo "$(utc_stamp) $*"
  fi
}

# warn/die go to stderr AND to the driver log when one is set. Without the
# log copy, a failed run left a driver log showing normal progress and no
# error at all -- the operator saw the failure on the terminal and the archived
# log did not record it.
warn() {
  echo "WARNING: $*" >&2
  [ -n "${DRIVER_LOG:-}" ] && echo "$(utc_stamp) WARNING: $*" >> "$DRIVER_LOG"
  return 0
}

die() {
  echo "ERROR: $*" >&2
  [ -n "${DRIVER_LOG:-}" ] && echo "$(utc_stamp) ERROR: $*" >> "$DRIVER_LOG"
  exit 1
}

run_id() { echo "${1:-run}-$(date -u '+%Y%m%dT%H%M%SZ')"; }

# ----------------------------------------------------------- value guards ---
# Measurement scripts divide, subtract and compare constantly. A zero, empty or
# negative value that slips through does not crash -- it produces a plausible
# wrong number, which is the failure mode this whole program exists to avoid.

is_num() {
  case "${1:-}" in
    ''|*[!0-9.+-]*) return 1 ;;
    *) [ "$(echo "${1}" | tr -cd '.' | wc -c)" -le 1 ] || return 1 ;;
  esac
  return 0
}

# require_num NAME VALUE -- non-empty and numeric, else die.
require_num() {
  local name="$1" val="${2:-}"
  [ -n "$val" ] || die "$name is empty; expected a number"
  is_num "$val" || die "$name is not numeric: '$val'"
}

# nonneg NAME VALUE -- numeric and >= 0. Heights, counts, durations and byte
# sizes are never negative; a negative one means a subtraction ran backwards.
nonneg() {
  local name="$1" val="${2:-}"
  require_num "$name" "$val"
  case "$val" in
    -*) die "$name is negative ($val); a count/height/duration cannot be" ;;
  esac
}

# positive NAME VALUE -- numeric and > 0. Use for denominators and block spans.
positive() {
  local name="$1" val="${2:-}"
  nonneg "$name" "$val"
  case "$val" in
    0|0.0|0.00|.0) die "$name is zero; expected a positive value" ;;
  esac
}

# safe_div NUM DEN [DEFAULT] -- never divides by zero. Prints DEFAULT (default
# empty) and warns instead, so a caller records a blank cell rather than a
# fabricated rate or a crash mid-run.
safe_div() {
  local num="${1:-}" den="${2:-}" dflt="${3:-}"
  if ! is_num "$num" || ! is_num "$den"; then
    warn "safe_div: non-numeric operand (num='$num' den='$den')"
    printf '%s' "$dflt"; return 1
  fi
  case "$den" in
    0|0.0|0.00|-0|.0)
      warn "safe_div: denominator is zero; refusing to divide"
      printf '%s' "$dflt"; return 1 ;;
  esac
  awk -v n="$num" -v d="$den" 'BEGIN { if (d == 0) exit 1; printf "%.4f", n / d }'
}

# span_blocks START END -- inclusive block count with the sign checked. A
# reversed pair means the caller paired the wrong begin/done.
span_blocks() {
  local start="${1:-}" end="${2:-}"
  nonneg "start height" "$start"
  nonneg "end height" "$end"
  if [ "$end" -lt "$start" ]; then
    die "end height ($end) is below start ($start); span would be negative"
  fi
  echo $(( end - start + 1 ))
}

# ------------------------------------------------------ datadir disposition --

# _perflib_is_protected PATH -- true if PATH is any plausible production
# datadir, on any platform (zeropaths.is_protected_datadir).
_perflib_is_protected() {
  python3 - "$1" <<'EOF' 2>/dev/null
import sys, os
sys.path.insert(0, os.environ.get("_PERFLIB_DIR", "."))
import zeropaths
sys.exit(0 if zeropaths.is_protected_datadir(sys.argv[1]) else 1)
EOF
}
#
# What to do when the target datadir already exists. Default is set-aside then
# recreate: the old tree is preserved under a timestamped name and a fresh one
# is created, so a re-run never silently destroys the previous run's evidence.
#
#   ZERO_PERF_DATADIR_POLICY = aside   (default) rename to <path>.aside-<utc>, recreate
#                              replace           delete and recreate  [destructive]
#                              recreate          synonym for replace
#                              keep              leave as is, use in place
#                              external          do not touch; caller manages it
#
# Deletion uses `rm -r`. `-f` is added only when ZERO_PERF_FORCE=1 (scripts
# expose this as --force), so a permission error is reported rather than
# forced through.
#
# Live-datadir refusal still applies first: dispose_datadir never operates on a
# runtime or Zero400 path unless ZERO_PERF_ALLOW_LIVE_DATADIR is set.
dispose_datadir() {
  local path="${1:?usage: dispose_datadir PATH [LABEL]}"
  local label="${2:-LAB}"
  local policy="${ZERO_PERF_DATADIR_POLICY:-aside}"

  # Refuse a live datadir before any policy is applied.
  #
  # The return status MUST be checked. perflib is sourced by callers that may
  # not run under `set -e`, and refuse_live_datadir reports by exit status --
  # ignoring it once moved a real datadir during development.
  if [ -f "$_PERFLIB_DIR/datadir_guard.sh" ]; then
    # shellcheck source=/dev/null
    . "$_PERFLIB_DIR/datadir_guard.sh"
    if ! refuse_live_datadir "$label" "$path"; then
      die "refusing to apply policy '$policy' to a live datadir: $path"
    fi
    # refuse_live_datadir passes when ZERO_PERF_ALLOW_LIVE_DATADIR is set --
    # that override exists so a lab may READ a live datadir. It must not also
    # authorise DELETING one: the override is routinely set for a whole
    # session, and a destructive policy would then run unchallenged.
    # Destructive policies require their own, separate acknowledgement.
    case "$policy" in
      replace|recreate|aside)
        if [ -n "${ZERO_PERF_ALLOW_LIVE_DATADIR:-}" ] \
           && _perflib_is_protected "$path"; then
          if [ "${ZERO_PERF_ALLOW_LIVE_DESTROY:-}" != "1" ]; then
            die "$path is a production datadir. ZERO_PERF_ALLOW_LIVE_DATADIR permits reading it, not '$policy'. Set ZERO_PERF_ALLOW_LIVE_DESTROY=1 as well if you truly intend to destroy it."
          fi
          warn "ZERO_PERF_ALLOW_LIVE_DESTROY set; applying '$policy' to PRODUCTION datadir '$path'"
        fi ;;
    esac
  else
    die "datadir_guard.sh not found next to perflib.sh; refusing to touch '$path'"
  fi

  case "$policy" in
    external)
      log "$label datadir policy=external; leaving '$path' untouched"
      return 0 ;;
    keep)
      if [ -d "$path" ]; then
        warn "$label datadir policy=keep; REUSING existing '$path'. Results may reflect prior state."
      else
        mkdir -p "$path"
        log "$label datadir policy=keep; created '$path'"
      fi
      return 0 ;;
    replace|recreate)
      if [ -d "$path" ]; then
        warn "$label datadir policy=$policy; DELETING existing '$path' (previous run's data is lost)"
        # `rm -r`, not `rm -rf`. Without -f, a permission problem or a
        # read-only file surfaces as an error instead of being forced through
        # silently. -f is added only when the caller asks for it.
        if [ "${ZERO_PERF_FORCE:-}" = "1" ]; then
          rm -rf "$path" || die "could not remove '$path' even with force"
        else
          rm -r "$path" || die "could not remove '$path'; re-run with ZERO_PERF_FORCE=1 (or --force) if that is intended"
        fi
      fi
      mkdir -p "$path"
      log "$label datadir recreated at '$path'"
      return 0 ;;
    aside)
      if [ -d "$path" ]; then
        local stamp kept
        stamp="$(date -u '+%Y%m%dT%H%M%SZ')"
        kept="$path.aside-$stamp"
        mv "$path" "$kept" || die "could not set aside '$path'"
        log "$label datadir set aside -> '$kept'"
        warn "previous datadir preserved at '$kept'; remove it when no longer needed"
      fi
      mkdir -p "$path"
      log "$label datadir recreated at '$path'"
      return 0 ;;
    *)
      die "unknown ZERO_PERF_DATADIR_POLICY='$policy' (aside|replace|recreate|keep|external)" ;;
  esac
}

# ------------------------------------------------------------ node control ---

# stop_node CLI DATADIR RPCPORT [EXTRA_CLI_ARGS...] -- graceful RPC stop, then
# escalate only against a process matched on THIS datadir, never a bare name.
stop_node() {
  local cli_bin="${1:?usage: stop_node CLI DATADIR RPCPORT}"
  local datadir="${2:?}" port="${3:?}"
  shift 3
  "$cli_bin" -datadir="$datadir" -rpcport="$port" "$@" stop >/dev/null 2>&1 || true
  local i=0
  while [ $i -lt 30 ]; do
    pgrep -f "zerod .*-datadir=$datadir" >/dev/null 2>&1 || return 0
    sleep 1
    i=$((i + 1))
  done
  warn "node on '$datadir' did not stop within 30s; escalating"
  pkill -f "zerod .*-datadir=$datadir" 2>/dev/null || true
}
