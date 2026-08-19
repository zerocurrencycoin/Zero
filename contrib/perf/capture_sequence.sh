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
#   rm -rf reindex-profile/datadir
#   rsync -a --exclude='chainstate' "/Users/walter/Library/Application Support/Zero/" reindex-profile/datadir/
#   contrib/perf/capture_sequence.sh reindex-profile/datadir reindex-profile/captures 1200 300
#
# [template] selects the xctrace Instruments template (default: 'Time Profiler',
# the only one decode_captures.py can parse headlessly -- see GUI.md before
# using anything else). Passing 'File Activity' or 'Allocations' records real
# data but produces a trace `xcrun xctrace export` cannot read in this
# Instruments version ("Document Missing Template Error") -- GUI.md documents
# opening those in Instruments.app by hand. Traces from non-Time-Profiler
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
ZEROD="$REPO_ROOT/src/zerod"
ZERO_CLI="$REPO_ROOT/src/zero-cli"
RPCPORT=23920

# Refuse the live datadir -- labs must use a disposable -datadir
# unless ZERO_PERF_ALLOW_LIVE_DATADIR=1.
refuse_live_datadir DATADIR "$DATADIR"

mkdir -p "$OUT_DIR"
SEQ_LOG="$OUT_DIR/sequence.log"

log() {
    echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') $*" | tee -a "$SEQ_LOG"
}

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

height_of() {
    "$ZERO_CLI" -datadir="$DATADIR" -rpcport=$RPCPORT getblockcount 2>/dev/null
}

# --- launch zerod ---
log "launching zerod -reindex on $DATADIR"
"$ZEROD" -datadir="$DATADIR" -reindex -connect=0 -listen=0 -rpcport=$RPCPORT \
    >"$OUT_DIR/zerod_stdout.log" 2>&1 &
PID=$!
log "zerod pid=$PID"

until h=$(height_of) && [[ "$h" =~ ^[0-9]+$ ]] && [ "$h" -gt 0 ]; do
    if ! kill -0 "$PID" 2>/dev/null; then
        log "ERROR: zerod exited before RPC came up"
        exit 1
    fi
    sleep 3
done
log "RPC up, starting height=$h"

capture_num=0
start_epoch=$(date +%s)

while kill -0 "$PID" 2>/dev/null; do
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

    if ! kill -0 "$PID" 2>/dev/null; then
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
        while [ "$sleep_for" -gt 0 ] && kill -0 "$PID" 2>/dev/null; do
            chunk=$(( sleep_for < 10 ? sleep_for : 10 ))
            sleep "$chunk"
            sleep_for=$(( sleep_for - chunk ))
        done
    fi
done

if kill -0 "$PID" 2>/dev/null; then
    log "sequence stopped, zerod (pid=$PID) still running -- leave it or kill -TERM $PID"
else
    log "zerod (pid=$PID) has exited -- reindex presumably complete or crashed, check zerod_stdout.log"
fi

log "sequence finished, $capture_num capture(s) in $OUT_DIR"
