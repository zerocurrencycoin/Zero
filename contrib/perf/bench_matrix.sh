#!/bin/bash
# Repeated-trial A/B benchmark for ZERO_FDCACHE's -perfbufsize (and,
# incidentally, -perffdcache) against -reindex and, if a bootstrap.dat is
# provided, bootstrap.dat import. Fixes the two problems in an earlier
# one-off comparison: (a) different runs measured different height ranges
# (throughput varies by height, so that's not a fair comparison), and
# (b) one trial per condition gives no noise estimate at all.
#
# Design:
#   - Every trial resets to a freshly-rsynced scratch datadir (source from
#     ZERO_PERF_SRC_DATADIR or ~/Library/Application Support/zero/ is only ever
#     read, never modified or deleted -- all resets act on the local scratch
#     copy only; scratch defaults to reindex-profile/datadir and must not be
#     the default user datadir). The reset differs by mode (see
#     reset_scratch_datadir): reindex keeps the source's
#     blocks/ (it rescans them) and excludes only chainstate; bootstrap
#     excludes blocks/ too, since -loadblock needs a genuinely empty chain to
#     import into, not one whose blocks/index already covers the full source
#     chain (that produces a long, misleading RPC "Loading block index..."
#     state that is index reconciliation, not the import being measured).
#   - Every trial warms up to the same start height (unmeasured), then
#     measures the same fixed height range (not a fixed wall-clock window --
#     avoids partial-block boundary effects and lets throughput be compared
#     directly as blocks/exact-elapsed-seconds).
#   - Elapsed time for the measured range is read from debug.log's UpdateTip
#     timestamps (exact, per Perf.md §6), not RPC-polling wall clock.
#   - N repeated trials per condition, so mean/stdev/CI can be computed
#     instead of trusting a single sample.
#
# Usage:
#   contrib/perf/bench_matrix.sh <out_dir> [warmup_height] [measure_blocks] [n_trials] [bootstrap_dat_path]
#
# Example:
#   contrib/perf/bench_matrix.sh reindex-profile/bench 50000 300000 4
#   contrib/perf/bench_matrix.sh reindex-profile/bench 50000 300000 4 /path/to/bootstrap.dat
#
# Conditions run per mode (reindex, and bootstrap if a .dat path is given):
#   default buffer  (-perffdcache=1, no -perfbufsize)
#   1MB buffer      (-perffdcache=1 -perfbufsize=1048576)
#
# Output: <out_dir>/results.tsv (one row per trial) plus per-trial debug.log
# copies and driver logs under <out_dir>/<mode>_<condition>_trial<N>/.

set -u

OUT_DIR="${1:?usage: bench_matrix.sh <out_dir> [warmup_height] [measure_blocks] [n_trials] [bootstrap_dat_path]}"
WARMUP_HEIGHT="${2:-50000}"
MEASURE_BLOCKS="${3:-300000}"
N_TRIALS="${4:-4}"
BOOTSTRAP_DAT="${5:-}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ZEROD="$REPO_ROOT/src/zerod"
ZERO_CLI="$REPO_ROOT/src/zero-cli"
# Read-only source for rsync resets. Override with ZERO_PERF_SRC_DATADIR.
# Must NOT be the scratch dir; never wipe or -reindex this path in place.
SRC_DATADIR="${ZERO_PERF_SRC_DATADIR:-$HOME/Library/Application Support/zero}"
SCRATCH_DATADIR="${ZERO_PERF_SCRATCH_DATADIR:-$REPO_ROOT/reindex-profile/datadir}"
RPCPORT=23921   # distinct from capture_sequence.sh's 23920, in case both run near each other

default_datadir_mac="$HOME/Library/Application Support/zero"
default_datadir_mac_alt="$HOME/Library/Application Support/Zero"
refuse_default_datadir() {
    local label="$1" d
    d="$(cd "$2" 2>/dev/null && pwd -P)" || d="$2"
    case "$d" in
        "$default_datadir_mac"|"$default_datadir_mac_alt"|"$HOME/.zero")
            echo "ERROR: $label must not be the default user datadir: $d" >&2
            echo "Set ZERO_PERF_SCRATCH_DATADIR to a disposable path under the repo or \$TMPDIR." >&2
            exit 1
            ;;
    esac
}
refuse_default_datadir "scratch datadir" "$SCRATCH_DATADIR"
if [ "$(cd "$SRC_DATADIR" 2>/dev/null && pwd -P)" = "$(cd "$SCRATCH_DATADIR" 2>/dev/null && pwd -P)" ]; then
    echo "ERROR: SRC_DATADIR and SCRATCH_DATADIR must differ (source is read-only)." >&2
    exit 1
fi

mkdir -p "$OUT_DIR"
RESULTS_TSV="$OUT_DIR/results.tsv"
DRIVER_LOG="$OUT_DIR/driver.log"

log() {
    echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') $*" | tee -a "$DRIVER_LOG"
}

if [ ! -f "$RESULTS_TSV" ]; then
    printf "mode\tcondition\ttrial\twarmup_height\tend_height\tblocks\telapsed_s\tblocks_per_sec\n" > "$RESULTS_TSV"
fi

height_of() {
    "$ZERO_CLI" -datadir="$SCRATCH_DATADIR" -rpcport=$RPCPORT getblockcount 2>/dev/null
}

# SIGTERM, briefly wait, then SIGKILL if still alive. Needed because zerod's
# shutdown path relies on RPC (not always up) or an interruption_point() a
# stuck thread may not reach for a long time (e.g. LoadBlockIndexDB's
# per-block accounting loop, main.cpp -- see the comment above run_trial's
# wait loops). This script always rm -rf's the datadir before the next
# trial anyway, so there's no data-preservation reason to wait indefinitely
# for a graceful exit once a bounded wait has already been exceeded.
kill_pid_hard() {
    local pid="$1"
    kill -TERM "$pid" 2>/dev/null
    for i in $(seq 1 10); do
        kill -0 "$pid" 2>/dev/null || return 0
        sleep 2
    done
    if kill -0 "$pid" 2>/dev/null; then
        log "pid=$pid did not respond to SIGTERM after 20s, sending SIGKILL"
        kill -9 "$pid" 2>/dev/null
        for i in $(seq 1 10); do
            kill -0 "$pid" 2>/dev/null || return 0
            sleep 1
        done
        log "WARNING: pid=$pid still alive after SIGKILL -- unexpected, check manually"
    fi
}

# $1: "reindex" or "bootstrap". The two modes need genuinely different
# starting states, not just different zerod flags:
#   - reindex rescans existing blk*.dat/rev*.dat and rebuilds chainstate from
#     them, so the source's blocks/ (raw files + its LevelDB index) is
#     exactly what it needs; only chainstate is excluded (rebuilt fresh).
#   - bootstrap (-loadblock) imports a separate pre-staged file into what
#     should be an empty chain. Reusing the source's blocks/ (which, on a
#     fully-synced datadir, includes an index already covering the whole
#     chain) makes zerod reconcile -loadblock's import against a pre-existing
#     multi-million-block index instead of starting clean -- confirmed via
#     debug.log showing LoadBlockIndexDB finding "heights=...484412" before
#     RPC ever becomes ready, and a long, misleading "Loading block index..."
#     RPC state that is NOT the bootstrap import itself. So bootstrap mode
#     excludes blocks/ entirely (not just chainstate), same as chainstate:
#     both must be rebuilt fresh from the bootstrap.dat being tested.
reset_scratch_datadir() {
    local mode="$1"
    log "resetting scratch datadir for mode=$mode (source untouched: $SRC_DATADIR)"
    rm -rf "$SCRATCH_DATADIR"
    if [ "$mode" = "bootstrap" ]; then
        rsync -a --exclude='chainstate' --exclude='blocks' "$SRC_DATADIR" "$SCRATCH_DATADIR/"
        mkdir -p "$SCRATCH_DATADIR/blocks"
    else
        rsync -a --exclude='chainstate' "$SRC_DATADIR" "$SCRATCH_DATADIR/"
    fi
}

# Reads debug.log's UpdateTip timestamps to get the exact wall-clock elapsed
# time between the block at $1 first appearing and the block at $2 first
# appearing -- exact, not RPC-poll-interval-limited (Perf.md §6 method).
# Delegates to extract_measures.py so tip parsing stays in one place.
elapsed_between_heights() {
    local log_path="$1" h_start="$2" h_end="$3"
    python3 "$REPO_ROOT/contrib/perf/extract_measures.py" \
        --elapsed-heights "$log_path" "$h_start" "$h_end"
}

# Runs one trial: launch zerod with the given extra args (reindex or
# bootstrap import), wait for warmup height, then wait for
# warmup+measure_blocks, then record elapsed time and stop.
run_trial() {
    local mode="$1" condition="$2" trial="$3"; shift 3
    local extra_args=("$@")
    local trial_dir="$OUT_DIR/${mode}_${condition}_trial${trial}"
    mkdir -p "$trial_dir"

    reset_scratch_datadir "$mode"

    local target_end=$(( WARMUP_HEIGHT + MEASURE_BLOCKS ))
    log "trial start: mode=$mode condition=$condition trial=$trial warmup=$WARMUP_HEIGHT target_end=$target_end args=${extra_args[*]:-none}"

    "$ZEROD" -datadir="$SCRATCH_DATADIR" -connect=0 -listen=0 -rpcport=$RPCPORT \
        "${extra_args[@]}" > "$trial_dir/zerod_stdout.log" 2>&1 &
    local pid=$!
    log "zerod pid=$pid"

    # Bounded waits: LoadBlockIndexDB's per-block accounting loop (main.cpp,
    # the BOOST_FOREACH over vSortedByHeight building nChainWork/nChainTx/etc.)
    # has no interruption_point() inside it, only one right before the loop
    # starts -- so a zerod that ends up reconciling an unexpectedly large
    # pre-existing block index (e.g. a datadir-reset bug reusing a fully-
    # synced index) can become uninterruptible by both RPC stop (not up yet)
    # and SIGTERM (no interruption point reached) for as long as that loop
    # runs, which can be tens of minutes on a multi-million-block index. Each
    # wait below is capped so a misbehaving trial fails fast and gets
    # escalated to SIGKILL instead of hanging the whole matrix indefinitely.
    local max_wait_s=600  # 10 min: generous for RPC-up, still bounded
    local waited=0
    until h=$(height_of) && [[ "$h" =~ ^[0-9]+$ ]] && [ "$h" -ge 0 ]; do
        if ! kill -0 "$pid" 2>/dev/null; then
            log "ERROR: zerod exited before RPC came up (trial $trial)"
            return 1
        fi
        if [ "$waited" -ge "$max_wait_s" ]; then
            log "ERROR: RPC did not come up within ${max_wait_s}s (trial $trial) -- killing and failing this trial"
            kill_pid_hard "$pid"
            return 1
        fi
        sleep 2; waited=$((waited + 2))
    done

    # Warmup/measure waits scale with how many blocks they actually need to
    # cover -- a flat 600s (fine for a small pre-Sapling warmup, where
    # throughput is 800-1,100 blk/s per Perf.md §2) is too tight once
    # WARMUP_HEIGHT reaches into or past post-Sapling heights, where
    # throughput drops to ~240-290 blk/s. Floor of 600s preserves prior
    # behavior for small targets; 200 blk/s is a conservative floor below
    # every post-Sapling capture in Perf.md's table (237-1,103 blk/s).
    local warmup_wait_s=$(( WARMUP_HEIGHT / 200 + 600 ))
    waited=0
    until h=$(height_of) && [ "$h" -ge "$WARMUP_HEIGHT" ]; do
        if ! kill -0 "$pid" 2>/dev/null; then
            log "ERROR: zerod exited during warmup at height=$h (trial $trial) -- source data may not reach warmup height"
            cp "$SCRATCH_DATADIR/debug.log" "$trial_dir/debug.log.snapshot" 2>/dev/null
            return 1
        fi
        if [ "$waited" -ge "$warmup_wait_s" ]; then
            log "ERROR: warmup height not reached within ${warmup_wait_s}s (trial $trial, height=$h) -- killing and failing this trial"
            cp "$SCRATCH_DATADIR/debug.log" "$trial_dir/debug.log.snapshot" 2>/dev/null
            kill_pid_hard "$pid"
            return 1
        fi
        sleep 2; waited=$((waited + 2))
    done
    log "warmup reached (height=$h)"

    local measure_wait_s=$(( MEASURE_BLOCKS / 200 + 600 ))
    waited=0
    until h=$(height_of) && [ "$h" -ge "$target_end" ]; do
        if ! kill -0 "$pid" 2>/dev/null; then
            log "ERROR: zerod exited before target_end at height=$h (trial $trial) -- source data may not reach target height, or import finished early"
            cp "$SCRATCH_DATADIR/debug.log" "$trial_dir/debug.log.snapshot" 2>/dev/null
            return 1
        fi
        if [ "$waited" -ge "$measure_wait_s" ]; then
            log "ERROR: target_end not reached within ${measure_wait_s}s (trial $trial, height=$h) -- killing and failing this trial"
            cp "$SCRATCH_DATADIR/debug.log" "$trial_dir/debug.log.snapshot" 2>/dev/null
            kill_pid_hard "$pid"
            return 1
        fi
        sleep 2; waited=$((waited + 2))
    done
    log "target_end reached (height=$h)"

    cp "$SCRATCH_DATADIR/debug.log" "$trial_dir/debug.log.snapshot"
    grep "ReadFdCache:" "$SCRATCH_DATADIR/debug.log" | tail -3 > "$trial_dir/readfdcache_tail.log"

    "$ZERO_CLI" -datadir="$SCRATCH_DATADIR" -rpcport=$RPCPORT stop >/dev/null 2>&1
    for i in $(seq 1 20); do
        kill -0 "$pid" 2>/dev/null || break
        sleep 3
    done
    if kill -0 "$pid" 2>/dev/null; then
        log "WARNING: zerod (pid=$pid) did not exit cleanly after stop, escalating"
        kill_pid_hard "$pid"
    fi

    local elapsed=$(elapsed_between_heights "$trial_dir/debug.log.snapshot" "$WARMUP_HEIGHT" "$target_end")
    if [ "$elapsed" = "NA" ] || [ -z "$elapsed" ]; then
        log "WARNING: could not determine elapsed time for trial $trial (heights not found in log)"
        printf "%s\t%s\t%s\t%s\t%s\t%s\tNA\tNA\n" "$mode" "$condition" "$trial" "$WARMUP_HEIGHT" "$h" "$MEASURE_BLOCKS" >> "$RESULTS_TSV"
        return 1
    fi

    local bps
    bps=$(python3 -c "print(f'{$MEASURE_BLOCKS / $elapsed:.2f}')" 2>/dev/null || echo "NA")
    log "trial done: mode=$mode condition=$condition trial=$trial elapsed=${elapsed}s blocks_per_sec=$bps"
    printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" "$mode" "$condition" "$trial" "$WARMUP_HEIGHT" "$target_end" "$MEASURE_BLOCKS" "$elapsed" "$bps" >> "$RESULTS_TSV"
    return 0
}

log "=== bench_matrix starting: warmup=$WARMUP_HEIGHT measure_blocks=$MEASURE_BLOCKS n_trials=$N_TRIALS bootstrap_dat=${BOOTSTRAP_DAT:-none} ==="

# nofdcache is the true baseline -perffdcache is compared against -- every
# condition before this one (see Perf.md §3/§0 item 1) had -perffdcache=1 on
# unconditionally, so the buffer-size A/B could never actually isolate
# -perffdcache's own effect from -perfbufsize's. This condition omits
# -perffdcache entirely (defaults to off), giving a real 2x2-style isolation:
# nofdcache vs defaultbuf isolates -perffdcache; defaultbuf vs 1mbbuf isolates
# -perfbufsize with -perffdcache held fixed at on.
for trial in $(seq 1 "$N_TRIALS"); do
    run_trial "reindex" "nofdcache" "$trial" -reindex -mrclogevery=100000
done

for trial in $(seq 1 "$N_TRIALS"); do
    run_trial "reindex" "defaultbuf" "$trial" -reindex -perffdcache=1 -mrclogevery=100000
done

for trial in $(seq 1 "$N_TRIALS"); do
    run_trial "reindex" "1mbbuf" "$trial" -reindex -perffdcache=1 -perfbufsize=1048576 -mrclogevery=100000
done

if [ -n "$BOOTSTRAP_DAT" ] && [ -f "$BOOTSTRAP_DAT" ]; then
    for trial in $(seq 1 "$N_TRIALS"); do
        run_trial "bootstrap" "defaultbuf" "$trial" -loadblock="$BOOTSTRAP_DAT" -perffdcache=1 -mrclogevery=100000
    done
    for trial in $(seq 1 "$N_TRIALS"); do
        run_trial "bootstrap" "1mbbuf" "$trial" -loadblock="$BOOTSTRAP_DAT" -perffdcache=1 -perfbufsize=1048576 -mrclogevery=100000
    done
else
    log "no bootstrap_dat provided or file not found -- skipping bootstrap trials (reindex trials still valid and complete)"
fi

log "=== bench_matrix finished, results in $RESULTS_TSV ==="
