#!/usr/bin/env bash
# BENCH-MINE: Equihash *solve* profile env (regtest / mainnet-template / neon-stock).
# Does not replace ConnectBlock rematch. Assign M-* via recbench when measured.
#
# Usage (repo root):
#   contrib/perf/mine_bench.sh regtest
#   contrib/perf/mine_bench.sh mainnet-template
#   contrib/perf/mine_bench.sh neon-probe   # test mode; not used in production
#
# Env:
#   ZERO_PERF_SCRATCH_DATADIR  disposable (refuses default Application Support/zero)
#   ZERO_PERF_RPCPORT         default 23950
#   MINE_BLOCKS               regtest blocks to generate (default 8)
#   MINE_TIMEOUT_S            per-mode wall cap (default 600)
#   SAMPLE_UTIL               1 (default) -> util.tsv
#   CAMPAIGN                  ledger campaign (default mine-equihash-<mode>)
#   ZERO_PERF_NEON_ZEROD      optional NEON-enabled zerod for A/B (else probe-only)

export LC_ALL=C
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck disable=SC1091
. "$REPO_ROOT/contrib/perf/datadir_guard.sh"
# shellcheck source=/dev/null
. "$REPO_ROOT/contrib/perf/perflib.sh"
ZEROD="${ZEROD:-$REPO_ROOT/src/zerod}"
ZERO_CLI="${ZERO_CLI:-$REPO_ROOT/src/zero-cli}"
MODE="${1:-regtest}"
SCRATCH="${ZERO_PERF_SCRATCH_DATADIR:-$REPO_ROOT/reindex-profile/mine-bench-datadir}"
OUT_ROOT="${ZERO_PERF_OUT_DIR:-$REPO_ROOT/test-logs}"
STORE_DIR="${ZERO_PERF_STORE_DIR:-$REPO_ROOT/reindex-profile/bench-summaries}"
RPCPORT="${ZERO_PERF_RPCPORT:-23950}"
MINE_BLOCKS="${MINE_BLOCKS:-8}"
MINE_TIMEOUT_S="${MINE_TIMEOUT_S:-600}"
SAMPLE_UTIL="${SAMPLE_UTIL:-1}"
CAMPAIGN="${CAMPAIGN:-mine-equihash-${MODE}}"
NEON_ZEROD="${ZERO_PERF_NEON_ZEROD:-}"

refuse_live_datadir SCRATCH "$SCRATCH"

if [ ! -x "$ZEROD" ]; then
  echo "ERROR: missing $ZEROD" >&2
  exit 1
fi

RUN_ID="mine-$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="$OUT_ROOT/$RUN_ID"
mkdir -p "$OUT_DIR" "$STORE_DIR"
DRIVER="$OUT_DIR/driver.log"
# log() comes from perflib.sh and tees to DRIVER_LOG.
# shellcheck disable=SC2034
DRIVER_LOG="$DRIVER"
RESULTS="$OUT_DIR/results.tsv"
# cli, stop_node, sample_util act on this node (perflib.sh).
# shellcheck disable=SC2034  # read by perflib.sh
NODE_DATADIR="$SCRATCH"
# shellcheck disable=SC2034
NODE_RPCPORT="$RPCPORT"

util_tsv_init "$OUT_DIR/util.tsv"
printf "mode\tblocks\telapsed_s\tblocks_per_sec\tms_per_block\tnotes\trun_id\n" > "$RESULTS"

probe_neon() {
  local report="$OUT_DIR/neon-probe.txt"
  {
    echo "arch=$(uname -m)"
    echo "sysctl_neon=$(sysctl -n hw.optional.neon 2>/dev/null || echo NA)"
    echo "stock_zerod=$ZEROD"
    echo "neon_zerod=${NEON_ZEROD:-UNSET}"
    if [ -n "$NEON_ZEROD" ] && [ -x "$NEON_ZEROD" ]; then
      echo "neon_zerod_present=1"
    else
      echo "neon_zerod_present=0"
      echo "note=NEON A/B needs ZERO_PERF_NEON_ZEROD pointing at a NEON-blake2b build; stock arm64 uses libsodium compress_ref."
    fi
    # libsodium symbols hint (ref vs accelerated)
    if command -v nm >/dev/null 2>&1; then
      echo "blake2b_compress_ref=$(nm "$ZEROD" 2>/dev/null | grep -c blake2b_compress_ref || true)"
      echo "blake2b_compress_neon=$(nm "$ZEROD" 2>/dev/null | grep -c blake2b_compress_neon || true)"
    fi
  } | tee "$report"
  log "neon probe written $report"
}

run_regtest() {
  stop_node
  dispose_datadir "$SCRATCH" SCRATCH
  lab_conf "$SCRATCH" "$RPCPORT" regtest=1 gen=0
  log "START mode=regtest blocks=$MINE_BLOCKS timeout=${MINE_TIMEOUT_S}s"
  "$ZEROD" -datadir="$SCRATCH" -daemon
  sleep 2
  local pid
  pid=$(node_pid)
  sample_util start "$pid" 0
  # fund + mine
  local t0 elapsed bps ms
  t0=$(now_ms)
  ZERO_PERF_CLI_TIMEOUT_S="$MINE_TIMEOUT_S" cli generate "$MINE_BLOCKS" >/dev/null
  elapsed=$(elapsed_s "$t0")   # ms resolution; whole seconds read 1 s for 8 blocks
  positive elapsed_s "$elapsed"
  local h
  h=$(cli getblockcount)
  sample_util after_generate "$pid" "$h"
  bps=$(safe_div "$MINE_BLOCKS" "$elapsed")
  ms=$(python3 -c "print(round(1000.0*$elapsed/float($MINE_BLOCKS), 3))")
  printf "regtest\t%s\t%s\t%s\t%s\t48,5-solve\t%s\n" \
    "$MINE_BLOCKS" "$elapsed" "$bps" "$ms" "$RUN_ID" >> "$RESULTS"
  log "result regtest blocks=$MINE_BLOCKS elapsed_s=$elapsed blk/s=$bps ms/blk=$ms"
  stop_node
  # The solver in effect changes the measurement without changing the binary;
  # unset in the conf means the compiled default. A regtest node logs under
  # its network subdirectory.
  local solver
  solver=$(grep -E '^equihashsolver=' "$SCRATCH/zero.conf" 2>/dev/null | tail -1 | cut -d= -f2 || true)
  if ! record_trial "$SCRATCH/regtest/debug.log" "$SCRATCH/zero.conf" "" "" "$UTIL_TSV" \
       --store-dir "$STORE_DIR" --campaign "$CAMPAIGN" --run-id "$RUN_ID" \
       --mode solve --condition regtest-48-5 --workload op=solve \
       --runtime "solver=${solver:-default}" \
       --warmup-height 0 --end-height "$h" --blocks "$MINE_BLOCKS" \
       --elapsed-s "$elapsed" --blocks-per-sec "$bps" \
       --binary "$ZEROD" --notes "ms_per_block=$ms"; then
    die "row not recorded (see above); results.tsv kept"
  fi
}

run_mainnet_template() {
  # Env + NEON probe for mainnet (192,7) solve lab. Unbounded solve is opt-in.
  mkdir -p "$OUT_DIR"
  log "START mode=mainnet-template (Equihash 192,7); verify ref ~0.252 ms/blk"
  probe_neon
  local notes="verify_bucket_ref_ms=0.252; set MINE_MAINNET_SOLVE=1 + Instruments on zcash-miner for timed solve"
  if [ "${MINE_MAINNET_SOLVE:-0}" = "1" ]; then
    notes="MINE_MAINNET_SOLVE=1: use isolated mainnet template under MINE_TIMEOUT_S; not auto-batched here"
    log "WARN: 192,7 solve is opt-in / Instruments; tools ready, no unbounded auto-solve"
  fi
  printf "mainnet-template\t0\t0\t0\t0\t%s\t%s\n" "$notes" "$RUN_ID" >> "$RESULTS"
  log "mainnet-template env ready; neon probe + results stub written"
}

case "$MODE" in
  regtest) run_regtest ;;
  mainnet-template) run_mainnet_template ;;
  neon-probe)
    mkdir -p "$OUT_DIR"
    probe_neon
    printf "neon-probe\t0\t0\t0\t0\tprobe-only\t%s\n" "$RUN_ID" >> "$RESULTS"
    ;;
  *)
    echo "Usage: $0 regtest|mainnet-template|neon-probe" >&2
    exit 1
    ;;
esac

# Only regtest records a row (run_regtest). mainnet-template and neon-probe
# write stub lines to results.tsv: no measurement, nothing to record.
log "done OUT_DIR=$OUT_DIR RESULTS=$RESULTS CAMPAIGN=$CAMPAIGN"
cat "$RESULTS"
