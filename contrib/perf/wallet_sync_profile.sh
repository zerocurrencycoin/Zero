#!/usr/bin/env bash
# Wallet-on sync util profile (CPU / RSS / wallet.zero size / txcount).
# Disposable scratch only. Never writes default Application Support/zero.
#
# Intended for Dev wallet profile 0 (small wallet.zero0) via env -- do not
# hardcode ops paths in docs/Measures.
#
# Usage:
#   ZERO_PERF_WALLET_FILE=/path/to/wallet.zero0 \
#   ZERO_PERF_SRC_DATADIR="$HOME/Library/Application Support/zero" \
#   ZERO_PERF_CHAIN_SNAP=tiny \
#     contrib/perf/wallet_sync_profile.sh
#
# Env:
#   ZERO_PERF_WALLET_FILE   required -- source wallet.zero (copied in)
#   ZERO_PERF_SRC_DATADIR   blocks source (read-only rsync) OR use snap
#   ZERO_PERF_CHAIN_SNAP    tiny|short|full  (tiny/short unpack chainblocks-*.tgz
#                           from SRC; full rsyncs blocks/)
#   TARGET_HEIGHT           stop measure at height (default: tip of snap)
#   SAMPLE_PERIOD_S         default 15
#   WALLETINFO_TIMEOUT_S    default 5 -- alarm around getwalletinfo (0=skip txcount)
#   RESUME                  1 = keep existing scratch chainstate/wallet
#   CAMPAIGN                default wallet-sync-profile0
#   ZERO_PERF_RPCPORT       default 23955
#   ZEROD_EXTRA_ARGS        extra zerod args (e.g. -walletwitness=ibd-defer)

export LC_ALL=C
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck disable=SC1091
. "$REPO_ROOT/contrib/perf/datadir_guard.sh"
ZEROD="${ZEROD:-$REPO_ROOT/src/zerod}"
ZERO_CLI="${ZERO_CLI:-$REPO_ROOT/src/zero-cli}"
SRC_DATADIR="${ZERO_PERF_SRC_DATADIR:-$HOME/Library/Application Support/zero}"
SCRATCH="${ZERO_PERF_SCRATCH_DATADIR:-$REPO_ROOT/reindex-profile/wallet-sync-datadir}"
OUT_ROOT="${ZERO_PERF_OUT_DIR:-$REPO_ROOT/test-logs}"
WALLET_FILE="${ZERO_PERF_WALLET_FILE:-}"
SNAP="${ZERO_PERF_CHAIN_SNAP:-tiny}"
SAMPLE_PERIOD_S="${SAMPLE_PERIOD_S:-15}"
WALLETINFO_TIMEOUT_S="${WALLETINFO_TIMEOUT_S:-5}"
RPCPORT="${ZERO_PERF_RPCPORT:-23955}"
CAMPAIGN="${CAMPAIGN:-wallet-sync-profile0}"
RESUME="${RESUME:-0}"
TARGET_HEIGHT="${TARGET_HEIGHT:-}"
ZEROD_EXTRA_ARGS="${ZEROD_EXTRA_ARGS:-}"

refuse_live_datadir SCRATCH "$SCRATCH"

if [ -z "$WALLET_FILE" ] || [ ! -f "$WALLET_FILE" ]; then
  echo "ERROR: set ZERO_PERF_WALLET_FILE to an existing wallet.zero*" >&2
  exit 1
fi
if [ ! -x "$ZEROD" ]; then
  echo "ERROR: missing $ZEROD" >&2
  exit 1
fi

RUN_ID="walletsync-$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="$OUT_ROOT/$RUN_ID"
mkdir -p "$OUT_DIR"
DRIVER="$OUT_DIR/driver.log"
UTIL_TSV="$OUT_DIR/util.tsv"
log() { echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') $*" | tee -a "$DRIVER"; }

printf "utc\tphase\theight\tpct_cpu\tpct_mem\trss_kb\tphys_footprint_mb\twallet_bytes\ttxcount\tnote_tx_count\tpid\n" > "$UTIL_TSV"

cli() { "$ZERO_CLI" -datadir="$SCRATCH" -rpcport="$RPCPORT" "$@"; }

sample_row() {
  local phase="$1" pid="$2"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null || return 0
  local ps_line pct_cpu pct_mem rss_kb phys_mb="" height="" txcount="" wbytes=0
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
  height=$(cli getblockcount 2>/dev/null || true)
  # getwalletinfo can block for minutes under fat-wallet cs_wallet (VerifyAndSetInitialWitness).
  # Timeout keeps util.tsv advancing; empty txcount means skip/timeout.
  txcount=""
  note_tx_count=""
  if [ "${WALLETINFO_TIMEOUT_S}" != "0" ]; then
    wi_json=$(perl -e "alarm $WALLETINFO_TIMEOUT_S; exec @ARGV" \
      "$ZERO_CLI" -datadir="$SCRATCH" -rpcport="$RPCPORT" getwalletinfo 2>/dev/null || true)
    if [ -n "$wi_json" ]; then
      txcount=$(printf '%s' "$wi_json" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("txcount",""))' 2>/dev/null || true)
      note_tx_count=$(printf '%s' "$wi_json" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("note_tx_count",""))' 2>/dev/null || true)
    fi
    if [ -z "$txcount" ]; then
      txcount="TIMEOUT"
    fi
  fi
  if [ -f "$SCRATCH/wallet.zero" ]; then
    wbytes=$(stat -f%z "$SCRATCH/wallet.zero" 2>/dev/null || stat -c%s "$SCRATCH/wallet.zero" 2>/dev/null || echo 0)
  fi
  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$phase" "${height:-}" \
    "$pct_cpu" "$pct_mem" "$rss_kb" "${phys_mb:-}" "$wbytes" "${txcount:-}" "${note_tx_count:-}" "$pid" >> "$UTIL_TSV"
  log "util phase=$phase h=${height:-NA} cpu%=$pct_cpu rss_kb=$rss_kb wallet_B=$wbytes txcount=${txcount:-NA} note_tx=${note_tx_count:-NA}"
}

prepare_scratch() {
  if [ "$RESUME" = "1" ] && [ -d "$SCRATCH/blocks" ]; then
    log "RESUME=1 keeping scratch $SCRATCH"
    return 0
  fi
  log "prepare scratch snap=$SNAP"
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
      echo "ERROR: ZERO_PERF_CHAIN_SNAP must be tiny|short|full" >&2
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
  } > "$SCRATCH/zero.conf"
  # ensure no sticky reindex=
  if grep -q '^reindex=' "$SCRATCH/zero.conf" 2>/dev/null; then
    grep -v '^reindex=' "$SCRATCH/zero.conf" > "$SCRATCH/zero.conf.tmp" || true
    mv "$SCRATCH/zero.conf.tmp" "$SCRATCH/zero.conf"
  fi
}

stop_node() {
  cli stop >/dev/null 2>&1 || true
  sleep 2
  pkill -f "zerod -datadir=$SCRATCH" 2>/dev/null || true
}

prepare_scratch
stop_node

log "RUN_ID=$RUN_ID campaign=$CAMPAIGN wallet_src_bytes=$(stat -f%z "$WALLET_FILE" 2>/dev/null || stat -c%s "$WALLET_FILE")"
log "starting -reindex with wallet (solo) extra=[${ZEROD_EXTRA_ARGS}]"
# shellcheck disable=SC2086
"$ZEROD" -datadir="$SCRATCH" -reindex -daemon $ZEROD_EXTRA_ARGS
sleep 3
pid=$(pgrep -f "zerod -datadir=$SCRATCH" | head -1 || true)
if [ -z "$pid" ]; then
  log "ERROR: zerod failed to start; see $SCRATCH/debug.log"
  tail -30 "$SCRATCH/debug.log" || true
  exit 1
fi
sample_row start "$pid"

# Default tip targets for snaps (approx)
if [ -z "$TARGET_HEIGHT" ]; then
  case "$SNAP" in
    tiny) TARGET_HEIGHT=187417 ;;
    short) TARGET_HEIGHT=245992 ;;
    full) TARGET_HEIGHT=0 ;; # 0 => until tip / interrupt
  esac
fi

log "polling until height>=$TARGET_HEIGHT (0=run until stopped) period=${SAMPLE_PERIOD_S}s"
while kill -0 "$pid" 2>/dev/null; do
  sample_row measure "$pid"
  h=$(cli getblockcount 2>/dev/null || echo 0)
  if [ "${TARGET_HEIGHT:-0}" -gt 0 ] && [ "${h:-0}" -ge "$TARGET_HEIGHT" ]; then
    log "target height reached h=$h"
    sample_row done "$pid"
    break
  fi
  sleep "$SAMPLE_PERIOD_S"
done

stop_node
sample_row after_stop "$pid" || true

# summary without host wallet path
python3 - <<PY
import csv
from pathlib import Path
p = Path("$UTIL_TSV")
rows = list(csv.DictReader(p.open(), delimiter="\t"))
print(f"samples={len(rows)}")
if rows:
    hs = [int(r["height"]) for r in rows if r.get("height") and r["height"].isdigit()]
    ws = [int(r["wallet_bytes"]) for r in rows if r.get("wallet_bytes") and str(r["wallet_bytes"]).isdigit()]
    if hs:
        print(f"height {hs[0]} -> {hs[-1]}")
    if ws:
        print(f"wallet_bytes {ws[0]} -> {ws[-1]} (delta {ws[-1]-ws[0]})")
print("util_tsv=$UTIL_TSV")
print("campaign=$CAMPAIGN")
PY

log "done OUT_DIR=$OUT_DIR"
