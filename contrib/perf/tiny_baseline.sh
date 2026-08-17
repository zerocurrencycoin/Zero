#!/bin/bash
# Tiny-snap reindex baseline: disposable LAB datadir + extract_measures.
# Never touches the default Application Support/zero tree except as a
# read-only archive source.
#
# Usage (from repo root):
#   contrib/perf/tiny_baseline.sh
#   LAB=/tmp/my-lab ZERO_PERF_ARCHIVE_DIR="..." contrib/perf/tiny_baseline.sh short
#
# Args: [tiny|short]  (default tiny)

set -euo pipefail

SNAP="${1:-tiny}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
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

LAB="${LAB:-${TMPDIR:-/tmp}/zero-lab-${SNAP}-baseline-$$}"
default_zero="$HOME/Library/Application Support/zero"
default_zero_alt="$HOME/Library/Application Support/Zero"
lab_res="$(cd "$LAB" 2>/dev/null && pwd -P || echo "$LAB")"
case "$lab_res" in
  "$default_zero"|"$default_zero_alt"|"$HOME/.zero")
    echo "ERROR: LAB must not be the default user datadir: $lab_res" >&2
    exit 1
    ;;
esac

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
mkdir -p "$OUT_DIR" "$LAB"
echo "LAB=$LAB (disposable)"
echo "RUN_ID=$RUN_ID"

# Fresh unpack into LAB only
rm -rf "$LAB"/*
tar -xzf "$ARCHIVE_PATH" -C "$LAB"

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

echo "artifacts:"
echo "  $JSONL"
echo "  $CSV"
echo "  $MD"
echo "LAB left at $LAB (delete when done)"
