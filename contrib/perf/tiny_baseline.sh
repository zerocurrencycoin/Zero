#!/usr/bin/env bash
# Tiny-snap reindex baseline: disposable LAB datadir + extract_measures.
# Never touches the default Application Support/zero tree except as a
# read-only archive source.
#
# Usage (from repo root):
#   contrib/perf/tiny_baseline.sh
#   LAB=/tmp/my-lab ZERO_PERF_ARCHIVE_DIR="..." contrib/perf/tiny_baseline.sh short
#
# Env: SAMPLE_UTIL=1 samples CPU, RSS and threads at every poll into
# <run>-util.tsv (footprint once, after the timed span); ZEROD_EXTRA_ARGS adds
# zerod flags, declared in the row's runtime (e.g. -debug=bench).
#
# Args: [tiny|short]  (default tiny)

export LC_ALL=C
set -euo pipefail

SNAP="${1:-tiny}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=/dev/null
. "$REPO_ROOT/contrib/perf/perflib.sh"
# shellcheck disable=SC1091
. "$REPO_ROOT/contrib/perf/datadir_guard.sh"
ZEROD="${ZEROD:-$REPO_ROOT/src/zerod}"
ZERO_CLI="${ZERO_CLI:-$REPO_ROOT/src/zero-cli}"
OUT_DIR="${ZERO_PERF_OUT_DIR:-$REPO_ROOT/test-logs}"
STORE_DIR="${ZERO_PERF_STORE_DIR:-$REPO_ROOT/reindex-profile/bench-summaries}"
RPCPORT="${ZERO_PERF_RPCPORT:-23925}"
# Poll pacing. Defaults chosen from M-LAB-POLL-COST: 5 s while far cuts polling
# overhead to ~4% of the span; 2 s near the target keeps detection latency
# bounded, since that latency is inside the measured span too.
# (poll_interval, perflib.sh; ZERO_PERF_POLL_FAR_S / _NEAR_S / _NEAR_BLOCKS).
SAMPLE_UTIL="${SAMPLE_UTIL:-0}"
ZEROD_EXTRA_ARGS="${ZEROD_EXTRA_ARGS:-}"

case "$SNAP" in
  tiny) ARCHIVE="chainblocks-tiny.tgz"; EXPECT_TIP=187417 ;;
  short) ARCHIVE="chainblocks-short.tgz"; EXPECT_TIP=245992 ;;
  *) echo "usage: $0 [tiny|short]" >&2; exit 1 ;;
esac

LAB="${LAB:-/tmp/zero-lab-${SNAP}-baseline-$$}"
refuse_live_datadir LAB "$LAB"

if [ ! -x "$ZEROD" ]; then
  echo "ERROR: missing $ZEROD" >&2
  exit 1
fi
ARCHIVE_PATH="$(snap_archive "$ARCHIVE")" || exit 1
# height_of and stop_node act on this node (perflib.sh).
# shellcheck disable=SC2034  # read by perflib.sh
NODE_DATADIR="$LAB"
# shellcheck disable=SC2034
NODE_RPCPORT="$RPCPORT"

RUN_ID="${SNAP}-$(date -u +%Y%m%dT%H%M%SZ)"
# Only OUT_DIR here: creating LAB first would make dispose_datadir always
# find an existing tree and set aside an empty one on every run.
mkdir -p "$OUT_DIR"

# Durable run log, keyed by RUN_ID like the artifacts. Without this the whole
# run existed only on stdout: a backgrounded or piped invocation kept the
# measures but lost every decision that produced them -- which datadir policy
# applied, what was unpacked, whether the ledger append succeeded.
# shellcheck disable=SC2034  # consumed by log() in perflib.sh
DRIVER_LOG="$OUT_DIR/${RUN_ID}-driver.log"
: > "$DRIVER_LOG"

log "START run_id=$RUN_ID snap=$SNAP campaign=${CAMPAIGN:-tiny-baseline}"
log "binary=$ZEROD ($("$ZEROD" --version 2>/dev/null | head -1))"
warn_if_busy || true   # records load in the driver log; does not block
log "LAB=$LAB (disposable) policy=${ZERO_PERF_DATADIR_POLICY:-aside}"
log "archive=$ARCHIVE_PATH"

# Fresh unpack into LAB only. dispose_datadir honours
# ZERO_PERF_DATADIR_POLICY and refuses a production datadir outright.
dispose_datadir "${LAB:?}" LAB
log "unpacking $ARCHIVE -> $LAB"
if ! tar -xzf "$ARCHIVE_PATH" -C "$LAB"; then
  die "unpack failed: $ARCHIVE_PATH"
fi
log "unpack complete"

# Standard lab config (lab_conf, perflib.sh). The tiny/short archives carry
# their own zero.conf with insightexplorer=1 and dbcache=512, which costs ~9%
# and quadruples spread (M-RX-TINY-20260930); it is replaced unless
# ZERO_PERF_ARCHIVE_CONF=1 asks for the historical setup.
lab_conf "$LAB" "$RPCPORT"

# Millisecond wall clock for the measured span (M-LAB-WALL-MS).
# extract_measures.py
# derives elapsed from debug.log timestamp prefixes, which carry whole seconds,
# so its wall_s quantises the rate to ~9.8 blk/s over this window
# (M-LAB-WALL-QUANTUM) and no A/B on it can resolve better than 0.7%. The
# launcher brackets the same span and can time it directly.
LAB_T0=$(now_ms)
echo "starting -reindex (disablewallet, listen=0)..."
ZARGS="-disablewallet -reindex -listen=0 -maxconnections=0 -connect=0 $ZEROD_EXTRA_ARGS"
# shellcheck disable=SC2086  # ZARGS is a flag list
"$ZEROD" -datadir="$LAB" $ZARGS -rpcport="$RPCPORT" -daemon

cleanup() { stop_node; }
trap cleanup EXIT

# Wait for tip
# Progress is appended every poll and flushed by the shell's own append, so a
# run that crashes or is killed still leaves the height/time series behind. A
# long trial that dies at 90% previously left nothing at all: the ledger row is
# written only at the end, and the driver log records decisions, not progress.
PROGRESS_TSV="$OUT_DIR/${RUN_ID}-progress.tsv"
printf "utc\telapsed_s\theight\n" > "$PROGRESS_TSV"
UTIL_TSV=""
if [ "$SAMPLE_UTIL" = "1" ]; then
  util_tsv_init "$OUT_DIR/${RUN_ID}-util.tsv"
fi
NODE_PID=""
for i in $(seq 1 600); do
  h="$(height_of)"
  [ -n "$NODE_PID" ] || NODE_PID="$(node_pid)"
  UTIL_FOOTPRINT=0 UTIL_QUIET=1 sample_util poll "$NODE_PID" "$h"
  if [[ "$h" =~ ^[0-9]+$ ]]; then
    printf "%s\t%s\t%s\n" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
      "$(elapsed_s "$LAB_T0")" "$h" >> "$PROGRESS_TSV"
  fi
  if [[ "$h" =~ ^[0-9]+$ ]] && [ "$h" -ge "$EXPECT_TIP" ]; then
    echo "tip reached height=$h"
    break
  fi
  if [ "$i" -eq 600 ]; then
    echo "ERROR: tip $EXPECT_TIP not reached (last height=$h)" >&2
    exit 1
  fi
  # Each poll costs ~212 ms inside the timed span (M-LAB-POLL-COST): sparse
  # while far from the target, tight near it, where it bounds detection.
  sleep "$(poll_interval "$h" "$EXPECT_TIP")"
done

LAB_WALL_MS=$(( $(now_ms) - LAB_T0 ))
log "reindex finished; stopping node (span ${LAB_WALL_MS} ms)"
sample_util tip "$NODE_PID" "$h"   # with footprint; outside the timed span
# Allow reindex finished line to flush
sleep 3
stop_node
trap - EXIT

JSONL="$OUT_DIR/${RUN_ID}.jsonl"
CSV="$OUT_DIR/measures_${RUN_ID}.csv"
MD="$OUT_DIR/measures_${RUN_ID}.md"

python3 "$REPO_ROOT/contrib/perf/extract_measures.py" \
  --datadir "$LAB" \
  --run-id "$RUN_ID" \
  --op-class reindex \
  --no-wallet \
  --env lab \
  --sample-tip 50 \
  --jsonl "$JSONL" \
  --csv "$CSV" \
  --md | tee "$MD"

# Append to the durable throughput ledger. CAMPAIGN has always been documented
# as this script's grouping key, but nothing consumed it: a lab run produced
# artifacts and no ledger row, so it could not be aggregated or compared.
CAMPAIGN="${CAMPAIGN:-tiny-baseline}"
LEDGER_VARS="$(python3 - "$CSV" <<'EOF'
import csv, sys
wall = hps = start = end = None
with open(sys.argv[1], newline="", encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        if r.get("op_class") != "reindex":
            continue
        if r.get("metric") == "wall_s":
            wall = float(r["value"])
        elif r.get("metric") == "height_per_s":
            hps = float(r["value"])
        if r.get("height_start") not in (None, "", "-"):
            start = int(r["height_start"])
        if r.get("height_end") not in (None, "", "-"):
            end = int(r["height_end"])
# Absent rather than fabricated: a partial run must not look like a full one.
if None in (wall, hps, start, end):
    sys.exit(1)
print("LR_START=%d LR_END=%d LR_BLOCKS=%d LR_WALL=%s LR_HPS=%s"
      % (start, end, end - start, wall, hps))
EOF
)" || LEDGER_VARS=""

if [ -n "$LEDGER_VARS" ]; then
  eval "$LEDGER_VARS"
  # Prefer the launcher's millisecond span over the log-derived whole-second
  # wall time. Both measure the same interval; only one can resolve better
  # than a second (M-LAB-WALL-SECONDS). Fall back if the timing did not run.
  if [ -n "${LAB_WALL_MS:-}" ] && [ "$LAB_WALL_MS" -gt 0 ] 2>/dev/null; then
    LR_WALL=$(elapsed_s 0 "$LAB_WALL_MS")
    LR_HPS=$(safe_div "$LR_BLOCKS" "$LR_WALL")
    log "elapsed from launcher: ${LR_WALL}s -> ${LR_HPS} blk/s (log-derived was ~whole seconds)"
  fi
  # record_trial (perflib.sh): runtime as the node ran it, checked against its
  # log; the archive identified by hash, since two archives called
  # chainblocks-tiny differ in blocks and in the zero.conf they carry.
  if record_trial "$LAB/debug.log" "$LAB/zero.conf" \
       "$ZARGS" "$ARCHIVE_PATH" "$UTIL_TSV" \
       --store-dir "$STORE_DIR" \
       --warmup-height "$LR_START" \
       --end-height "$LR_END" \
       --blocks "$LR_BLOCKS" \
       --elapsed-s "$LR_WALL" \
       --blocks-per-sec "$LR_HPS" \
       --campaign "$CAMPAIGN" \
       --run-id "$RUN_ID" \
       --mode reindex \
       --condition "${CONDITION:-stock}" \
       --trial "${TRIAL:-1}" \
       --binary "$ZEROD" \
       --workload "op=reindex" \
       --workload "snap=$SNAP" \
       --notes "snap=$SNAP"; then
    log "ledger row appended (campaign=$CAMPAIGN)"
  else
    warn "ledger row NOT appended; artifacts are still in $OUT_DIR"
  fi
else
  warn "no complete reindex measure found; ledger row NOT appended"
fi

log "extracting measures -> $OUT_DIR"

echo "artifacts:"
echo "  $JSONL"
echo "  $CSV"
echo "  $MD"
echo "  $DRIVER_LOG"
log "DONE run_id=$RUN_ID"
echo "LAB left at $LAB (delete when done)"
