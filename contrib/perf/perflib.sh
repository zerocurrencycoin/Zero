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
#   lab_conf DIR PORT [K=V ...]   the lab zero.conf: lab template plus the trial's keys
#   cli / height_of / node_pid    RPC to the launcher's node (NODE_DATADIR, NODE_RPCPORT), bounded
#   stop_node [PID]               RPC stop, then escalate (kill_pid_hard)
#   wait_done_loading PID         until "Done loading" or the node exits
#   util_tsv_init / sample_util   per-process CPU, memory and thermal samples
#   runtime_record LOG CONF ARGS  declared runtime, checked against the node's log
#   record_trial ...              one RecBench row: runtime, input hash, util path
#   snap_archive NAME             locate a snapshot archive
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
# runtime or Zero path unless ZERO_PERF_ALLOW_LIVE_DATADIR is set.
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
#
# The launcher's node: set once after the datadir and port are known.
#   NODE_DATADIR  the -datadir the node runs on
#   NODE_RPCPORT  its -rpcport
#   ZERO_CLI      zero-cli path (default $REPO_ROOT/src/zero-cli)
# RPC user and password come from NODE_DATADIR/zero.conf (lab_conf writes them).

# run_bounded SECS CMD... -- run CMD, killed after SECS. coreutils timeout where
# present, else perl alarm (macOS ships perl, not timeout). Exit 124 or 142 on
# expiry.
run_bounded() {
  local secs="${1:?usage: run_bounded SECS CMD...}"
  shift
  if command -v timeout >/dev/null 2>&1; then
    timeout "$secs" "$@"
  elif command -v gtimeout >/dev/null 2>&1; then
    gtimeout "$secs" "$@"
  else
    perl -e 'alarm shift; exec @ARGV' "$secs" "$@"
  fi
}

# cli ARGS... -- zero-cli against the launcher's node, under a timeout.
# An unguarded call blocks for as long as the RPC does: getwalletinfo waits on
# cs_wallet for minutes under a fat-wallet witness build, and getblockcount on
# cs_main during a height walk, which stalled util sampling mid-run
# (M-WAL-SYNC-FAT). ZERO_PERF_CLI_TIMEOUT_S, default 60; 0 disables.
cli() {
  local t="${ZERO_PERF_CLI_TIMEOUT_S:-60}"
  local bin="${ZERO_CLI:-${REPO_ROOT:-.}/src/zero-cli}"
  if [ "$t" = "0" ]; then
    "$bin" -datadir="${NODE_DATADIR:?NODE_DATADIR unset}" -rpcport="${NODE_RPCPORT:?NODE_RPCPORT unset}" "$@"
  else
    run_bounded "$t" "$bin" -datadir="${NODE_DATADIR:?NODE_DATADIR unset}" \
      -rpcport="${NODE_RPCPORT:?NODE_RPCPORT unset}" "$@"
  fi
}

# height_of -- the node's block count, or empty when RPC is not answering.
height_of() { cli getblockcount 2>/dev/null || true; }

# node_pid -- pid of a zerod on NODE_DATADIR, matched on the datadir, never
# on the bare process name. Empty, status 0, when none runs: callers use it
# under set -e -o pipefail, where pgrep's no-match status would exit them.
node_pid() { pgrep -f "zerod .*-datadir=${NODE_DATADIR:?}( |$)" | head -1 || true; }

# pid_alive PID -- the process exists and is not a zombie (exited, not yet
# reaped by its parent). The one liveness test the node helpers use.
pid_alive() {
  local st
  st="$(ps -o stat= -p "${1:?usage: pid_alive PID}" 2>/dev/null)" || return 1
  case "$st" in *Z*|'') return 1 ;; esac
  return 0
}

# kill_pid_hard PID -- SIGTERM, wait up to 20 s, then SIGKILL. For a node that
# is past answering RPC: zerod's shutdown needs RPC or an interruption point,
# and LoadBlockIndexDB's per-block loop has none.
kill_pid_hard() {
  local pid="${1:?usage: kill_pid_hard PID}" i
  kill -TERM "$pid" 2>/dev/null || return 0
  for i in 1 2 3 4 5 6 7 8 9 10; do
    pid_alive "$pid" || return 0
    sleep 2
  done
  warn "pid $pid did not exit 20 s after SIGTERM; sending SIGKILL"
  kill -9 "$pid" 2>/dev/null || true
  for i in 1 2 3 4 5; do
    pid_alive "$pid" || return 0
    sleep 1
  done
  warn "pid $pid still alive after SIGKILL"
}

# stop_node [PID] -- RPC stop, wait up to ZERO_PERF_STOP_WAIT_S (60) for the
# node to exit, then kill_pid_hard. PID defaults to the node on NODE_DATADIR.
stop_node() {
  local pid="${1:-}" i=0 wait_s="${ZERO_PERF_STOP_WAIT_S:-60}"
  [ -n "$pid" ] || pid="$(node_pid)"
  cli stop >/dev/null 2>&1 || true
  [ -n "$pid" ] || return 0
  while pid_alive "$pid"; do
    if [ "$i" -ge "$wait_s" ]; then
      warn "node pid $pid on $NODE_DATADIR did not stop within ${wait_s}s; escalating"
      kill_pid_hard "$pid"
      return 0
    fi
    sleep 1
    i=$((i + 1))
  done
}

# wait_done_loading PID -- until NODE_DATADIR/debug.log shows "Done loading" or
# the node exits. Returns 1 if it exited first.
wait_done_loading() {
  local pid="${1:?usage: wait_done_loading PID}"
  while pid_alive "$pid"; do
    if grep -q "Done loading" "$NODE_DATADIR/debug.log" 2>/dev/null; then
      log "detected Done loading"
      return 0
    fi
    log "waiting Done loading height=$(height_of)"
    sleep 15
  done
  return 1
}

# util_tsv_init PATH [EXTRA_HEADER] -- start a util.tsv. EXTRA_HEADER is
# tab-separated column names appended after the standard ones; the launcher
# then sets UTIL_EXTRA_FN to a function printing the same number of
# tab-separated values for each sample.
UTIL_COLUMNS="utc	phase	height	pct_cpu	cpu_rate	pct_mem	rss_kb	phys_footprint_mb	pid	therm	cpu_s	threads"
util_tsv_init() {
  UTIL_TSV="${1:?usage: util_tsv_init PATH [EXTRA_HEADER]}"
  _util_prev_cpu_s=""; _util_prev_t=""
  printf '%s%s\n' "$UTIL_COLUMNS" "${2:+	$2}" > "$UTIL_TSV"
}

# sample_util PHASE PID [HEIGHT] -- one row to UTIL_TSV. No-op when
# SAMPLE_UTIL=0, UTIL_TSV is unset, or the process is gone. cpu_s is the
# process's cumulative CPU seconds, threads its thread count. vmmap suspends
# the target while it walks the address space, so UTIL_FOOTPRINT=0 skips the
# footprint inside a timed span (take it at a phase boundary instead).
sample_util() {
  local phase="$1" pid="$2" height="${3:-}"
  [ "${SAMPLE_UTIL:-1}" = "1" ] && [ -n "${UTIL_TSV:-}" ] || return 0
  [ -n "$pid" ] && pid_alive "$pid" || return 0
  local ps_line pct_cpu pct_mem rss_kb phys_mb="" cpu_s now cpu_rate="" therm="NA" extra="" threads=""
  ps_line=$(ps -o %cpu=,%mem=,rss= -p "$pid" 2>/dev/null | head -1 | sed 's/^ *//')
  [ -n "$ps_line" ] || return 0
  pct_cpu=$(echo "$ps_line" | awk '{print $1}')
  pct_mem=$(echo "$ps_line" | awk '{print $2}')
  rss_kb=$(echo "$ps_line" | awk '{print $3}')
  # ps %cpu is a decaying average (ps(1)): it lags a step change by tens of
  # seconds and read 101.8-113.8 where the delta below read 113.2-115.2 on one
  # import. cpu_rate is CPU seconds over wall seconds since the last sample.
  cpu_s=$(ps -o time= -p "$pid" 2>/dev/null | tr -d ' ' \
          | awk -F: '{if(NF==3)print $1*3600+$2*60+$3; else if(NF==2)print $1*60+$2; else print $1+0}')
  now=$(date +%s)
  if [ -n "${_util_prev_cpu_s:-}" ] && [ -n "${_util_prev_t:-}" ]; then
    cpu_rate=$(awk -v a="$cpu_s" -v b="$_util_prev_cpu_s" -v t="$now" -v p="$_util_prev_t" \
      'BEGIN{d=t-p; if(d>0) printf "%.1f",(a-b)/d*100}')
  fi
  _util_prev_cpu_s="$cpu_s"; _util_prev_t="$now"
  # ps -M lists one line per thread after a header (macOS); Linux: ps -T.
  threads=$( { ps -M -p "$pid" 2>/dev/null || ps -T -p "$pid" 2>/dev/null; } | awk 'NR>1' | wc -l | tr -d ' ')
  if [ "${UTIL_FOOTPRINT:-1}" = "1" ] && command -v vmmap >/dev/null 2>&1; then
    # -F: -- vmmap prints "Physical footprint:  202.1M".
    phys_mb=$(vmmap -summary "$pid" 2>/dev/null | awk -F: '/Physical footprint:/ {
      v = $2; gsub(/^[ \t]+|[ \t]+$/, "", v);
      if (v ~ /G/) { gsub(/[^0-9.]/, "", v); printf "%.1f", v*1024; exit }
      if (v ~ /M/) { gsub(/[^0-9.]/, "", v); printf "%.1f", v; exit }
      if (v ~ /K/) { gsub(/[^0-9.]/, "", v); printf "%.1f", v/1024; exit }
    }')
  fi
  # Thermal or performance warning (K3). macOS reports a level only once one
  # has been raised, so "none" is the normal reading.
  if command -v pmset >/dev/null 2>&1; then
    therm=$(pmset -g therm 2>/dev/null \
      | awk '/level|Limit/ && !/No / {gsub(/[ \t]+/, ""); printf "%s;", $0}')
    therm="${therm:-none}"
  fi
  [ -n "${UTIL_EXTRA_FN:-}" ] && extra="	$("$UTIL_EXTRA_FN" "$pid")"
  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s%s\n" \
    "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$phase" "${height:-}" \
    "$pct_cpu" "${cpu_rate:-}" "$pct_mem" "$rss_kb" "${phys_mb:-}" "$pid" "$therm" \
    "$cpu_s" "$threads" "$extra" >> "$UTIL_TSV"
  [ "${UTIL_QUIET:-0}" = "1" ] || log "util phase=$phase h=${height:-NA} cpu%=$pct_cpu cpu_rate=${cpu_rate:-NA} rss_kb=$rss_kb threads=$threads phys_mb=${phys_mb:-NA} therm=$therm"
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

# runtime_record LOG CONF "ZEROD_ARGS"
#   Derive the runtime a trial ran with from the zero.conf the node read plus
#   its command line, and check it against the node's own log (wallet, script
#   threads, dbcache). Sets RUNTIME_ARGS (--runtime k=v ... for recbench.py),
#   RUNTIME_DECLARED (k=v,... as set) and RUNTIME_OBSERVED (k=v,... as the log
#   shows), for row notes and trial summaries. Returns 1 on a mismatch, so a
#   caller can refuse to record a row whose declared runtime is not the fact.
#   One implementation for every launcher: see debuglog.py --check-runtime.
runtime_record() {
  local logf="${1:?log}" conf="${2:?conf}" zargs="${3:-}" out errf rc line
  # shellcheck disable=SC2034  # both are outputs, read by the caller
  RUNTIME_ARGS=()
  # shellcheck disable=SC2034
  RUNTIME_DECLARED=""
  # shellcheck disable=SC2034
  RUNTIME_OBSERVED=""
  errf="$(mktemp)"
  out="$(python3 "$_PERFLIB_DIR/debuglog.py" --check-runtime "$logf" \
           --conf "$conf" --zerod-args="$zargs" 2>"$errf")"
  rc=$?
  while IFS= read -r line; do
    [ -n "$line" ] && RUNTIME_ARGS+=(--runtime "$line")
  done <<< "$out"
  # shellcheck disable=SC2034
  RUNTIME_DECLARED="$(printf '%s\n' "$out" | sed '/^$/d' | paste -sd, -)"
  # shellcheck disable=SC2034
  RUNTIME_OBSERVED="$(python3 "$_PERFLIB_DIR/debuglog.py" --observed-runtime "$logf" \
                        | paste -sd, -)"
  if [ "$rc" -ne 0 ]; then
    while IFS= read -r line; do warn "$line"; done < "$errf"
  fi
  rm -f "$errf"
  return "$rc"
}

# lab_conf DIR RPCPORT [KEY=VALUE ...]
#   Write DIR/zero.conf for a lab node: contrib/zero-conf.sh's lab template
#   (server, listen=0, maxconnections=0, RPC user and password rt/rt) plus the
#   given keys, which are the trial's conditions. That is the standard lab
#   config: no Insight indexes, dbcache, txindex or witness keys unless the
#   caller names them. Replaces any conf the input carried, so an archive's
#   zero.conf never decides the runtime. ZERO_PERF_ARCHIVE_CONF=1 keeps an
#   existing DIR/zero.conf instead. A sticky reindex= is refused or stripped.
lab_conf() {
  local dir="${1:?usage: lab_conf DIR RPCPORT [KEY=VALUE ...]}"
  local port="${2:?usage: lab_conf DIR RPCPORT [KEY=VALUE ...]}"
  shift 2
  local conf="$dir/zero.conf" kv
  # shellcheck source=/dev/null
  . "$_PERFLIB_DIR/datadir_guard.sh"
  refuse_live_datadir LAB "$dir" || die "lab_conf: refusing to write a conf into $dir"
  for kv in "$@"; do
    case "$kv" in
      reindex=*) die "lab_conf: reindex is a one-shot command-line flag, not a conf key" ;;
      [a-z]*=*) ;;
      *) die "lab_conf: '$kv' is not KEY=VALUE" ;;
    esac
  done
  if [ "${ZERO_PERF_ARCHIVE_CONF:-0}" = "1" ] && [ -f "$conf" ]; then
    grep -v '^reindex=' "$conf" > "$conf.tmp" || true
    mv "$conf.tmp" "$conf"
    for kv in "$@"; do printf '%s\n' "$kv" >> "$conf"; done
    log "lab conf: kept the input's zero.conf (ZERO_PERF_ARCHIVE_CONF=1)${1:+; added $*}"
    return 0
  fi
  mkdir -p "$dir"
  # ZERO_DBCACHE is read by zero-conf.sh; cleared so the caller's environment
  # cannot add a dbcache the trial did not name.
  ZERO_RPCUSER=rt ZERO_RPCPASSWORD=rt ZERO_RPCPORT="$port" ZERO_DBCACHE='' \
    "$_PERFLIB_DIR/../zero-conf.sh" lab -dir "$dir" -out zero.conf -force >/dev/null \
    || die "lab_conf: contrib/zero-conf.sh lab failed for $dir"
  for kv in "$@"; do printf '%s\n' "$kv" >> "$conf"; done
  log "lab conf: lab template, rpcport=$port${1:+, $*}"
}

# record_trial LOG CONF "ZEROD_ARGS" INPUT UTIL_TSV RECBENCH_ARGS...
#   Record one trial through recbench.py --record, with what every row needs
#   and launchers used to add by hand, or not at all:
#     - runtime_record LOG CONF ZEROD_ARGS: the declared runtime, checked
#       against the node's log. A mismatch records nothing and returns 1.
#     - INPUT (a file, or empty): its name and the first 16 hex of its sha256 in
#       the notes, so two inputs with one name do not pool. A directory is
#       named, not hashed.
#     - UTIL_TSV (a file, or empty): its path relative to the run directory.
#   RECBENCH_ARGS are passed through (--campaign, --run-id, --mode, the
#   window or --metric/--value, --binary, ...); a --notes among them is kept
#   and the above appended. Sets RECORD_FINGERPRINT from recbench's reply.
record_trial() {
  local logf="${1:?usage: record_trial LOG CONF ZEROD_ARGS INPUT UTIL_TSV RECBENCH_ARGS...}"
  local conf="${2:?conf}" zargs="${3:-}" input="${4:-}" util="${5:-}"
  shift 5
  local notes="" out
  local pass=()
  RECORD_FINGERPRINT=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --notes) notes="${2:-}"; shift 2 ;;
      --notes=*) notes="${1#--notes=}"; shift ;;
      *) pass+=("$1"); shift ;;
    esac
  done
  if ! runtime_record "$logf" "$conf" "$zargs"; then
    warn "record_trial: runtime mismatch; row NOT recorded"
    return 1
  fi
  if [ -n "$input" ] && [ -f "$input" ]; then
    notes="${notes:+$notes;}input=$(basename "$input");input_sha256=$(shasum -a 256 "$input" | cut -c1-16)"
  elif [ -n "$input" ]; then
    notes="${notes:+$notes;}input=$(basename "$input")"
  fi
  if [ -n "$util" ] && [ -f "$util" ]; then
    notes="${notes:+$notes;}util=$(basename "$(dirname "$util")")/$(basename "$util")"
  fi
  notes="${notes:+$notes;}observed=$RUNTIME_OBSERVED"
  if ! out="$(python3 "$_PERFLIB_DIR/recbench/recbench.py" --record \
                "${RUNTIME_ARGS[@]}" ${pass[@]+"${pass[@]}"} --notes "$notes")"; then
    warn "record_trial: recbench.py --record failed: $out"
    return 1
  fi
  log "$out"
  # shellcheck disable=SC2034  # output, read by the caller
  RECORD_FINGERPRINT="$(printf '%s\n' "$out" | sed -n 's/.*fingerprint=\([^ ]*\).*/\1/p' | head -1)"
  return 0
}

# snap_archive NAME
#   Print the path of a snapshot archive (chainblocks-tiny.tgz, ...). Searched
#   in $ZERO_PERF_ARCHIVE_DIR, the platform default datadir, then its ".save"
#   sibling -- the previous datadir, renamed when the chain was re-imported,
#   still holds the archives. One lookup for every launcher; returns 1 with the
#   searched list when absent.
snap_archive() {
  local name="${1:?archive name}" dd d
  dd="$(python3 -c "import sys; sys.path.insert(0, '$_PERFLIB_DIR'); import zeropaths; print(zeropaths.default_datadir())" 2>/dev/null)" \
    || dd="$HOME/Library/Application Support/zero"
  for d in ${ZERO_PERF_ARCHIVE_DIR:+"$ZERO_PERF_ARCHIVE_DIR"} "$dd" "$dd.save"; do
    if [ -f "$d/$name" ]; then printf '%s\n' "$d/$name"; return 0; fi
  done
  warn "snapshot archive $name not found in: ${ZERO_PERF_ARCHIVE_DIR:+$ZERO_PERF_ARCHIVE_DIR, }$dd, $dd.save"
  return 1
}
