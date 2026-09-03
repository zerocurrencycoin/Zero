#!/usr/bin/env bash
# Tiny-snap reindex baseline: disposable LAB datadir + extract_measures.
# Never touches the default Application Support/zero tree except as a
# read-only archive source.
#
# Usage (from repo root):
#   contrib/perf/tiny_baseline.sh
#   LAB=/tmp/my-lab ZERO_PERF_ARCHIVE_DIR="..." contrib/perf/tiny_baseline.sh short
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
ZERO_HOME="${ZERO_PERF_ARCHIVE_DIR:-$HOME/Library/Application Support/zero}"
OUT_DIR="${ZERO_PERF_OUT_DIR:-$REPO_ROOT/test-logs}"
RPCPORT="${ZERO_PERF_RPCPORT:-23925}"

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
ARCHIVE_PATH="$ZERO_HOME/$ARCHIVE"
if [ ! -f "$ARCHIVE_PATH" ]; then
  echo "ERROR: missing archive $ARCHIVE_PATH" >&2
  exit 1
fi

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

# Ensure offline / no sticky reindex in conf if present
if [ -f "$LAB/zero.conf" ]; then
  # Drop sticky reindex= if present (one-shot CLI flag only)
  if grep -q '^reindex=' "$LAB/zero.conf" 2>/dev/null; then
    grep -v '^reindex=' "$LAB/zero.conf" > "$LAB/zero.conf.tmp" || true
    mv "$LAB/zero.conf.tmp" "$LAB/zero.conf"
  fi
fi

echo "starting -reindex (disablewallet, listen=0)..."
"$ZEROD" -datadir="$LAB" -disablewallet -reindex -listen=0 -maxconnections=0 \
  -connect=0 -rpcport="$RPCPORT" -daemon

cleanup() {
  "$ZERO_CLI" -datadir="$LAB" -rpcport="$RPCPORT" stop >/dev/null 2>&1 || true
}
trap cleanup EXIT

# Wait for tip
for i in $(seq 1 600); do
  h="$("$ZERO_CLI" -datadir="$LAB" -rpcport="$RPCPORT" getblockcount 2>/dev/null || true)"
  if [[ "$h" =~ ^[0-9]+$ ]] && [ "$h" -ge "$EXPECT_TIP" ]; then
    echo "tip reached height=$h"
    break
  fi
  if [ "$i" -eq 600 ]; then
    echo "ERROR: tip $EXPECT_TIP not reached (last height=$h)" >&2
    exit 1
  fi
  sleep 2
done

log "reindex finished; stopping node"
# Allow reindex finished line to flush
sleep 3
"$ZERO_CLI" -datadir="$LAB" -rpcport="$RPCPORT" stop >/dev/null 2>&1 || true
trap - EXIT
sleep 2

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
  # `if cmd; then` -- not `A && B || C`, which runs C even when A succeeds.
  if python3 "$REPO_ROOT/contrib/perf/recbench/recbench.py" \
    --record \
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
    --notes "snap=$SNAP" >/dev/null; then
    log "ledger row appended (campaign=$CAMPAIGN)"
  else
    warn "ledger append failed; artifacts are still in $OUT_DIR"
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
