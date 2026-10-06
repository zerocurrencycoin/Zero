#!/usr/bin/env bash
# Run a long `-reindex` under repeated Time Profiler captures: capture for
# CAPTURE_SECS, then idle until the next PERIOD_SECS boundary, repeat until
# the node exits (reindex complete) or MAX_CAPTURES is reached.
#
# Each capture's trace, XML export, height range, and system-state snapshot
# are written to their own subdirectory under OUT_DIR, so decode_captures.py
# can process the whole run after the fact. See the perf docs for the
# underlying methodology (why height range must be derived from debug.log,
# not guessed; why xctrace's id/ref export format needs bucket_profile.py's
# parser rather than a naive regex).
#
# Usage:
#   contrib/perf/capture_sequence.sh <datadir> <out_dir> [period_secs] [capture_secs] [max_captures] [template]
#
# Example (this investigation's actual parameters, run from repo root):
#   contrib/perf/prep_lab_datadir.sh   # or dispose_datadir via perflib.sh
#   rsync -a --exclude='chainstate' "$HOME/Library/Application Support/zero/" reindex-profile/datadir/
#   contrib/perf/capture_sequence.sh reindex-profile/datadir reindex-profile/captures 1200 300
#
# [template] selects the xctrace Instruments template (default: 'Time Profiler',
# the only one decode_captures.py can parse headlessly; inspect anything else
# in Instruments.app). Passing 'File Activity' or 'Allocations' records real
# data but produces a trace `xcrun xctrace export` cannot read in this
# Instruments version ("Document Missing Template Error"); open those in
# Instruments.app by hand. Traces from non-Time-Profiler
# templates are typically far larger (a 30s File Activity capture against a
# busy reindex was ~2.2GB) -- check free disk space before a long run.

export LC_ALL=C
set -u

DATADIR="${1:?usage: capture_sequence.sh <datadir> <out_dir> [period_secs] [capture_secs] [max_captures] [template]}"
OUT_DIR="${2:?usage: capture_sequence.sh <datadir> <out_dir> [period_secs] [capture_secs] [max_captures] [template]}"
PERIOD_SECS="${3:-1200}"   # 20 minutes
CAPTURE_SECS="${4:-300}"   # 5 minutes
MAX_CAPTURES="${5:-0}"     # 0 = unbounded (until reindex exits)
TEMPLATE="${6:-Time Profiler}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck disable=SC1091
. "$REPO_ROOT/contrib/perf/datadir_guard.sh"
# shellcheck source=/dev/null
. "$REPO_ROOT/contrib/perf/perflib.sh"
ZEROD="$REPO_ROOT/src/zerod"
# shellcheck disable=SC2034  # read by perflib.sh cli()
ZERO_CLI="$REPO_ROOT/src/zero-cli"
RPCPORT=23920

# Refuse the live datadir -- labs must use a disposable -datadir
# unless ZERO_PERF_ALLOW_LIVE_DATADIR=1.
refuse_live_datadir DATADIR "$DATADIR"

mkdir -p "$OUT_DIR"
SEQ_LOG="$OUT_DIR/sequence.log"
# log() comes from perflib.sh and tees to DRIVER_LOG.
# shellcheck disable=SC2034
DRIVER_LOG="$SEQ_LOG"


record_system_state() {
    local dest="$1"
    {
        echo "== date =="; date -u '+%Y-%m-%d %H:%M:%S UTC'
        echo "== sysctl =="; sysctl -n hw.ncpu hw.physicalcpu hw.memsize
        echo "== pmset thermlog =="; pmset -g therm
        echo "== uptime =="; uptime
        echo "== top (zerod) =="; top -l 1 -pid "$PID" 2>/dev/null | tail -15
    } > "$dest" 2>&1
}

# height_of acts on this node (perflib.sh).
# shellcheck disable=SC2034  # read by perflib.sh
NODE_DATADIR="$DATADIR"
# shellcheck disable=SC2034
NODE_RPCPORT="$RPCPORT"

# --- launch zerod ---
# The datadir is usually an rsync of a live one, zero.conf included; the lab
# writes its own so the source's keys do not become the trial's runtime.
lab_conf "$DATADIR" "$RPCPORT"
log "launching zerod -reindex on $DATADIR"
"$ZEROD" -datadir="$DATADIR" -reindex -connect=0 -listen=0 -rpcport=$RPCPORT \
    >"$OUT_DIR/zerod_stdout.log" 2>&1 &
PID=$!
log "zerod pid=$PID"

until h=$(height_of) && [[ "$h" =~ ^[0-9]+$ ]] && [ "$h" -gt 0 ]; do
    if ! pid_alive "$PID"; then
        log "ERROR: zerod exited before RPC came up"
        exit 1
    fi
    sleep 3
done
log "RPC up, starting height=$h"

capture_num=0
start_epoch=$(date +%s)

while pid_alive "$PID"; do
    capture_num=$((capture_num + 1))
    if [ "$MAX_CAPTURES" -gt 0 ] && [ "$capture_num" -gt "$MAX_CAPTURES" ]; then
        log "reached max_captures=$MAX_CAPTURES, stopping sequence (zerod left running)"
        break
    fi

    cap_dir="$OUT_DIR/capture_$(printf '%03d' "$capture_num")"
    mkdir -p "$cap_dir"

    h_before=$(height_of)
    log "capture $capture_num: start, height=$h_before -> $cap_dir (template: $TEMPLATE)"

    xcrun xctrace record --template "$TEMPLATE" \
        --output "$cap_dir/timeprofile.trace" \
        --time-limit "${CAPTURE_SECS}s" \
        --attach "$PID" >"$cap_dir/xctrace.log" 2>&1

    h_after=$(height_of)
    record_system_state "$cap_dir/system_state.txt"
    cp "$DATADIR/debug.log" "$cap_dir/debug.log.snapshot" 2>/dev/null

    {
        echo "capture_num=$capture_num"
        echo "height_before=$h_before"
        echo "height_after=$h_after"
        echo "capture_secs=$CAPTURE_SECS"
    } > "$cap_dir/capture_meta.txt"

    log "capture $capture_num: done, height=$h_before -> $h_after"

    if ! pid_alive "$PID"; then
        log "zerod exited during/after capture $capture_num, stopping sequence"
        break
    fi

    # idle until the next PERIOD_SECS boundary (relative to sequence start)
    next_boundary=$(( start_epoch + capture_num * PERIOD_SECS ))
    now=$(date +%s)
    sleep_for=$(( next_boundary - now ))
    if [ "$sleep_for" -gt 0 ]; then
        log "idling ${sleep_for}s until next capture boundary"
        # sleep in short chunks so a zerod exit is noticed promptly
        while [ "$sleep_for" -gt 0 ] && pid_alive "$PID"; do
            chunk=$(( sleep_for < 10 ? sleep_for : 10 ))
            sleep "$chunk"
            sleep_for=$(( sleep_for - chunk ))
        done
    fi
done

if pid_alive "$PID"; then
    log "sequence stopped, zerod (pid=$PID) still running -- leave it or kill -TERM $PID"
else
    log "zerod (pid=$PID) has exited -- reindex presumably complete or crashed, check zerod_stdout.log"
fi

log "sequence finished, $capture_num capture(s) in $OUT_DIR"
