#!/bin/bash
# Post-Sapling ConnectBlock rematch -- overall throughput measures (stock -reindex).
# FDCACHE A/B is out of the current mix; optional CONDITIONS remain for later.
#
# Default: CONDITIONS=stock, N_TRIALS=4. Each trial appends to
# reindex-profile/bench-summaries/ledger.{jsonl,tsv}.
#
# Conditions:
#   stock / nofdcache -> -reindex only (preferred for measure campaigns)
#   defaultbuf        -> -reindex -perffdcache=1          (ZERO_FDCACHE build)
#   1mbbuf            -> ... -perfbufsize=1048576         (ZERO_FDCACHE build)
#
# Usage (repo root):
#   ZERO_PERF_SRC_DATADIR="$HOME/Library/Application Support/zero" \
#     contrib/perf/run_postsapling_baseline.sh
#   N_TRIALS=4 CONDITIONS=stock CAMPAIGN=postsapling
#
# Per-run artifacts: test-logs/postsapling-<UTC>/
# Durable ledger:     reindex-profile/bench-summaries/ledger.*
# Collation report:   reindex-profile/bench-summaries/REPORT-postsapling.md

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ZEROD="${ZEROD:-$REPO_ROOT/src/zerod}"
ZERO_CLI="${ZERO_CLI:-$REPO_ROOT/src/zero-cli}"
SRC_DATADIR="${ZERO_PERF_SRC_DATADIR:-$HOME/Library/Application Support/zero}"
SCRATCH="${ZERO_PERF_SCRATCH_DATADIR:-$REPO_ROOT/reindex-profile/postsapling-datadir}"
OUT_ROOT="${ZERO_PERF_OUT_DIR:-$REPO_ROOT/test-logs}"
STORE_DIR="${ZERO_PERF_STORE_DIR:-$REPO_ROOT/reindex-profile/bench-summaries}"
WARMUP_HEIGHT="${WARMUP_HEIGHT:-600000}"
MEASURE_BLOCKS="${MEASURE_BLOCKS:-300000}"
N_TRIALS="${N_TRIALS:-4}"
CONDITIONS="${CONDITIONS:-stock}"
CAMPAIGN="${CAMPAIGN:-postsapling}"
# MODE=reindex (default) or bootstrap (-loadblock). Bootstrap excludes blocks/
# from the scratch reset and requires LOADBLOCK / BOOTSTRAP_DAT.
MODE="${MODE:-reindex}"
LOADBLOCK="${LOADBLOCK:-${BOOTSTRAP_DAT:-}}"
RPCPORT="${ZERO_PERF_RPCPORT:-23926}"
# System utilization samples (ps + optional vmmap). Default on; SAMPLE_UTIL=0 to disable.
SAMPLE_UTIL="${SAMPLE_UTIL:-1}"
UTIL_PERIOD_S="${UTIL_PERIOD_S:-30}"

default_zero="$HOME/Library/Application Support/zero"
default_zero_alt="$HOME/Library/Application Support/Zero"
refuse_default() {
  local d
  d="$(cd "$1" 2>/dev/null && pwd -P)" || d="$1"
  case "$d" in
    "$default_zero"|"$default_zero_alt"|"$HOME/.zero")
      echo "ERROR: scratch must not be default user datadir: $d" >&2
      exit 1
      ;;
  esac
}
refuse_default "$SCRATCH"
if [ ! -d "$SRC_DATADIR/blocks" ]; then
  echo "ERROR: SRC_DATADIR lacks blocks/: $SRC_DATADIR" >&2
  exit 1
fi
if [ ! -x "$ZEROD" ]; then
  echo "ERROR: missing $ZEROD" >&2
  exit 1
fi
case "$MODE" in
  reindex) ;;
  bootstrap)
    if [ -z "$LOADBLOCK" ] || [ ! -f "$LOADBLOCK" ]; then
      echo "ERROR: MODE=bootstrap requires LOADBLOCK=/path/to/bootstrap.dat (copy or softlink; do not modify original)" >&2
      exit 1
    fi
    ;;
  *)
    echo "ERROR: MODE must be reindex or bootstrap (got '$MODE')" >&2
    exit 1
    ;;
esac

FDCACHE_BUILT=0
if "$ZEROD" -help 2>&1 | grep -qi 'perffdcache\|perfbufsize'; then
  FDCACHE_BUILT=1
fi

condition_args() {
  case "$1" in
    stock|nofdcache) echo "" ;;
    defaultbuf) echo "-perffdcache=1" ;;
    1mbbuf) echo "-perffdcache=1 -perfbufsize=1048576" ;;
    *)
      echo "ERROR: unknown condition '$1' (stock|nofdcache|defaultbuf|1mbbuf)" >&2
      exit 1
      ;;
  esac
}

RUN_ID="postsapling-$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="$OUT_ROOT/$RUN_ID"
mkdir -p "$OUT_DIR" "$STORE_DIR"
RESULTS="$OUT_DIR/results.tsv"
printf "mode\tcondition\ttrial\twarmup_height\tend_height\tblocks\telapsed_s\tblocks_per_sec\trun_id\n" > "$RESULTS"
DRIVER="$OUT_DIR/driver.log"
log() { echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') $*" | tee -a "$DRIVER"; }

TARGET_END=$((WARMUP_HEIGHT + MEASURE_BLOCKS))
IFS=',' read -r -a COND_ARR <<< "$CONDITIONS"

log "RUN_ID=$RUN_ID campaign=$CAMPAIGN mode=$MODE SRC=$SRC_DATADIR SCRATCH=$SCRATCH"
log "window warmup=$WARMUP_HEIGHT end=$TARGET_END N_TRIALS=$N_TRIALS CONDITIONS=$CONDITIONS"
if [ "$MODE" = "bootstrap" ]; then
  log "LOADBLOCK=$LOADBLOCK"
fi
log "ZERO_FDCACHE_built=$FDCACHE_BUILT (0 => A/B flags ignored by binary)"
log "SAMPLE_UTIL=$SAMPLE_UTIL UTIL_PERIOD_S=$UTIL_PERIOD_S"

height_of() {
  "$ZERO_CLI" -datadir="$SCRATCH" -rpcport="$RPCPORT" getblockcount 2>/dev/null || true
}

# One-line util sample -> UTIL_TSV. Args: phase pid [height]
sample_util() {
  local phase="$1" pid="$2" height="${3:-}"
  [ "$SAMPLE_UTIL" = "1" ] || return 0
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null || return 0
  local ps_line rss_kb pct_cpu pct_mem phys_mb=""
  # macOS ps: rss in KB
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

kill_pid_hard() {
  local pid="$1"
  kill -TERM "$pid" 2>/dev/null || true
  for _ in $(seq 1 10); do kill -0 "$pid" 2>/dev/null || return 0; sleep 2; done
  kill -9 "$pid" 2>/dev/null || true
}

reset_scratch() {
  if [ "$MODE" = "bootstrap" ]; then
    log "reset scratch bootstrap (exclude blocks/ + chainstate; empty chain for -loadblock)"
    rm -rf "$SCRATCH"
    mkdir -p "$SCRATCH"
    # Keep conf/params-adjacent files if present; never copy blocks or chainstate.
    rsync -a --exclude='blocks' --exclude='chainstate' --exclude='wallet.zero' \
      --exclude='wallet.zero*' --exclude='debug*.log' --exclude='.lock' \
      --exclude='bootstrap.dat' --exclude='bootstrap.dat.old' \
      --exclude='chainblocks*.tgz' --exclude='chainblocks*.sha256' \
      "$SRC_DATADIR/" "$SCRATCH/" 2>/dev/null || true
  else
    log "reset scratch (rsync blocks, exclude chainstate; source read-only)"
    rm -rf "$SCRATCH"
    mkdir -p "$SCRATCH"
    rsync -a --exclude='chainstate' --exclude='wallet.zero' --exclude='wallet.zero*' \
      --exclude='debug*.log' --exclude='.lock' \
      "$SRC_DATADIR/" "$SCRATCH/"
  fi
  {
    echo "listen=0"
    echo "maxconnections=0"
    echo "disablewallet=1"
    echo "server=1"
    echo "rpcuser=rt"
    echo "rpcpassword=rt"
    echo "rpcport=$RPCPORT"
  } > "$SCRATCH/zero.conf"
}

run_one() {
  local condition="$1" trial="$2"
  local trial_dir="$OUT_DIR/${condition}_trial${trial}"
  mkdir -p "$trial_dir"
  UTIL_TSV="$trial_dir/util.tsv"
  if [ "$SAMPLE_UTIL" = "1" ]; then
    printf "utc\tphase\theight\tpct_cpu\tpct_mem\trss_kb\tphys_footprint_mb\tpid\n" > "$UTIL_TSV"
  fi
  reset_scratch

  local extra
  extra=$(condition_args "$condition")
  # shellcheck disable=SC2206
  local extra_arr=($extra)

  log "trial start mode=$MODE condition=$condition trial=$trial args=${extra:-none}"
  if [ "$MODE" = "bootstrap" ]; then
    "$ZEROD" -datadir="$SCRATCH" -disablewallet -connect=0 -listen=0 \
      -loadblock="$LOADBLOCK" \
      -rpcport="$RPCPORT" ${extra_arr[@]+"${extra_arr[@]}"} \
      >"$trial_dir/zerod_stdout.log" 2>&1 &
  else
    "$ZEROD" -datadir="$SCRATCH" -disablewallet -reindex -connect=0 -listen=0 \
      -rpcport="$RPCPORT" ${extra_arr[@]+"${extra_arr[@]}"} \
      >"$trial_dir/zerod_stdout.log" 2>&1 &
  fi
  local pid=$!
  log "zerod pid=$pid"
  sample_util start "$pid" 0

  local warmup_wait_s=$(( WARMUP_HEIGHT / 200 + 600 ))
  local measure_wait_s=$(( MEASURE_BLOCKS / 200 + 600 ))
  local waited=0 h
  local last_util=0

  until h=$(height_of); [[ "$h" =~ ^[0-9]+$ ]] && [ "$h" -ge 0 ]; do
    kill -0 "$pid" 2>/dev/null || { log "ERROR: exited before RPC"; return 1; }
    [ "$waited" -ge 600 ] && { kill_pid_hard "$pid"; log "ERROR: RPC timeout"; return 1; }
    sleep 2; waited=$((waited + 2))
  done
  sample_util rpc_up "$pid" "$h"

  waited=0
  last_util=0
  until h=$(height_of); [[ "$h" =~ ^[0-9]+$ ]] && [ "$h" -ge "$WARMUP_HEIGHT" ]; do
    kill -0 "$pid" 2>/dev/null || { log "ERROR: exited in warmup h=$h"; return 1; }
    [ "$waited" -ge "$warmup_wait_s" ] && { kill_pid_hard "$pid"; log "ERROR: warmup timeout h=$h"; return 1; }
    if [ "$SAMPLE_UTIL" = "1" ] && [ $((waited - last_util)) -ge "$UTIL_PERIOD_S" ]; then
      sample_util warmup "$pid" "$h"
      last_util=$waited
    fi
    sleep 2; waited=$((waited + 2))
  done
  log "warmup ok condition=$condition h=$h"
  sample_util warmup_done "$pid" "$h"

  waited=0
  last_util=0
  until h=$(height_of); [[ "$h" =~ ^[0-9]+$ ]] && [ "$h" -ge "$TARGET_END" ]; do
    kill -0 "$pid" 2>/dev/null || { log "ERROR: exited in measure h=$h"; return 1; }
    [ "$waited" -ge "$measure_wait_s" ] && { kill_pid_hard "$pid"; log "ERROR: measure timeout h=$h"; return 1; }
    if [ "$SAMPLE_UTIL" = "1" ] && [ $((waited - last_util)) -ge "$UTIL_PERIOD_S" ]; then
      sample_util measure "$pid" "$h"
      last_util=$waited
    fi
    sleep 2; waited=$((waited + 2))
  done
  log "measure end condition=$condition h=$h"
  sample_util measure_done "$pid" "$h"

  cp "$SCRATCH/debug.log" "$trial_dir/debug.log" 2>/dev/null || true
  local elapsed bps
  elapsed=$(python3 "$REPO_ROOT/contrib/perf/extract_measures.py" \
    --elapsed-heights "$trial_dir/debug.log" "$WARMUP_HEIGHT" "$TARGET_END")
  if [ "$elapsed" = "NA" ] || [ -z "$elapsed" ]; then
    log "ERROR: elapsed NA condition=$condition trial=$trial"
    "$ZERO_CLI" -datadir="$SCRATCH" -rpcport="$RPCPORT" stop >/dev/null 2>&1 || kill_pid_hard "$pid"
    return 1
  fi
  bps=$(python3 -c "print(round($MEASURE_BLOCKS / float('$elapsed'), 4))")
  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$MODE" "$condition" "$trial" "$WARMUP_HEIGHT" "$TARGET_END" "$MEASURE_BLOCKS" "$elapsed" "$bps" "$RUN_ID" \
    >> "$RESULTS"
  log "result mode=$MODE condition=$condition trial=$trial elapsed_s=$elapsed blk/s=$bps"

  local notes="fdcache_built=$FDCACHE_BUILT;mode=$MODE"
  if [ "$SAMPLE_UTIL" = "1" ] && [ -f "$UTIL_TSV" ]; then
    notes="${notes};util=$(basename "$trial_dir")/util.tsv"
  fi
  python3 "$REPO_ROOT/contrib/perf/accumulate_bench.py" \
    --store-dir "$STORE_DIR" \
    --append \
    --campaign "$CAMPAIGN" \
    --run-id "$RUN_ID" \
    --mode "$MODE" \
    --condition "$condition" \
    --trial "$trial" \
    --warmup-height "$WARMUP_HEIGHT" \
    --end-height "$TARGET_END" \
    --blocks "$MEASURE_BLOCKS" \
    --elapsed-s "$elapsed" \
    --blocks-per-sec "$bps" \
    --binary "$ZEROD" \
    --notes "$notes" | tee -a "$DRIVER"

  python3 "$REPO_ROOT/contrib/perf/extract_measures.py" \
    --datadir "$SCRATCH" \
    --run-id "${RUN_ID}-${condition}-t${trial}" \
    --op-class "$MODE" --no-wallet --env lab \
    --sample-tip 200 \
    --csv "$OUT_DIR/measures_${condition}_t${trial}.csv" \
    --no-md 2>>"$DRIVER" || true

  "$ZERO_CLI" -datadir="$SCRATCH" -rpcport="$RPCPORT" stop >/dev/null 2>&1 || kill_pid_hard "$pid"
  sleep 1
  sample_util after_stop "$pid" "$h" 2>/dev/null || true
  sleep 1
}

for condition in "${COND_ARR[@]}"; do
  condition="${condition// /}"
  [ -n "$condition" ] || continue
  for trial in $(seq 1 "$N_TRIALS"); do
    run_one "$condition" "$trial" || exit 1
  done
done

log "done. per-run=$RESULTS ledger=$STORE_DIR/ledger.tsv"
cat "$RESULTS"

# Single-line invocations avoid fragile backslash continuations under tee/pipefail.
python3 "$REPO_ROOT/contrib/perf/accumulate_bench.py" --store-dir "$STORE_DIR" --report --campaign "$CAMPAIGN" --md "$STORE_DIR/REPORT-${CAMPAIGN}.md" --json "$OUT_DIR/collation.json" | tee -a "$DRIVER"
python3 "$REPO_ROOT/contrib/perf/accumulate_bench.py" --store-dir "$STORE_DIR" --report --md "$STORE_DIR/REPORT.md" --json "$STORE_DIR/collation.json" >/dev/null

log "collation: $STORE_DIR/REPORT-${CAMPAIGN}.md and $STORE_DIR/REPORT.md"
