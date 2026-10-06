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
#   CONDITION               RecBench condition (default stock)
#   ZERO_PERF_RUN_ID        run id (default walletsync-<utc>)
#   ZERO_PERF_STORE_DIR     RecBench store (default reindex-profile/bench-summaries)
#   ZERO_PERF_ROW_FILE      if set, the recorded row's run_id and fingerprint go here

export LC_ALL=C
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck disable=SC1091
. "$REPO_ROOT/contrib/perf/datadir_guard.sh"
# shellcheck source=/dev/null
. "$REPO_ROOT/contrib/perf/perflib.sh"
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

RUN_ID="${ZERO_PERF_RUN_ID:-walletsync-$(date -u +%Y%m%dT%H%M%SZ)}"
OUT_DIR="$OUT_ROOT/$RUN_ID"
STORE_DIR="${ZERO_PERF_STORE_DIR:-$REPO_ROOT/reindex-profile/bench-summaries}"
mkdir -p "$OUT_DIR"
DRIVER="$OUT_DIR/driver.log"
# log() comes from perflib.sh and tees to DRIVER_LOG.
# shellcheck disable=SC2034
DRIVER_LOG="$DRIVER"
# cli, stop_node, sample_util act on this node (perflib.sh).
# shellcheck disable=SC2034  # read by perflib.sh
NODE_DATADIR="$SCRATCH"
# shellcheck disable=SC2034
NODE_RPCPORT="$RPCPORT"

# Wallet columns after perflib's standard ones. getwalletinfo blocks on
# cs_wallet for minutes under a fat-wallet witness build; the bound keeps
# util.tsv advancing, and TIMEOUT in txcount marks a sample it cut short.
wallet_columns() {
  local wbytes=0 txcount="" note_tx_count="" wi_json=""
  if [ "${WALLETINFO_TIMEOUT_S}" != "0" ]; then
    wi_json=$(ZERO_PERF_CLI_TIMEOUT_S="$WALLETINFO_TIMEOUT_S" cli getwalletinfo 2>/dev/null || true)
    if [ -n "$wi_json" ]; then
      read -r txcount note_tx_count < <(printf '%s' "$wi_json" | python3 -c 'import sys, json
w = json.load(sys.stdin); print(w.get("txcount", ""), w.get("note_tx_count", ""))' 2>/dev/null || true)
    fi
    txcount="${txcount:-TIMEOUT}"
  fi
  if [ -f "$SCRATCH/wallet.zero" ]; then
    wbytes=$(stat -f%z "$SCRATCH/wallet.zero" 2>/dev/null || stat -c%s "$SCRATCH/wallet.zero" 2>/dev/null || echo 0)
  fi
  printf '%s\t%s\t%s' "$wbytes" "$txcount" "$note_tx_count"
}
util_tsv_init "$OUT_DIR/util.tsv" "$(printf 'wallet_bytes\ttxcount\tnote_tx_count')"
# shellcheck disable=SC2034  # read by sample_util
UTIL_EXTRA_FN=wallet_columns

prepare_scratch() {
  if [ "$RESUME" = "1" ] && [ -d "$SCRATCH/blocks" ]; then
    log "RESUME=1 keeping scratch $SCRATCH"
    return 0
  fi
  log "prepare scratch snap=$SNAP"
  # Honours ZERO_PERF_DATADIR_POLICY (default: set aside, then recreate).
  dispose_datadir "$SCRATCH" SCRATCH
  case "$SNAP" in
    tiny)
      tar -xzf "$(snap_archive chainblocks-tiny.tgz)" -C "$SCRATCH"
      ;;
    short)
      tar -xzf "$(snap_archive chainblocks-short.tgz)" -C "$SCRATCH"
      ;;
    full)
      rsync -a --exclude='chainstate' --exclude='wallet.zero' --exclude='wallet.zero*' \
        --exclude='debug*.log' --exclude='.lock' \
        "$SRC_DATADIR/" "$SCRATCH/"
      rm -r "$SCRATCH/chainstate" 2>/dev/null || true
      ;;
    *)
      echo "ERROR: ZERO_PERF_CHAIN_SNAP must be tiny|short|full" >&2
      exit 1
      ;;
  esac
  cp -p "$WALLET_FILE" "$SCRATCH/wallet.zero"
  lab_conf "$SCRATCH" "$RPCPORT"
}

prepare_scratch
stop_node

log "RUN_ID=$RUN_ID campaign=$CAMPAIGN wallet_src_bytes=$(stat -f%z "$WALLET_FILE" 2>/dev/null || stat -c%s "$WALLET_FILE")"
log "starting -reindex with wallet (solo) extra=[${ZEROD_EXTRA_ARGS}]"
# shellcheck disable=SC2086
"$ZEROD" -datadir="$SCRATCH" -reindex -daemon $ZEROD_EXTRA_ARGS
sleep 3
pid=$(node_pid || true)
if [ -z "$pid" ]; then
  log "ERROR: zerod failed to start; see $SCRATCH/debug.log"
  tail -30 "$SCRATCH/debug.log" || true
  exit 1
fi
sample_util start "$pid" "$(height_of)"

# Default tip targets for snaps (approx)
if [ -z "$TARGET_HEIGHT" ]; then
  case "$SNAP" in
    tiny) TARGET_HEIGHT=187417 ;;
    short) TARGET_HEIGHT=245992 ;;
    full) TARGET_HEIGHT=0 ;; # 0 => until tip / interrupt
  esac
fi

log "polling until height>=$TARGET_HEIGHT (0=run until stopped) period=${SAMPLE_PERIOD_S}s"
h=0
while pid_alive "$pid"; do
  h=$(height_of)
  h="${h:-0}"
  sample_util measure "$pid" "$h"
  if [ "${TARGET_HEIGHT:-0}" -gt 0 ] && [ "$h" -ge "$TARGET_HEIGHT" ]; then
    log "target height reached h=$h"
    sample_util "done" "$pid" "$h"
    break
  fi
  sleep "$SAMPLE_PERIOD_S"
done

stop_node "$pid"

# One RecBench row (record_trial, perflib.sh): runtime checked against the
# node's log, the wallet identified by hash, util.tsv named. A node that did
# not apply what it was given ran a different trial, and gets no row.
ELAPSED=$(python3 "$REPO_ROOT/contrib/perf/extract_measures.py" \
  --elapsed-heights "$SCRATCH/debug.log" 0 "$h" 2>/dev/null || echo NA)
if [ "$ELAPSED" = "NA" ] || [ -z "$ELAPSED" ] || [ "$h" -le 0 ]; then
  die "no elapsed time for heights 0-$h in $SCRATCH/debug.log; util.tsv kept, no row recorded"
fi
BPS=$(safe_div "$h" "$ELAPSED")
if ! record_trial "$SCRATCH/debug.log" "$SCRATCH/zero.conf" "-reindex $ZEROD_EXTRA_ARGS" \
     "$WALLET_FILE" "$UTIL_TSV" \
     --store-dir "$STORE_DIR" --campaign "$CAMPAIGN" --run-id "$RUN_ID" \
     --mode reindex --condition "${CONDITION:-stock}" --trial "${TRIAL:-1}" \
     --workload op=reindex --workload "snap=$SNAP" \
     --warmup-height 0 --end-height "$h" --blocks "$h" \
     --elapsed-s "$ELAPSED" --blocks-per-sec "$BPS" \
     --binary "$ZEROD" --notes "snap=$SNAP"; then
  die "row not recorded (see above); util.tsv kept"
fi
if [ -n "${ZERO_PERF_ROW_FILE:-}" ]; then
  printf 'run_id=%s\nfingerprint=%s\nelapsed_s=%s\n' "$RUN_ID" "$RECORD_FINGERPRINT" "$ELAPSED" > "$ZERO_PERF_ROW_FILE"
fi

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
