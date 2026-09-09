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
#   require_file PATH [LABEL]     artifact exists and is non-empty
#   require_marker PATH RE [LBL]  artifact carries a completion marker
#   count_matches PATH RE         matching line count; 0 if absent
#   require_counts_agree ...      suite summary vs its own per-test lines
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

# ------------------------------------------------------- run verification ---
# Rationale and usage: README.md, "Shared shell library".

# require_file PATH [LABEL]
require_file() {
  local path="${1:-}" label="${2:-artifact}"
  [ -n "$path" ] || die "$label: no path given"
  [ -e "$path" ] || die "$label: '$path' does not exist; the run produced nothing"
  [ -s "$path" ] || die "$label: '$path' is empty; the run produced no output"
}

# require_marker PATH REGEX [LABEL]
require_marker() {
  local path="${1:-}" pat="${2:-}" label="${3:-run}"
  require_file "$path" "$label"
  [ -n "$pat" ] || die "$label: no marker pattern given"
  if ! grep -Eq -- "$pat" "$path"; then
    die "$label: completion marker '$pat' absent from '$path'; treat the run as incomplete"
  fi
}

# count_matches PATH REGEX -- matching lines; 0 when absent.
count_matches() {
  local path="${1:-}" pat="${2:-}" n
  [ -f "$path" ] || { echo 0; return 0; }
  # grep -c prints 0 and exits 1 on no match; `|| echo 0` would emit two lines.
  n="$(grep -Ec -- "$pat" "$path" 2>/dev/null)"
  case "$n" in
    ''|*[!0-9]*) echo 0 ;;
    *)           echo "$n" ;;
  esac
}

# require_counts_agree PATH TOTAL_PAT PASS_PAT FAIL_PAT [LABEL]
# die on disagreement; return 1 when any test failed.
require_counts_agree() {
  local path="${1:-}" total_pat="${2:-}" pass_pat="${3:-}" fail_pat="${4:-}"
  local label="${5:-suite}"
  require_file "$path" "$label"
  local ran passed failed
  ran="$(count_matches "$path" "$total_pat")"
  passed="$(count_matches "$path" "$pass_pat")"
  failed="$(count_matches "$path" "$fail_pat")"
  log "$label: ran=$ran passed=$passed failed=$failed"
  if [ "$ran" -ne $((passed + failed)) ]; then
    die "$label: $ran started but $passed passed + $failed failed; counts disagree"
  fi
  [ "$failed" -eq 0 ] || return 1
  return 0
}

# warn_if_busy [MAX_BUSY_PCT] -- report competing CPU load before a timed run.
#
# A benchmark sharing a machine with a build measured 15% slow on 2026-09-05,
# which is larger than any effect this lab sets out to detect. The run was not
# wrong, it was uninterpretable, and nothing in the harness said so.
#
# Uses CPU busy percent, not load average. Load average counts runnable threads
# and does not normalise by core count: this 14-core host sits at load ~2.0
# while 89% idle, so a load threshold warns on every run and is ignored within
# a day. Busy percent answers the question actually being asked -- is another
# process going to compete for cores.
#
# Warns rather than refuses: the operator may have a reason, and blocking a
# long run on a heuristic costs more than it saves. The point is that the
# driver log records the state, so a suspicious number can be explained later.
warn_if_busy() {
  local max="${1:-${ZERO_PERF_MAX_BUSY_PCT:-25}}" idle busy
  # Match the number attached to "idle" rather than counting fields: the line
  # has a trailing space, so a positional parse returned the word "idle" and
  # the guard silently passed every time.
  idle=$(top -l 1 -n 0 2>/dev/null | sed -n 's/.*[^0-9.]\([0-9.][0-9.]*\)% idle.*/\1/p' | head -1)
  case "$idle" in ''|*[!0-9.]*) return 0 ;; esac
  busy=$(awk -v i="$idle" 'BEGIN{printf "%.1f", 100-i}')
  log "cpu_busy=${busy}% (threshold ${max}%)"
  if awk -v b="$busy" -v m="$max" 'BEGIN{exit !(b>m)}'; then
    warn "CPU ${busy}% busy before start: a competing process can move this result by 10-15%; timings from this run are not comparable to idle-machine runs"
    return 1
  fi
  return 0
}

# poll_interval CURRENT TARGET -- seconds to wait before the next poll.
#
# Each RPC poll costs ~212 ms of round trip and process spawn
# (M-LAB-POLL-COST), and in a timed run that cost lands inside the measured
# span. A fixed 2 s pace spent 9.6% of a 141 s reindex on polling. Backing off
# while far from the target and tightening near it cut that to 4.4%
# (M-LAB-POLL-BACKOFF) without losing detection accuracy, because the interval
# only bounds latency in the final approach.
#
# Env: ZERO_PERF_POLL_FAR_S (5), ZERO_PERF_POLL_NEAR_S (2),
#      ZERO_PERF_POLL_NEAR_BLOCKS (10000).
poll_interval() {
  local cur="${1:-}" target="${2:-}"
  local far="${ZERO_PERF_POLL_FAR_S:-5}" near="${ZERO_PERF_POLL_NEAR_S:-2}"
  local band="${ZERO_PERF_POLL_NEAR_BLOCKS:-10000}"
  case "$cur$target" in ''|*[!0-9]*) echo "$near"; return 0 ;; esac
  if [ $((target - cur)) -lt "$band" ]; then echo "$near"; else echo "$far"; fi
}

# now_ms -- wall clock in milliseconds.
# elapsed_s T0_MS [T1_MS] -- seconds, 3 decimals, between two now_ms readings.
#
# `date +%s` yields whole seconds. Over a fixed block count that rounds the
# reported rate to a discrete set: one second is ~9.8 blk/s on the tiny reindex
# window (M-LAB-WALL-SECONDS), so differences below ~0.7% are not
# representable. Timing the span in milliseconds removes that floor
# (M-LAB-WALL-MS). Use these instead of $((t1 - t0)) wherever a duration is
# reported or recorded.
now_ms() { python3 -c 'import time; print(int(time.time()*1000))'; }
elapsed_s() {
  local t0="${1:-}" t1="${2:-$(now_ms)}"
  case "$t0$t1" in ''|*[!0-9]*) echo "0"; return 1 ;; esac
  python3 -c "print(f'{($t1-$t0)/1000.0:.3f}')"
}
