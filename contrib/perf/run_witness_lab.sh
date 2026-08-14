#!/bin/bash
# Witness lab: INV-DIRTY-CONT (one-shot decision data) and BENCH-WIT-REBUILD.
# Disposable scratch only. Reusable automation; each mode is one restartable trial.
#
# Usage (repo root):
#   ZERO_PERF_WALLET_FILE=/path/to/fat/wallet.zero \
#     contrib/perf/run_witness_lab.sh dirty-cont
#   ZERO_PERF_WALLET_FILE=/path/to/fat/wallet.zero \
#     contrib/perf/run_witness_lab.sh rebuild
#   ZERO_PERF_WALLET_FILE=... contrib/perf/run_witness_lab.sh rebuild-noteidx
#   ZERO_PERF_WALLET_FILE=... ZERO_PERF_TIP_TEMPLATE=reindex-profile/fulltip-812-datadir \
#     contrib/perf/run_witness_lab.sh tip-rebuild-note
#   ZERO_PERF_WALLET_FILE=... contrib/perf/run_witness_lab.sh rescan-noteidx
#   ZERO_PERF_WALLET_FILE=... contrib/perf/run_witness_lab.sh catchup-noteidx
#
# Env:
#   ZERO_PERF_WALLET_FILE   required
#   ZERO_PERF_SRC_DATADIR   blocks source (default Application Support/zero)
#   ZERO_PERF_CHAIN_SNAP    tiny|short|full (default tiny) -- rebuild*/rescan/catchup
#   ZERO_PERF_TIP_TEMPLATE  tip-rebuild* / tip-catchup*: datadir with blocks+chainstate at tip
#   TARGET_HEIGHT           dirty-cont stop height (default 8000)
#   ZERO_PERF_RPCPORT       default 23956
#   ZERO_PERF_SCRATCH_DATADIR  default reindex-profile/witness-lab-datadir
#
# Automation vs one-time:
#   dirty-cont -- one-time decision sample is enough (continue_rate); re-run only
#     if stock per-block Verify stays a product default. Not a CI gate.
#   rebuild*   -- full -reindex + ibd-defer (L wall on full tip).
#   tip-rebuild* -- copy tip template, inject wallet, -walletwitness=rebuild
#     without -reindex (preferred post-Sap walk measure). One trial at a time.
#   rescan* / catchup* -- known-state chain + injected wallet; see run_cycle_campaign.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MODE="${1:-}"
ZEROD="${ZEROD:-$REPO_ROOT/src/zerod}"
ZERO_CLI="${ZERO_CLI:-$REPO_ROOT/src/zero-cli}"
SRC_DATADIR="${ZERO_PERF_SRC_DATADIR:-$HOME/Library/Application Support/zero}"
SCRATCH="${ZERO_PERF_SCRATCH_DATADIR:-$REPO_ROOT/reindex-profile/witness-lab-datadir}"
OUT_ROOT="${ZERO_PERF_OUT_DIR:-$REPO_ROOT/test-logs}"
WALLET_FILE="${ZERO_PERF_WALLET_FILE:-}"
SNAP="${ZERO_PERF_CHAIN_SNAP:-tiny}"
TIP_TEMPLATE="${ZERO_PERF_TIP_TEMPLATE:-$REPO_ROOT/reindex-profile/fulltip-812-datadir}"
TARGET_HEIGHT="${TARGET_HEIGHT:-8000}"
RPCPORT="${ZERO_PERF_RPCPORT:-23956}"

default_zero="$HOME/Library/Application Support/zero"
refuse_default() {
  local d
  d="$(cd "$1" 2>/dev/null && pwd -P)" || d="$1"
  case "$d" in
    "$default_zero"|"$HOME/Library/Application Support/Zero"|"$HOME/.zero")
      echo "ERROR: scratch must not be default user datadir: $d" >&2
      exit 1
      ;;
  esac
}
refuse_default "$SCRATCH"

if [ -z "$MODE" ]; then
  echo "Usage: $0 dirty-cont|rebuild|rebuild-noteidx|tip-rebuild|tip-rebuild-note" >&2
  exit 1
fi
if [ -z "$WALLET_FILE" ] || [ ! -f "$WALLET_FILE" ]; then
  echo "ERROR: set ZERO_PERF_WALLET_FILE" >&2
  exit 1
fi
if [ ! -x "$ZEROD" ]; then
  echo "ERROR: missing $ZEROD (rebuild after NOTEIDX walk changes)" >&2
  exit 1
fi

RUN_ID="witness-lab-${MODE}-$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="$OUT_ROOT/$RUN_ID"
mkdir -p "$OUT_DIR"
DRIVER="$OUT_DIR/driver.log"
SUMMARY="$OUT_DIR/SUMMARY.txt"
log() { echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') $*" | tee -a "$DRIVER"; }

cli() { "$ZERO_CLI" -datadir="$SCRATCH" -rpcport="$RPCPORT" -rpcuser=rt -rpcpassword=rt "$@"; }

prepare_scratch() {
  rm -rf "$SCRATCH"
  mkdir -p "$SCRATCH"
  case "$SNAP" in
    tiny)
      tar -xzf "$SRC_DATADIR/chainblocks-tiny.tgz" -C "$SCRATCH"
      ;;
    short)
      tar -xzf "$SRC_DATADIR/chainblocks-short.tgz" -C "$SCRATCH"
      ;;
    full)
      rsync -a --exclude='chainstate' --exclude='wallet.zero' --exclude='wallet.zero*' \
        --exclude='debug*.log' --exclude='.lock' \
        "$SRC_DATADIR/" "$SCRATCH/"
      rm -rf "$SCRATCH/chainstate"
      ;;
    *)
      echo "ERROR: unknown SNAP=$SNAP" >&2
      exit 1
      ;;
  esac
  cp -p "$WALLET_FILE" "$SCRATCH/wallet.zero"
  {
    echo "listen=0"
    echo "maxconnections=0"
    echo "server=1"
    echo "rpcuser=rt"
    echo "rpcpassword=rt"
    echo "rpcport=$RPCPORT"
    # Match Insight-built blocks/index (tip templates / full rsync).
    echo "experimentalfeatures=1"
    echo "insightexplorer=1"
  } > "$SCRATCH/zero.conf"
  log "scratch ready SNAP=$SNAP wallet=$(basename "$WALLET_FILE")"
}

prepare_tip_scratch() {
  # Copy a verified tip template (blocks+chainstate+index); inject wallet; no -reindex.
  if [ ! -d "$TIP_TEMPLATE/blocks" ] || [ ! -d "$TIP_TEMPLATE/chainstate" ]; then
    echo "ERROR: ZERO_PERF_TIP_TEMPLATE missing blocks/ or chainstate/: $TIP_TEMPLATE" >&2
    exit 1
  fi
  refuse_default "$TIP_TEMPLATE"
  if [ "$(cd "$TIP_TEMPLATE" 2>/dev/null && pwd -P)" = "$(cd "$SCRATCH" 2>/dev/null && pwd -P)" ]; then
    echo "ERROR: scratch must differ from TIP_TEMPLATE (refusing to clobber template)" >&2
    exit 1
  fi
  log "prepare tip template=$TIP_TEMPLATE -> scratch"
  rm -rf "$SCRATCH"
  mkdir -p "$SCRATCH"
  rsync -a --delete \
    --exclude='wallet.zero' --exclude='wallet.zero*' \
    --exclude='debug*.log' --exclude='.lock' --exclude='zero.conf' \
    "$TIP_TEMPLATE/" "$SCRATCH/"
  cp -p "$WALLET_FILE" "$SCRATCH/wallet.zero"
  {
    echo "listen=0"
    echo "maxconnections=0"
    echo "server=1"
    echo "rpcuser=rt"
    echo "rpcpassword=rt"
    echo "rpcport=$RPCPORT"
    echo "experimentalfeatures=1"
    echo "insightexplorer=1"
  } > "$SCRATCH/zero.conf"
  log "tip scratch ready wallet=$(basename "$WALLET_FILE") bytes=$(stat -f%z "$SCRATCH/wallet.zero" 2>/dev/null || stat -c%s "$SCRATCH/wallet.zero")"
}

stop_node() {
  local pid="$1"
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    cli stop 2>/dev/null || true
    for _ in $(seq 1 60); do
      kill -0 "$pid" 2>/dev/null || break
      sleep 1
    done
    kill -TERM "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
  fi
}

run_dirty_cont() {
  prepare_scratch
  local extra=(-reindex -connect=0 -listen=0 -rpcport="$RPCPORT"
    -walletwitnessnote=1 -walletwitnessstats=1)
  log "START dirty-cont TARGET_HEIGHT=$TARGET_HEIGHT extras=${extra[*]}"
  "$ZEROD" -datadir="$SCRATCH" "${extra[@]}" >"$OUT_DIR/zerod.stdout" 2>"$OUT_DIR/zerod.stderr" &
  local pid=$!
  echo "$pid" >"$OUT_DIR/zerod.pid"
  # wait RPC
  for _ in $(seq 1 120); do
    cli getblockcount >/dev/null 2>&1 && break
    sleep 2
  done
  local h=0
  while true; do
    h=$(cli getblockcount 2>/dev/null || echo 0)
    log "height=$h"
    if [ "$h" -ge "$TARGET_HEIGHT" ] 2>/dev/null; then
      break
    fi
    sleep 15
  done
  stop_node "$pid"
  # Aggregate WitnessStats lines
  {
    echo "mode=dirty-cont target=$TARGET_HEIGHT final_height=$h"
    echo "NOTE: stock per-block Verify + NOTEIDX + stats (no ibd-defer)"
    echo "--- last 20 WitnessStats ---"
    grep 'WitnessStats ' "$SCRATCH/debug.log" 2>/dev/null | tail -20 || true
    echo "--- early_continue / full_work totals (sum of logged fields) ---"
    python3 - <<'PY'
import re, pathlib, os
p = pathlib.Path(os.environ.get("SCRATCH_DEBUG", ""))
# path passed below
PY
  } >"$SUMMARY" || true
  SCRATCH_DEBUG="$SCRATCH/debug.log" python3 - <<'PY' | tee -a "$SUMMARY"
import re, os, pathlib
log = pathlib.Path(os.environ["SCRATCH_DEBUG"])
visits = early = full = 0
n = 0
pat = re.compile(r"note_visits=(\d+) early_continue=(\d+) full_work=(\d+)")
if log.is_file():
    for line in log.open(errors="replace"):
        m = pat.search(line)
        if not m:
            continue
        n += 1
        visits += int(m.group(1))
        early += int(m.group(2))
        full += int(m.group(3))
print("witness_stats_lines=%d" % n)
print("sum_note_visits=%d sum_early_continue=%d sum_full_work=%d" % (visits, early, full))
if visits:
    print("early_continue_rate=%.4f" % (early / float(visits)))
    print("full_work_rate=%.4f" % (full / float(visits)))
elif n == 0:
    print("early_continue_rate=NA (no WitnessStats lines)")
else:
    print("early_continue_rate=NA (note_visits=0 -- typically pre-Sapling tip; notes not yet in chain)")
print("DIRTY: park if shipping ibd-defer; else re-run CONT on post-Sapling TARGET_HEIGHT.")
PY
  log "done OUT_DIR=$OUT_DIR SUMMARY=$SUMMARY"
  cat "$SUMMARY"
}

wait_rebuild_done() {
  local pid="$1"
  local last=-1 stable=0
  while kill -0 "$pid" 2>/dev/null; do
    local h
    h=$(cli getblockcount 2>/dev/null || echo 0)
    if [ "$h" = "$last" ] && [ "$h" -gt 0 ]; then
      stable=$((stable + 1))
    else
      stable=0
      last=$h
    fi
    log "height=$h stable_ticks=$stable"
    if grep -q "BuildWitnessCache height-walk done" "$SCRATCH/debug.log" 2>/dev/null; then
      log "detected height-walk done"
      break
    fi
    if grep -q "RebuildWitnessCacheForChainTip" "$SCRATCH/debug.log" 2>/dev/null \
      && grep -q "height-walk done" "$SCRATCH/debug.log" 2>/dev/null; then
      log "detected tip rebuild walk done"
      break
    fi
    # Allowlisted status should work under -33; walletinfo should not until done.
    if [ "$stable" -ge 8 ]; then
      if cli getwalletinfo >/dev/null 2>&1; then
        log "height stable; getwalletinfo ok (rebuild finished or skipped)"
        break
      fi
    fi
    sleep 15
  done
}

run_rebuild() {
  local noteidx="$1"
  prepare_scratch
  local extra=(-reindex -connect=0 -listen=0 -rpcport="$RPCPORT" -walletwitness=ibd-defer)
  if [ "$noteidx" = "1" ]; then
    extra+=(-walletwitnessnote=1)
  fi
  log "START rebuild noteidx=$noteidx extras=${extra[*]}"
  local t0
  t0=$(date +%s)
  "$ZEROD" -datadir="$SCRATCH" "${extra[@]}" >"$OUT_DIR/zerod.stdout" 2>"$OUT_DIR/zerod.stderr" &
  local pid=$!
  echo "$pid" >"$OUT_DIR/zerod.pid"
  for _ in $(seq 1 180); do
    cli getblockcount >/dev/null 2>&1 && break
    sleep 2
  done
  wait_rebuild_done "$pid"
  local t1 elapsed
  t1=$(date +%s)
  elapsed=$((t1 - t0))
  stop_node "$pid"
  {
    echo "mode=rebuild noteidx=$noteidx wall_s=$elapsed"
    echo "--- height-walk log lines ---"
    grep -E "BuildWitnessCache height-walk|walletwitness=.*RebuildWitnessCache" "$SCRATCH/debug.log" 2>/dev/null | tail -40 || true
    echo "--- extract elapsed_ms from height-walk done ---"
    grep "BuildWitnessCache height-walk done" "$SCRATCH/debug.log" 2>/dev/null | tail -5 || true
  } | tee "$SUMMARY"
  log "done OUT_DIR=$OUT_DIR"
}

run_tip_rebuild() {
  local noteidx="$1"
  prepare_tip_scratch
  local extra=(-connect=0 -listen=0 -rpcport="$RPCPORT" -walletwitness=rebuild)
  if [ "$noteidx" = "1" ]; then
    extra+=(-walletwitnessnote=1)
  fi
  log "START tip-rebuild noteidx=$noteidx extras=${extra[*]}"
  # Status allowlist smoke under -33 (best-effort; rebuild may finish fast)
  local t0
  t0=$(date +%s)
  "$ZEROD" -datadir="$SCRATCH" "${extra[@]}" >"$OUT_DIR/zerod.stdout" 2>"$OUT_DIR/zerod.stderr" &
  local pid=$!
  echo "$pid" >"$OUT_DIR/zerod.pid"
  for _ in $(seq 1 180); do
    cli getblockcount >/dev/null 2>&1 && break
    sleep 2
  done
  # Early status RPC check (allowlist) -- may already be past -33.
  if cli getblockcount >/dev/null 2>&1; then
    log "status_rpc getblockcount=ok"
  fi
  if cli getblockchaininfo >/dev/null 2>&1; then
    log "status_rpc getblockchaininfo=ok"
  fi
  wait_rebuild_done "$pid"
  local t1 elapsed
  t1=$(date +%s)
  elapsed=$((t1 - t0))
  local tip wi
  tip=$(cli getblockcount 2>/dev/null || echo NA)
  wi=$(cli getwalletinfo 2>/dev/null || echo '{}')
  stop_node "$pid"
  {
    echo "mode=tip-rebuild noteidx=$noteidx wall_s=$elapsed tip=$tip"
    echo "walletinfo=$wi"
    echo "--- height-walk log lines ---"
    grep -E "BuildWitnessCache height-walk|walletwitness=.*RebuildWitnessCache|Reindexing block file" "$SCRATCH/debug.log" 2>/dev/null | tail -60 || true
    echo "--- extract elapsed_ms from height-walk done ---"
    grep "BuildWitnessCache height-walk done" "$SCRATCH/debug.log" 2>/dev/null | tail -5 || true
    if grep -q "Reindexing block file" "$SCRATCH/debug.log" 2>/dev/null; then
      echo "WARN: unexpected reindex started (insight flags / template mismatch?)"
    fi
  } | tee "$SUMMARY"
  log "done OUT_DIR=$OUT_DIR"
}

wait_done_loading() {
  local pid="$1"
  while kill -0 "$pid" 2>/dev/null; do
    if grep -q "Done loading" "$SCRATCH/debug.log" 2>/dev/null; then
      log "detected Done loading"
      sleep 2
      return 0
    fi
    local h
    h=$(cli getblockcount 2>/dev/null || echo 0)
    log "waiting Done loading height=$h"
    sleep 15
  done
  return 0
}

write_scratch_conf() {
  local insight="${1:-0}"
  {
    echo "listen=0"
    echo "maxconnections=0"
    echo "server=1"
    echo "rpcuser=rt"
    echo "rpcpassword=rt"
    echo "rpcport=$RPCPORT"
    if [ "$insight" = "1" ]; then
      echo "experimentalfeatures=1"
      echo "insightexplorer=1"
    fi
  } > "$SCRATCH/zero.conf"
}

run_rescan() {
  local noteidx="$1"
  prepare_scratch
  write_scratch_conf 0
  if [ ! -d "$SCRATCH/chainstate" ]; then
    echo "ERROR: rescan needs chainstate in the snap (got SNAP=$SNAP)" >&2
    exit 1
  fi
  local extra=(-rescan -connect=0 -listen=0 -rpcport="$RPCPORT")
  if [ "$noteidx" = "1" ]; then
    extra+=(-walletwitnessnote=1)
  fi
  log "START rescan noteidx=$noteidx extras=${extra[*]}"
  local t0
  t0=$(date +%s)
  "$ZEROD" -datadir="$SCRATCH" "${extra[@]}" >"$OUT_DIR/zerod.stdout" 2>"$OUT_DIR/zerod.stderr" &
  local pid=$!
  echo "$pid" >"$OUT_DIR/zerod.pid"
  for _ in $(seq 1 180); do
    cli getblockcount >/dev/null 2>&1 && break
    sleep 2
  done
  wait_done_loading "$pid"
  wait_rebuild_done "$pid"
  local t1 elapsed tip
  t1=$(date +%s)
  elapsed=$((t1 - t0))
  tip=$(cli getblockcount 2>/dev/null || echo NA)
  stop_node "$pid"
  {
    echo "mode=rescan noteidx=$noteidx wall_s=$elapsed tip=$tip"
    echo "--- rescan / height-walk ---"
    grep -E "Rescanning last| rescan +[0-9]+ms|BuildWitnessCache height-walk|Done loading" "$SCRATCH/debug.log" 2>/dev/null | tail -40 || true
  } | tee "$SUMMARY"
  log "done OUT_DIR=$OUT_DIR"
}

run_catchup() {
  local noteidx="$1"
  local use_tip="${2:-0}"
  if [ "$use_tip" = "1" ]; then
    prepare_tip_scratch
  else
    prepare_scratch
    write_scratch_conf 0
  fi
  if [ ! -d "$SCRATCH/chainstate" ]; then
    echo "ERROR: sync/catchup needs chainstate (SNAP=$SNAP use_tip=$use_tip)" >&2
    exit 1
  fi
  local extra=(-connect=0 -listen=0 -rpcport="$RPCPORT")
  if [ "$noteidx" = "1" ]; then
    extra+=(-walletwitnessnote=1)
  fi
  log "START catchup noteidx=$noteidx use_tip=$use_tip extras=${extra[*]}"
  local t0
  t0=$(date +%s)
  "$ZEROD" -datadir="$SCRATCH" "${extra[@]}" >"$OUT_DIR/zerod.stdout" 2>"$OUT_DIR/zerod.stderr" &
  local pid=$!
  echo "$pid" >"$OUT_DIR/zerod.pid"
  for _ in $(seq 1 180); do
    cli getblockcount >/dev/null 2>&1 && break
    sleep 2
  done
  wait_done_loading "$pid"
  local t1 elapsed tip
  t1=$(date +%s)
  elapsed=$((t1 - t0))
  tip=$(cli getblockcount 2>/dev/null || echo NA)
  stop_node "$pid"
  {
    echo "mode=catchup noteidx=$noteidx wall_s=$elapsed tip=$tip"
    echo "--- Done loading / height-walk ---"
    grep -E "Done loading|BuildWitnessCache height-walk|Rescanning last" "$SCRATCH/debug.log" 2>/dev/null | tail -40 || true
  } | tee "$SUMMARY"
  log "done OUT_DIR=$OUT_DIR"
}

case "$MODE" in
  dirty-cont) run_dirty_cont ;;
  rebuild) run_rebuild 0 ;;
  rebuild-noteidx) run_rebuild 1 ;;
  tip-rebuild) run_tip_rebuild 0 ;;
  tip-rebuild-note) run_tip_rebuild 1 ;;
  rescan) run_rescan 0 ;;
  rescan-noteidx) run_rescan 1 ;;
  catchup) run_catchup 0 0 ;;
  catchup-noteidx) run_catchup 1 0 ;;
  tip-catchup) run_catchup 0 1 ;;
  tip-catchup-note) run_catchup 1 1 ;;
  *)
    echo "Usage: $0 dirty-cont|rebuild|rebuild-noteidx|tip-rebuild|tip-rebuild-note|rescan|rescan-noteidx|catchup|catchup-noteidx|tip-catchup|tip-catchup-note" >&2
    exit 1
    ;;
esac
