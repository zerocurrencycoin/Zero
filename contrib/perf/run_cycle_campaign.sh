#!/bin/bash
# One restartable cycle-campaign trial. Does not batch long runs.
#
# Usage (repo root):
#   contrib/perf/run_cycle_campaign.sh list
#   CYCLE=1 SET=smoke contrib/perf/run_cycle_campaign.sh next
#   CYCLE=1 contrib/perf/run_cycle_campaign.sh run p0-reindex-tiny
#   contrib/perf/run_cycle_campaign.sh report
#
# Env:
#   CYCLE                 1|2|3 (default 1) -- ledger campaign cycle-N
#   SET                   smoke|gate|long|all (default smoke for next)
#   ZERO_PERF_WALLET_P0   wallet.zero for p0 trials
#   ZERO_PERF_WALLET_P1   wallet.zero for p1 trials
#   ZERO_PERF_WALLET_FAT  golden fat wallet.zero
#   LOADBLOCK             bootstrap.dat copy (nowallet-bootstrap-presap)
#   ZERO_PERF_TIP_TEMPLATE  tip datadir (fat-sync-tip-noteidx)
#   ZERO_PERF_SRC_DATADIR   blocks/snap archives
#
# Durable: reindex-profile/cycle-campaign/status.jsonl
#          reindex-profile/bench-summaries/ledger.* (CAMPAIGN=cycle-N)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"
CATALOG="${CYCLE_CATALOG:-$REPO_ROOT/contrib/perf/cycle_trials.tsv}"
STORE_DIR="${ZERO_PERF_STORE_DIR:-$REPO_ROOT/reindex-profile/bench-summaries}"
STATUS_DIR="${ZERO_PERF_CYCLE_DIR:-$REPO_ROOT/reindex-profile/cycle-campaign}"
STATUS_JSONL="$STATUS_DIR/status.jsonl"
CYCLE="${CYCLE:-1}"
SET="${SET:-smoke}"
CMD="${1:-list}"
TRIAL_ID="${2:-}"

mkdir -p "$STATUS_DIR" "$STORE_DIR"
touch "$STATUS_JSONL"

usage() {
  echo "Usage: $0 list|next|run <id>|report" >&2
  exit 2
}

done_ids() {
  python3 - "$STATUS_JSONL" "$CYCLE" <<'PY'
import json, sys
path, cycle = sys.argv[1], sys.argv[2]
seen = set()
try:
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        if str(r.get("cycle")) == str(cycle) and r.get("result") == "ok":
            seen.add(r.get("id", ""))
except FileNotFoundError:
    pass
print("\n".join(sorted(seen)))
PY
}

catalog_rows() {
  python3 - "$CATALOG" "$CYCLE" "$SET" <<'PY'
import csv, sys
path, cycle, sel = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path, newline="") as f:
    rows = [r for r in csv.DictReader(f, delimiter="\t") if r.get("id") and not r["id"].startswith("#")]
for r in rows:
    cycles = {c.strip() for c in r["cycles"].split(",") if c.strip()}
    if cycle not in cycles:
        continue
    if sel != "all" and r["set"] != sel:
        continue
    print("\t".join([r["id"], r["set"], r["wallet"], r["op"], r["snap"], r.get("flags", "") or "-", r.get("comment", "")]))
PY
}

cmd_list() {
  echo "CYCLE=$CYCLE SET=$SET"
  echo "id	set	wallet	op	snap	flags	comment"
  catalog_rows
  echo "--- done this cycle ---"
  done_ids
}

next_id() {
  local done
  done=$(done_ids)
  while IFS=$'\t' read -r id _rest; do
    [ -n "$id" ] || continue
    if ! printf '%s\n' "$done" | grep -qx "$id"; then
      echo "$id"
      return 0
    fi
  done < <(catalog_rows)
  return 1
}

wallet_file_for() {
  case "$1" in
    none) echo "" ;;
    p0)
      [ -n "${ZERO_PERF_WALLET_P0:-}" ] || { echo "ERROR: set ZERO_PERF_WALLET_P0" >&2; return 1; }
      echo "$ZERO_PERF_WALLET_P0"
      ;;
    p1)
      [ -n "${ZERO_PERF_WALLET_P1:-}" ] || { echo "ERROR: set ZERO_PERF_WALLET_P1" >&2; return 1; }
      echo "$ZERO_PERF_WALLET_P1"
      ;;
    fat)
      [ -n "${ZERO_PERF_WALLET_FAT:-}" ] || { echo "ERROR: set ZERO_PERF_WALLET_FAT" >&2; return 1; }
      echo "$ZERO_PERF_WALLET_FAT"
      ;;
    *) echo "ERROR: unknown wallet $1" >&2; return 1 ;;
  esac
}

extra_from_flags() {
  local flags="$1"
  local extra=""
  case "$flags" in
    -|"") ;;
    noteidx) extra="-walletwitnessnote=1" ;;
    defer) extra="-walletwitness=ibd-defer" ;;
    noteidx+defer) extra="-walletwitness=ibd-defer -walletwitnessnote=1" ;;
    *) echo "ERROR: unknown flags $flags" >&2; return 1 ;;
  esac
  echo "$extra"
}

snap_heights() {
  case "$1" in
    tiny) echo "0 187417" ;;
    short) echo "0 245992" ;;
    window) echo "50000 75000" ;;
    full|tip) echo "0 0" ;;
    *) echo "0 0" ;;
  esac
}

append_status() {
  python3 - "$STATUS_JSONL" "$CYCLE" "$1" "$2" "$3" "$4" <<'PY'
import json, sys
from datetime import datetime, timezone
path, cycle, tid, result, run_id, notes = sys.argv[1:7]
row = {
    "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "cycle": cycle,
    "id": tid,
    "result": result,
    "run_id": run_id,
    "notes": notes,
}
with open(path, "a") as f:
    f.write(json.dumps(row, sort_keys=True) + "\n")
PY
}

ledger_append() {
  local run_id="$1" mode="$2" condition="$3" h0="$4" h1="$5" elapsed="$6"
  if [ -z "$elapsed" ] || [ "$elapsed" = "NA" ]; then
    echo "ledger skip (no elapsed) id=$condition" >&2
    return 0
  fi
  local blocks=0 bps=0
  if [ "$h1" -gt "$h0" ] 2>/dev/null; then
    blocks=$((h1 - h0))
    bps=$(python3 -c "print(round($blocks / float($elapsed), 4) if float($elapsed) else 0)")
  else
    blocks=0
    bps=0
  fi
  python3 "$REPO_ROOT/contrib/perf/accumulate_bench.py" --store-dir "$STORE_DIR" \
    --append \
    --campaign "cycle-${CYCLE}" \
    --run-id "$run_id" \
    --mode "$mode" \
    --condition "$condition" \
    --trial 1 \
    --warmup-height "$h0" \
    --end-height "$h1" \
    --blocks "$blocks" \
    --elapsed-s "$elapsed" \
    --blocks-per-sec "$bps" \
    --notes "cycle=$CYCLE id=$condition"
}

elapsed_from_log() {
  local log="$1" h0="$2" h1="$3"
  if [ ! -f "$log" ] || [ "$h1" -le "$h0" ]; then
    echo NA
    return 0
  fi
  python3 "$REPO_ROOT/contrib/perf/extract_measures.py" --elapsed-heights "$log" "$h0" "$h1" 2>/dev/null || echo NA
}

run_trial() {
  local id="$1"
  local row
  row=$(python3 - "$CATALOG" "$id" <<'PY'
import csv, sys
want = sys.argv[2]
with open(sys.argv[1], newline="") as f:
    for r in csv.DictReader(f, delimiter="\t"):
        if r.get("id") == want:
            print("\t".join([r["wallet"], r["op"], r["snap"], r.get("flags","") or "-", r.get("comment","")]))
            break
    else:
        raise SystemExit("unknown id %s" % want)
PY
)
  local wallet op snap flags
  IFS=$'\t' read -r wallet op snap flags _comment <<<"$row"
  local extra wf
  extra=$(extra_from_flags "$flags")
  local hpair h0 h1
  hpair=$(snap_heights "$snap")
  h0=${hpair%% *}
  h1=${hpair##* }
  local run_id="cycle${CYCLE}-${id}-$(date -u +%Y%m%dT%H%M%SZ)"
  echo "RUN trial=$id cycle=$CYCLE wallet=$wallet op=$op snap=$snap flags=$flags run_id=$run_id"

  export ZERO_PERF_RPCPORT="${ZERO_PERF_RPCPORT:-23957}"
  export CAMPAIGN="cycle-${CYCLE}"
  local rc=0
  case "$wallet:$op:$snap" in
    none:reindex:tiny|none:reindex:short)
      export LAB="${ZERO_PERF_SCRATCH_DATADIR:-$REPO_ROOT/reindex-profile/cycle-datadir}"
      mkdir -p "$LAB"
      contrib/perf/run_tiny_baseline.sh "$snap" || rc=$?
      if [ -f "$LAB/debug.log" ]; then
        local el
        el=$(elapsed_from_log "$LAB/debug.log" "$h0" "$h1")
        ledger_append "$run_id" reindex "$id" "$h0" "$h1" "$el"
      fi
      ;;
    none:bootstrap:window)
      if [ -z "${LOADBLOCK:-}" ] || [ ! -f "$LOADBLOCK" ]; then
        echo "ERROR: nowallet-bootstrap-presap needs LOADBLOCK=/path/to/bootstrap.dat copy" >&2
        return 1
      fi
      N_TRIALS=1 MODE=bootstrap LOADBLOCK="$LOADBLOCK" \
        WARMUP_HEIGHT=50000 MEASURE_BLOCKS=25000 \
        CAMPAIGN="cycle-${CYCLE}" \
        ZERO_PERF_SCRATCH_DATADIR="${ZERO_PERF_SCRATCH_DATADIR:-$REPO_ROOT/reindex-profile/cycle-datadir}" \
        contrib/perf/run_postsapling_baseline.sh || rc=$?
      ;;
    *:reindex:tiny|*:reindex:short|*:reindex:full)
      wf=$(wallet_file_for "$wallet")
      ZERO_PERF_WALLET_FILE="$wf" ZERO_PERF_CHAIN_SNAP="$snap" \
        ZEROD_EXTRA_ARGS="$extra" \
        ZERO_PERF_SCRATCH_DATADIR="${ZERO_PERF_SCRATCH_DATADIR:-$REPO_ROOT/reindex-profile/cycle-datadir}" \
        contrib/perf/run_wallet_sync_profile.sh || rc=$?
      local scratch="${ZERO_PERF_SCRATCH_DATADIR:-$REPO_ROOT/reindex-profile/cycle-datadir}"
      if [ -f "$scratch/debug.log" ] && [ "$h1" -gt 0 ]; then
        local el
        el=$(elapsed_from_log "$scratch/debug.log" "$h0" "$h1")
        ledger_append "$run_id" reindex "$id" "$h0" "$h1" "$el"
      fi
      ;;
    *:rescan:tiny|*:rescan:short|*:rescan:full)
      wf=$(wallet_file_for "$wallet")
      local wmode=rescan
      case "$flags" in
        noteidx|noteidx+defer) wmode=rescan-noteidx ;;
      esac
      ZERO_PERF_WALLET_FILE="$wf" ZERO_PERF_CHAIN_SNAP="$snap" \
        ZERO_PERF_SCRATCH_DATADIR="${ZERO_PERF_SCRATCH_DATADIR:-$REPO_ROOT/reindex-profile/cycle-datadir}" \
        contrib/perf/run_witness_lab.sh "$wmode" || rc=$?
      local scratch="${ZERO_PERF_SCRATCH_DATADIR:-$REPO_ROOT/reindex-profile/cycle-datadir}"
      if [ -f "$scratch/debug.log" ]; then
        local el
        if [ "$h1" -gt 0 ]; then
          el=$(elapsed_from_log "$scratch/debug.log" "$h0" "$h1")
        else
          el=$(python3 -c "import re,pathlib; t=pathlib.Path('$scratch/debug.log').read_text(errors='replace'); m=re.search(r'rescan\\s+([0-9]+)ms', t); print(round(int(m.group(1))/1000,3) if m else 'NA')")
        fi
        ledger_append "$run_id" rescan "$id" "$h0" "$h1" "$el"
      fi
      ;;
    *:sync:tiny|*:sync:short)
      wf=$(wallet_file_for "$wallet")
      local wmode=catchup
      case "$flags" in
        noteidx|noteidx+defer) wmode=catchup-noteidx ;;
      esac
      ZERO_PERF_WALLET_FILE="$wf" ZERO_PERF_CHAIN_SNAP="$snap" \
        ZERO_PERF_SCRATCH_DATADIR="${ZERO_PERF_SCRATCH_DATADIR:-$REPO_ROOT/reindex-profile/cycle-datadir}" \
        contrib/perf/run_witness_lab.sh "$wmode" || rc=$?
      local el
      el=$(python3 - "$REPO_ROOT/test-logs" "$wmode" <<'PY'
import glob, os, re, sys
root, mode = sys.argv[1], sys.argv[2]
cands = sorted(glob.glob(os.path.join(root, "witness-lab-%s*/SUMMARY.txt" % mode)))
if not cands:
    print("NA")
    raise SystemExit
t = open(cands[-1]).read()
m = re.search(r"wall_s=(\d+)", t)
print(m.group(1) if m else "NA")
PY
)
      ledger_append "$run_id" catchup "$id" "$h0" "$h1" "$el"
      ;;
    *:sync:tip)
      wf=$(wallet_file_for "$wallet")
      local wmode=tip-catchup
      case "$flags" in
        noteidx|noteidx+defer) wmode=tip-catchup-note ;;
      esac
      ZERO_PERF_WALLET_FILE="$wf" \
        ZERO_PERF_SCRATCH_DATADIR="${ZERO_PERF_SCRATCH_DATADIR:-$REPO_ROOT/reindex-profile/cycle-datadir}" \
        contrib/perf/run_witness_lab.sh "$wmode" || rc=$?
      ledger_append "$run_id" catchup "$id" 0 0 0
      ;;
    *)
      echo "ERROR: no dispatcher for wallet=$wallet op=$op snap=$snap" >&2
      return 1
      ;;
  esac

  if [ "$rc" -eq 0 ]; then
    append_status "$id" ok "$run_id" ""
    echo "OK $id"
  else
    append_status "$id" fail "$run_id" "rc=$rc"
    echo "FAIL $id rc=$rc" >&2
  fi
  return "$rc"
}

case "$CMD" in
  list) cmd_list ;;
  next)
    nid=$(next_id) || { echo "all trials in SET=$SET CYCLE=$CYCLE are done"; exit 0; }
    echo "next=$nid"
    run_trial "$nid"
    ;;
  run)
    [ -n "$TRIAL_ID" ] || usage
    run_trial "$TRIAL_ID"
    ;;
  report)
    python3 "$REPO_ROOT/contrib/perf/collate_cycle.py" --store-dir "$STORE_DIR" \
      --status "$STATUS_JSONL" \
      --md "$STATUS_DIR/REPORT-cycle.md"
    ;;
  *) usage ;;
esac
