#!/usr/bin/env bash
# BENCH-MINE: Equihash *solve* profile env (regtest / mainnet-template / neon-stock).
# Does not replace ConnectBlock rematch. Assign M-* via accumulate_bench when measured.
#
# Usage (repo root):
#   contrib/perf/mine_bench.sh regtest
#   contrib/perf/mine_bench.sh mainnet-template
#   contrib/perf/mine_bench.sh neon-probe
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
UTIL_TSV="$OUT_DIR/util.tsv"
RESULTS="$OUT_DIR/results.tsv"

printf "utc\tphase\theight\tpct_cpu\tpct_mem\trss_kb\tphys_footprint_mb\tpid\n" > "$UTIL_TSV"
printf "mode\tblocks\telapsed_s\tblocks_per_sec\tms_per_block\tnotes\trun_id\n" > "$RESULTS"

sample_util() {
  local phase="$1" pid="$2" height="${3:-}"
  [ "$SAMPLE_UTIL" = "1" ] || return 0
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null || return 0
  local ps_line pct_cpu pct_mem rss_kb phys_mb=""
  ps_line=$(ps -o %cpu=,%mem=,rss= -p "$pid" 2>/dev/null | head -1 | sed 's/^ *//')
  [ -n "$ps_line" ] || return 0
  pct_cpu=$(echo "$ps_line" | awk '{print $1}')
  pct_mem=$(echo "$ps_line" | awk '{print $2}')
  rss_kb=$(echo "$ps_line" | awk '{print $3}')
  if command -v vmmap >/dev/null 2>&1; then
    phys_mb=$(vmmap -summary "$pid" 2>/dev/null | awk -F= '/Physical footprint:/ {
      gsub(/^[ \t]+|[ \t]+$/, "", $2);
      if ($2 ~ /G/) { gsub(/[^0-9.]/, "", $2); printf "%.1f", $2*1024; exit }
      if ($2 ~ /M/) { gsub(/[^0-9.]/, "", $2); printf "%.1f", $2; exit }
      if ($2 ~ /K/) { gsub(/[^0-9.]/, "", $2); printf "%.1f", $2/1024; exit }
    }')
  fi
  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$phase" "${height:-}" \
    "$pct_cpu" "$pct_mem" "$rss_kb" "${phys_mb:-}" "$pid" >> "$UTIL_TSV"
  log "util phase=$phase h=${height:-NA} cpu%=$pct_cpu mem%=$pct_mem rss_kb=$rss_kb phys_mb=${phys_mb:-NA}"
}

write_conf() {
  local netline="$1"
  mkdir -p "$SCRATCH"
  {
    echo "$netline"
    echo "listen=0"
    echo "maxconnections=0"
    echo "server=1"
    echo "rpcuser=rt"
    echo "rpcpassword=rt"
    echo "rpcport=$RPCPORT"
    echo "gen=0"
  } > "$SCRATCH/zero.conf"
}

cli() { "$ZERO_CLI" -datadir="$SCRATCH" -rpcport="$RPCPORT" "$@"; }

stop_node() {
  cli stop >/dev/null 2>&1 || true
  sleep 2
  pkill -f "zerod -datadir=$SCRATCH" 2>/dev/null || true
}

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
  rm -rf "$SCRATCH"
  write_conf "regtest=1"
  log "START mode=regtest blocks=$MINE_BLOCKS timeout=${MINE_TIMEOUT_S}s"
  "$ZEROD" -datadir="$SCRATCH" -daemon
  sleep 2
  local pid
  pid=$(pgrep -f "zerod -datadir=$SCRATCH" | head -1)
  sample_util start "$pid" 0
  # fund + mine
  local t0 t1 elapsed bps ms
  t0=$(date +%s)
  if command -v gtimeout >/dev/null 2>&1; then
    gtimeout "$MINE_TIMEOUT_S" "$ZERO_CLI" -datadir="$SCRATCH" -rpcport="$RPCPORT" \
      generate "$MINE_BLOCKS" >/dev/null
  elif command -v timeout >/dev/null 2>&1; then
    timeout "$MINE_TIMEOUT_S" "$ZERO_CLI" -datadir="$SCRATCH" -rpcport="$RPCPORT" \
      generate "$MINE_BLOCKS" >/dev/null
  else
    cli generate "$MINE_BLOCKS" >/dev/null
  fi
  t1=$(date +%s)
  elapsed=$((t1 - t0))
  [ "$elapsed" -gt 0 ] || elapsed=1
  local h
  h=$(cli getblockcount)
  sample_util after_generate "$pid" "$h"
  bps=$(python3 -c "print(round($MINE_BLOCKS/float($elapsed), 4))")
  ms=$(python3 -c "print(round(1000.0*$elapsed/float($MINE_BLOCKS), 3))")
  printf "regtest\t%s\t%s\t%s\t%s\t48,5-solve\t%s\n" \
    "$MINE_BLOCKS" "$elapsed" "$bps" "$ms" "$RUN_ID" >> "$RESULTS"
  log "result regtest blocks=$MINE_BLOCKS elapsed_s=$elapsed blk/s=$bps ms/blk=$ms"
  stop_node
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

# Append to ledger if accumulate helper exists
if [ -f "$REPO_ROOT/contrib/perf/accumulate_bench.py" ]; then
  python3 "$REPO_ROOT/contrib/perf/accumulate_bench.py" --import-tsv "$RESULTS" \
    --campaign "$CAMPAIGN" 2>/dev/null || log "ledger import skipped/failed (ok for stub rows)"
fi

log "done OUT_DIR=$OUT_DIR RESULTS=$RESULTS CAMPAIGN=$CAMPAIGN"
cat "$RESULTS"
