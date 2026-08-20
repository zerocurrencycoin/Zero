#!/usr/bin/env bash
export LC_ALL=C
# Sample CPU / memory / IO / thread state of a running zerod into a TSV.
#
# Complements the per-campaign samplers (wallet_sync_profile.sh, mine_bench.sh)
# which record %cpu / rss / footprint only. This adds:
#   - per-thread CPU (which thread is hot: loadblk, scriptcheck, wallet, net)
#   - host-wide disk throughput (iostat) to separate CPU-bound from IO-bound
#   - page-in/page-out and compressor state (vm_stat) for memory pressure
#   - chain height from RPC, so every row is attributable to a block range
#
# Unprivileged by design: no fs_usage / powermetrics, which need sudo.
#
# Usage (repo root, node already running):
#   contrib/perf/res_sample.sh <out.tsv> [period_s] [datadir] [rpcport]
#
# Stop with SIGINT/SIGTERM; the file is complete at every row.

set -uo pipefail

OUT="${1:?usage: res_sample.sh <out.tsv> [period_s] [datadir] [rpcport]}"
PERIOD="${2:-5}"
DATADIR="${3:-$HOME/Library/Application Support/zero}"
RPCPORT="${4:-23811}"
CLI="${ZERO_CLI:-./src/zero-cli}"

PID="$(pgrep -x zerod | head -1)"
[ -n "$PID" ] || { echo "no zerod running" >&2; exit 1; }

# RPC can block when the node is CPU-saturated (a long solveequihash holds the
# RPC worker), which would stall the whole sampler. Bound it: a missing height
# is far better than losing the CPU/memory rows for that interval.
RPC_TIMEOUT="${ZERO_RES_RPC_TIMEOUT:-3}"
cli() {
  if command -v timeout >/dev/null 2>&1; then
    timeout "$RPC_TIMEOUT" "$CLI" -datadir="$DATADIR" -rpcport="$RPCPORT" "$@" 2>/dev/null
  else
    "$CLI" -datadir="$DATADIR" -rpcport="$RPCPORT" "$@" 2>/dev/null
  fi
}

printf 'utc\telapsed_s\tpid\tpct_cpu\trss_mb\tphys_mb\tthreads\tthreads_cpu_sum\thot_thread_pct\tdisk_mb_s\tpageins\tcompressed_mb\theight\n' > "$OUT"

START=$(date +%s)
trap 'echo "stopped after $(( $(date +%s) - START ))s -> $OUT" >&2; exit 0' INT TERM

while kill -0 "$PID" 2>/dev/null; do
  now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  elapsed=$(( $(date +%s) - START ))

  # Process CPU / RSS
  read -r pct rss <<<"$(ps -o %cpu=,rss= -p "$PID" 2>/dev/null | sed 's/^ *//')"
  rss_mb=$(( ${rss:-0} / 1024 ))

  # Physical footprint (macOS accounts compressed pages here, RSS does not)
  # Physical footprint: footprint(1) prints "Footprint: N MB" on its header.
  phys_mb=""
  if command -v footprint >/dev/null 2>&1; then
    phys_mb=$(footprint -p "$PID" 2>/dev/null \
      | awk '/Footprint:/ {for(i=1;i<=NF;i++) if($i=="Footprint:"){print int($(i+1)); exit}}')
  fi

  # Per-thread CPU. `ps -M` prints a wide process row (USER PID TT %CPU ...)
  # then one narrow row per thread (PID %CPU STAT PRI ...) -- %CPU is field 4
  # on the process row but field 2 on thread rows. Read thread rows only.
  threads=$(ps -M -p "$PID" 2>/dev/null | tail -n +3 | grep -c .)
  hot_pct=$(ps -M -p "$PID" 2>/dev/null | tail -n +3 | awk 'NF>=6 {print $2}' | sort -rn | head -1)
  thr_cpu=$(ps -M -p "$PID" 2>/dev/null | tail -n +3 | awk 'NF>=6 {s+=$2} END {printf "%.1f", s+0}')

  # Host disk throughput: iostat one sample, MB/s on disk0
  disk=$(iostat -d -w 1 -c 2 disk0 2>/dev/null | tail -1 | awk '{print $3}')

  # Memory pressure
  pageins=$(vm_stat 2>/dev/null | awk '/Pageins/ {gsub(/[^0-9]/,"",$NF); print $NF}')
  comp_pages=$(vm_stat 2>/dev/null | awk '/stored in compressor/ {gsub(/[^0-9]/,"",$NF); print $NF}')
  comp_mb=$(( ${comp_pages:-0} * 4096 / 1048576 ))

  # Height: RPC first, but during -reindex / a long solve the RPC worker is
  # blocked and every call times out. Fall back to the last UpdateTip in
  # debug.log so rows stay attributable to a block range.
  height=$(cli getblockcount 2>/dev/null)
  if [ -z "$height" ] && [ -r "$DATADIR/debug.log" ]; then
    height=$(tail -n 400 "$DATADIR/debug.log" 2>/dev/null \
      | awk 'match($0,/height=[0-9]+/){h=substr($0,RSTART+7,RLENGTH-7)} END{print h}')
  fi

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$now" "$elapsed" "$PID" "${pct:-}" "$rss_mb" "${phys_mb:-}" \
    "${threads:-}" "${thr_cpu:-}" "${hot_pct:-}" "${disk:-}" \
    "${pageins:-}" "$comp_mb" "${height:-}" >> "$OUT"

  sleep "$PERIOD"
done

echo "zerod (pid $PID) exited; $(( $(wc -l < "$OUT") - 1 )) rows -> $OUT" >&2
